from collections import OrderedDict
import os
import subprocess
import threading
import time
from endstone_primebds.utils.configUtil import find_and_load_config, load_config

import psutil

def start_additional_servers(self):
        config = load_config()
        multiworld = config["modules"].get("multiworld", {})
        if not multiworld.get("enabled", False):
            return

        worlds = multiworld.get("worlds", OrderedDict())
        current_profile = config["modules"]["allowlist"].get("profile", "default")

        default_path = os.path.join("endstone_primebds", "utils", "default_server.properties")
        default_props = {}
        if os.path.isfile(default_path):
            with open(default_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, val = line.strip().split("=", 1)
                        default_props[key.strip()] = val.strip()

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

        def launch_endstone_server(folder, level_name, max_retries=1):
            attempt = 0
            while attempt <= max_retries:
                process = subprocess.Popen(
                    [sys.executable, "-m", "endstone", "--yes", f"--server-folder={folder}"],
                    cwd=multiworld_base_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                time.sleep(5)
                if process.poll() is not None:
                    print(f"[PrimeBDS] World '{level_name}' crashed or exited early (attempt {attempt + 1}).")
                    attempt += 1
                else:
                    return process
            print(f"[PrimeBDS] World '{level_name}' failed to start after {max_retries + 1} attempts.")
            return None

        def stop_process_for_folder(folder_name):
            to_stop = []
            with lock:
                for level_name, proc in self.multiworld_processes.items():
                    if level_name.startswith(folder_name):
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

        def copy_plugins_to_world(root_plugins_dir, world_plugins_dir):
            if not os.path.exists(world_plugins_dir):
                os.makedirs(world_plugins_dir, exist_ok=True)
            for item in os.listdir(root_plugins_dir):
                if not item.endswith(".whl"):
                    continue
                source_path = os.path.join(root_plugins_dir, item)
                target_path = os.path.join(world_plugins_dir, item)
                try:
                    shutil.copy2(source_path, target_path)
                except Exception as e:
                    print(f"[PrimeBDS] Failed to copy '{item}': {e}")

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

        def launch_world_threaded(world_key, settings, idx):
            if world_key == current_profile:
                return

            world_dir = os.path.join(multiworld_base_dir, world_key)
            os.makedirs(world_dir, exist_ok=True)
            stop_process_for_folder(world_dir)

            world_plugins_dir = os.path.join(world_dir, "plugins")
            copy_plugins_to_world(root_plugins_dir, world_plugins_dir)

            server_properties_path = os.path.join(world_dir, "server.properties")
            with open(server_properties_path, "w", encoding="utf-8") as f:
                for key, value in default_props.items():
                    f.write(f"{key}={value}\n")
                for key, value in settings.items():
                    value_str = str(value).lower() if isinstance(value, bool) else str(value)
                    f.write(f"{key}={value_str}\n")

            level_name = settings.get("level-name", world_key)
            with lock:
                if level_name in seen_level_names:
                    seen_level_names[level_name] += 1
                    level_name = f"{level_name}_{seen_level_names[level_name]}"
                else:
                    seen_level_names[level_name] = 0

            time.sleep(2)
            process = launch_endstone_server(world_key, level_name, max_retries=3)
            if not process:
                return

            with lock:
                self.multiworld_processes[level_name] = process

            port_str = settings.get("server-port")
            try:
                port = int(port_str)
            except (TypeError, ValueError):
                port = self.base_port + idx + 1
                print(f"[PrimeBDS] Invalid or missing port for '{level_name}', using fallback: {port}")

            with lock:
                self.multiworld_ports[level_name] = port

            threading.Thread(target=forward_output, args=(process.stdout, f"[{level_name}] "), daemon=True).start()
            threading.Thread(target=forward_output, args=(process.stderr, f"[{level_name}][ERR] "), daemon=True).start()

        # Start each world in a thread
        for idx, (world_key, settings) in enumerate(worlds.items()):
            threading.Thread(target=launch_world_threaded, args=(world_key, settings, idx), daemon=True).start()

def stop_additional_servers(self):
    def stop_world(level_name, process):
        if process.poll() is None:  # still running
            print(f"[PrimeBDS] Closing '{level_name}' (PID {process.pid})")

            try:
                if process.stdin:
                    try:
                        start_path = os.path.dirname(os.path.abspath(__file__))
                        config = find_and_load_config("primebds_data/config.json", start_path) or {}
                        server_properties = find_and_load_config("server.properties", start_path) or {}
                        multiworld = config.get("modules", {}).get("multiworld", {})
                        main_port = int(server_properties.get("server-port", 19132))
                        main_ip = multiworld.get("ip_main", "127.0.0.1")
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
    
def is_nested_multiworld_instance(self):
    return "plugins{}primebds_data{}multiworld".format(os.sep, os.sep) in os.path.abspath(__file__)
