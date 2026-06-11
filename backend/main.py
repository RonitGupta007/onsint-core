import datetime
import random
import re
import socket
import urllib.parse
import concurrent.futures
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

# Import local backend routines
from backend.database import init_db, create_case, get_cases, save_finding, get_findings
from backend.osint import (
    fetch_proxies, perform_whois, get_geoip_info, PLATFORMS, check_platform, generate_username_guesses
)

# Initialize database
init_db()

app = FastAPI(title="📡 ONSINT General Purpose OSINT API", version="3.0.0")

# In-memory proxy list shared state
proxies_pool = []

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

class DomainInput(BaseModel):
    domain: str
    case_name: Optional[str] = None

class IPInput(BaseModel):
    ip: str
    case_name: Optional[str] = None

class PhoneInput(BaseModel):
    phone: str
    country_code: Optional[str] = None
    case_name: Optional[str] = None

class DorkInput(BaseModel):
    target: str
    target_type: str  # "domain", "username", "email", "organization"
    case_name: Optional[str] = None

class ScanInput(BaseModel):
    username: str
    categories: List[str] = []
    case_name: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/cases")
def get_cases_endpoint():
    return {"cases": get_cases()}

@app.post("/api/cases")
def create_case_endpoint(case: CaseCreate):
    name_clean = case.name.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Case name cannot be empty.")
    success = create_case(name_clean)
    if not success:
        raise HTTPException(status_code=400, detail="Case already exists.")
    return {"status": "success", "message": f"Case '{name_clean}' created successfully."}

@app.get("/api/cases/{case_name}/findings")
def get_findings_endpoint(case_name: str):
    return {"findings": get_findings(case_name)}

@app.post("/api/cases/{case_name}/findings")
def create_finding_endpoint(case_name: str, finding: FindingCreate):
    save_finding(case_name, finding.category, finding.label, finding.value)
    return {"status": "success"}

# --- Proxies ---

@app.post("/api/proxies/refresh")
def refresh_proxies_endpoint():
    global proxies_pool
    proxies = fetch_proxies()
    if proxies:
        proxies_pool = proxies
        return {"status": "success", "count": len(proxies_pool)}
    else:
        raise HTTPException(status_code=502, detail="Failed to fetch proxies from API provider.")

@app.get("/api/proxies/status")
def get_proxy_status():
    return {
        "active": len(proxies_pool) > 0,
        "count": len(proxies_pool)
    }

def get_random_proxy():
    global proxies_pool
    return random.choice(proxies_pool) if proxies_pool else None

# --- Domain & IP Intel ---

@app.post("/api/domain/dns")
def lookup_dns(payload: DomainInput):
    domain = payload.domain.strip()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain cannot be empty")
        
    import dns.resolver
    records_dict = {}
    record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME']
    
    for rtype in record_types:
        try:
            answers = dns.resolver.resolve(domain, rtype)
            records_dict[rtype] = [str(r).strip(".") for r in answers]
            if payload.case_name:
                for val in records_dict[rtype]:
                    save_finding(payload.case_name, "DNS Record", f"{rtype} Record ({domain})", val)
        except Exception:
            records_dict[rtype] = []
            
    return {"domain": domain, "records": records_dict}

@app.post("/api/domain/whois")
def lookup_whois(payload: DomainInput):
    domain = payload.domain.strip()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain cannot be empty")
        
    raw_whois = perform_whois(domain)
    
    registrar = "Unknown"
    creation_date = "Unknown"
    for line in raw_whois.splitlines():
        line_lower = line.lower()
        if "registrar:" in line_lower and registrar == "Unknown":
            registrar = line.split(":", 1)[1].strip()
        elif "creation date:" in line_lower and creation_date == "Unknown":
            creation_date = line.split(":", 1)[1].strip()
        elif "created:" in line_lower and creation_date == "Unknown":
            creation_date = line.split(":", 1)[1].strip()
            
    if payload.case_name:
        if registrar != "Unknown":
            save_finding(payload.case_name, "Domain WHOIS", f"Registrar ({domain})", registrar)
        if creation_date != "Unknown":
            save_finding(payload.case_name, "Domain WHOIS", f"Created Date ({domain})", creation_date)
            
    return {
        "domain": domain,
        "registrar": registrar,
        "creation_date": creation_date,
        "raw": raw_whois
    }

