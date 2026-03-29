// Theme Toggle Logic
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('panelTheme', newTheme);
    
    const icon = document.querySelector('#theme-toggle i');
    icon.className = newTheme === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
    
    // Update chart colors based on theme
    Chart.defaults.color = newTheme === 'dark' ? '#cbd5e1' : '#475569';
    if(charts.cpu) { charts.cpu.update(); charts.ram.update(); charts.disk.update(); }
}

const savedTheme = localStorage.getItem('panelTheme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);
if(savedTheme === 'light') {
    document.querySelector('#theme-toggle i').className = 'fa-solid fa-sun';
}

// Tab Switching
async function switchTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(`tab-${tabId}`).classList.add('active');
    const activeBtn = Array.from(document.querySelectorAll('.nav-btn')).find(btn => 
        btn.getAttribute('onclick').includes(`'${tabId}'`)
    );
    if(activeBtn) activeBtn.classList.add('active');

    if (tabId === 'dashboard') {
        loadServices();
    }
}

async function openFileManager() {
    const hostname = window.location.hostname;
    try {
        const services = await api.get('/services/');
        const fb = services.find(s => 
            s.name.toLowerCase().includes('file') || 
            s.name.toLowerCase().includes('browse') || 
            s.name.toLowerCase().includes('explorer') ||
            s.command.toLowerCase().includes('filebrowser')
        );
        
        if (fb) {
            if (fb.status === 'stopped') {
                alert("File Browser is currently stopped. Please start it from the Dashboard first.");
                return;
            }
            const port = fb.port || 8083;
            window.open(`http://${hostname}:${port}`, '_blank');
        } else {
            // Fallback
            window.open(`http://${hostname}:8083`, '_blank');
        }
    } catch(e) {
        window.open(`http://${hostname}:8083`, '_blank');
    }
}

// Charts Initialization
const charts = {};

function initCharts() {
    const commonOptions = {
        type: 'doughnut',
        options: {
            responsive: true,
            cutout: '70%',
            plugins: { legend: { display: false } },
            animation: { animateScale: true, animateRotate: true }
        }
    };

    const ctxCpu = document.getElementById('cpuChart').getContext('2d');
    charts.cpu = new Chart(ctxCpu, {
        ...commonOptions,
        data: { labels: ['Used', 'Free'], datasets: [{ data: [0, 100], backgroundColor: ['#3b82f6', 'rgba(100,100,100,0.2)'], borderWidth: 0 }] }
    });

    const ctxRam = document.getElementById('ramChart').getContext('2d');
    charts.ram = new Chart(ctxRam, {
        ...commonOptions,
        data: { labels: ['Used', 'Free'], datasets: [{ data: [0, 100], backgroundColor: ['#10b981', 'rgba(100,100,100,0.2)'], borderWidth: 0 }] }
    });

    const ctxDisk = document.getElementById('diskChart').getContext('2d');
    charts.disk = new Chart(ctxDisk, {
        ...commonOptions,
        data: { labels: ['Used', 'Free'], datasets: [{ data: [0, 100], backgroundColor: ['#f59e0b', 'rgba(100,100,100,0.2)'], borderWidth: 0 }] }
    });
}

