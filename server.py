import sqlite3
import datetime
import random
import re
import urllib.parse
import concurrent.futures
import requests
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

# Database path
DB_FILE = "ig_int_vault.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cases 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS findings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, case_name TEXT, category TEXT, label TEXT, value TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="📸 IG INT Core OSINT API", version="2.0.0")

# In-memory proxy list shared state
proxies_pool = []

# Platform mappings for footprint scanning
PLATFORMS = {
    "GitHub": ("https://github.com/{}", ["Not Found", "404"], "Developer"),
    "Twitter/X": ("https://twitter.com/{}", ["doesn't exist", "page doesn't exist"], "Social"),
    "Reddit": ("https://www.reddit.com/user/{}", ["user not found", "page not found"], "Social"),
    "TikTok": ("https://www.tiktok.com/@{}", ["Couldn't find this account", "notfound"], "Social"),
    "Pinterest": ("https://www.pinterest.com/{}", ["couldn't find that page", "resource_not_found"], "Social"),
    "Twitch": ("https://www.twitch.tv/{}", ["unavailable", "page is unavailable"], "Gaming/Video"),
    "Dev.to": ("https://dev.to/{}", ["404", "page not found"], "Developer"),
    "Keybase": ("https://keybase.io/{}", ["not found", "\"them\":null"], "Developer"),
    "Medium": ("https://medium.com/@{}", ["404", "page not found", "out of order"], "Blogging"),
    "Spotify": ("https://open.spotify.com/user/{}", ["not found", "404"], "Entertainment"),
    "Steam": ("https://steamcommunity.com/id/{}", ["The specified profile could not be found"], "Gaming/Video"),
    "Linktree": ("https://linktr.ee/{}", ["404", "page not found"], "Social"),
    "Flickr": ("https://www.flickr.com/photos/{}", ["page not found", "404"], "Entertainment"),
    "Letterboxd": ("https://letterboxd.com/{}", ["404", "not found"], "Entertainment"),
    "Vimeo": ("https://vimeo.com/{}", ["not found", "404"], "Gaming/Video"),
    "SoundCloud": ("https://soundcloud.com/{}", ["not found", "404"], "Entertainment"),
}

# --- Database Helper Functions ---

def create_case_db(case_name: str) -> bool:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    success = False
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO cases (name, created_at) VALUES (?, ?)", (case_name.strip(), ts))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return success

def get_cases_db() -> List[str]:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT name FROM cases ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def save_finding_db(case_name: str, category: str, label: str, value: str):
    if not case_name or case_name == "-- Select Active Case --":
        return
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO findings (case_name, category, label, value, timestamp) VALUES (?, ?, ?, ?, ?)",
              (case_name, category, label, str(value), ts))
    conn.commit()
    conn.close()

def get_findings_db(case_name: str) -> List[dict]:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT category, label, value, timestamp FROM findings WHERE case_name = ? ORDER BY id DESC", (case_name,))
    rows = c.fetchall()
    conn.close()
    return [{"category": r[0], "label": r[1], "value": r[2], "timestamp": r[3]} for r in rows]

# --- Models ---

class CaseCreate(BaseModel):
    name: str

class FindingCreate(BaseModel):
    category: str
    label: str
    value: str

class EmailInput(BaseModel):
    email: str
    case_name: Optional[str] = None

class InstagramInput(BaseModel):
    username: str
    case_name: Optional[str] = None

class GeotagInput(BaseModel):
    username: str
    city: str
    case_name: Optional[str] = None

class ScanInput(BaseModel):
    username: str
    categories: List[str] = []
    case_name: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/cases")
def get_cases():
    return {"cases": get_cases_db()}

@app.post("/api/cases")
def create_case(case: CaseCreate):
    name_clean = case.name.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Case name cannot be empty.")
    success = create_case_db(name_clean)
    if not success:
        raise HTTPException(status_code=400, detail="Case already exists.")
    return {"status": "success", "message": f"Case '{name_clean}' created successfully."}

