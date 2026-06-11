import streamlit as st
import requests
import pandas as pd
import concurrent.futures
import random
import urllib.parse
import re
import socket
import dns.resolver

# Import shared OSINT and DB routines
from backend.database import init_db, create_case, get_cases, save_finding, get_findings, DB_FILE
from backend.osint import (
    fetch_proxies, perform_whois, get_geoip_info, PLATFORMS, check_platform, generate_username_guesses
)

# Initialize database
init_db()

# ─────────────────────────────────────────────
# 1. STREAMLIT LAYOUT & CUSTOM CSS
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="ONSINT Core Dashboard")

st.markdown("""
    <style>
    .stMetric { background-color: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #21262d; }
    .stButton>button { border-radius: 6px; background-color: #4361ee !important; color: white !important; font-weight: bold; }
    .stAlert { border-radius: 6px; }
    </style>
    """, unsafe_allow_html=True)

# SIDEBAR: Investigator's Dashboard
with st.sidebar:
    st.title("📡 ONSINT Core")
    st.info("General Purpose OSINT Intelligence Dashboard")
    
    st.divider()
    
    st.subheader("📁 Case File Registry")
    new_case = st.text_input("Create Investigation File", placeholder="e.g. Case_2026_Global_Audit")
    if st.button("Initialize Case File"):
        if new_case:
            create_case(new_case)
            st.success(f"File created: '{new_case}'")
            st.rerun()

    cases = get_cases()
    active_case = st.selectbox("Active Case Target", ["-- Select Active Case --"] + cases)
    
    st.divider()
    
    st.subheader("🌐 Stealth Proxy Controls")
    if st.button("🔄 Scrape & Cycle Proxy Pool"):
        st.session_state.proxies = fetch_proxies()
        st.success(f"Refreshed {len(st.session_state.proxies)} proxies!")
    
    st.write(f"**Stealth Mode:** {'✅ Active (Rotating)' if st.session_state.proxies else '⚠️ Direct IP (No Proxy)'}")
    st.divider()
    st.markdown("<p style='font-size:0.8rem; color:#94a3b8; font-weight:500;'><i class='fa-solid fa-user-ninja' style='color:#9d4edd; margin-right:0.25rem;'></i> Made by <strong>Ronit Gupta</strong></p>", unsafe_allow_html=True)

# EXECUTIVE DASHBOARD HEADER
st.title("📡 ONSINT Core Intelligence Suite")
st.markdown("---")

col1, col2, col3 = st.columns(3)
col1.metric("Active Case File", active_case if active_case != "-- Select Active Case --" else "Unlinked", delta_color="off")
col2.metric("Recorded Findings", len(get_findings(active_case)) if active_case != "-- Select Active Case --" else "0")
col3.metric("Proxy Pool Size", f"{len(st.session_state.proxies)} IPs" if st.session_state.proxies else "Direct IP")

st.markdown("---")

# SYSTEM WORKSPACE TABS
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👤 Username Search", 
    "🖥️ Domain & IP Intel",
    "📧 Email Intel",
    "📞 Phone Resolver",
    "🛠️ Dork Studio",
    "📁 Case Vault Reporting"
])

def get_random_proxy():
    return random.choice(st.session_state.proxies) if st.session_state.proxies else None

# 👤 USERNAME SEARCH
with tab1:
    st.header("Username & Digital Footprint Scan")
    st.write("Scan handle deployments across developer, social, and entertainment network endpoints.")
    
    suggested_username = st.session_state.get("derived_username_choice", "")
    target_username = st.text_input("Audit Username Handle", value=suggested_username, placeholder="e.g. john_doe")
    
    available_categories = sorted(list(set(p[2] for p in PLATFORMS.values())))
    selected_categories = st.multiselect("Scan Categories Filter (Leave empty to scan all)", available_categories, key="uname_cats")
    
    if target_username:
        target_username = target_username.replace("@", "").strip()
        
        platforms_to_scan = [
            name for name, data in PLATFORMS.items() 
            if not selected_categories or data[2] in selected_categories
        ]
        
        if st.button("Start High-Precision Scan"):
            results = []
            progress = st.progress(0)
            status = st.empty()
            
            st.subheader("⚡ Live Finding Streams")
            live_table_placeholder = st.empty()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(check_platform, name, target_username, get_random_proxy()): name 
                    for name in platforms_to_scan
                }
                
                for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                    res = future.result()
                    if res:
                        # Normalize key name for visual consistency in Streamlit dataframe
                        res_fmt = {"Platform": res["platform"], "Category": res["category"], "Status": res["status"], "URL": res["url"]}
                        results.append(res_fmt)
                        save_finding(active_case, "Cross Platform Profile", f"{res['platform']} ({target_username})", res["url"])
                        
                        live_table_placeholder.dataframe(pd.DataFrame(results), use_container_width=True)
                    
                    progress_pct = (idx + 1) / len(platforms_to_scan)
                    progress.progress(progress_pct)
                    status.text(f"Auditing Environment: {idx + 1}/{len(platforms_to_scan)} networks checked...")
            
            if results:
                st.success(f"Execution complete. Identified {len(results)} active profile structures!")
            else:
                live_table_placeholder.empty()
                st.warning("No matches detected. Platform structures returned no valid environmental signs.")

