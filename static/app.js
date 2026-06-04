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
    
    // Tab 1: Direct Profiling
    directUsername: document.getElementById("direct-username"),
    btnFetchDirect: document.getElementById("btn-fetch-direct"),
    directResultsGrid: document.getElementById("direct-results-grid"),
    directUid: document.getElementById("direct-uid"),
    directMirrorsList: document.getElementById("direct-mirrors-list"),
    
    // Tab 2: Email to Username
    targetEmail: document.getElementById("target-email"),
    btnFetchEmail: document.getElementById("btn-fetch-email"),
    emailResultsGrid: document.getElementById("email-results-grid"),
    emailCandidatesContainer: document.getElementById("email-candidates-container"),
    emailDomainName: document.getElementById("email-domain-name"),
    emailMxStatus: document.getElementById("email-mx-status"),
    emailMxServers: document.getElementById("email-mx-servers"),
    
    // Tab 3: Environment Scanner
    envUsername: document.getElementById("env-username"),
    btnFetchEnv: document.getElementById("btn-fetch-env"),
    envResultsGrid: document.getElementById("env-results-grid"),
    envDorksContainer: document.getElementById("env-dorks-container"),
    envCity: document.getElementById("env-city"),
    btnSearchCity: document.getElementById("btn-search-city"),
    cityDorkOutput: document.getElementById("city-dork-output"),
    cityDorkCode: document.getElementById("city-dork-code"),
    cityDorkLink: document.getElementById("city-dork-link"),
    
    // Tab 4: Digital Footprint
    footprintUsername: document.getElementById("footprint-username"),
    scanCategoryCheckboxes: document.getElementById("scan-category-checkboxes"),
    btnStartScan: document.getElementById("btn-start-scan"),
    scanProgressFrame: document.getElementById("scan-progress-frame"),
    scanProgressBar: document.getElementById("scan-progress-bar"),
    scanStatusLabel: document.getElementById("scan-status-label"),
    scanResultsCard: document.getElementById("scan-results-card"),
    scanHitsBadge: document.getElementById("scan-hits-badge"),
    scanResultsTbody: document.getElementById("scan-results-tbody"),
    
    // Tab 5: Case Vault
    vaultEmptyBanner: document.getElementById("vault-empty-banner"),
    vaultDataFrame: document.getElementById("vault-data-frame"),
    vaultTableTbody: document.getElementById("vault-table-tbody"),
    btnDownloadCsv: document.getElementById("btn-download-csv")
};

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initCopyButtons();
    loadCases();
    checkProxyStatus();
    renderCategories();
    
    // Event Listeners
    elements.btnCreateCase.addEventListener("click", handleCreateCase);
    elements.activeCaseSelect.addEventListener("click", handleCaseSelect);
    elements.btnRefreshProxies.addEventListener("click", handleRefreshProxies);
    elements.btnFetchDirect.addEventListener("click", handleDirectProfileQuery);
    elements.btnFetchEmail.addEventListener("click", handleEmailQuery);
    elements.btnFetchEnv.addEventListener("click", handleEnvQuery);
    elements.btnSearchCity.addEventListener("click", handleCityQuery);
    elements.btnStartScan.addEventListener("click", handleFootprintScan);
    elements.btnDownloadCsv.addEventListener("click", handleDownloadCSV);
    
    // Automatically keep username fields in sync
    [elements.directUsername, elements.envUsername, elements.footprintUsername].forEach(input => {
        input.addEventListener("input", (e) => {
            syncUsernameGlobally(e.target.value);
        });
    });
});

// --- STATE SYNCING ---
function syncUsernameGlobally(val) {
    state.targetUsername = val;
    elements.directUsername.value = val;
    elements.envUsername.value = val;
    elements.footprintUsername.value = val;
}

