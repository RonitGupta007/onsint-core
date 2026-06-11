// --- GLOBAL STATE ---
const state = {
    activeCase: "",
    targetUsername: "",
    findingsCount: 0,
    proxyCount: 0,
    categories: ["Social", "Developer", "Gaming/Video", "Blogging", "Entertainment"]
};

// --- DOM ELEMENTS ---
const elements = {
    // Sidebar
    newCaseInput: document.getElementById("new-case-name"),
    btnCreateCase: document.getElementById("btn-create-case"),
    activeCaseSelect: document.getElementById("active-case-select"),
    btnRefreshProxies: document.getElementById("btn-refresh-proxies"),
    proxyDot: document.getElementById("proxy-dot"),
    proxyStatusText: document.getElementById("proxy-status-text"),
    proxyCountText: document.getElementById("proxy-count-text"),
    
    // Stats Banner
    statActiveCase: document.getElementById("stat-active-case"),
    statFindingsCount: document.getElementById("stat-findings-count"),
    statProxyStatus: document.getElementById("stat-proxy-status"),
    
    // Tabs Navigation
    tabButtons: document.querySelectorAll(".tab-btn"),
    tabContents: document.querySelectorAll(".tab-content"),
    
    // Tab: Username Search
    footprintUsername: document.getElementById("footprint-username"),
    scanCategoryCheckboxes: document.getElementById("scan-category-checkboxes"),
    btnStartScan: document.getElementById("btn-start-scan"),
    scanProgressFrame: document.getElementById("scan-progress-frame"),
    scanProgressBar: document.getElementById("scan-progress-bar"),
    scanStatusLabel: document.getElementById("scan-status-label"),
    scanResultsCard: document.getElementById("scan-results-card"),
    scanHitsBadge: document.getElementById("scan-hits-badge"),
    scanResultsTbody: document.getElementById("scan-results-tbody"),
    
    // Tab: Domain Intel
    targetDomain: document.getElementById("target-domain"),
    btnFetchDomain: document.getElementById("btn-fetch-domain"),
    domainResultsGrid: document.getElementById("domain-results-grid"),
    dnsRecordsContainer: document.getElementById("dns-records-container"),
    domainRegistrar: document.getElementById("domain-registrar"),
    domainCreated: document.getElementById("domain-created"),
    domainWhoisRaw: document.getElementById("domain-whois-raw"),
    
    // Tab: IP Intel
    targetIp: document.getElementById("target-ip"),
    btnFetchIp: document.getElementById("btn-fetch-ip"),
    ipResultsGrid: document.getElementById("ip-results-grid"),
    ipCoords: document.getElementById("ip-coords"),
    ipCity: document.getElementById("ip-city"),
    ipCountry: document.getElementById("ip-country"),
    ipIsp: document.getElementById("ip-isp"),
    ipOrg: document.getElementById("ip-org"),
    ipMapsLink: document.getElementById("ip-maps-link"),
    
    // Tab: Email Intel
    targetEmail: document.getElementById("target-email"),
    btnFetchEmail: document.getElementById("btn-fetch-email"),
    emailResultsGrid: document.getElementById("email-results-grid"),
    emailCandidatesContainer: document.getElementById("email-candidates-container"),
    emailDomainName: document.getElementById("email-domain-name"),
    emailMxStatus: document.getElementById("email-mx-status"),
    emailMxServers: document.getElementById("email-mx-servers"),
    emailDorksContainer: document.getElementById("email-dorks-container"),
    
    // Tab: Phone Resolver
    targetPhone: document.getElementById("target-phone"),
    phoneCountryCode: document.getElementById("phone-country-code"),
    btnFetchPhone: document.getElementById("btn-fetch-phone"),
    phoneResultsGrid: document.getElementById("phone-results-grid"),
    phoneFormatted: document.getElementById("phone-formatted"),
    phoneCountry: document.getElementById("phone-country"),
    phoneDorksContainer: document.getElementById("phone-dorks-container"),
    
    // Tab: Dork Studio
    dorkTarget: document.getElementById("dork-target"),
    dorkTargetType: document.getElementById("dork-target-type"),
    btnFetchDorks: document.getElementById("btn-fetch-dorks"),
    dorksResultsCard: document.getElementById("dorks-results-card"),
    studioDorksContainer: document.getElementById("studio-dorks-container"),
    
    // Tab: Case Vault
    vaultEmptyBanner: document.getElementById("vault-empty-banner"),
    vaultDataFrame: document.getElementById("vault-data-frame"),
    vaultTableTbody: document.getElementById("vault-table-tbody"),
    btnDownloadCsv: document.getElementById("btn-download-csv"),
    
    // Tab: Connection Graph
    graphEmptyBanner: document.getElementById("graph-empty-banner"),
    graphDataFrame: document.getElementById("graph-data-frame"),
    networkGraph: document.getElementById("network-graph"),
    btnRefreshGraph: document.getElementById("btn-refresh-graph")
};

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initCopyButtons();
    loadCases();
    checkProxyStatus();
    renderCategories();
    initResizableSidebar();
    
    // Sidebar toggle logic for mobile
    const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
    const sidebarEl = document.querySelector(".sidebar");
    const sidebarOverlayEl = document.getElementById("sidebar-overlay");
    
    if (btnToggleSidebar && sidebarEl && sidebarOverlayEl) {
        btnToggleSidebar.addEventListener("click", () => {
            sidebarEl.classList.toggle("open");
            sidebarOverlayEl.classList.toggle("active");
        });
        
        sidebarOverlayEl.addEventListener("click", () => {
            sidebarEl.classList.remove("open");
            sidebarOverlayEl.classList.remove("active");
        });
        
        const tabLinks = document.querySelectorAll(".tab-btn");
        tabLinks.forEach(link => {
            link.addEventListener("click", () => {
                sidebarEl.classList.remove("open");
                sidebarOverlayEl.classList.remove("active");
            });
        });
    }
    
    // Event Listeners
    elements.btnCreateCase.addEventListener("click", handleCreateCase);
    elements.activeCaseSelect.addEventListener("change", handleCaseSelect);
    elements.btnRefreshProxies.addEventListener("click", handleRefreshProxies);
    elements.btnStartScan.addEventListener("click", handleFootprintScan);
    elements.btnFetchDomain.addEventListener("click", handleDomainQuery);
    elements.btnFetchIp.addEventListener("click", handleIpQuery);
    elements.btnFetchEmail.addEventListener("click", handleEmailQuery);
    elements.btnFetchPhone.addEventListener("click", handlePhoneQuery);
    elements.btnFetchDorks.addEventListener("click", handleDorksQuery);
    elements.btnDownloadCsv.addEventListener("click", handleDownloadCSV);
    elements.btnRefreshGraph.addEventListener("click", loadConnectionGraph);
    
    // Automatically keep input targets in sync where relevant
    elements.footprintUsername.addEventListener("input", (e) => {
        state.targetUsername = e.target.value;
    });
});