# 🖥️ DOMAIN & IP INTEL
with tab2:
    st.header("Domain & IP Address Intelligence")
    st.write("Resolve DNS records, fetch WHOIS registrar details, and geolocate IP network endpoints.")
    
    dom_col1, dom_col2 = st.columns(2)
    
    with dom_col1:
        st.subheader("DNS & WHOIS Lookup")
        domain_input = st.text_input("Enter Target Domain", placeholder="e.g. example.com")
        if st.button("Query Domain Info"):
            if domain_input:
                domain_clean = domain_input.strip()
                
                # Resolve DNS
                dns_records = {}
                record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME']
                for rtype in record_types:
                    try:
                        answers = dns.resolver.resolve(domain_clean, rtype)
                        dns_records[rtype] = [str(r).strip(".") for r in answers]
                        for val in dns_records[rtype]:
                            save_finding(active_case, "DNS Record", f"{rtype} Record ({domain_clean})", val)
                    except:
                        dns_records[rtype] = []
                
                # Fetch WHOIS
                whois_raw = perform_whois(domain_clean)
                registrar = "Unknown"
                creation_date = "Unknown"
                for line in whois_raw.splitlines():
                    line_lower = line.lower()
                    if "registrar:" in line_lower and registrar == "Unknown":
                        registrar = line.split(":", 1)[1].strip()
                    elif "creation date:" in line_lower and creation_date == "Unknown":
                        creation_date = line.split(":", 1)[1].strip()
                        
                if registrar != "Unknown":
                    save_finding(active_case, "Domain WHOIS", f"Registrar ({domain_clean})", registrar)
                if creation_date != "Unknown":
                    save_finding(active_case, "Domain WHOIS", f"Created Date ({domain_clean})", creation_date)
                
                st.success("Analysis complete. Saved records to active case vault.")
                
                # Render DNS Results
                st.markdown("### DNS records")
                for rtype, records in dns_records.items():
                    if records:
                        st.markdown(f"**{rtype} Record:**")
                        for r in records:
                            st.code(r)
                
                # Render WHOIS Results
                st.markdown("### WHOIS Summary")
                st.write(f"**Registrar:** {registrar}")
                st.write(f"**Created On:** {creation_date}")
                with st.expander("Show Raw WHOIS Log"):
                    st.code(whois_raw)
                    
    with dom_col2:
        st.subheader("IP Address Geolocation")
        ip_input = st.text_input("Enter Target IP or Hostname", placeholder="e.g. 8.8.8.8")
        if st.button("Geolocate Network Node"):
            if ip_input:
                ip_clean = ip_input.strip()
                geoip = get_geoip_info(ip_clean)
                
                if not geoip or geoip.get("status") == "fail":
                    try:
                        resolved = socket.gethostbyname(ip_clean)
                        geoip = get_geoip_info(resolved)
                        ip_clean = resolved
                    except:
                        pass
                
                if geoip and geoip.get("status") != "fail":
                    city = geoip.get("city", "Unknown")
                    country = geoip.get("country", "Unknown")
                    isp = geoip.get("isp", "Unknown")
                    lat = geoip.get("lat", 0.0)
                    lon = geoip.get("lon", 0.0)
                    org = geoip.get("org", "Unknown")
                    
                    save_finding(active_case, "IP GeoIP", f"Location ({ip_clean})", f"{city}, {country}")
                    save_finding(active_case, "IP GeoIP", f"ISP ({ip_clean})", isp)
                    save_finding(active_case, "IP GeoIP", f"Coordinates ({ip_clean})", f"{lat}, {lon}")
                    
                    st.success(f"IP geolocated successfully.")
                    st.write(f"**Coordinates:** `{lat}, {lon}`")
                    st.write(f"**City:** {city}")
                    st.write(f"**Country:** {country}")
                    st.write(f"**ISP Provider:** {isp}")
                    st.write(f"**Organization:** {org}")
                    st.link_button("View on Google Maps", f"https://www.google.com/maps/search/?api=1&query={lat},{lon}")
                else:
                    st.error("Failed to fetch Geolocation records for this node.")

