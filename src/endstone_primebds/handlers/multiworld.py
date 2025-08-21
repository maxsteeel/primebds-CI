import os
import shutil
import psutil
import subprocess
import sys
import socket
import threading
import time
from endstone_primebds.utils.config_util import find_and_load_config, load_config, save_properties_file, parse_properties_file

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from endstone_primebds.primebds import PrimeBDS

def start_additional_servers(self: "PrimeBDS"):
    config = load_config()
    multiworld = config["modules"].get("multiworld", {})
    worlds = multiworld.get("worlds", {})

    worlds = {
        name: cfg for name, cfg in worlds.items()
        if cfg.get("enabled", False)
    }

    if not any(world.get("enabled", False) for world in worlds.values()):
        return

    default_path = os.path.join("endstone_primebds", "utils", "default_server.properties")
    default_props = {}
    if os.path.isfile(default_path):
        default_props = parse_properties_file(default_path)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            print("[PrimeBDS] Could not locate project root containing 'plugins' and 'worlds'.")
            return
        current_dir = parent_dir

    DB_FOLDER = os.path.join(current_dir, 'plugins', 'primebds_data')
    multiworld_base_dir = os.path.join(DB_FOLDER, "multiworld")

    os.makedirs(DB_FOLDER, exist_ok=True)
    os.makedirs(multiworld_base_dir, exist_ok=True)

    root_plugins_dir = os.path.join(current_dir, "plugins")
    seen_level_names = {}
    lock = threading.Lock()

    for idx, (world_key, settings) in enumerate(worlds.items()):
        threading.Thread(
            target=start_world,
            args=(self, world_key, settings, idx, default_props, root_plugins_dir, multiworld_base_dir, seen_level_names, lock),
            daemon=True
        ).start()

def stop_additional_servers(self: "PrimeBDS"):
    def stop_world(level_name, process):
        if process.poll() is None:  # still running
            print(f"[PrimeBDS] Closing '{level_name}' (PID {process.pid})")

            try:
                if process.stdin:
                    try:
                        start_path = os.path.dirname(os.path.abspath(__file__))
                        server_properties = find_and_load_config("server.properties", start_path) or {}
                        main_port = int(server_properties.get("server-port", 19132))
                        hostname = socket.gethostname()
                        main_ip = socket.gethostbyname(hostname)
                        process.stdin.write(f"send @a {main_ip} {main_port}\n") # send back to main
                        process.stdin.write("stop\n")
                        process.stdin.flush()
                    except Exception as e:
                        print(f"[PrimeBDS] Failed to send stop command to '{level_name}': {e}")

                try:
                    process.wait(timeout=3)
                    print(f"[PrimeBDS] World '{level_name}' stopped correctly")
                except subprocess.TimeoutExpired:
                    try:
                        parent = psutil.Process(process.pid)
                        for child in parent.children(recursive=True):
                            try:
                                child.kill()
                            except psutil.NoSuchProcess:
                                pass
                        parent.kill()
                        print(f"[PrimeBDS] Killed process tree for world '{level_name}'.")
                    except psutil.NoSuchProcess:
                        print(f"[PrimeBDS] Process for world '{level_name}' already exited.")
                    except Exception as e:
                        print(f"[PrimeBDS] Error killing process tree for world '{level_name}': {e}")
            except Exception as e:
                    print(f"[PrimeBDS] Error killing process tree for world '{level_name}': {e}")

    threads = []

    for level_name, process in list(self.multiworld_processes.items()):
        thread = threading.Thread(target=stop_world, args=(level_name, process))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    self.multiworld_processes.clear()
    
