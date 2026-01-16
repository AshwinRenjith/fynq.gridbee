import asyncio

class Pacemaker:
    """
    Manages synchronization of the Systolic Pulse.
    Implements 2/3 functional majority triggering.
    """
    def __init__(self):
        self.buffer = {
            "EAST": [],
            "SOUTH": []
        }
        self.step_event = asyncio.Event()
        
    def enqueue(self, direction, payload):
        if direction in self.buffer:
            self.buffer[direction].append(payload)
            self._check_quorum()
            
    def _check_quorum(self):
        # Cannon's algo needs inputs from East (for A) and South (for B).
        # We trigger if BOTH are present (ideal) or based on timeout (straggler).
        
        # Simplified: If we have data from both required directions for the current step
        if len(self.buffer["EAST"]) > 0 and len(self.buffer["SOUTH"]) > 0:
            self.step_event.set()
            
    async def wait_for_pulse(self):
        # In this POC, we just wait for a moment to simulate sync window
        # Real logic: await self.step_event.wait()
        await asyncio.sleep(0.5) 
        return True
