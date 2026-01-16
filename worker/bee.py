import signal
import sys

# ... existing imports ...

class WorkerBee:
    def __init__(self):
        # ... existing init ...
        self.stop_event = asyncio.Event()
        self.websocket = None # Store ws for cleanup

    async def shutdown(self):
        print("\n[BEE] Shutting down gracefully...")
        try:
            if self.websocket and self.websocket.open:
                goodbye = {"type": "GOODBYE", "beeId": self.bee_id}
                await self.websocket.send(json.dumps(goodbye))
                print("[BEE] Sent GOODBYE to Hive.")
                await self.websocket.close()
        except:
            pass
        finally:
            self.stop_event.set()

    # ... existing methods ...

    async def run(self):
        # Register signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        p2p_port = await self.mesh.start_server()
        
        # ... discovery ...
        
        try:
            async with websockets.connect(self.queen_uri) as websocket:
                self.websocket = websocket
                
                # ... handshake ...
                initial_metrics = self.monitor.capture_metrics()
                handshake = {
                    "type": "HANDSHAKE",
                    "beeId": self.bee_id,
                    "metrics": initial_metrics,
                    "p2pPort": p2p_port
                }
                await websocket.send(json.dumps(handshake))
                
                response = await websocket.recv()
                ack = json.loads(response)
                
                if ack.get('type') == 'ACK':
                    coords = ack['coordinates']
                    self.role = ack['role']
                    print(f"[CONNECTED] Assigned to Cell ({coords['i']}, {coords['j']}). Role: {self.role}.")
                    
                    if self.role == 'PRINCE':
                        print("[HA] Monitoring Hive Heartbeats...")
                        asyncio.create_task(self.raft.run_election_loop(None, self.promote_to_queen))
                else:
                    return

                while not self.stop_event.is_set():
                    try:
                        # Use wait_for with the websocket recv
                        # But we also need to check stop_event
                        # We can race recv() and stop_event.wait()
                        
                        recv_task = asyncio.create_task(websocket.recv())
                        wait_task = asyncio.create_task(self.stop_event.wait())
                        
                        done, pending = await asyncio.wait(
                            [recv_task, wait_task], 
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        if wait_task in done:
                            recv_task.cancel()
                            break

                        message = recv_task.result()
                        data = json.loads(message)
                        
                        # ... message handling ...
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("[BEE] Connection to Queen Lost!")
                        break
                    except Exception as e:
                         print(f"[BEE] Error in loop: {e}")
                         # break? No, try to continue unless fatal
                    
                    # Heartbeat
                    should_send, metrics = self.monitor.should_pulse()
                    if should_send:
                        payload = {"type": "HEARTBEAT", "beeId": self.bee_id, "metrics": metrics}
                        await websocket.send(json.dumps(payload))
        finally:
            print("[BEE] Process Terminated.")


# Local Imports
try:
    from lead_logic import GrecoLatinGenerator, ParityBuffer
    from mesh import BitchatMesh
    from systolic import SystolicEngine
    from pacemaker import Pacemaker
    from immune import Lymphocyte, BloomFilter, FlagManager
except ImportError:
    from worker.lead_logic import GrecoLatinGenerator, ParityBuffer
    from worker.mesh import BitchatMesh
    from worker.systolic import SystolicEngine
    from worker.pacemaker import Pacemaker
    from worker.immune import Lymphocyte, BloomFilter, FlagManager

# Configuration
UDP_PORT = 41234
HEARTBEAT_INTERVAL_SEC = 60
SPIKE_THRESHOLD = 0.05

class DiscoveryChain:
    """Handles Queen Discovery via UDP"""
    
    @staticmethod
    async def listen_udp():
        print(f"[BEE] Listening for Queen Beacon on port {UDP_PORT}...")
        
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) # MacOS support
        except AttributeError:
            pass
            
        sock.bind(('', UDP_PORT))
        
        while True:
            data = await loop.sock_recv(sock, 1024)
            try:
                message = json.loads(data.decode())
                if message.get('type') == 'BEACON':
                    print(f"[BEE] Discovered Queen at {message['queenIp']} (Version: {message['hiveVersion']})")
                    sock.close() # Close usage of port 41234 so we can potentially bind later
                    return message['queenIp'], message['hivePort']
            except json.JSONDecodeError:
                pass
                
