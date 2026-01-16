import click
import asyncio
import socket
import json
import websockets
import os
import sys

# Add current directory to path so we can import porter if needed locally, though ideally installed as package
sys.path.append(os.getcwd())

from porter import GridbeePorter

CONFIG_FILE = ".gridbee_config"

def save_config(queen_ip, hive_port):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"queenIp": queen_ip, "hivePort": hive_port}, f)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

async def scan_for_queen():
    UDP_PORT = 41234
    print(f"[CLI] Scanning for Hive on UDP {UDP_PORT}...")
    
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass
        
    sock.bind(('', UDP_PORT))
    
    # Wait for one packet
    data = await loop.sock_recv(sock, 1024)
    message = json.loads(data.decode())
    
    if message.get('type') == 'BEACON':
        print(f"[CLI] Queen Found at {message['queenIp']}")
        return message['queenIp'], message['hivePort']
    return None, None

async def submit_job(model_path):
    config = load_config()
    if not config:
        print("[ERROR] Not logged in. Run 'gridbee login' first.")
        return

    # Load Model (Dynamically import the file)
    # For simulation, we assume model_path is a .py file with a variable 'model' or class 'Model'
    # But to be robust, let's just assume the user passes a serialized package or we import a class.
    # SIMPLIFICATION: We will import the module given by path
    
    # Actually, let's keep it simple: The user writes a script that uses the SDK.
    # The CLI here acts as the "Runner". 
    # But the prompt asks for `gridbee submit --model path/to/model.py`.
    
    print(f"[CLI] Loading model from {model_path}...")
    import importlib.util
    spec = importlib.util.spec_from_file_location("user_model", model_path)
    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)
    
    # Assume the user defined a variable `model` in that file
    if not hasattr(user_module, 'model'):
        print("[ERROR] The script must define a 'model' variable (torch.nn.Module).")
        return
        
    porter = GridbeePorter(user_module.model)
    payload_data, size = porter.prepare_for_hive()
    
    uri = f"ws://{config['queenIp']}:{config['hivePort']}"
    if config['queenIp'] == "127.0.0.1": # fix for local testing
         uri = f"ws://localhost:{config['hivePort']}"

    print(f"[CLI] Conneting to Queen at {uri}...")
    
    async with websockets.connect(uri) as ws:
        submission = {
            "type": "JOB_SUBMISSION",
            "jobName": os.path.basename(model_path),
            "fileSize": size,
            "data": payload_data
        }
        await ws.send(json.dumps(submission))
        
        response = await ws.recv()
        ack = json.loads(response)
        
        if ack.get('type') == 'JOB_ACK':
            print(f"[SUCCESS] Job Submitted! ID: {ack['jobId']}")
        else:
            print(f"[ERROR] Hive rejected job: {response}")

@click.group()
def cli():
    pass

@cli.command()
def login():
    """Scan for the Queen and save connection info."""
    queen_ip, port = asyncio.run(scan_for_queen())
    if queen_ip:
        save_config(queen_ip, port)
        click.echo("[SUCCESS] Logged in to Hive.")

@cli.command()
@click.option('--model', required=True, help='Path to python file defining "model"')
def submit(model):
    """Submit a model to the Hive."""
    asyncio.run(submit_job(model))

@cli.command()
def status():
    """Check Hive Status."""
    click.echo("Telemetry not implemented yet.")

if __name__ == '__main__':
    cli()