@app.post("/api/ip/geoip")
def lookup_geoip(payload: IPInput):
    ip = payload.ip.strip()
    if not ip:
        raise HTTPException(status_code=400, detail="IP address cannot be empty")
        
    geoip_data = get_geoip_info(ip)
    if not geoip_data or geoip_data.get("status") == "fail":
        try:
            resolved_ip = socket.gethostbyname(ip)
            geoip_data = get_geoip_info(resolved_ip)
            ip = resolved_ip
        except Exception:
            pass
            
    if not geoip_data or geoip_data.get("status") == "fail":
        raise HTTPException(status_code=400, detail=f"Failed to lookup IP/Domain GeoIP for {ip}")
        
    city = geoip_data.get("city", "Unknown")
    country = geoip_data.get("country", "Unknown")
    isp = geoip_data.get("isp", "Unknown")
    lat = geoip_data.get("lat", 0.0)
    lon = geoip_data.get("lon", 0.0)
    org = geoip_data.get("org", "Unknown")
    
    if payload.case_name:
        save_finding(payload.case_name, "IP GeoIP", f"Location ({ip})", f"{city}, {country}")
        save_finding(payload.case_name, "IP GeoIP", f"ISP ({ip})", isp)
        save_finding(payload.case_name, "IP GeoIP", f"Coordinates ({ip})", f"{lat}, {lon}")
        
    return {
        "ip": ip,
        "city": city,
        "country": country,
        "isp": isp,
        "org": org,
        "lat": lat,
        "lon": lon
    }

# --- Email Intel ---

@app.post("/api/email/analyze")
def analyze_email(payload: EmailInput):
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
                save_finding(payload.case_name, "Email Intel", f"MX Route ({email})", srv)
    except Exception as e:
        mx_status = f"Failed/Inactive ({str(e)})"
        
    dorks = {
        "Email Leak Search": f'"{email}" filetype:txt OR filetype:csv OR filetype:sql',
        "Credential Dumps": f'"{email}" site:pastebin.com OR site:controlc.com OR site:rentry.co',
        "Public Mentions": f'"{email}" site:github.com OR site:gitlab.com OR site:bitbucket.org'
    }
    
    if payload.case_name:
        for label, dork in dorks.items():
            save_finding(payload.case_name, "Email Leak Dorks", f"{label} ({email})", dork)

    return {
        "candidates": candidates,
        "domain": domain,
        "mx_status": mx_status,
        "mx_servers": mx_servers,
        "dorks": [{"label": k, "query": v, "url": f"https://www.google.com/search?q={urllib.parse.quote(v)}"} for k, v in dorks.items()]
    }

# Legacy endpoint fallback
@app.post("/api/email-heuristics")
def email_heuristics(payload: EmailInput):
    return analyze_email(payload)

# --- Phone Intel ---

@app.post("/api/phone/analyze")
def analyze_phone(payload: PhoneInput):
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
        
    clean_phone = re.sub(r"[^\d+]", "", phone)
    if not clean_phone.startswith("+") and payload.country_code:
        cc = re.sub(r"\D", "", payload.country_code)
        clean_phone = f"+{cc}{clean_phone}"
    elif not clean_phone.startswith("+"):
        clean_phone = f"+{clean_phone}"
        
    formatted = clean_phone
    detected_country = "Unknown/Global"
    
    country_prefixes = {
        "1": "United States/Canada",
        "44": "United Kingdom",
        "91": "India",
        "61": "Australia",
        "33": "France",
        "49": "Germany",
        "81": "Japan",
        "86": "China",
        "55": "Brazil",
        "7": "Russia",
        "34": "Spain",
        "39": "Italy",
        "971": "United Arab Emirates",
        "65": "Singapore",
    }
    
    for prefix, cname in sorted(country_prefixes.items(), key=lambda x: len(x[0]), reverse=True):
        if clean_phone.startswith(f"+{prefix}"):
            detected_country = cname
            break
            
    dorks = {
        "Web Mentions": f'"{clean_phone}" OR "{phone}"',
        "Leaked Excel/CSV files": f'("{clean_phone}" OR "{phone}") filetype:xls OR filetype:xlsx OR filetype:csv',
        "Social Media Mentions": f'("{clean_phone}" OR "{phone}") site:facebook.com OR site:twitter.com OR site:linkedin.com',
        "Public Paste Logs": f'("{clean_phone}" OR "{phone}") site:pastebin.com OR site:controlc.com'
    }
    
    if payload.case_name:
        save_finding(payload.case_name, "Phone Intel", f"Details ({clean_phone})", f"Country: {detected_country}")
        for k, v in dorks.items():
            save_finding(payload.case_name, "Phone OSINT Dorks", f"{k} ({clean_phone})", v)
            
    return {
        "phone": clean_phone,
        "country": detected_country,
        "formatted": formatted,
        "dorks": [{"label": k, "query": v, "url": f"https://www.google.com/search?q={urllib.parse.quote(v)}"} for k, v in dorks.items()]
    }