class SpikeMonitor:
    def __init__(self):
        self.last_metrics = self.capture_metrics()
        self.last_sent_time = 0
        
    def capture_metrics(self):
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        
        # Mock VRAM for now (requires nvidia-smi usually)
        # Using swap free as a placeholder for 'secondary memory' if needed, or just 0
        # Mocking High VRAM to ensure Prince Status for testing
        vram_free = 8000 
        
        return {
            "vramFree": vram_free,
            "ramFree": vm.available / (1024 * 1024), # MB
            "cpuIdle": 100 - cpu,
            "jitter": 0 # Placeholder for network ping
        }
        
    def should_pulse(self):
        current_metrics = self.capture_metrics()
        now = time.time()
        
        if now - self.last_sent_time > HEARTBEAT_INTERVAL_SEC:
            self.last_sent_time = now
            self.last_metrics = current_metrics
            return True, current_metrics
            
        ram_delta = abs(current_metrics['ramFree'] - self.last_metrics['ramFree']) / (self.last_metrics['ramFree'] or 1)
        cpu_delta = abs(current_metrics['cpuIdle'] - self.last_metrics['cpuIdle']) / 100.0
        
        if ram_delta > SPIKE_THRESHOLD or cpu_delta > SPIKE_THRESHOLD:
            self.last_sent_time = now
            self.last_metrics = current_metrics
            return True, current_metrics
            
        return False, None