// --- STATE SYNCING ---
function updateStatsBanner() {
    elements.statActiveCase.innerText = state.activeCase ? state.activeCase : "Unlinked";
    elements.statFindingsCount.innerText = state.findingsCount;
    elements.statProxyStatus.innerText = state.proxyCount > 0 ? `${state.proxyCount} IPs Active` : "Direct Routing";
    
    const hasCase = !!state.activeCase;
    elements.vaultEmptyBanner.style.display = hasCase ? "none" : "flex";
    elements.vaultDataFrame.style.display = hasCase ? "block" : "none";
    elements.graphEmptyBanner.style.display = hasCase ? "none" : "flex";
    elements.graphDataFrame.style.display = hasCase ? "block" : "none";
}

// --- TABS CONTROLS ---
function initTabs() {
    elements.tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            // Toggle active buttons
            elements.tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            // Toggle active content frames
            elements.tabContents.forEach(content => {
                if (content.id === targetTab) {
                    content.classList.add("active");
                } else {
                    content.classList.remove("active");
                }
            });
            
            // Reload specific content if vault/graph is selected
            if (targetTab === "tab-vault") {
                loadVaultFindings();
            } else if (targetTab === "tab-graph") {
                loadConnectionGraph();
            }
        });
    });
}

function switchTab(tabId) {
    const tabBtn = Array.from(elements.tabButtons).find(b => b.getAttribute("data-tab") === tabId);
    if (tabBtn) tabBtn.click();
}