# --- Search Dorks Studio ---

@app.post("/api/dorks/generate")
def generate_dorks_api(payload: DorkInput):
    target = payload.target.strip()
    ttype = payload.target_type.strip().lower()
    
    if not target:
        raise HTTPException(status_code=400, detail="Target value is required")
        
    dorks = []
    
    if ttype == "domain":
        dorks = [
            {"label": "Directory Listings (Open Indexes)", "query": f'site:{target} intitle:"index of"', "desc": "Finds files and folders exposed on web servers."},
            {"label": "Sensitive File Formats", "query": f'site:{target} filetype:pdf OR filetype:doc OR filetype:xls OR filetype:xlsx OR filetype:ppt', "desc": "Locates PDF, Word, and Excel files exposed on the domain."},
            {"label": "Database & Backup Leaks", "query": f'site:{target} filetype:sql OR filetype:db OR filetype:bak OR filetype:tar OR filetype:zip', "desc": "Finds backups, database files, and zip files."},
            {"label": "Configuration & Env Files", "query": f'site:{target} filetype:env OR filetype:conf OR filetype:config OR filetype:xml OR filetype:json', "desc": "Finds exposed database credentials, config files, and environmental keys."},
            {"label": "Subdomain Enumeration", "query": f'site:*.{target} -site:www.{target}', "desc": "Excludes the primary www domain to uncover hidden subdomains."},
            {"label": "Log & Console Files", "query": f'site:{target} filetype:log OR filetype:txt OR filetype:err', "desc": "Locates application error logs and debug outputs."},
            {"label": "API Endpoints / Swagger", "query": f'site:{target} intext:"swagger" OR intext:"api-docs" OR intext:"redoc"', "desc": "Uncovers API endpoints and documentation pages."}
        ]
    elif ttype == "username":
        dorks = [
            {"label": "Cross-Platform Mentions", "query": f'"{target}" site:facebook.com OR site:twitter.com OR site:instagram.com OR site:linkedin.com', "desc": "Finds mentions of the handle on major social networks."},
            {"label": "Developer Footprint", "query": f'"{target}" site:github.com OR site:gitlab.com OR site:bitbucket.org OR site:stackoverflow.com', "desc": "Finds developer-specific profiles, commits, or repos."},
            {"label": "Forum & Discussion Posts", "query": f'"{target}" site:reddit.com OR site:quora.com OR site:medium.com', "desc": "Checks if the username has made public posts on Reddit or blogging sites."},
            {"label": "Credential Leak paste sites", "query": f'"{target}" site:pastebin.com OR site:controlc.com OR site:rentry.co', "desc": "Checks paste bins for leaks containing the target username."},
            {"label": "Avatar / Image Cache", "query": f'site:instagram.com "{target}" OR site:pinterest.com "{target}"', "desc": "Checks image platforms for target handle associations."}
        ]
    elif ttype == "email":
        dorks = [
            {"label": "Public Leak Logs", "query": f'"{target}" filetype:txt OR filetype:csv OR filetype:sql', "desc": "Finds database dumps and plaintext leaks."},
            {"label": "Pastebin Credentials", "query": f'"{target}" site:pastebin.com OR site:controlc.com', "desc": "Finds login credentials or lists associated with the email address."},
            {"label": "Government or Education Mentions", "query": f'"{target}" site:gov OR site:edu', "desc": "Finds associations with government or educational domains."},
            {"label": "General Mentions", "query": f'"{target}" -site:gmail.com -site:outlook.com -site:yahoo.com', "desc": "Searches for the email address outside of its default provider pages."}
        ]
    elif ttype == "organization":
        dorks = [
            {"label": "Public S3 / Cloud Buckets", "query": f'"{target}" site:amazonaws.com OR site:digitaloceanspaces.com OR site:googleapis.com', "desc": "Finds unsecured cloud storage buckets matching the org name."},
            {"label": "Employee Profiles", "query": f'site:linkedin.com/in/ "{target}"', "desc": "Finds employees or staff members claiming association with the org."},
            {"label": "Domain Leaks & Repos", "query": f'"{target}" site:github.com OR site:gitlab.com', "desc": "Finds repositories or code snippets mentioning the organization."}
        ]
        
    for dk in dorks:
        dk["url"] = f"https://www.google.com/search?q={urllib.parse.quote(dk['query'])}"
        if payload.case_name:
            save_finding(payload.case_name, "Google Dorks Studio", f"{dk['label']} ({target})", dk['query'])
            
    return {"target": target, "target_type": ttype, "dorks": dorks}

