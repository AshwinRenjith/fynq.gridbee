import torch
import torch.nn as nn

class SoylentGreenModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(10, 50)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(50, 2)
        
    def forward(self, x):
        return self.fc2(self.relu(self.fc1(x)))

# The CLI expects a 'model' variable
model = SoylentGreenModel()
