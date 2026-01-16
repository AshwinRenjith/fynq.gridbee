import hashlib
import json

class BloomFilter:
    """
    Simplified probabilistic data structure for blacklisting.
    Uses a python set for POC instead of bitarray to reduce dependencies.
    """
    def __init__(self):
        self.blacklist = set()
        
    def add(self, item):
        self.blacklist.add(item)
        
    def __contains__(self, item):
        return item in self.blacklist

class Lymphocyte:
    """
    Handles BFT Signing and Verification.
    """
    def __init__(self, bee_id):
        self.bee_id = bee_id
        
    def sign(self, data_str):
        """
        Signs data with a hash of (Data + BeeID). 
        Real impl would use Private Key.
        """
        payload = f"{data_str}:{self.bee_id}"
        return hashlib.sha256(payload.encode()).hexdigest()
        
    def verify(self, data_str, signature, signer_id):
        """
        Verifies the signature matches the calculated hash.
        """
        expected_payload = f"{data_str}:{signer_id}"
        expected_sig = hashlib.sha256(expected_payload.encode()).hexdigest()
        return signature == expected_sig

class FlagManager:
    """
    Manages Gossip about malicious nodes.
    """
    def __init__(self, mesh, bloom_filter):
        self.mesh = mesh
        self.bloom = bloom_filter
        
    async def report_malice(self, target_id, reason):
        print(f"[IMMUNE] DETECTED MALICE from {target_id}: {reason}")
        self.bloom.add(target_id)
        
        # Gossip to neighbors
        flag = {
            "type": "GOSSIP_FLAG",
            "targetId": target_id,
            "reason": reason
        }
        
        # Broadcast to all connected neighbors
        for direction in ["NORTH", "SOUTH", "EAST", "WEST"]:
            await self.mesh.pulse(direction, flag)
