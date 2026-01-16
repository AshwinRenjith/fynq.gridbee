import WebSocket from 'ws';

const ws = new WebSocket('ws://localhost:41234');

ws.on('open', () => {
    console.log('Connected as Observer');
    ws.send(JSON.stringify({ type: 'OBSERVER' }));
});

ws.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'HIVE_STATE') {
        process.stdout.write(`\r[STATE] Bees: ${msg.beeCount} | Princes: ${msg.bees.filter(b => b.role === 'PRINCE').length}`);
    }
});
