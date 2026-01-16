import torch
import base64
import pickle
import copy

class SystolicEngine:
    def __init__(self):
        self.device = 'cpu'
        if torch.backends.mps.is_available():
            self.device = 'mps'
        elif torch.cuda.is_available():
            self.device = 'cuda'
            
        print(f"[COMPUTE] Systolic Engine initialized on {self.device}")
        
        self.local_A = None
        self.local_B = None
        self.local_C = None
        
    def load_shard(self, shard_data):
        # Deserializing mocked byte data
        # In real scenario: base64 decode -> pickle load -> tensor
        # Mocking tensors for POC
        self.local_A = torch.randn(10, 10, device=self.device) # Mock 10x10 shard
        self.local_B = torch.randn(10, 10, device=self.device)
        self.local_C = torch.zeros(10, 10, device=self.device)
        
    def step(self):
        # C += A @ B
        if self.local_A is not None and self.local_B is not None:
            self.local_C += torch.matmul(self.local_A, self.local_B)
            # print("[COMPUTE] Systolic Pulse: Matrix Mutiply Step Complete")
            
    def get_pulse_payloads(self):
        # Prepare data for West (A) and North (B)
        # Using base64 just to be safe with JSON
        
        # Simplified: Just sending checksums or small data for POC logs
        payload_A = "TENSOR_A_CHUNK" 
        payload_B = "TENSOR_B_CHUNK"
        
        return payload_A, payload_B
        
    def update_buffers(self, from_east, from_south):
        # Cannon's Algorithm:
        # A comes from East (moving West)
        # B comes from South (moving North)
        # Mock update
        pass