# --- Cross-Platform Footprint Scan ---

@app.post("/api/scan")
def footprint_scan(payload: ScanInput):
    username = payload.username.replace("@", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
        
    platforms_to_scan = []
    for name, data in PLATFORMS.items():
        if not payload.categories or data[2] in payload.categories:
            platforms_to_scan.append(name)
            
    results = []
    
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
                    save_finding(payload.case_name, "Cross Platform Profile", f"{res['platform']} ({username})", res["url"])
                    
    return {"results": results, "scanned_count": len(platforms_to_scan)}

# --- Case Relation Graph API ---

@app.get("/api/cases/{case_name}/graph")
def get_case_graph(case_name: str):
    findings = get_findings(case_name)
    nodes = []
    edges = []
    
    nodes.append({
        "id": "case_root",
        "label": f"📂 Case: {case_name}",
        "group": "case",
        "title": f"Investigation Case File: {case_name}"
    })
    
    added_nodes = {"case_root"}
    added_edges = set()
    
    def add_node(nid, label, group, title=""):
        if nid not in added_nodes:
            nodes.append({"id": nid, "label": label, "group": group, "title": title or label})
            added_nodes.add(nid)
            
    def add_edge(from_node, to_node, label=""):
        edge_key = f"{from_node}->{to_node}:{label}"
        if edge_key not in added_edges:
            edges.append({"from": from_node, "to": to_node, "label": label})
            added_edges.add(edge_key)

    for f in findings:
        cat = f["category"]
        lbl = f["label"]
        val = f["value"]
        
        if cat == "Cross Platform Profile":
            m = re.search(r"([^(]+)\s*\(([^)]+)\)", lbl)
            if m:
                platform = m.group(1).strip()
                username = m.group(2).strip()
            else:
                platform = lbl.strip()
                username = "Unknown Handle"
                
            user_node = f"user_{username}"
            add_node(user_node, f"👤 {username}", "target", f"Username: {username}")
            add_edge("case_root", user_node, "queries username")
            
            plat_node = f"plat_{platform}_{username}"
            add_node(plat_node, f"🌐 {platform}", "platform", f"Profile URL: {val}")
            add_edge(user_node, plat_node, "profile exists")
            
        elif cat == "DNS Record":
            m = re.search(r"([^(]+)\s*\(([^)]+)\)", lbl)
            if m:
                rtype = m.group(1).strip()
                domain = m.group(2).strip()
            else:
                rtype = lbl.strip()
                domain = "Unknown Domain"
                
            dom_node = f"dom_{domain}"
            add_node(dom_node, f"🖥️ {domain}", "platform", f"Domain under review")
            add_edge("case_root", dom_node, "analyzes domain")
            
            target_val = val.strip()
            if rtype == "A Record" or rtype == "AAAA Record":
                ip_node = f"ip_{target_val}"
                add_node(ip_node, f"🌐 IP: {target_val}", "server", f"IP Address host")
                add_edge(dom_node, ip_node, rtype)
            elif rtype == "MX Record" or rtype == "NS Record" or rtype == "CNAME Record":
                ref_node = f"dom_{target_val}"
                add_node(ref_node, f"🖥️ {target_val}", "platform", f"Referred Host")
                add_edge(dom_node, ref_node, rtype)
            else:
                record_node = f"rec_{rtype}_{domain}_{target_val}"
                add_node(record_node, f"📋 {rtype}: {target_val}", "mirror", val)
                add_edge(dom_node, record_node, "record detail")

        elif cat == "Domain WHOIS":
            m = re.search(r"([^(]+)\s*\(([^)]+)\)", lbl)
            if m:
                property_type = m.group(1).strip()
                domain = m.group(2).strip()
            else:
                property_type = lbl.strip()
                domain = "Unknown Domain"
                
            dom_node = f"dom_{domain}"
            add_node(dom_node, f"🖥️ {domain}", "platform", f"Domain under review")
            add_edge("case_root", dom_node, "analyzes domain")
            
            prop_node = f"whois_{property_type}_{domain}"
            add_node(prop_node, f"ℹ️ WHOIS: {val}", "mirror", f"Property: {property_type}")
            add_edge(dom_node, prop_node, property_type.lower())

        elif cat == "IP GeoIP":
            m = re.search(r"([^(]+)\s*\(([^)]+)\)", lbl)
            if m:
                property_type = m.group(1).strip()
                ip = m.group(2).strip()
            else:
                property_type = lbl.strip()
                ip = "Unknown IP"
                
            ip_node = f"ip_{ip}"
            add_node(ip_node, f"🌐 IP: {ip}", "server", f"IP Address host")
            add_edge("case_root", ip_node, "analyzes IP")
            
            geo_node = f"geo_{val}"
            add_node(geo_node, f"📍 {val}", "geotag", f"GeoIP Details")
            add_edge(ip_node, geo_node, property_type.lower())

        elif cat == "Email Intel":
            m = re.search(r"([^(]+)\s*\(([^)]+)\)", lbl)
            if m:
                property_type = m.group(1).strip()
                email = m.group(2).strip()
            else:
                property_type = lbl.strip()
                email = "Unknown Email"
                
            email_node = f"email_{email}"
            add_node(email_node, f"📧 {email}", "email", f"Email address")
            add_edge("case_root", email_node, "analyzes email")
            
            if "@" in email:
                domain = email.split("@", 1)[-1]
                dom_node = f"dom_{domain}"
                add_node(dom_node, f"🖥️ {domain}", "platform", f"Domain under review")
                add_edge(email_node, dom_node, "belongs to domain")
            
            srv_node = f"dom_{val}"
            add_node(srv_node, f"🖥️ {val}", "platform", f"Mail Server Exchange")
            add_edge(email_node, srv_node, "routes mail via")

        elif cat == "Phone Intel":
            m = re.search(r"([^(]+)\s*\(([^)]+)\)", lbl)
            if m:
                property_type = m.group(1).strip()
                phone = m.group(2).strip()
            else:
                property_type = lbl.strip()
                phone = "Unknown Phone"
                
            phone_node = f"phone_{phone}"
            add_node(phone_node, f"📞 {phone}", "uid", f"Phone number")
            add_edge("case_root", phone_node, "analyzes phone")
            
            info_node = f"phone_info_{phone}_{val}"
            add_node(info_node, f"ℹ️ {val}", "geotag", f"Phone details: {val}")
            add_edge(phone_node, info_node, "phone property")

        elif cat == "Email Pivot Data":
            domain = lbl.replace("MX Domain Server: ", "")
            email_node = f"email_pivot_{domain}"
            add_node(email_node, f"📧 @{domain}", "email", f"Associated Email Domain")
            add_edge("case_root", email_node, "linked email")
            
            srv_node = f"srv_{val}"
            add_node(srv_node, f"🖥️ {val}", "server", f"MX Host")
            add_edge(email_node, srv_node, "routes via")
            
        elif cat in ["Instagram Metadata", "Anonymous Mirrors", "Geotag Correlation", "Profile Environment Dorks"]:
            target_node = "ig_target"
            add_node(target_node, "📸 Target Profile", "target", "Instagram Target Profile")
            add_edge("case_root", target_node, "investigates")
            
            detail_node = f"ig_prop_{cat}_{lbl}_{val}"
            add_node(detail_node, f"ℹ️ {lbl}: {val}", "mirror", val)
            add_edge(target_node, detail_node, cat.lower())

    return {"nodes": nodes, "edges": edges}

# --- Static File Serving ---

@app.get("/")
def read_root():
    return FileResponse("frontend/static/index.html")

# Mount directories (frontend/static folder holds index.html, app.js, style.css)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