// System Status Polling
async function fetchSystemStatus() {
    try {
        const data = await api.get('/system/status');
        
        // Update text info
        document.getElementById('info-hostname').innerText = data.os.hostname || 'Unknown';
        document.getElementById('info-ip').innerText = window.location.hostname;
        document.getElementById('info-kernel').innerText = data.os.kernel || 'Unknown';
        document.getElementById('info-cpu-model').innerText = data.os.cpu_model || 'Unknown';
        
        const ramTotalGB = data.ram.total ? (data.ram.total / (1024 * 1024 * 1024)).toFixed(1) : 0;
        document.getElementById('info-ram-total').innerText = `${ramTotalGB} GB`;
        
        const diskTotalGB = data.disk.total ? (data.disk.total / (1024 * 1024 * 1024)).toFixed(1) : 0;
        document.getElementById('info-disk-total').innerText = `${diskTotalGB} GB`;
        
        document.getElementById('info-uptime').innerText = data.os.uptime || '0h 0m';
        
        // Network Speed and Traffic
        const upSpeed = data.net.up_speed ? (data.net.up_speed / 1024).toFixed(1) : 0;
        const downSpeed = data.net.down_speed ? (data.net.down_speed / 1024).toFixed(1) : 0;
        document.getElementById('info-net').innerHTML = `
            <i class="fa-solid fa-arrow-up"></i> ${upSpeed} KB/s | 
            <i class="fa-solid fa-arrow-down"></i> ${downSpeed} KB/s
        `;

        // Update charts
        const cpuUsage = data.cpu.percent || 0;
        charts.cpu.data.datasets[0].data = [cpuUsage, 100 - cpuUsage];
        charts.cpu.update();
        document.getElementById('cpu-percent').innerText = `${cpuUsage}%`;

        const ramUsage = data.ram.percent || 0;
        charts.ram.data.datasets[0].data = [ramUsage, 100 - ramUsage];
        charts.ram.update();
        document.getElementById('ram-percent').innerText = `${ramUsage}%`;

        const diskUsage = data.disk.percent || 0;
        charts.disk.data.datasets[0].data = [diskUsage, 100 - diskUsage];
        charts.disk.update();
        document.getElementById('disk-percent').innerText = `${diskUsage}%`;
        
    } catch (e) {
        console.error("Failed to fetch system status", e);
    }
}

// Services Management
async function loadServices() {
    const container = document.getElementById('services-container');
    container.innerHTML = '<p>Loading services...</p>';
    
    try {
        const services = await api.get('/services/');
        if(services.length === 0) {
            container.innerHTML = '<p>No services configured.</p>';
            return;
        }
        
        container.innerHTML = '';
        services.forEach(svc => {
            const statusColor = svc.status === 'running' ? '#10b981' : '#ef4444';
            const isTr = (localStorage.getItem('panelLang') || 'en') === 'tr';
            const statusText = svc.status === 'running' ? (isTr ? 'ÇALIŞIYOR' : 'RUNNING') : (isTr ? 'DURDURULDU' : 'STOPPED');
            let html = `
                <div class="service-item">
                    <div class="flex-header">
                        <h3>${svc.name}</h3>
                        <span style="color: ${statusColor}; font-weight:bold;">● ${statusText}</span>
                    </div>
                    <p style="font-size:0.85rem; color:var(--text-secondary)">Command: <code>${svc.command}</code></p>
                    <div class="item-actions">
            `;
            
            if(svc.status === 'stopped') {
                html += `<button class="btn primary-btn" onclick="startService(${svc.id})"><i class="fa-solid fa-play"></i> Start</button>`;
            } else {
                html += `<button class="btn" style="background:#ef4444" onclick="stopService(${svc.id})"><i class="fa-solid fa-stop"></i> Stop</button>`;
            }
            
            html += `<button class="btn icon-btn" onclick="viewLogs(${svc.id})" title="View Logs"><i class="fa-solid fa-file-lines"></i></button>`;
            
            if(svc.config_file) {
                const configs = svc.config_file.split(',');
                configs.forEach(cfg => {
                    const cleanCfg = cfg.trim();
                    const cfgName = cleanCfg.split('/').pop() || 'Config';
                    html += `<button class="btn icon-btn" onclick="openConfigEditor(${svc.id}, '${cleanCfg}')" title="Edit Config: ${cfgName}"><i class="fa-solid fa-pen-to-square"></i></button>`;
                });
            }
            
            if(svc.port) {
                const url = `http://${window.location.hostname}:${svc.port}`;
                html += `<a href="${url}" target="_blank" class="btn icon-btn" title="Open Dashboard"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>`;
            }
            
            html += `<button class="btn icon-btn" style="color:#ef4444; margin-left:auto;" onclick="deleteService(${svc.id})"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>`;
            container.innerHTML += html;
        });
    } catch(e) {
        container.innerHTML = '<p style="color:red">Failed to load services.</p>';
    }
}

