import threading
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
registered_commands = []
WORLD_COMMAND_HANDLER = None  # This should be a callable that takes (command: str)

@app.route('/health')
def health():
    return 'OK', 200

@app.route("/run", methods=["POST"])
def run_command():
    data = request.get_json(force=True)
    command = data.get("command")

    if not command:
        return jsonify({"error": "Missing 'command'"}), 400

    if WORLD_COMMAND_HANDLER:
        try:
            WORLD_COMMAND_HANDLER(command)
            return jsonify({"status": "ok", "executed": command})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "No handler set for command execution"}), 500


def start_flask_server(port: int, command_handler):
    """Start a Flask server on the given port with a command handler function"""
    global WORLD_COMMAND_HANDLER
    WORLD_COMMAND_HANDLER = command_handler

    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False),
        daemon=True
    )
    thread.start()
    
class MultiworldHttpClient:
    def __init__(self):
        self.endpoints = {}  # level_name -> URL string

    def register_world(self, level_name: str, port: int):
        """Registers a world and its Flask server port"""
        self.endpoints[level_name] = f"http://localhost:{port}/run"

    def send_command(self, level_name: str, command: str):
        """Sends a command to a registered world"""
        url = self.endpoints.get(level_name)
        if not url:
            print(f"[PrimeBDS] No endpoint registered for world '{level_name}'")
            return

        try:
            requests.post(url, json={"command": command})
        except Exception as e:
            print(f"[PrimeBDS] [{level_name}] Error: {e}")

def wait_for_flask_server(port, timeout=15):
    url = f"http://localhost:{port}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.5)
    return False