import streamlit as st
import requests
import pandas as pd
import concurrent.futures
import random
import datetime
import urllib.parse
import sqlite3
import re

# ─────────────────────────────────────────────
# 1. DATABASE & CASE MANAGEMENT (SQLite)
# ─────────────────────────────────────────────
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

def create_case(case_name):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO cases (name, created_at) VALUES (?, ?)", (case_name.strip(), ts))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def get_cases():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT name FROM cases ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def save_finding(case_name, category, label, value):
    if not case_name or case_name == "-- Select Active Case --":
        return
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO findings (case_name, category, label, value, timestamp) VALUES (?, ?, ?, ?, ?)",
              (case_name, category, label, str(value), ts))
    conn.commit()
    conn.close()

def get_findings(case_name):
    if not case_name or case_name == "-- Select Active Case --":
        return []
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT category, label, value, timestamp FROM findings WHERE case_name = ? ORDER BY id DESC", (case_name,))
    rows = c.fetchall()
    conn.close()
    return [{"Category": r[0], "Label": r[1], "Value": r[2], "Timestamp": r[3]} for r in rows]

init_db()

# ─────────────────────────────────────────────
# 2. PROXY ROUTING SYSTEM
# ─────────────────────────────────────────────
if "proxies" not in st.session_state:
    st.session_state.proxies = []

def fetch_proxies():
    url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lines = r.text.splitlines()
            return [{"http": f"http://{p}", "https": f"http://{p}"} for p in lines if p.strip()]
    except:
        return []

def get_random_proxy():
    return random.choice(st.session_state.proxies) if st.session_state.proxies else None

# ─────────────────────────────────────────────
# 3. UPGRADED CONCURRENCY PLATFORM CONFIG
# ─────────────────────────────────────────────
# Format: Name -> (URL_Template, [Not_Found_Strings], Category)
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

def check_platform(name, username, proxy):
    url_tpl, not_found_strs, category = PLATFORMS[name]
    url = url_tpl.format(username)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, timeout=6, headers=headers, proxies=proxy, allow_redirects=True)
        if r.status_code != 200:
            return None
            
        # Parse body for signature checks (false positive prevention)
        body_lower = r.text.lower()
        if any(err_str.lower() in body_lower for err_str in not_found_strs):
            return None
            
        return {"Platform": name, "Category": category, "Status": "Active Profile", "URL": url}
    except:
        pass
    return None

# ─────────────────────────────────────────────
# 4. EMAIL HEURISTIC GENERATOR
# ─────────────────────────────────────────────
def generate_username_guesses(email):
    """Derives a rich set of username candidates from an email address local-part"""
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

    # Ensure output has unique handles with lengths of 3 or more characters
    return list(dict.fromkeys(g for g in guesses if g and len(g) >= 3))

# ─────────────────────────────────────────────
# 5. INSTAGRAM INTELLIGENCE CORE
# ─────────────────────────────────────────────
def get_ig_user_id(username):
    try:
        url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data['graphql']['user']['id']
    except:
        return "Manual Verification Required (API Rate-Limited)"

def generate_environment_dorks(username):
    encoded = urllib.parse.quote(username)
    return {
        "Tagged Photo Ecosystem": f'site:instagram.com "{username}" -site:instagram.com/{encoded}',
        "Comments Tracking": f'site:instagram.com "from {username}" OR "comment" "{username}"',
        "Leaked Associated Contact Info": f'site:instagram.com "{username}" "@gmail.com" OR "contact" OR "+1"',
        "Web Mentions (Cross-Platform)": f'"{username}" site:facebook.com OR site:twitter.com OR site:linkedin.com',
        "Archived/Cached Snapshots": f'cache:https://www.instagram.com/{encoded}'
    }

def get_opsec_viewers(username):
    return {
        "View Stories Anonymously (StoryNavigation)": f"https://storynavigation.com/user/{username}",
        "View Posts & Reels Safely (Imginn)": f"https://imginn.com/user/{username}",
        "Deep Search (Dumpor)": f"https://dumpor.com/v/{username}"
    }