@app.get("/api/cases/{case_name}/findings")
def get_findings(case_name: str):
    return {"findings": get_findings_db(case_name)}

@app.post("/api/cases/{case_name}/findings")
def create_finding(case_name: str, finding: FindingCreate):
    save_finding_db(case_name, finding.category, finding.label, finding.value)
    return {"status": "success"}

# --- Proxies ---

@app.post("/api/proxies/refresh")
def refresh_proxies():
    global proxies_pool
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lines = r.text.splitlines()
            proxies_pool = [{"http": f"http://{p}", "https": f"http://{p}"} for p in lines if p.strip()]
            return {"status": "success", "count": len(proxies_pool)}
        else:
            raise HTTPException(status_code=502, detail="Failed to fetch proxies from API provider.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/proxies/status")
def get_proxy_status():
    return {
        "active": len(proxies_pool) > 0,
        "count": len(proxies_pool)
    }

def get_random_proxy():
    global proxies_pool
    return random.choice(proxies_pool) if proxies_pool else None

# --- Username Candidates Generator ---

def generate_username_guesses(email: str) -> List[str]:
    local = email.split("@")[0]
    suffix = (re.search(r"\d+$", local) or type("", (), {"group": lambda s, x: ""})()).group(0)
    base = re.sub(r"\d+$", "", local)
    parts = re.split(r"[._\-]", base)
    clean = "".join(parts)

    guesses = [
        local, clean + suffix, base, clean,
        "_".join(parts), ".".join(parts),
        "".join(reversed(parts)), ".".join(reversed(parts)),
        "_".join(reversed(parts)), clean + "official", clean + "_official",
        "the" + clean, clean + "real", clean + "ig", clean + "yt",
        "_" + clean, clean + "_",
    ]
    if len(parts) >= 2:
        guesses += [parts[0] + parts[1][0], parts[0][0] + parts[1]]

    return list(dict.fromkeys(g for g in guesses if g and len(g) >= 3))

@app.post("/api/email-heuristics")
def email_heuristics(payload: EmailInput):
    email = payload.email.strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email formatting.")
    
    candidates = generate_username_guesses(email)
    domain = email.split("@")[-1]
    
    mx_status = "Unknown"
    mx_servers = []
    
    try:
        import dns.resolver
        records = dns.resolver.resolve(domain, 'MX')
        mx_status = "Active"
        for r in records:
            srv = str(r.exchange).strip(".")
            mx_servers.append(srv)
            if payload.case_name:
                save_finding_db(payload.case_name, "Email Pivot Data", f"MX Domain Server: {domain}", srv)
    except Exception as e:
        mx_status = f"Failed/Inactive ({str(e)})"
        
    return {
        "candidates": candidates,
        "domain": domain,
        "mx_status": mx_status,
        "mx_servers": mx_servers
    }

# --- Instagram Intelligence Core ---

def get_ig_user_id(username: str) -> str:
    try:
        url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return str(data['graphql']['user']['id'])
    except:
        pass
    return "Manual Verification Required (API Rate-Limited)"

def get_opsec_viewers(username: str) -> dict:
    return {
        "View Stories Anonymously (StoryNavigation)": f"https://storynavigation.com/user/{username}",
        "View Posts & Reels Safely (Imginn)": f"https://imginn.com/user/{username}",
        "Deep Search (Dumpor)": f"https://dumpor.com/v/{username}"
    }