async function startService(id) { await api.post(`/services/${id}/start`); loadServices(); }
async function stopService(id) { await api.post(`/services/${id}/stop`); loadServices(); }
async function deleteService(id) { if(confirm('Delete service?')) { await api.delete(`/services/${id}`); loadServices(); } }

// Logs Modal
async function viewLogs(id) {
    const modal = document.getElementById('logModal');
    const logContent = document.getElementById('log-content');
    logContent.innerText = "Fetching logs...";
    modal.style.display = "block";
    
    try {
        const res = await api.get(`/services/${id}/logs`);
        logContent.innerText = res.logs || 'No logs available.';
    } catch(e) {
        logContent.innerText = "Error fetching logs.";
    }
}

// Add Service Modal
function openAddServiceModal() {
    document.getElementById('svc-name').value = '';
    document.getElementById('svc-command').value = '';
    document.getElementById('svc-port').value = '';
    document.getElementById('svc-logfile').value = '';
    document.getElementById('svc-configfile').value = '';
    document.getElementById('addServiceModal').style.display = 'block';
}

async function saveServiceModal() {
    const data = {
        name: document.getElementById('svc-name').value,
        command: document.getElementById('svc-command').value,
        port: document.getElementById('svc-port').value ? parseInt(document.getElementById('svc-port').value) : null,
        autostart: false,
        log_file: document.getElementById('svc-logfile').value || null,
        config_file: document.getElementById('svc-configfile').value || null
    };
    if(!data.name || !data.command) { alert("Name and Command are required"); return; }
    
    try {
        await api.post('/services/', data);
        closeModal('addServiceModal');
        loadServices();
    } catch(e) {
        alert("Failed to save service");
    }
}

function closeModal(id) {
    document.getElementById(id).style.display = "none";
}

// Config Editor Logic
async function openConfigEditor(id, targetFile) {
    const modal = document.getElementById('configModal');
    const contentBox = document.getElementById('config-content');
    contentBox.value = "Fetching configuration...";
    modal.style.display = "block";
    
    try {
        let url = `/services/${id}/config`;
        if (targetFile) {
            url += `?file=${encodeURIComponent(targetFile)}`;
        }
        const res = await api.get(url);
        contentBox.value = res.content;
        document.getElementById('config-title').innerText = `Editing: ${res.path}`;
        
        document.getElementById('save-config-btn').onclick = async function() {
            try {
                await api.post(`/services/${id}/config`, { content: contentBox.value, file: targetFile });
                alert("Configuration saved successfully.");
                closeModal('configModal');
            } catch(e) {
                alert("Failed to save configuration.");
            }
        };
    } catch(e) {
        contentBox.value = "Error fetching configuration. File might not exist.";
        document.getElementById('save-config-btn').onclick = null;
    }
}

let term = null;
let terminalSocket = null;
const fitAddon = (typeof TerminalAddonFit !== 'undefined') ? new TerminalAddonFit.FitAddon() : null;

