import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dgram from 'dgram';
import { WebSocketServer } from 'ws';
import { networkInterfaces } from 'os';
import { randomUUID } from 'crypto';
import { GlobalDivider } from './sharding.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Configuration
const HIVE_PORT = 41234;
const DASHBOARD_PORT = 3000;
const BEACON_INTERVAL_MS = 2000;
const HIVE_VERSION = "0.1.0-alpha";

/**
 * DiscoveryBeacon: Broadcasts Queen's presence via UDP
 */
class DiscoveryBeacon {
    constructor() {
        this.socket = dgram.createSocket('udp4');
        this.socket.bind(() => {
            this.socket.setBroadcast(true);
        });
    }

    getPublicIp() {
        const nets = networkInterfaces();
        for (const name of Object.keys(nets)) {
            for (const net of nets[name]) {
                // Skip internal and non-IPv4 addresses
                if (net.family === 'IPv4' && !net.internal) {
                    return net.address;
                }
            }
        }
        return '127.0.0.1';
    }

    start() {
        console.log(`[QUEEN] UDP Beacon active on port ${HIVE_PORT}`);
        setInterval(() => {
            const payload = JSON.stringify({
                type: 'BEACON',
                queenIp: this.getPublicIp(),
                hivePort: HIVE_PORT,
                hiveVersion: HIVE_VERSION,
                timestamp: Date.now()
            });

            const message = Buffer.from(payload);
            this.socket.send(message, 0, message.length, HIVE_PORT, '255.255.255.255', (err) => {
                if (err) console.error('[QUEEN] Beacon Error:', err);
            });
        }, BEACON_INTERVAL_MS);
    }
}

/**
 * HiveMind: Orchestrates Grid coordinates and Bee assignments
 */
class HiveMind {
    constructor() {
        this.grid = Array(10).fill(null).map(() => Array(10).fill(null)); // 10x10 Grid
        this.bees = new Map(); // BeeID -> Connection Info
        this.princes = new Set(); // Set of Prince BeeIDs
        this.observers = new Set(); // Dashboard Clients

        this.currentTerm = 1;
        this.wss = new WebSocketServer({ port: HIVE_PORT });

        this.setupWebSocket();
        this.startHeartbeat();
        this.startDashboardServer();
    }

    startDashboardServer() {
        const server = http.createServer((req, res) => {
            let filePath = path.join(__dirname, '../public', req.url === '/' ? 'index.html' : req.url);
            const extname = path.extname(filePath);
            let contentType = 'text/html';

            if (extname === '.js') contentType = 'text/javascript';
            if (extname === '.css') contentType = 'text/css';

            fs.readFile(filePath, (err, content) => {
                if (err) {
                    if (err.code == 'ENOENT') {
                        res.writeHead(404);
                        res.end('Not Found');
                    } else {
                        res.writeHead(500);
                        res.end(`Server Error: ${err.code}`);
                    }
                } else {
                    res.writeHead(200, { 'Content-Type': contentType });
                    res.end(content, 'utf-8');
                }
            });
        });

        server.listen(DASHBOARD_PORT, () => {
            console.log(`[DASHBOARD] Command Center running at http://localhost:${DASHBOARD_PORT}`);
        });
    }

    startHeartbeat() {
        // High-Frequency Raft Heartbeat (AppendEntries) to Princes
        setInterval(() => {
            this.broadcastToPrinces({
                type: 'APPEND_ENTRIES',
                term: this.currentTerm,
                leaderId: 'QUEEN', // The Node.js Queen is always the original leader
                hiveState: {
                    grid: this.grid,
                    beeCount: this.bees.size
                }
            });
        }, 100); // 100ms heartbeat
    }

    broadcastToPrinces(message) {
        const payload = JSON.stringify(message);
        for (const princeId of this.princes) {
            const prince = this.bees.get(princeId);
            if (prince && prince.ws.readyState === 1) { // OPEN
                prince.ws.send(payload);
            }
        }
    }

