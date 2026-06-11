import re
import socket
import requests
import random
from typing import List, Optional

# ─────────────────────────────────────────────
# 1. PROXY ROUTING SYSTEM
# ─────────────────────────────────────────────
def fetch_proxies() -> List[dict]:
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lines = r.text.splitlines()
            return [{"http": f"http://{p}", "https": f"http://{p}"} for p in lines if p.strip()]
    except:
        pass
    return []

# ─────────────────────────────────────────────
# 2. DOMAIN & IP OSINT CLIENTS
# ─────────────────────────────────────────────
def perform_whois(domain: str) -> str:
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0].split(":")[0]
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4.0)
        s.connect(("whois.iana.org", 43))
        s.send((domain + "\r\n").encode("utf-8"))
        response = b""
        while True:
            data = s.recv(4096)
            if not data:
                break
            response += data
        s.close()
        
        resp_str = response.decode('utf-8', errors='ignore')
        
        refer_server = None
        for line in resp_str.splitlines():
            line = line.strip()
            if line.startswith("refer:"):
                refer_server = line.split(":", 1)[1].strip()
                break
                
        if not refer_server:
            tld = domain.split(".")[-1]
            if tld == "com" or tld == "net":
                refer_server = "whois.verisign-grs.com"
            elif tld == "org":
                refer_server = "whois.pir.org"
            elif tld == "edu":
                refer_server = "whois.educause.edu"
            else:
                refer_server = f"whois.nic.{tld}"
                
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.settimeout(4.0)
        s2.connect((refer_server, 43))
        query = domain + "\r\n"
        if "verisign" in refer_server:
            query = "= " + domain + "\r\n"
        s2.send(query.encode("utf-8"))
        
        refer_response = b""
        while True:
            data = s2.recv(4096)
            if not data:
                break
            refer_response += data
        s2.close()
        return refer_response.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"WHOIS Query for '{domain}' failed:\nCould not query WHOIS registrar. (Error: {str(e)})"

def get_geoip_info(ip: str) -> dict:
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

# ─────────────────────────────────────────────
# 3. USERNAME HEURISTICS & FOOTPRINT SCANNER
# ─────────────────────────────────────────────
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