function updateStatsBanner() {
    elements.statActiveCase.innerText = state.activeCase ? state.activeCase : "Unlinked";
    elements.statFindingsCount.innerText = state.findingsCount;
    elements.statProxyStatus.innerText = state.proxyCount > 0 ? `${state.proxyCount} IPs Active` : "Direct Routing";
    
    if (state.activeCase) {
        elements.vaultEmptyBanner.style.display = "none";
        elements.vaultDataFrame.style.display = "block";
    } else {
        elements.vaultEmptyBanner.style.display = "flex";
        elements.vaultDataFrame.style.display = "none";
    }
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
            
            // Load case data if case vault tab selected
            if (targetTab === "tab-vault") {
                loadVaultFindings();
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
        
        // Clear options except first
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

// Tab 1: Direct Profiling
async function handleDirectProfileQuery() {
    const username = elements.directUsername.value.trim();
    if (!username) return;
    
    elements.btnFetchDirect.disabled = true;
    elements.btnFetchDirect.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing';
    
    try {
        const r = await fetch("/api/instagram/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.directUid.innerText = data.user_id;
            
            // Build mirrors list
            elements.directMirrorsList.innerHTML = "";
            data.mirrors.forEach(m => {
                const li = document.createElement("li");
                const a = document.createElement("a");
                a.href = m.url;
                a.target = "_blank";
                a.innerText = m.label;
                li.appendChild(a);
                elements.directMirrorsList.appendChild(li);
            });
            
            elements.directResultsGrid.style.display = "grid";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchDirect.disabled = false;
        elements.btnFetchDirect.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Analyze';
    }
}

// Tab 2: Email Permuter
async function handleEmailQuery() {
    const email = elements.targetEmail.value.trim();
    if (!email) return;
    
    elements.btnFetchEmail.disabled = true;
    elements.btnFetchEmail.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Resolving';
    
    try {
        const r = await fetch("/api/email-heuristics", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.emailDomainName.innerText = `@${data.domain}`;
            
            // MX status classes
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
            
            // Username permutation buttons
            elements.emailCandidatesContainer.innerHTML = "";
            data.candidates.forEach(cand => {
                const badge = document.createElement("button");
                badge.className = "candidate-badge";
                badge.innerHTML = `<i class="fa-solid fa-crosshair"></i> @${cand}`;
                badge.addEventListener("click", () => {
                    syncUsernameGlobally(cand);
                    switchTab("tab-direct");
                    handleDirectProfileQuery();
                });
                elements.emailCandidatesContainer.appendChild(badge);
            });
            
            elements.emailResultsGrid.style.display = "grid";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchEmail.disabled = false;
        elements.btnFetchEmail.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate';
    }
}

// Tab 3: Environment Scanner (Dorks)
async function handleEnvQuery() {
    const username = elements.envUsername.value.trim();
    if (!username) return;
    
    elements.btnFetchEnv.disabled = true;
    elements.btnFetchEnv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Fetching';
    
    try {
        const r = await fetch("/api/instagram/environment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.envDorksContainer.innerHTML = "";
            
            data.dorks.forEach((dk, index) => {
                const item = document.createElement("div");
                item.className = "dork-item";
                
                const meta = document.createElement("div");
                meta.className = "dork-meta";
                meta.innerHTML = `<span class="dork-title">${dk.label}</span>`;
                
                const queryWrapper = document.createElement("div");
                queryWrapper.className = "dork-query-wrapper";
                
                const codeId = `dork-code-${index}`;
                queryWrapper.innerHTML = `
                    <code id="${codeId}">${dk.query}</code>
                    <button class="btn btn-copy" data-copy-target="${codeId}">
                        <i class="fa-regular fa-copy"></i>
                    </button>
                    <a href="${dk.url}" target="_blank" class="btn btn-secondary btn-sm">
                        <i class="fa-solid fa-square-arrow-up-right"></i> Open
                    </a>
                `;
                
                item.appendChild(meta);
                item.appendChild(queryWrapper);
                elements.envDorksContainer.appendChild(item);
            });
            
            elements.envResultsGrid.style.display = "grid";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    } finally {
        elements.btnFetchEnv.disabled = false;
        elements.btnFetchEnv.innerHTML = '<i class="fa-solid fa-network-wired"></i> Map Ecosystem';
    }
}

async function handleCityQuery() {
    const username = elements.envUsername.value.trim();
    const city = elements.envCity.value.trim();
    if (!username || !city) return;
    
    try {
        const r = await fetch("/api/instagram/geotag", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, city: city, case_name: state.activeCase })
        });
        
        if (r.ok) {
            const data = await r.json();
            elements.cityDorkCode.innerText = data.dork;
            elements.cityDorkLink.href = data.url;
            elements.cityDorkOutput.style.display = "block";
            await refreshFindingsCount();
            updateStatsBanner();
        }
    } catch (e) {
        console.error(e);
    }
}

// Tab 4: Digital Footprint
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
    
    // Get categories checked
    const checkedBoxes = elements.scanCategoryCheckboxes.querySelectorAll("input:checked");
    const categoriesSelected = Array.from(checkedBoxes).map(b => b.value);
    
    // UI adjustments
    elements.btnStartScan.disabled = true;
    elements.btnStartScan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning endpoints';
    elements.scanProgressFrame.style.display = "block";
    elements.scanProgressBar.style.width = "0%";
    elements.scanStatusLabel.innerText = "Querying platforms...";
    elements.scanResultsCard.style.display = "none";
    
    // Simulate smooth progress loading
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
            
            // Build findings rows
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

// Tab 5: Case Vault table
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

// CSV Exporter
async function handleDownloadCSV() {
    if (!state.activeCase) return;
    
    try {
        const r = await fetch(`/api/cases/${encodeURIComponent(state.activeCase)}/findings`);
        const data = await r.json();
        
        if (data.findings.length === 0) {
            alert("No logs to export.");
            return;
        }
        
        // Escape helper
        const escapeCSV = (val) => {
            if (val === null || val === undefined) return '';
            const stringified = String(val);
            if (stringified.includes(',') || stringified.includes('"') || stringified.includes('\n')) {
                return `"${stringified.replace(/"/g, '""')}"`;
            }
            return stringified;
        };
        
        // Header
        let csvContent = "Category,Property,Value,Timestamp\n";
        
        // Rows
        data.findings.forEach(f => {
            csvContent += `${escapeCSV(f.category)},${escapeCSV(f.label)},${escapeCSV(f.value)},${escapeCSV(f.timestamp)}\n`;
        });
        
        // Trigger download
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `IG_INT_LEDGER_${state.activeCase}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch (e) {
        console.error(e);
    }
}