class WorkerBee:
    def __init__(self):
        self.bee_id = str(uuid.uuid4())
        self.monitor = SpikeMonitor()
        self.raft = RaftConsensus(self.bee_id)
        
        self.mesh = BitchatMesh(self.bee_id, self.handle_p2p_message)
        self.engine = SystolicEngine()
        self.pacemaker = Pacemaker()
        
        # Immune System
        self.bloom = BloomFilter()
        self.lymphocyte = Lymphocyte(self.bee_id)
        self.flags = FlagManager(self.mesh, self.bloom)
        
        self.queen_uri = None
        self.role = "WORKER"
        
    async def promote_to_queen(self):
        print("[HA] I am initializing Queen Protocols...")
        loop = asyncio.get_running_loop()
        async def broadcast_beacon():
            print("[QUEEN] Python UDP Beacon Active")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while True:
                payload = json.dumps({
                    "type": "BEACON",
                    "queenIp": "127.0.0.1",
                    "hivePort": UDP_PORT,
                    "hiveVersion": "0.2.0-PY",
                    "timestamp": time.time()
                }).encode()
                sock.sendto(payload, ('255.255.255.255', UDP_PORT))
                await asyncio.sleep(2)
        loop.create_task(broadcast_beacon())

    async def handle_block_assignment(self, payload):
        print(f"[LEAD] Received Block {payload['blockId']}/{payload['totalBlocks']} from Queen.")
        N = 3
        gls_grid = GrecoLatinGenerator.generate_gls(N)
        print(f"[SHARD] Generated {N}x{N} Greco-Latin Square for recursive sharding.")
        parity = ParityBuffer(N*N)
        for r in range(N):
            for c in range(N):
                (task_id, data_id) = gls_grid[r][c]
                mock_shard = f"SHARD_T{task_id}_D{data_id}".encode()
                parity.add_shard(f"{r}-{c}", mock_shard)
                print(f"[SHARD] Dispatched Task {task_id} / Data {data_id} to cell ({r},{c})")
        print("[RELIABILITY] Parity XOR Buffer Initialized. Monitoring for dropouts...")

    async def handle_shard_assignment(self, payload):
        print(f"[WORKER] Received Shard Assignment (Task {payload['taskId']}) from Lead.")
        self.engine.load_shard(payload['fragment']) 
        
        self.engine.step()
        
        # Sign Result
        result_hash = self.lymphocyte.sign("RESULT_DATA_MOCK")
        print(f"[IMMUNE] Signed Result: {result_hash[:8]}...")
        
        payload_A, payload_B = self.engine.get_pulse_payloads()
        await self.mesh.pulse("WEST", {"type": "PULSE_DATA", "step": 1, "payload": payload_A})
        await self.mesh.pulse("NORTH", {"type": "PULSE_DATA", "step": 1, "payload": payload_B})
        
        print(f"[PULSE] Systolic Pulse Fired (West/North). Waiting for Quorum...")

    async def handle_p2p_message(self, data):
        """Callback for incoming P2P messages"""
        
        # 1. Check Blacklist
        sender_id = data.get('beeId') # Assuming handshake or included in packet
        if sender_id and sender_id in self.bloom:
            print(f"[IMMUNE] Blocked message from blacklisted node: {sender_id}")
            return

        if data['type'] == 'PULSE_DATA':
            # Pacemaker logic would go here
            pass
            
        elif data['type'] == 'GOSSIP_FLAG':
             print(f"[IMMUNE] Received GOSSIP about {data['targetId']}: {data['reason']}")
             self.bloom.add(data['targetId'])
             # Propagate? (TTL logic needed in real impl to prevent loops)

    async def run(self):
        # Register signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        p2p_port = await self.mesh.start_server()
        
        # ... discovery ...
        
        try:
            queen_ip, queen_port = await DiscoveryChain.listen_udp()
            self.queen_uri = f"ws://{queen_ip}:{queen_port}"
            if queen_ip == "127.0.0.1": self.queen_uri = f"ws://localhost:{queen_port}"
            
            print(f"[BEE] Connecting to Hive at {self.queen_uri}...")
            
            async with websockets.connect(self.queen_uri) as websocket:
                self.websocket = websocket
                
                # ... handshake ...
                initial_metrics = self.monitor.capture_metrics()
                handshake = {
                    "type": "HANDSHAKE",
                    "beeId": self.bee_id,
                    "metrics": initial_metrics,
                    "p2pPort": p2p_port
                }
                await websocket.send(json.dumps(handshake))
                
                response = await websocket.recv()
                ack = json.loads(response)
                
                if ack.get('type') == 'ACK':
                    coords = ack['coordinates']
                    self.role = ack['role']
                    print(f"[CONNECTED] Assigned to Cell ({coords['i']}, {coords['j']}). Role: {self.role}.")
                    
                    if self.role == 'PRINCE':
                        print("[HA] Monitoring Hive Heartbeats...")
                        asyncio.create_task(self.raft.run_election_loop(None, self.promote_to_queen))
                else:
                    return

                while not self.stop_event.is_set():
                    try:
                        # Use wait_for with the websocket recv
                        # But we also need to check stop_event
                        # We can race recv() and stop_event.wait()
                        
                        recv_task = asyncio.create_task(websocket.recv())
                        wait_task = asyncio.create_task(self.stop_event.wait())
                        
                        done, pending = await asyncio.wait(
                            [recv_task, wait_task], 
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        if wait_task in done:
                            recv_task.cancel()
                            break

                        message = recv_task.result()
                        data = json.loads(message)
                        
                        if data.get('type') == 'APPEND_ENTRIES':
                            self.raft.process_append_entries(data)
                        elif data.get('type') == 'BLOCK_ASSIGNMENT':
                            await self.handle_block_assignment(data)
                        elif data.get('type') == 'SHARD_ASSIGNMENT':
                            await self.handle_shard_assignment(data)
                        elif data.get('type') == 'NEIGHBOR_UPDATE':
                            conn = data['connectionInfo']
                            direction = data['direction']
                            target_ip = conn['ip'].replace("::ffff:", "")
                            if target_ip == "127.0.0.1": target_ip = "localhost"  
                            await self.mesh.connect_to(direction, target_ip, conn['port'])
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("[BEE] Connection to Queen Lost!")
                        break
                    except Exception as e:
                         print(f"[BEE] Error in loop: {e}")
                         if self.stop_event.is_set(): break
                    
                    # Heartbeat
                    should_send, metrics = self.monitor.should_pulse()
                    if should_send:
                        payload = {"type": "HEARTBEAT", "beeId": self.bee_id, "metrics": metrics}
                        await websocket.send(json.dumps(payload))
        finally:
            print("[BEE] Process Terminated.")

if __name__ == "__main__":
    bee = WorkerBee()
    asyncio.run(bee.run())