def start_world(
    self: "PrimeBDS",
    world_key: str,
    settings: dict,
    idx: int,
    default_props: dict,
    root_plugins_dir: str,
    multiworld_base_dir: str,
    seen_level_names: dict,
    lock: threading.Lock
):
    """Start a single world with its own properties and plugins."""

    if world_key == self.server.level.name:
        print(f"[PrimeBDS] Skipping main world '{world_key}'")
        return

    world_dir = os.path.join(multiworld_base_dir, world_key)
    os.makedirs(world_dir, exist_ok=True)

    to_stop = []
    with lock:
        for level_name, proc in self.multiworld_processes.items():
            if level_name.startswith(world_key):
                to_stop.append(level_name)

    for level_name in to_stop:
        proc = self.multiworld_processes.get(level_name)
        if proc is None:
            continue
        print(f"[PrimeBDS] Attempting to stop existing process for '{level_name}'")
        try:
            if proc.stdin:
                proc.stdin.write("stop\n")
                proc.stdin.flush()
            try:
                proc.wait(timeout=5)
                print(f"[PrimeBDS] Process for '{level_name}' stopped gracefully.")
            except subprocess.TimeoutExpired:
                print(f"[PrimeBDS] Process for '{level_name}' did not stop in time, killing...")
                proc.kill()
                proc.wait()
                print(f"[PrimeBDS] Process for '{level_name}' killed.")
        except Exception as e:
            print(f"[PrimeBDS] Error stopping process for '{level_name}': {e}")
        with lock:
            self.multiworld_processes.pop(level_name, None)
            self.multiworld_ports.pop(level_name, None)

    world_plugins_dir = os.path.join(world_dir, "plugins")
    if not copy_plugins_to_world(root_plugins_dir, world_plugins_dir):
        print(f"[PrimeBDS] Warning: Not all plugins copied for world '{world_key}'")

    server_properties_path = os.path.join(world_dir, "server.properties")
    merged_props = {**default_props, **settings}
    save_properties_file(server_properties_path, merged_props)

    level_name = settings.get("level-name", world_key)
    with lock:
        if level_name in seen_level_names:
            seen_level_names[level_name] += 1
            level_name = f"{level_name}_{seen_level_names[level_name]}"
        else:
            seen_level_names[level_name] = 0

    process = launch_endstone_server(multiworld_base_dir, world_key, level_name, max_retries=3)
    if not process:
        return

    with lock:
        self.multiworld_processes[level_name] = process

    try:
        port = int(settings.get("server-port"))
    except (TypeError, ValueError):
        port = self.base_port + idx + 1
        print(f"[PrimeBDS] Invalid or missing port for '{level_name}', using fallback: {port}")

    with lock:
        self.multiworld_ports[level_name] = port

    for stream, prefix in [
        (process.stdout, f"[{level_name}] "),
        (process.stderr, f"[{level_name}][ERR] ")
    ]:
        threading.Thread(
            target=forward_output,
            args=(stream, prefix),
            daemon=True
        ).start()

def stop_world(self, world_key: str):
    """Stop a single world by name."""
    lock = threading.Lock()
    to_stop = []
    with lock:
        for level_name, proc in self.multiworld_processes.items():
            if level_name.startswith(world_key):
                to_stop.append(level_name)

    for level_name in to_stop:
        proc = self.multiworld_processes.get(level_name)
        if proc is None:
            continue

        print(f"[PrimeBDS] Stopping world '{level_name}'")
        try:
            if proc.stdin:
                proc.stdin.write("stop\n")
                proc.stdin.flush()
            try:
                proc.wait(timeout=5)
                print(f"[PrimeBDS] Process for '{level_name}' stopped gracefully.")
            except subprocess.TimeoutExpired:
                print(f"[PrimeBDS] Process for '{level_name}' did not stop in time, killing...")
                proc.kill()
                proc.wait()
                print(f"[PrimeBDS] Process for '{level_name}' killed.")
        except Exception as e:
            print(f"[PrimeBDS] Error stopping process for '{level_name}': {e}")

        with lock:
            self.multiworld_processes.pop(level_name, None)
            self.multiworld_ports.pop(level_name, None)

def is_nested_multiworld_instance():
    return "plugins{}primebds_data{}multiworld".format(os.sep, os.sep) in os.path.abspath(__file__)

def launch_endstone_server(multiworld_base_dir: str, folder: str, level_name: str, max_retries: int = 3):
    """Launch an Endstone server with retry logic."""
    for attempt in range(max_retries + 1):
        process = subprocess.Popen(
            [sys.executable, "-m", "endstone", "--yes", f"--server-folder={folder}"],
            cwd=multiworld_base_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(1)

        if process.poll() is None:
            return process

        print(f"[PrimeBDS] World '{level_name}' crashed or exited early (attempt {attempt + 1}).")

    print(f"[PrimeBDS] World '{level_name}' failed to start after {max_retries + 1} attempts.")
    return None

def forward_output(stream, prefix):
    while True:
        try:
            line = stream.readline()
            if not line:
                break
            print(f"{prefix}{line}", end='')
        except Exception as e:
            print(f"{prefix}[ReadError]: {e}")
            break

def copy_plugins_to_world(root_plugins_dir, world_plugins_dir, timeout=5):
    os.makedirs(world_plugins_dir, exist_ok=True)

    for file in os.listdir(world_plugins_dir):
        if file.endswith(".whl"):
            try:
                os.remove(os.path.join(world_plugins_dir, file))
            except Exception as e:
                print(f"[PrimeBDS] Failed to remove '{file}': {e}")

    expected_plugins = []
    for item in os.listdir(root_plugins_dir):
        if not item.endswith(".whl"):
            continue
        source_path = os.path.join(root_plugins_dir, item)
        target_path = os.path.join(world_plugins_dir, item)
        try:
            shutil.copy2(source_path, target_path)
            expected_plugins.append(item)
        except Exception as e:
            print(f"[PrimeBDS] Failed to copy '{item}': {e}")

    start = time.time()
    while time.time() - start < timeout:
        existing = [f for f in os.listdir(world_plugins_dir) if f.endswith(".whl")]
        if all(plugin in existing for plugin in expected_plugins):
            return True
        time.sleep(0.05)

    return False