// --- COPY TO CLIPBOARD HELPER ---
function initCopyButtons() {
    document.body.addEventListener("click", (e) => {
        const copyBtn = e.target.closest(".btn-copy");
        if (copyBtn) {
            const targetId = copyBtn.getAttribute("data-copy-target");
            const codeEl = document.getElementById(targetId);
            if (codeEl) {
                navigator.clipboard.writeText(codeEl.innerText.trim()).then(() => {
                    const originalHTML = copyBtn.innerHTML;
                    copyBtn.innerHTML = '<i class="fa-solid fa-check" style="color: #4ade80;"></i>';
                    setTimeout(() => {
                        copyBtn.innerHTML = originalHTML;
                    }, 2000);
                });
            }
        }
    });
}

// --- API ACTIONS ---

// Cases Management
async function loadCases() {
    try {
        const r = await fetch("/api/cases");
        const data = await r.json();
        
        elements.activeCaseSelect.innerHTML = '<option value="">-- Select Active Case --</option>';
        data.cases.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c;
            opt.innerText = c;
            elements.activeCaseSelect.appendChild(opt);
        });
        
        if (state.activeCase) {
            elements.activeCaseSelect.value = state.activeCase;
        }
    } catch (e) {
        console.error("Error loading cases:", e);
    }
}

async function handleCreateCase() {
    const caseName = elements.newCaseInput.value.trim();
    if (!caseName) return;
    
    try {
        const r = await fetch("/api/cases", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: caseName })
        });
        
        if (r.ok) {
            state.activeCase = caseName;
            elements.newCaseInput.value = "";
            await loadCases();
            await refreshFindingsCount();
            updateStatsBanner();
        } else {
            const err = await r.json();
            alert(err.detail || "Failed to create case file.");
        }
    } catch (e) {
        console.error("Error creating case:", e);
    }
}

function handleCaseSelect(e) {
    const val = e.target.value;
    state.activeCase = val;
    refreshFindingsCount();
    updateStatsBanner();
}

async function refreshFindingsCount() {
    if (!state.activeCase) {
        state.findingsCount = 0;
        return;
    }
    try {
        const r = await fetch(`/api/cases/${encodeURIComponent(state.activeCase)}/findings`);
        const data = await r.json();
        state.findingsCount = data.findings.length;
    } catch (e) {
        console.error(e);
    }
}

// Proxy Management
async function checkProxyStatus() {
    try {
        const r = await fetch("/api/proxies/status");
        const data = await r.json();
        state.proxyCount = data.count;
        
        if (data.active) {
            elements.proxyDot.className = "status-dot success";
            elements.proxyStatusText.innerText = "Stealth Mode Active";
            elements.proxyCountText.innerText = `${data.count} IPs Rotated`;
        } else {
            elements.proxyDot.className = "status-dot warning";
            elements.proxyStatusText.innerText = "Direct IP (No Proxy)";
            elements.proxyCountText.innerText = "0 IPs Scraped";
        }
        updateStatsBanner();
    } catch (e) {
        console.error(e);
    }
}