    broadcastState() {
        const state = {
            type: 'HIVE_STATE',
            grid: this.grid,
            beeCount: this.bees.size,
            bees: Array.from(this.bees.entries()).map(([id, data]) => ({
                id,
                coords: data.coords,
                role: data.role,
                pmi: data.pmi,
                p2pPort: data.p2pPort
            }))
        };

        const payload = JSON.stringify(state);
        for (const ws of this.observers) {
            if (ws.readyState === 1) ws.send(payload);
        }
    }

    handleDisconnection(ws) {
        // 1. Check if it's an Observer
        if (this.observers.has(ws)) {
            this.observers.delete(ws);
            return;
        }

        // 2. Check if it's a Bee
        let disconnectedBeeId = null;
        for (const [id, bee] of this.bees.entries()) {
            if (bee.ws === ws) {
                disconnectedBeeId = id;
                break;
            }
        }

        if (disconnectedBeeId) {
            const bee = this.bees.get(disconnectedBeeId);
            const { coords } = bee;
            console.log(`[HIVE] Graceful Pruning: Node ${disconnectedBeeId} at [${coords.i},${coords.j}] disconnected`);

            // Remove from Memory
            this.bees.delete(disconnectedBeeId);
            if (this.princes.has(disconnectedBeeId)) {
                this.princes.delete(disconnectedBeeId);
            }

            // Free the grid cell
            this.grid[coords.i][coords.j] = null;

            // Broadcast NODE_REMOVED to Frontend
            const payload = JSON.stringify({
                type: 'NODE_REMOVED',
                id: disconnectedBeeId,
                coords: coords
            });

            for (const obs of this.observers) {
                if (obs.readyState === 1) obs.send(payload);
            }
        }
    }

    setupWebSocket() {
        this.wss.on('connection', (ws, req) => {
            const ip = req.socket.remoteAddress;
            // console.log(`[HIVE] New connection request from ${ip}`);

            ws.on('message', (message) => {
                try {
                    const data = JSON.parse(message);
                    this.handleMessage(ws, data);
                } catch (e) {
                    console.error('[HIVE] Malformed message:', e);
                }
            });

            ws.on('close', () => this.handleDisconnection(ws));
            ws.on('error', (err) => {
                console.error('[HIVE] Socket error:', err.message);
                this.handleDisconnection(ws);
            });


        });

        console.log(`[QUEEN] WebSocket Server listening on port ${HIVE_PORT}`);
    }

    handleMessage(ws, data) {
        if (data.type === 'HANDSHAKE') {
            this.registerBee(ws, data);
        } else if (data.type === 'HEARTBEAT') {
            // Handle heartbeat updates (Spike Protocol)
            if (this.bees.has(data.beeId)) {
                const bee = this.bees.get(data.beeId);
                bee.pmi = this.calculatePMI(data.metrics);
                // Maybe trigger broadcast if significant change?
            }
        } else if (data.type === 'JOB_SUBMISSION') {
            this.handleJobSubmission(ws, data);
        } else if (data.type === 'OBSERVER') {
            this.observers.add(ws);
            this.broadcastState();
        }
    }

    handleJobSubmission(ws, data) {
        const jobId = randomUUID();
        const sizeMB = data.fileSize / (1024 * 1024);

        console.log(`[JOB] Received Model "${data.jobName}" (Size: ${sizeMB.toFixed(2)} MB)`);
        console.log(`[JOB] Job ID Assigned: ${jobId}`);

        // 1. Identify Lead Bees (For now, use all Princes as Leads)
        // In real logic, we'd select top N Princes.
        const leads = Array.from(this.princes);
        const numBlocks = leads.length || 1;

        // 2. Global Divide
        console.log(`[SHARD] Dividing job into ${numBlocks} blocks...`);
        const blocks = GlobalDivider.divide(data.data, numBlocks);

        // 3. Dispatch to Leads
        leads.forEach((beeId, index) => {
            const bee = this.bees.get(beeId);
            if (bee && bee.ws.readyState === 1) {
                const assignment = {
                    type: 'BLOCK_ASSIGNMENT',
                    jobId: jobId,
                    blockId: index,
                    totalBlocks: numBlocks,
                    data: blocks[index]
                };
                bee.ws.send(JSON.stringify(assignment));
                console.log(`[SHARD] Assigned Block ${index} to Lead ${beeId}`);
            }
        });

        const ack = {
            type: 'JOB_ACK',
            jobId: jobId,
            status: 'RECEIVED'
        };
        ws.send(JSON.stringify(ack));
    }

