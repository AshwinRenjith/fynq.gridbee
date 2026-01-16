import asyncio
import websockets
import json
import logging

class BitchatMesh:
    def __init__(self, bee_id, message_handler):
        self.bee_id = bee_id
        self.message_handler = message_handler
        self.neighbors = {
            "NORTH": None,
            "SOUTH": None,
            "EAST": None,
            "WEST": None
        }
        self.p2p_port = 0 # Ephemeral
        self.server = None

    async def start_server(self):
        # Bind to ephemeral port
        self.server = await websockets.serve(self._handle_incoming, "0.0.0.0", 0)
        self.p2p_port = self.server.sockets[0].getsockname()[1]
        print(f"[MESH] P2P Listener active on port {self.p2p_port}")
        return self.p2p_port

    async def connect_to(self, direction, ip, port):
        uri = f"ws://{ip}:{port}"
        try:
            ws = await websockets.connect(uri)
            self.neighbors[direction] = ws
            print(f"[MESH] Connected to Neighbor {direction} at {uri}")
            
            # Send Handshake
            handshake = {
                "type": "P2P_HANDSHAKE",
                "beeId": self.bee_id
            }
            await ws.send(json.dumps(handshake))
            
            # Start Reader logic
            asyncio.create_task(self._read_loop(ws, direction))
            
        except Exception as e:
            print(f"[MESH] Failed to connect {direction}: {e}")

    async def _handle_incoming(self, ws):
        # For simplicity in this POC, we just read. 
        # In real logic, we'd map this WS to a direction based on handshake.
        try:
            async for message in ws:
                data = json.loads(message)
                if data['type'] == 'P2P_HANDSHAKE':
                    # Determine direction if possible, or just log
                    pass 
                else:
                    await self.message_handler(data)
        except:
            pass

    async def _read_loop(self, ws, direction):
        try:
            async for message in ws:
                data = json.loads(message)
                await self.message_handler(data)
        except:
            print(f"[MESH] Neighbor {direction} disconnected.")
            self.neighbors[direction] = None

    async def pulse(self, direction, payload):
        ws = self.neighbors.get(direction)
        if ws:
            try:
                await ws.send(json.dumps(payload))
            except:
                pass