# 📧 EMAIL INTEL
with tab3:
    st.header("Email Intelligence & Heuristic Candidates")
    st.write("Analyze email hosts, extract handle guesses, and search leak networks.")
    
    input_email = st.text_input("Target Email Address", placeholder="e.g. john.doe99@gmail.com")
    
    if input_email:
        if "@" in input_email:
            col_em_l, col_em_r = st.columns(2)
            
            with col_em_l:
                st.subheader("💡 Username Candidates")
                st.write("Permutation handles derived from local email structure. Click a choice to select for profile scanning:")
                
                candidates = generate_username_guesses(input_email)
                for candidate in candidates:
                    if st.button(f"🎯 Use @{candidate}", key=f"cand_{candidate}"):
                        st.session_state["derived_username_choice"] = candidate
                        st.success(f"Loaded handle @{candidate}. Switch to Username tab to scan.")
                        st.rerun()
                        
            with col_em_r:
                st.subheader("🛠️ Mail Host Resolution")
                domain = input_email.split("@")[-1]
                
                mx_servers = []
                try:
                    records = dns.resolver.resolve(domain, 'MX')
                    st.success(f"Host Configured: @{domain} actively routing mail.")
                    for r in records:
                        srv = str(r.exchange).strip(".")
                        mx_servers.append(srv)
                        st.write(f"🖥️ Exchange Server: `{srv}`")
                        save_finding(active_case, "Email Intel", f"MX Route ({input_email})", srv)
                except Exception:
                    st.error(f"Host Route Error: @{domain} lacks active MX records.")
                    
                st.subheader("🔍 Leak Audit Queries")
                dorks = {
                    "Email Leak Search": f'"{input_email}" filetype:txt OR filetype:csv OR filetype:sql',
                    "Credential Dumps": f'"{input_email}" site:pastebin.com OR site:controlc.com OR site:rentry.co',
                    "Public Mentions": f'"{input_email}" site:github.com OR site:gitlab.com OR site:bitbucket.org'
                }
                for label, query_str in dorks.items():
                    st.markdown(f"**{label}**")
                    st.code(query_str)
                    st.link_button(f"Search {label}", f"https://www.google.com/search?q={urllib.parse.quote(query_str)}")
                    save_finding(active_case, "Email Leak Dorks", f"{label} ({input_email})", query_str)
        else:
            st.error("Please provide a valid email format.")

# 📞 PHONE RESOLVER
with tab4:
    st.header("Phone Decoder & Prefix Validator")
    st.write("Validate international formats, decode country tags, and generate exposure dorks.")
    
    phone_input = st.text_input("Enter Target Phone", placeholder="e.g. +1 (555) 123-4567")
    phone_cc = st.selectbox("Default Region Prefix", ["-- Auto-detect --", "1 (US/Canada)", "44 (UK)", "91 (India)", "61 (Australia)", "33 (France)", "49 (Germany)"])
    
    if st.button("Decode Target Phone"):
        if phone_input:
            clean_phone = re.sub(r"[^\d+]", "", phone_input)
            if not clean_phone.startswith("+") and phone_cc != "-- Auto-detect --":
                cc = phone_cc.split(" ")[0]
                clean_phone = f"+{cc}{clean_phone}"
            elif not clean_phone.startswith("+"):
                clean_phone = f"+{clean_phone}"
                
            detected_country = "Unknown/Global"
            country_prefixes = {
                "1": "United States/Canada", "44": "United Kingdom", "91": "India", 
                "61": "Australia", "33": "France", "49": "Germany", "81": "Japan"
            }
            for prefix, name in country_prefixes.items():
                if clean_phone.startswith(f"+{prefix}"):
                    detected_country = name
                    break
                    
            save_finding(active_case, "Phone Intel", f"Details ({clean_phone})", f"Country: {detected_country}")
            
            st.success("Phone parsed successfully.")
            st.write(f"**Formatted number:** `{clean_phone}`")
            st.write(f"**Detected Region:** {detected_country}")
            
            st.subheader("🔍 Phone Mentions Queries")
            dorks = {
                "Web Mentions": f'"{clean_phone}" OR "{phone_input}"',
                "Leaked Spreadsheets": f'("{clean_phone}" OR "{phone_input}") filetype:xls OR filetype:xlsx OR filetype:csv',
                "Social Postings": f'("{clean_phone}" OR "{phone_input}") site:facebook.com OR site:twitter.com OR site:linkedin.com'
            }
            for label, query_str in dorks.items():
                st.markdown(f"**{label}**")
                st.code(query_str)
                st.link_button(f"Search {label}", f"https://www.google.com/search?q={urllib.parse.quote(query_str)}")
                save_finding(active_case, "Phone OSINT Dorks", f"{label} ({clean_phone})", query_str)