    calculatePMI(metrics) {
        const vramScore = (metrics.vramFree || 0) * 0.01;
        const cpuScore = (metrics.cpuIdle || 0);
        const jitterPenalty = (metrics.jitter || 0) * 0.5;

        return (vramScore * 0.7) + (cpuScore * 0.3) - jitterPenalty;
    }

    findEmptySlot() {
        for (let i = 0; i < 10; i++) {
            for (let j = 0; j < 10; j++) {
                if (this.grid[i][j] === null) {
                    return { i, j };
                }
            }
        }
        return null;
    }

    registerBee(ws, data) {
        const pmi = this.calculatePMI(data.metrics);
        const coords = this.findEmptySlot();
        const p2pPort = data.p2pPort || 0;

        if (!coords) {
            console.warn(`[HIVE] Grid Full! Rejecting Bee ${data.beeId}`);
            ws.close();
            return;
        }

        const role = pmi > 20 ? 'PRINCE' : 'WORKER';

        // Update State
        const beeInfo = { ws, coords, pmi, role, p2pPort, ip: ws._socket.remoteAddress };
        this.grid[coords.i][coords.j] = data.beeId;
        this.bees.set(data.beeId, beeInfo);

        if (role === 'PRINCE') {
            this.princes.add(data.beeId);
            console.log(`[HA] New Prince Designated: ${data.beeId}`);
        }

        console.log(`[DISCOVERY] Bee Joined Hive at (${coords.i}, ${coords.j}) with PMI: ${pmi.toFixed(2)} (${role})`);

        // Send Ack
        const response = {
            type: 'ACK',
            status: 'ACCEPTED',
            coordinates: coords,
            role: role
        };
        ws.send(JSON.stringify(response));

        // Notify Neighbors
        this.notifyNeighbors(data.beeId, coords);

        // Update Dashboard
        this.broadcastState();
    }

    notifyNeighbors(newBeeId, coords) {
        const newBee = this.bees.get(newBeeId);
        const deltas = [
            { dir: 'NORTH', di: -1, dj: 0, opp: 'SOUTH' },
            { dir: 'SOUTH', di: 1, dj: 0, opp: 'NORTH' },
            { dir: 'EAST', di: 0, dj: 1, opp: 'WEST' },
            { dir: 'WEST', di: 0, dj: -1, opp: 'EAST' }
        ];

        deltas.forEach(({ dir, di, dj, opp }) => {
            const ni = coords.i + di;
            const nj = coords.j + dj;

            if (ni >= 0 && ni < 10 && nj >= 0 && nj < 10) {
                const neighborId = this.grid[ni][nj];
                if (neighborId) {
                    const neighbor = this.bees.get(neighborId);

                    if (newBee.ws.readyState === 1) {
                        newBee.ws.send(JSON.stringify({
                            type: 'NEIGHBOR_UPDATE',
                            direction: dir,
                            connectionInfo: { ip: neighbor.ip, port: neighbor.p2pPort }
                        }));
                    }

                    if (neighbor.ws.readyState === 1) {
                        neighbor.ws.send(JSON.stringify({
                            type: 'NEIGHBOR_UPDATE',
                            direction: opp,
                            connectionInfo: { ip: newBee.ip, port: newBee.p2pPort }
                        }));
                    }
                }
            }
        });
    }
}

// Start Systems
const beacon = new DiscoveryBeacon();
const mind = new HiveMind();

beacon.start();
