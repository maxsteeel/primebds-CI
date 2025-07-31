import json
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
    current_dir = os.path.dirname(current_dir)

CONFIG_FOLDER = os.path.join(current_dir, 'plugins', 'primebds_data')
CONFIG_PATH = os.path.join(CONFIG_FOLDER, 'config.json')

os.makedirs(CONFIG_FOLDER, exist_ok=True)

def save_config(config):
    """Save the current config state to disk."""
    with open(CONFIG_PATH, "w") as config_file:
        json.dump(config, config_file, indent=4)

def parse_properties_file(path):
    props = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                props[key.strip()] = val.strip()
    return props

cache = None 
def load_config():
    """Load or create a configuration file in primebds_info/config.json, cached in memory"""
    global cache
    if cache is not None:
        return cache

    if not os.path.exists(CONFIG_PATH):
        default_config = {
            "commands": {}
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
            json.dump(default_config, config_file, indent=4)
        cache = default_config
    else:
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            cache = json.load(config_file)

    return cache

def find_and_load_config(filename, start_path=None, forbidden_subdir="multiworld", max_depth=20):
    """
    Searches upward for a file named `filename` not within `forbidden_subdir`
    If found, loads and returns it as a dict (supports .json and .properties)
    Caches the loaded config per filename to avoid repeated loads
    """
    if not hasattr(find_and_load_config, "_cache"):
        find_and_load_config._cache = {}

    if filename in find_and_load_config._cache:
        return find_and_load_config._cache[filename]

    if start_path is None:
        start_path = os.getcwd()

    current_path = os.path.abspath(start_path)
    depth = 0

    while depth < max_depth:
        candidate_path = os.path.join(current_path, filename)

        if os.path.isfile(candidate_path):
            norm_path = os.path.normpath(candidate_path)
            path_parts = norm_path.split(os.sep)
            if forbidden_subdir not in path_parts:
                try:
                    if filename.endswith(".json"):
                        with open(candidate_path, "r", encoding="utf-8") as f:
                            config_data = json.load(f)
                            find_and_load_config._cache[filename] = config_data
                            return config_data
                    elif filename.endswith(".properties"):
                        config_data = parse_properties_file(candidate_path)
                        find_and_load_config._cache[filename] = config_data
                        return config_data
                    else:
                        raise ValueError(f"Unsupported file type: {filename}")
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")
                    return None

        parent = os.path.dirname(current_path)
        if parent == current_path:
            break
        current_path = parent
        depth += 1

    find_and_load_config._cache[filename] = None
    return None