async function openTerminal(type = 'shell') {
    const modal = document.getElementById('terminalModal');
    modal.style.display = 'block';
    document.getElementById('terminal-title').innerText = type === 'shell' ? 'System Terminal' : 'Installation Terminal';
    
    if (!term) {
        term = new Terminal({
            cursorBlink: true,
            fontSize: 14,
            fontFamily: 'monospace',
            theme: {
                background: '#000000',
                foreground: '#00ff00'
            }
        });
        if (fitAddon) term.loadAddon(fitAddon);
        term.open(document.getElementById('terminal-container'));
        if (fitAddon) fitAddon.fit();
    } else {
        term.clear();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const endpoint = type === 'shell' ? '/ws/terminal/shell' : `/ws/install/${type}`;
    const wsUrl = `${protocol}//${window.location.host}${endpoint}`;
    
    if (terminalSocket) terminalSocket.close();
    terminalSocket = new WebSocket(wsUrl);
    
    terminalSocket.onopen = () => {
        term.write('\x1b[1;32m[CONNECTED]\x1b[0m Terminal ready.\r\n');
    };
    
    terminalSocket.onmessage = (event) => {
        term.write(event.data);
    };
    
    terminalSocket.onclose = () => {
        term.write('\r\n\x1b[1;33m[DISCONNECTED]\x1b[0m Terminal session closed.\r\n');
    };
    
    term.onData(data => {
        if (terminalSocket && terminalSocket.readyState === WebSocket.OPEN) {
            terminalSocket.send(data);
        }
    });

    // Resize handling
    window.addEventListener('resize', () => fitAddon && fitAddon.fit());
}

// Terminal Button Hook
document.getElementById('terminal-btn').addEventListener('click', () => {
    const modal = document.getElementById('terminalModal');
    const container = document.getElementById('terminal-container');
    const iframe = document.getElementById('terminal-iframe');
    const title = document.getElementById('terminal-title');
    
    title.innerText = "System Terminal (ttyd)";
    modal.style.display = 'block';
    
    // Switch to iframe mode for ttyd
    container.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = `http://${window.location.hostname}:7681`;
});

function closeTerminalModal() {
    document.getElementById('terminalModal').style.display = 'none';
    if (terminalSocket) {
        terminalSocket.close();
    }
    // Stop ttyd iframe to save bandwidth/resources
    const iframe = document.getElementById('terminal-iframe');
    if(iframe) iframe.src = "";
}

// Profile Update Logic
async function updateProfile() {
    const username = document.getElementById('update-username').value;
    const password = document.getElementById('update-password').value;
    
    if(!username && !password) {
        alert("Please enter a new username or password.");
        return;
    }
    
    if(!confirm("Are you sure you want to update your profile? You will need to login again with new credentials.")) {
        return;
    }
    
    try {
        const body = {};
        if(username) body.username = username;
        if(password) body.password = password;
        
        await api.put('/auth/profile', body);
        alert("Profile updated successfully. Redirecting to login...");
        logout();
    } catch(e) {
        alert(e.detail || "Failed to update profile.");
    }
}

// Diagnostics Logic
async function showDiagnostics() {
    const modal = document.getElementById('diagModal');
    const content = document.getElementById('diag-content');
    content.innerText = "Running deep system scan...";
    modal.style.display = 'block';
    
    try {
        const data = await api.get('/debug/info');
        content.innerText = JSON.stringify(data, null, 2);
    } catch(e) {
        content.innerText = "Error: Could not connect to diagnostics API.\n" + (e.detail || e.message);
    }
}

function copyDiagnostics() {
    const content = document.getElementById('diag-content').innerText;
    navigator.clipboard.writeText(content).then(() => {
        alert("Diagnostics copied to clipboard. Please paste them to the support chat.");
    });
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    if(!localStorage.getItem('access_token')) {
        window.location.href = '/login.html';
        return;
    }
    initCharts();
    fetchSystemStatus();
    loadServices();
    setInterval(fetchSystemStatus, 5000); // Poll every 5 seconds
    setInterval(loadServices, 30000);    // Refresh services every 30s
});

// Close modal when clicking outside
window.onclick = function(event) {
    const logModal = document.getElementById('logModal');
    const addModal = document.getElementById('addServiceModal');
    const configModal = document.getElementById('configModal');
    const termModal = document.getElementById('terminalModal');
    const diagModal = document.getElementById('diagModal');
    if (event.target == logModal) logModal.style.display = "none";
    if (event.target == addModal) addModal.style.display = "none";
    if (event.target == configModal) configModal.style.display = "none";
    if (event.target == termModal) closeTerminalModal();
    if (event.target == diagModal) closeModal('diagModal');
}