# 🛠️ DORK STUDIO
with tab5:
    st.header("Search Engine Dorking Studio")
    st.write("Construct targeted parameters to find open indices, leaks, and server configuration files.")
    
    dork_target = st.text_input("Dork Query Target", placeholder="e.g. company.com or username123")
    dork_type = st.selectbox("Target Entity Type", ["Domain (company.com)", "Username/Handle", "Email Address", "Organization Name"])
    
    if st.button("Build Dork Studio Logs"):
        if dork_target:
            ttype = dork_type.split(" ")[0].lower()
            dorks = []
            
            if ttype == "domain":
                dorks = [
                    {"label": "Directory Listings", "query": f'site:{dork_target} intitle:"index of"'},
                    {"label": "Sensitive Formats", "query": f'site:{dork_target} filetype:pdf OR filetype:doc OR filetype:xls'},
                    {"label": "DB & Backup files", "query": f'site:{dork_target} filetype:sql OR filetype:db OR filetype:bak'},
                    {"label": "Config & Env variables", "query": f'site:{dork_target} filetype:env OR filetype:conf OR filetype:config'},
                    {"label": "Subdomain discovery", "query": f'site:*.{dork_target} -site:www.{dork_target}'}
                ]
            elif ttype == "username":
                dorks = [
                    {"label": "Social Mentions", "query": f'"{dork_target}" site:facebook.com OR site:twitter.com OR site:linkedin.com'},
                    {"label": "Developer Repos", "query": f'"{dork_target}" site:github.com OR site:gitlab.com'},
                    {"label": "Public Leak pastes", "query": f'"{dork_target}" site:pastebin.com OR site:controlc.com'}
                ]
            elif ttype == "email":
                dorks = [
                    {"label": "Credential leaks", "query": f'"{dork_target}" filetype:txt OR filetype:csv OR filetype:sql'},
                    {"label": "Pastebin logs", "query": f'"{dork_target}" site:pastebin.com OR site:controlc.com'}
                ]
            else:
                dorks = [
                    {"label": "S3 Cloud buckets", "query": f'"{dork_target}" site:amazonaws.com OR site:googleapis.com'},
                    {"label": "Staff profiles", "query": f'site:linkedin.com/in/ "{dork_target}"'}
                ]
                
            for dk in dorks:
                st.markdown(f"**{dk['label']}**")
                st.code(dk['query'])
                st.link_button(f"Run {dk['label']}", f"https://www.google.com/search?q={urllib.parse.quote(dk['query'])}")
                save_finding(active_case, "Google Dorks Studio", f"{dk['label']} ({dork_target})", dk['query'])
            st.success("Dorks generated and logged to vault.")

# 📁 CASE VAULT REPORTING
with tab6:
    st.header("Case Evidence File Repository")
    if active_case != "-- Select Active Case --":
        findings = get_findings(active_case)
        if findings:
            # Map database keys to visual table headers
            df = pd.DataFrame(findings)
            df.columns = ["Category", "Label", "Value", "Timestamp"]
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Evidence CSV Ledger",
                data=csv,
                file_name=f"ONSINT_LEDGER_{active_case}.csv",
                mime="text/csv"
            )
        else:
            st.info("No compiled findings saved to this Case File yet.")
    else:
        st.warning("Please select or initialize an active case target file in the sidebar to review logs.")