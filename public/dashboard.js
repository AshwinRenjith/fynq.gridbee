const socket = new WebSocket(`ws://${window.location.hostname}:41234`);
const gridContainer = document.getElementById('grid-container');
const beeCountEl = document.getElementById('bee-count');
const statusEl = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const logsEl = document.getElementById('logs');
const coordHoverEl = document.getElementById('coord-hover');
const uptimeEl = document.getElementById('uptime');
const sessionIdEl = document.getElementById('session-id');

// Session Setup
const sessionId = Math.random().toString(36).substring(2, 10).toUpperCase();
sessionIdEl.innerText = sessionId;

// Init Uptime
let startTime = Date.now();
setInterval(() => {
    let diff = Date.now() - startTime;
    let hh = Math.floor(diff / 3600000).toString().padStart(2, '0');
    let mm = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0');
    let ss = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0');
    uptimeEl.innerText = `${hh}:${mm}:${ss}`;
}, 1000);

// Init Empty grid
for (let i = 0; i < 100; i++) {
    const r = Math.floor(i / 10);
    const c = i % 10;
    const cell = document.createElement('div');
    cell.className = 'grid-cell cell-empty transition-all duration-300 flex items-center justify-center text-[6px] opacity-20';
    cell.id = `cell-${r}-${c}`;
    cell.onmouseover = () => { coordHoverEl.innerText = `[COORD: ${r}, ${c}]`; };
    cell.onmouseleave = () => { coordHoverEl.innerText = `[COORD: --, --]`; };
    gridContainer.appendChild(cell);
}

socket.onopen = () => {
    statusEl.innerText = 'ONLINE // SECURE_SOCKET_ESTABLISHED';
    statusDot.className = 'status-dot status-online';

    log('SYS_CONNECT: WebSocket handshake successful.');
    log(`AUTH_STATUS: Observer session ${sessionId} authorized.`);

    // Authenticate as Observer
    socket.send(JSON.stringify({ type: 'OBSERVER' }));
};

socket.onclose = () => {
    statusEl.innerText = 'OFFLINE // CONNECTION_TERMINATED';
    statusDot.className = 'status-dot status-offline';
    log('SYS_ERROR: Connection closed by remote host.');
};

socket.onerror = (err) => {
    log('SYS_CRIT: Network interface error detected.');
};

socket.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        if (data.type === 'HIVE_STATE') {
            updateUI(data);
        } else if (data.type === 'NODE_REMOVED') {
            const { id, coords } = data;
            const cell = document.getElementById(`cell-${coords.x || coords.i}-${coords.y || coords.j}`);
            if (cell) {
                cell.className = 'grid-cell cell-empty transition-all duration-300 flex items-center justify-center text-[6px] opacity-20';
                cell.innerHTML = '';
                cell.classList.remove('cell-active');
                cell.style.opacity = '0.2';
                log(`ALERT: Node ${id.substring(0, 8)}... [${coords.x || coords.i},${coords.y || coords.j}] DISCONNECTED.`);
            }
        }
    } catch (e) {
        console.error('PARSE_ERROR:', e);
    }
};

function updateUI(state) {
    beeCountEl.innerText = state.beeCount.toString().padStart(2, '0');

    // Reset Grid Visuals
    document.querySelectorAll('.grid-cell').forEach(el => {
        el.className = 'grid-cell cell-empty transition-all duration-300 flex items-center justify-center text-[6px] opacity-20';
        el.innerHTML = '';
        el.classList.remove('cell-active');
    });

    // Populate Bees
    state.bees.forEach(bee => {
        const cell = document.getElementById(`cell-${bee.coords.i}-${bee.coords.j}`);
        if (cell) {
            cell.classList.add('cell-active');
            cell.style.opacity = '1';

            if (bee.role === 'PRINCE') {
                cell.className = 'grid-cell cell-prince transition-all duration-300 flex items-center justify-center text-[8px] font-bold';
                cell.innerText = 'PR';
            } else if (bee.role === 'LEAD') {
                cell.className = 'grid-cell cell-lead transition-all duration-300 flex items-center justify-center text-[8px] font-bold';
                cell.innerText = 'LD';
            } else {
                cell.className = 'grid-cell cell-worker transition-all duration-300 flex items-center justify-center text-[8px] font-bold';
                cell.innerText = 'WK';
            }

            cell.title = `ID: ${bee.id}\nPMI: ${bee.pmi?.toFixed(2)}\nP2P: ${bee.p2pPort}`;
        }
    });

    // Randomize throughput for aesthetic "living" UI
    const tput = (Math.random() * 5 + 10).toFixed(1);
    document.getElementById('throughput').innerText = `${tput} G/s`;
}

function log(msg) {
    const entry = document.createElement('div');
    const time = new Date().toLocaleTimeString('en-GB', { hour12: false });
    entry.innerHTML = `<span class="opacity-30">[${time}]</span> <span class="text-green-400/90">${msg}</span>`;
    logsEl.prepend(entry);

    // Trim logs
    if (logsEl.children.length > 50) {
        logsEl.removeChild(logsEl.lastChild);
    }
}
