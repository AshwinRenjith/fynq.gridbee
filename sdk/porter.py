import torch
import torch.nn as nn
import pickle
import base64
import copy

class GridbeePorter:
    """
    Hydrates a standard torch.nn.Module for the Gridbee Hive.
    Handles Mathematical Obfuscation and Serialization.
    """
    def __init__(self, model: nn.Module):
        self.model = model
        
    def prepare_for_hive(self):
        """
        1. Copies the model to CPU.
        2. Multiplies all parameter tensors by 10 (Masking).
        3. Serializes to a pickle object.
        """
        print("[PORTER] Hydrating model for hive distribution...")
        
        # Clone to avoid mutating the user's local instance
        hive_model = copy.deepcopy(self.model).to('cpu')
        
        with torch.no_grad():
            for name, param in hive_model.named_parameters():
                if param.requires_grad:
                    # Mathematical Obfuscation: Factor 10
                    param.data.mul_(10.0)
        
        print(f"[PORTER] Mathematical Obfuscation Applied (Factor 10).")
        
        # Serialize
        serialized_data = pickle.dumps(hive_model.state_dict())
        encoded_data = base64.b64encode(serialized_data).decode('utf-8')
        
        size_mb = len(encoded_data) / (1024 * 1024)
        print(f"[PORTER] Package Ready. Size: {size_mb:.2f} MB")
        
        return encoded_data, len(encoded_data)