@app.post("/api/instagram/profile")
def instagram_profile(payload: InstagramInput):
    username = payload.username.replace("@", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
        
    uid = get_ig_user_id(username)
    mirrors = get_opsec_viewers(username)
    
    if payload.case_name:
        save_finding_db(payload.case_name, "Instagram Metadata", "Permanent UserID", uid)
        for label, url in mirrors.items():
            save_finding_db(payload.case_name, "Anonymous Mirrors", label, url)

            
    return {
        "username": username,
        "user_id": uid,
        "mirrors": [{"label": k, "url": v} for k, v in mirrors.items()]
    }

@app.post("/api/instagram/environment")
def instagram_environment(payload: InstagramInput):
    username = payload.username.replace("@", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
        
    encoded = urllib.parse.quote(username)
    dorks = {
        "Tagged Photo Ecosystem": f'site:instagram.com "{username}" -site:instagram.com/{encoded}',
        "Comments Tracking": f'site:instagram.com "from {username}" OR "comment" "{username}"',
        "Leaked Associated Contact Info": f'site:instagram.com "{username}" "@gmail.com" OR "contact" OR "+1"',
        "Web Mentions (Cross-Platform)": f'"{username}" site:facebook.com OR site:twitter.com OR site:linkedin.com',
        "Archived/Cached Snapshots": f'cache:https://www.instagram.com/{encoded}'
    }
    
    if payload.case_name:
        for label, dork_string in dorks.items():
            save_finding_db(payload.case_name, "Profile Environment Dorks", label, dork_string)
            
    return {
        "username": username,
        "dorks": [{"label": k, "query": v, "url": f"https://www.google.com/search?q={urllib.parse.quote(v)}"} for k, v in dorks.items()]
    }

@app.post("/api/instagram/geotag")
def instagram_geotag(payload: GeotagInput):
    username = payload.username.replace("@", "").strip()
    city = payload.city.strip()
    if not username or not city:
        raise HTTPException(status_code=400, detail="Username and City are required")
        
    geo_dork = f'site:instagram.com "{username}" "{city}"'
    url = f"https://www.google.com/search?q={urllib.parse.quote(geo_dork)}"
    
    if payload.case_name:
        save_finding_db(payload.case_name, "Geotag Correlation", f"City Check: {city}", geo_dork)
        
    return {
        "username": username,
        "city": city,
        "dork": geo_dork,
        "url": url
    }

# --- Cross-Platform Footprint Scan ---

def check_platform(name: str, username: str, proxy: Optional[dict]) -> Optional[dict]:
    url_tpl, not_found_strs, category = PLATFORMS[name]
    url = url_tpl.format(username)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, timeout=6, headers=headers, proxies=proxy, allow_redirects=True)
        if r.status_code != 200:
            return None
            
        body_lower = r.text.lower()
        if any(err_str.lower() in body_lower for err_str in not_found_strs):
            return None
            
        return {"platform": name, "category": category, "status": "Active Profile", "url": url}
    except:
        pass
    return None

@app.post("/api/scan")
def footprint_scan(payload: ScanInput):
    username = payload.username.replace("@", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
        
    # Get filtered platforms list
    platforms_to_scan = []
    for name, data in PLATFORMS.items():
        if not payload.categories or data[2] in payload.categories:
            platforms_to_scan.append(name)
            
    results = []
    
    # Thread pool configuration
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(check_platform, name, username, get_random_proxy()): name 
            for name in platforms_to_scan
        }
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                if payload.case_name:
                    save_finding_db(payload.case_name, "Cross Platform Profile", res["platform"], res["url"])
                    
    return {"results": results, "scanned_count": len(platforms_to_scan)}


# --- Case Relation Graph API ---

@app.get("/api/cases/{case_name}/graph")
def get_case_graph(case_name: str):
    findings = get_findings_db(case_name)
    nodes = []
    edges = []
    
    # Root node is the case
    nodes.append({
        "id": "case_root",
        "label": f"📂 Case: {case_name}",
        "group": "case",
        "title": f"Investigation Case File: {case_name}"
    })
    
    # Track unique items to prevent duplicate nodes
    added_nodes = {"case_root"}
    
    for f in findings:
        cat = f["category"]
        lbl = f["label"]
        val = f["value"]
        
        if cat == "Instagram Metadata" and lbl == "Permanent UserID":
            target_node = "ig_target"
            if target_node not in added_nodes:
                nodes.append({
                    "id": target_node,
                    "label": "📸 Target Profile",
                    "group": "target",
                    "title": "Primary Target Instagram Account"
                })
                edges.append({"from": "case_root", "to": target_node, "label": "investigates"})
                added_nodes.add(target_node)
                
            if not val.startswith("Manual Verification Required"):
                uid_node = f"uid_{val}"
                if uid_node not in added_nodes:
                    nodes.append({
                        "id": uid_node,
                        "label": f"🆔 UID: {val}",
                        "group": "uid",
                        "title": f"Permanent numerical ID: {val}"
                    })
                    edges.append({"from": target_node, "to": uid_node, "label": "resolves"})
                    added_nodes.add(uid_node)
                
        elif cat == "Cross Platform Profile":
            target_node = "ig_target"
            if target_node not in added_nodes:
                nodes.append({
                    "id": target_node,
                    "label": "📸 Target Profile",
                    "group": "target",
                    "title": "Primary Target Instagram Account"
                })
                edges.append({"from": "case_root", "to": target_node, "label": "investigates"})
                added_nodes.add(target_node)
                
            platform_node = f"plat_{lbl}"
            if platform_node not in added_nodes:
                nodes.append({
                    "id": platform_node,
                    "label": f"🌐 {lbl}",
                    "group": "platform",
                    "title": f"Active URL: {val}"
                })
                edges.append({"from": target_node, "to": platform_node, "label": "handle reuse"})
                added_nodes.add(platform_node)
                
        elif cat == "Email Pivot Data":
            domain = lbl.replace("MX Domain Server: ", "")
            email_node = f"email_{domain}"
            if email_node not in added_nodes:
                nodes.append({
                    "id": email_node,
                    "label": f"📧 @{domain}",
                    "group": "email",
                    "title": f"Target Email Domain: {domain}"
                })
                edges.append({"from": "case_root", "to": email_node, "label": "associated email"})
                added_nodes.add(email_node)
                
            srv_node = f"srv_{val}"
            if srv_node not in added_nodes:
                nodes.append({
                    "id": srv_node,
                    "label": f"🖥️ {val}",
                    "group": "server",
                    "title": f"MX Mail Server: {val}"
                })
                edges.append({"from": email_node, "to": srv_node, "label": "mx routing"})
                added_nodes.add(srv_node)
                
        elif cat == "Geotag Correlation":
            city = lbl.replace("City Check: ", "")
            city_node = f"city_{city}"
            
            target_node = "ig_target"
            if target_node not in added_nodes:
                nodes.append({
                    "id": target_node,
                    "label": "📸 Target Profile",
                    "group": "target",
                    "title": "Primary Target Instagram Account"
                })
                edges.append({"from": "case_root", "to": target_node, "label": "investigates"})
                added_nodes.add(target_node)
                
            if city_node not in added_nodes:
                nodes.append({
                    "id": city_node,
                    "label": f"📍 {city}",
                    "group": "geotag",
                    "title": f"Geotag check: {city}"
                })
                edges.append({"from": target_node, "to": city_node, "label": "geotag correlation"})
                added_nodes.add(city_node)

        elif cat == "Anonymous Mirrors":
            target_node = "ig_target"
            if target_node not in added_nodes:
                nodes.append({
                    "id": target_node,
                    "label": "📸 Target Profile",
                    "group": "target",
                    "title": "Primary Target Instagram Account"
                })
                edges.append({"from": "case_root", "to": target_node, "label": "investigates"})
                added_nodes.add(target_node)
            
            mirror_node = f"mirror_{lbl}"
            if mirror_node not in added_nodes:
                # Clean mirror label a bit
                clean_lbl = lbl.split("(")[0].strip()
                nodes.append({
                    "id": mirror_node,
                    "label": f"🕶️ {clean_lbl}",
                    "group": "mirror",
                    "title": f"Anonymous viewer mirror URL: {val}"
                })
                edges.append({"from": target_node, "to": mirror_node, "label": "view proxy"})
                added_nodes.add(mirror_node)
                
    return {"nodes": nodes, "edges": edges}

# --- Static File Serving ---

# Main entry page
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# Mount directories (Make sure static folder exists)
app.mount("/static", StaticFiles(directory="static"), name="static")