async function handleRefreshProxies() {
    elements.btnRefreshProxies.disabled = true;
    elements.btnRefreshProxies.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scraping...';
    try {
        const r = await fetch("/api/proxies/refresh", { method: "POST" });
        if (r.ok) {
            await checkProxyStatus();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnRefreshProxies.disabled = false;
        elements.btnRefreshProxies.innerHTML = '<i class="fa-solid fa-rotate"></i> Scrape & Cycle Proxies';
    }
}

// Reusable Dork Row Renderer
function renderDorkItem(dk, index, prefix) {
    const item = document.createElement("div");
    item.className = "dork-item";
    
    const meta = document.createElement("div");
    meta.className = "dork-meta";
    meta.innerHTML = `<span class="dork-title">${dk.label}</span>`;
    if (dk.desc) {
        meta.innerHTML += `<span class="description" style="margin-bottom:0; display:block; font-size:0.75rem;">${dk.desc}</span>`;
    }
    
    const queryWrapper = document.createElement("div");
    queryWrapper.className = "dork-query-wrapper";
    
    const codeId = `${prefix}-dork-code-${index}`;
    queryWrapper.innerHTML = `
        <code id="${codeId}">${dk.query}</code>
        <button class="btn btn-copy" data-copy-target="${codeId}">
            <i class="fa-regular fa-copy"></i>
        </button>
        <a href="${dk.url}" target="_blank" class="btn btn-secondary btn-sm">
            <i class="fa-solid fa-square-arrow-up-right"></i> Open Query
        </a>
    `;
    
    item.appendChild(meta);
    item.appendChild(queryWrapper);
    return item;
}

// --- Tab: Username Scan ---
function renderCategories() {
    elements.scanCategoryCheckboxes.innerHTML = "";
    state.categories.forEach(cat => {
        const label = document.createElement("label");
        label.className = "checkbox-btn";
        label.innerHTML = `<input type="checkbox" value="${cat}">${cat}`;
        
        const input = label.querySelector("input");
        input.addEventListener("change", () => {
            if (input.checked) {
                label.classList.add("checked");
            } else {
                label.classList.remove("checked");
            }
        });
        elements.scanCategoryCheckboxes.appendChild(label);
    });
}

async function handleFootprintScan() {
    const username = elements.footprintUsername.value.trim();
    if (!username) return;
    
    const checkedBoxes = elements.scanCategoryCheckboxes.querySelectorAll("input:checked");
    const categoriesSelected = Array.from(checkedBoxes).map(b => b.value);
    
    elements.btnStartScan.disabled = true;
    elements.btnStartScan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning endpoints';
    elements.scanProgressFrame.style.display = "block";
    elements.scanProgressBar.style.width = "0%";
    elements.scanStatusLabel.innerText = "Querying platform endpoints...";
    elements.scanResultsCard.style.display = "none";
    
    let percent = 0;
    const interval = setInterval(() => {
        if (percent < 90) {
            percent += Math.floor(Math.random() * 15) + 5;
            elements.scanProgressBar.style.width = `${Math.min(percent, 90)}%`;
        }
    }, 200);
    
    try {
        const r = await fetch("/api/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: username,
                categories: categoriesSelected,
                case_name: state.activeCase
            })
        });
        
        clearInterval(interval);
        elements.scanProgressBar.style.width = "100%";
        elements.scanStatusLabel.innerText = "Scan Complete.";
        
        if (r.ok) {
            const data = await r.json();
            elements.scanResultsTbody.innerHTML = "";
            elements.scanHitsBadge.innerText = `${data.results.length} Found`;
            
            if (data.results.length > 0) {
                data.results.forEach(res => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${res.platform}</strong></td>
                        <td>${res.category}</td>
                        <td><span class="badge success">Active Profile</span></td>
                        <td><a href="${res.url}" target="_blank" class="table-link"><i class="fa-solid fa-arrow-up-right-from-square"></i> Visit Profile</a></td>
                    `;
                    elements.scanResultsTbody.appendChild(tr);
                });
            } else {
                elements.scanResultsTbody.innerHTML = `
                    <tr>
                        <td colspan="4" style="text-align: center; color: var(--text-dim);">No active username deployments discovered.</td>
                    </tr>
                `;
            }
            
            setTimeout(() => {
                elements.scanProgressFrame.style.display = "none";
                elements.scanResultsCard.style.display = "block";
            }, 500);
            
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        clearInterval(interval);
        elements.scanProgressFrame.style.display = "none";
        elements.btnStartScan.disabled = false;
        console.error(e);
    } finally {
        elements.btnStartScan.disabled = false;
        elements.btnStartScan.innerHTML = '<i class="fa-solid fa-bolt"></i> Start High-Precision Scan';
    }
}

// --- Tab: Domain Intel ---
async function handleDomainQuery() {
    const domain = elements.targetDomain.value.trim();
    if (!domain) return;
    
    elements.btnFetchDomain.disabled = true;
    elements.btnFetchDomain.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing';
    
    try {
        // Query DNS Records
        const rDns = await fetch("/api/domain/dns", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain: domain, case_name: state.activeCase })
        });
        
        // Query WHOIS
        const rWhois = await fetch("/api/domain/whois", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ domain: domain, case_name: state.activeCase })
        });
        
        if (rDns.ok && rWhois.ok) {
            const dnsData = await rDns.json();
            const whoisData = await rWhois.json();
            
            // Render DNS records
            elements.dnsRecordsContainer.innerHTML = "";
            let hasRecords = false;
            
            for (const [rtype, vals] of Object.entries(dnsData.records)) {
                if (vals.length > 0) {
                    hasRecords = true;
                    const card = document.createElement("div");
                    card.style.marginBottom = "1.25rem";
                    card.innerHTML = `
                        <h5 style="color:var(--primary); font-weight:700; margin-bottom:0.4rem;">${rtype} Records</h5>
                        <ul class="servers-list" style="margin-top:0;">
                            ${vals.map(v => `<li>${v}</li>`).join("")}
                        </ul>
                    `;
                    elements.dnsRecordsContainer.appendChild(card);
                }
            }
            if (!hasRecords) {
                elements.dnsRecordsContainer.innerHTML = '<p class="description">No DNS resolution records found.</p>';
            }
            
            // Render WHOIS records
            elements.domainRegistrar.innerText = whoisData.registrar;
            elements.domainCreated.innerText = whoisData.creation_date;
            elements.domainWhoisRaw.innerText = whoisData.raw;
            
            elements.domainResultsGrid.style.display = "grid";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchDomain.disabled = false;
        elements.btnFetchDomain.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Analyze Domain';
    }
}

// --- Tab: IP Intel ---
async function handleIpQuery() {
    const ip = elements.targetIp.value.trim();
    if (!ip) return;
    
    elements.btnFetchIp.disabled = true;
    elements.btnFetchIp.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Geolocating';
    
    try {
        const r = await fetch("/api/ip/geoip", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip: ip, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.ipCoords.innerText = `${data.lat}, ${data.lon}`;
            elements.ipCity.innerText = data.city;
            elements.ipCountry.innerText = data.country;
            elements.ipIsp.innerText = data.isp;
            elements.ipOrg.innerText = data.org;
            elements.ipMapsLink.href = `https://www.google.com/maps/search/?api=1&query=${data.lat},${data.lon}`;
            
            elements.ipResultsGrid.style.display = "grid";
            await refreshFindingsCount();
            updateStatsBanner();
        } else {
            const err = await r.json();
            alert(err.detail || "IP lookup failed.");
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchIp.disabled = false;
        elements.btnFetchIp.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Geolocate IP';
    }
}

// --- Tab: Email Intel ---
async function handleEmailQuery() {
    const email = elements.targetEmail.value.trim();
    if (!email) return;
    
    elements.btnFetchEmail.disabled = true;
    elements.btnFetchEmail.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Resolving';
    
    try {
        const r = await fetch("/api/email/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.emailDomainName.innerText = `@${data.domain}`;
            elements.emailMxStatus.innerText = data.mx_status;
            
            if (data.mx_status === "Active") {
                elements.emailMxStatus.className = "value badge-status active";
            } else {
                elements.emailMxStatus.className = "value badge-status error";
            }
            
            // MX Servers
            elements.emailMxServers.innerHTML = "";
            if (data.mx_servers.length > 0) {
                data.mx_servers.forEach(srv => {
                    const li = document.createElement("li");
                    li.innerText = srv;
                    elements.emailMxServers.appendChild(li);
                });
            } else {
                const li = document.createElement("li");
                li.innerText = "No exchange servers verified.";
                elements.emailMxServers.appendChild(li);
            }
            
            // Username badge recommendations
            elements.emailCandidatesContainer.innerHTML = "";
            data.candidates.forEach(cand => {
                const badge = document.createElement("button");
                badge.className = "candidate-badge";
                badge.innerHTML = `<i class="fa-solid fa-crosshair"></i> @${cand}`;
                badge.addEventListener("click", () => {
                    elements.footprintUsername.value = cand;
                    state.targetUsername = cand;
                    switchTab("tab-username");
                    handleFootprintScan();
                });
                elements.emailCandidatesContainer.appendChild(badge);
            });
            
            // Leak queries
            elements.emailDorksContainer.innerHTML = "";
            data.dorks.forEach((dk, idx) => {
                const row = renderDorkItem(dk, idx, "email-leak");
                elements.emailDorksContainer.appendChild(row);
            });
            
            elements.emailResultsGrid.style.display = "grid";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchEmail.disabled = false;
        elements.btnFetchEmail.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analyze Email';
    }
}

// --- Tab: Phone Resolver ---
async function handlePhoneQuery() {
    const phone = elements.targetPhone.value.trim();
    if (!phone) return;
    
    const countryCode = elements.phoneCountryCode.value;
    elements.btnFetchPhone.disabled = true;
    elements.btnFetchPhone.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Resolving';
    
    try {
        const r = await fetch("/api/phone/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone: phone, country_code: countryCode, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.phoneFormatted.innerText = data.phone;
            elements.phoneCountry.innerText = data.country;
            
            elements.phoneDorksContainer.innerHTML = "";
            data.dorks.forEach((dk, idx) => {
                const row = renderDorkItem(dk, idx, "phone-osint");
                elements.phoneDorksContainer.appendChild(row);
            });
            
            elements.phoneResultsGrid.style.display = "grid";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchPhone.disabled = false;
        elements.btnFetchPhone.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Decode Number';
    }
}

// --- Tab: Dork Studio ---
async function handleDorksQuery() {
    const target = elements.dorkTarget.value.trim();
    if (!target) return;
    
    const type = elements.dorkTargetType.value;
    elements.btnFetchDorks.disabled = true;
    elements.btnFetchDorks.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Building';
    
    try {
        const r = await fetch("/api/dorks/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ target: target, target_type: type, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.studioDorksContainer.innerHTML = "";
            data.dorks.forEach((dk, idx) => {
                const row = renderDorkItem(dk, idx, "dork-studio");
                elements.studioDorksContainer.appendChild(row);
            });
            
            elements.dorksResultsCard.style.display = "block";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchDorks.disabled = false;
        elements.btnFetchDorks.innerHTML = '<i class="fa-solid fa-terminal"></i> Build Queries';
    }
}

// --- Tab: Case Vault ---
async function loadVaultFindings() {
    if (!state.activeCase) return;
    
    try {
        const r = await fetch(`/api/cases/${encodeURIComponent(state.activeCase)}/findings`);
        const data = await r.json();
        
        elements.vaultTableTbody.innerHTML = "";
        
        if (data.findings.length > 0) {
            data.findings.forEach(f => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><span class="badge info">${f.category}</span></td>
                    <td><strong>${f.label}</strong></td>
                    <td class="font-mono" style="word-break: break-all;">${f.value}</td>
                    <td style="color: var(--text-muted); font-size: 0.8rem;">${f.timestamp}</td>
                `;
                elements.vaultTableTbody.appendChild(tr);
            });
        } else {
            elements.vaultTableTbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; color: var(--text-dim); padding: 3rem;">No evidence entries saved to this Case File yet.</td>
                </tr>
            `;
        }
        
        state.findingsCount = data.findings.length;
        updateStatsBanner();
    } catch (e) {
        console.error(e);
    }
}

async function handleDownloadCSV() {
    if (!state.activeCase) return;
    
    try {
        const r = await fetch(`/api/cases/${encodeURIComponent(state.activeCase)}/findings`);
        const data = await r.json();
        
        if (data.findings.length === 0) {
            alert("No logs to export.");
            return;
        }
        
        const escapeCSV = (val) => {
            if (val === null || val === undefined) return '';
            const stringified = String(val);
            if (stringified.includes(',') || stringified.includes('"') || stringified.includes('\n')) {
                return `"${stringified.replace(/"/g, '""')}"`;
            }
            return stringified;
        };
        
        let csvContent = "Category,Property,Value,Timestamp\n";
        data.findings.forEach(f => {
            csvContent += `${escapeCSV(f.category)},${escapeCSV(f.label)},${escapeCSV(f.value)},${escapeCSV(f.timestamp)}\n`;
        });
        
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `ONSINT_LEDGER_${state.activeCase}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch (e) {
        console.error(e);
    }
}

// --- Tab: Connection Graph ---
let networkInstance = null;

async function loadConnectionGraph() {
    if (!state.activeCase) {
        elements.graphEmptyBanner.style.display = "flex";
        elements.graphDataFrame.style.display = "none";
        return;
    }
    
    elements.graphEmptyBanner.style.display = "none";
    elements.graphDataFrame.style.display = "block";
    
    try {
        const r = await fetch(`/api/cases/${encodeURIComponent(state.activeCase)}/graph`);
        const data = await r.json();
        
        const nodes = data.nodes.map(n => {
            let color = "#64748b"; // slate
            let shape = "dot";
            let size = 16;
            
            if (n.group === "case") {
                color = "#6366f1"; // Indigo
                shape = "hexagon";
                size = 26;
            } else if (n.group === "target") {
                color = "#a855f7"; // Purple
                shape = "dot";
                size = 22;
            } else if (n.group === "uid") {
                color = "#ec4899"; // Pink
                shape = "diamond";
                size = 18;
            } else if (n.group === "platform") {
                color = "#3b82f6"; // Blue
                shape = "dot";
                size = 18;
            } else if (n.group === "email") {
                color = "#f43f5e"; // Rose
                shape = "triangle";
                size = 18;
            } else if (n.group === "server") {
                color = "#eab308"; // Amber
                shape = "square";
                size = 14;
            } else if (n.group === "geotag") {
                color = "#10b981"; // Emerald
                shape = "star";
                size = 18;
            } else if (n.group === "mirror") {
                color = "#06b6d4"; // Cyan
                shape = "dot";
                size = 14;
            }
            
            return {
                ...n,
                color: {
                    background: color,
                    border: "#1e293b",
                    highlight: { background: color, border: "#f1f5f9" }
                },
                shape: shape,
                size: size,
                font: { color: "#f1f5f9", face: "Outfit", size: 12, bold: { color: "#f1f5f9" } },
                borderWidth: 2
            };
        });
        
        const edges = data.edges.map(e => {
            return {
                ...e,
                color: { color: "rgba(255,255,255,0.08)", highlight: "rgba(168, 85, 247, 0.4)" },
                font: { color: "#64748b", face: "Outfit", size: 9 },
                width: 1.5,
                arrows: { to: { enabled: true, scaleFactor: 0.8 } }
            };
        });
        
        const container = elements.networkGraph;
        const graphData = {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        };
        
        const options = {
            nodes: {
                borderWidth: 2,
                shadow: { enabled: true, color: "rgba(0,0,0,0.3)", size: 4, x: 2, y: 2 }
            },
            physics: {
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.015,
                    springLength: 100,
                    springConstant: 0.08
                },
                maxVelocity: 50,
                solver: "forceAtlas2Based",
                timestep: 0.35,
                stabilization: { iterations: 100 }
            },
            interaction: {
                hover: true,
                tooltipDelay: 150
            }
        };
        
        if (networkInstance) {
            networkInstance.destroy();
        }
        
        networkInstance = new vis.Network(container, graphData, options);
    } catch (e) {
        console.error("Error drawing graph:", e);
    }
}

// --- RESIZABLE SIDEBAR LOGIC ---
function initResizableSidebar() {
    const resizer = document.getElementById("sidebar-resizer");
    const sidebar = document.querySelector(".sidebar");
    if (!resizer || !sidebar) return;
    
    // Restore sidebar width from localStorage if exists
    const savedWidth = localStorage.getItem("onsint-sidebar-width");
    if (savedWidth) {
        sidebar.style.width = `${savedWidth}px`;
        // Delay resize event slightly to ensure DOM is fully laid out
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 100);
    }
    
    let isResizing = false;
    
    resizer.addEventListener("mousedown", (e) => {
        isResizing = true;
        resizer.classList.add("active");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    });
    
    document.addEventListener("mousemove", (e) => {
        if (!isResizing) return;
        // Bounded resizing: constrain sidebar width between 240px and 480px
        const newWidth = Math.max(240, Math.min(480, e.clientX));
        sidebar.style.width = `${newWidth}px`;
        
        // Trigger window resize event so vis.js canvas scales immediately
        window.dispatchEvent(new Event('resize'));
    });
    
    document.addEventListener("mouseup", () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove("active");
            document.body.style.cursor = "default";
            document.body.style.userSelect = "auto";
            
            // Save width to localStorage
            localStorage.setItem("onsint-sidebar-width", parseInt(sidebar.style.width));
        }
    });
}