# ─────────────────────────────────────────────
# 6. STREAMLIT LAYOUT & CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    .stMetric { background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #21262d; }
    .stButton>button { border-radius: 6px; background-color: #8a3ab9 !important; color: white !important; font-weight: bold; }
    .stAlert { border-radius: 6px; }
    </style>
    """, unsafe_allow_html=True)

# SIDEBAR: Investigator's Dashboard
with st.sidebar:
    st.title("📸 IG INT Core")
    st.info("Direct and Environmental Analysis framework for Instagram Targets.")
    
    st.divider()
    
    st.subheader("📁 Case File Registry")
    new_case = st.text_input("Create Investigation File", placeholder="e.g. Case_2026_IG_Target")
    if st.button("Initialize Case File"):
        if new_case:
            create_case(new_case)
            st.success(f"File created: '{new_case}'")
            st.rerun()

    cases = get_cases()
    active_case = st.selectbox("Active Case Target Profile", ["-- Select Active Case --"] + cases)
    
    st.divider()
    
    st.subheader("🌐 Stealth Proxy Controls")
    if st.button("🔄 Scrape & Cycle Proxy Pool"):
        st.session_state.proxies = fetch_proxies()
        st.success(f"Refreshed {len(st.session_state.proxies)} proxies!")
    
    st.write(f"**Stealth Mode:** {'✅ Active (Rotating)' if st.session_state.proxies else '⚠️ Direct IP (No Proxy)'}")

# EXECUTIVE DASHBOARD HEADER
st.title("📸 Specialized Instagram Intelligence Framework")
st.markdown("---")

col1, col2, col3 = st.columns(3)
col1.metric("Active Case Target", active_case if active_case != "-- Select Active Case --" else "Unlinked", delta_color="off")
col2.metric("Recorded Findings", len(get_findings(active_case)) if active_case != "-- Select Active Case --" else "0")
col3.metric("Proxy Pool Size", f"{len(st.session_state.proxies)} IPs" if st.session_state.proxies else "Direct IP")

st.markdown("---")

# SYSTEM WORKSPACE TABS
tab1, tab_email, tab2, tab3, tab4 = st.tabs([
    "🔐 Direct Target profiling", 
    "📧 Email to Username",
    "🕸️ Profile Environment Scanner", 
    "🌐 Cross-Platform Digital Footprint",
    "📁 Case Vault Reporting"
])

# 🔐 DIRECT TARGET PROFILING
with tab1:
    st.header("Direct Target Investigation & Keys")
    
    # Check if a username was loaded from the Email tab session state
    suggested_username = st.session_state.get("derived_username_choice", "")
    target_ig = st.text_input("Target Instagram Username", value=suggested_username, placeholder="e.g. j_doe", key="direct_ig")
    
    if target_ig:
        target_ig = target_ig.replace("@", "").strip()
        st.write("---")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("🔑 Persistent Key Resolution")
            uid = get_ig_user_id(target_ig)
            st.info(f"**Permanent Numerical User ID:** `{uid}`")
            save_finding(active_case, "Instagram Metadata", "Permanent UserID", uid)
            st.caption("💡 Key Concept: If the target renames their account to evade detection, this numerical ID remains constant.")
            
        with col_right:
            st.subheader("🛡️ OpSec-Safe Anonymous Mirrors")
            st.write("Examine target assets without logging in, bypassing story 'view receipts' and account tracking:")
            mirrors = get_opsec_viewers(target_ig)
            for label, url in mirrors.items():
                st.markdown(f"🔗 [{label}]({url})")
                save_finding(active_case, "Anonymous Mirrors", label, url)

# 📧 EMAIL TO USERNAME HEURISTICS
with tab_email:
    st.header("Email-to-Username Analysis")
    st.write("Construct username candidates from an email's local part structure and audit validation logs.")
    
    input_email = st.text_input("Target Email Address", placeholder="e.g. john.doe99@gmail.com")
    
    if input_email:
        if "@" in input_email:
            st.write("---")
            col_em_l, col_em_r = st.columns(2)
            
            with col_em_l:
                st.subheader("💡 Username Candidates")
                st.write("Heuristic handle permutations generated from the email structure. Click a suggestion to load it globally:")
                
                candidates = generate_username_guesses(input_email)
                
                for candidate in candidates:
                    # Clicking a button stores the candidate in st.session_state so tabs 1, 3, and 4 can use it
                    if st.button(f"🎯 Try @{candidate}", key=f"cand_{candidate}"):
                        st.session_state["derived_username_choice"] = candidate
                        st.success(f"Loaded handle @{candidate}. Go to other tabs to perform intelligence operations.")
                        st.rerun()
                        
            with col_em_r:
                st.subheader("🛠️ Quick Mail Environment Verification")
                st.write("Checking email structure and routing configuration properties.")
                domain = input_email.split("@")[-1]
                
                try:
                    # Validate domain is ready for mail operations
                    import dns.resolver
                    records = dns.resolver.resolve(domain, 'MX')
                    st.success(f"Domain Validation: @{domain} is actively configured to receive messages.")
                    for r in records:
                        save_finding(active_case, "Email Pivot Data", f"MX Domain Server: {domain}", str(r.exchange))
                except Exception:
                    st.error(f"Domain Error: @{domain} lacks valid MX routing records. This email host may be non-operational.")
        else:
            st.error("Please provide a valid email structure containing '@'.")

# 🕸️ PROFILE ENVIRONMENT SCANNER
with tab2:
    st.header("Profile Environment Scanner")
    st.write("Bypass target-controlled privacy configurations by scanning the outer ecosystem [8].")
    
    suggested_env_username = st.session_state.get("derived_username_choice", "")
    target_env = st.text_input("Target Instagram Username", value=suggested_env_username, placeholder="e.g. j_doe", key="env_ig")
    
    if target_env:
        target_env = target_env.replace("@", "").strip()
        st.write("---")
        
        col_l, col_r = st.columns(2)
        
        with col_l:
            st.subheader("🕸️ Associated Environment Analysis")
            st.write("Audit how other profiles interact with or mention the target [8]:")
            
            dorks = generate_environment_dorks(target_env)
            for label, dork_string in dorks.items():
                st.write(f"**{label}**")
                st.code(dork_string, language="bash")
                g_url = f"https://www.google.com/search?q={urllib.parse.quote(dork_string)}"
                st.link_button(f"Query {label} Caches", g_url)
                save_finding(active_case, "Profile Environment Dorks", label, dork_string)
                
        with col_r:
            st.subheader("🗺️ Geographical & Activity Correlator")
            st.write("Cross-reference the username with physical environments to pinpoint patterns of life:")
            
            search_city = st.text_input("Target Location tag filter (e.g. London)", placeholder="Miami")
            if search_city:
                geo_dork = f'site:instagram.com "{target_env}" "{search_city}"'
                st.code(geo_dork, language="bash")
                g_geo_url = f"https://www.google.com/search?q={urllib.parse.quote(geo_dork)}"
                st.link_button(f"Search Tagged Media in {search_city}", g_geo_url)
                save_finding(active_case, "Geotag Correlation", f"City Check: {search_city}", geo_dork)

# 🌐 UPGRADED CROSS-PLATFORM DIGITAL FOOTPRINT SCANNER
with tab3:
    st.header("Advanced Digital Footprint Scan")
    st.write("Trace target-handle deployment across multiple domains using real-time content verification.")
    
    suggested_cross_username = st.session_state.get("derived_username_choice", "")
    target_cross = st.text_input("Target Instagram Username", value=suggested_cross_username, placeholder="e.g. j_doe", key="cross_ig")
    
    # Category filter configuration
    available_categories = sorted(list(set(p[2] for p in PLATFORMS.values())))
    selected_categories = st.multiselect("Scan Categories Filter (Leave empty to scan all)", available_categories)
    
    if target_cross:
        target_cross = target_cross.replace("@", "").strip()
        st.write("---")
        
        # Filter platform list based on user choices
        platforms_to_scan = [
            name for name, data in PLATFORMS.items() 
            if not selected_categories or data[2] in selected_categories
        ]
        
        if st.button("Start High-Precision Scan"):
            results = []
            progress = st.progress(0)
            status = st.empty()
            
            # Placeholders to stream live data
            st.subheader("⚡ Live Finding Streams")
            live_table_placeholder = st.empty()
            
            # Thread pooling and executing
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(check_platform, name, target_cross, get_random_proxy()): name 
                    for name in platforms_to_scan
                }
                
                for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    if res:
                        results.append(res)
                        save_finding(active_case, "Cross Platform Profile", res["Platform"], res["URL"])
                        
                        # Dynamically update the output frame with active results
                        live_table_placeholder.dataframe(pd.DataFrame(results), use_container_width=True)
                    
                    # Update progress metric
                    progress_pct = (idx + 1) / len(platforms_to_scan)
                    progress.progress(progress_pct)
                    status.text(f"Auditing Environment: {idx + 1}/{len(platforms_to_scan)} networks checked...")
            
            if results:
                st.success(f"Execution complete. Identified {len(results)} active profile structures!")
            else:
                live_table_placeholder.empty()
                st.warning("No matches detected. Platform structures returned no valid environmental signs.")

# 📁 CASE VAULT REPORTING
with tab4:
    st.header("Investigation File Repository")
    if active_case != "-- Select Active Case --":
        findings = get_findings(active_case)
        if findings:
            df = pd.DataFrame(findings)
            st.dataframe(df, use_container_width=True)
            
            # Export CSV Action
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Evidence CSV Ledger",
                data=csv,
                file_name=f"IG_INT_LEDGER_{active_case}.csv",
                mime="text/csv"
            )
        else:
            st.info("No compiled findings saved to this Case File yet.")
    else:
        st.warning("Please select or initialize an active case target file in the sidebar to review logs.")