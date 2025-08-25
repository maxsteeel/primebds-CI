import json
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
    current_dir = os.path.dirname(current_dir)

CONFIG_FOLDER = os.path.join(current_dir, 'plugins', 'primebds_data')
CONFIG_PATH = os.path.join(CONFIG_FOLDER, 'config.json')
PERMISSIONS_PATH = os.path.join(CONFIG_FOLDER, 'permissions.json')
RULES_PATH = os.path.join(CONFIG_FOLDER, 'rules.txt')

os.makedirs(CONFIG_FOLDER, exist_ok=True)

PERMISSIONS_DEFAULT = {
        "Default": [
            "endstone.broadcast",
            "endstone.broadcast.user",
            "endstone.command.version",
            "endstone.command.plugins",
            "primebds.command.ping",
            "primebds.command.reply",
            "minecraft.command.list",
            "minecraft.command.help",
            "minecraft.command.tell",
            "minecraft.command.me",
        ],
        "Operator": [
            "*"
        ],
    }

cache = None 
permissions_cache = None
rules_cache = None

def load_config():
    """Load or create a configuration file in primebds_info/config.json, cached in memory."""
    global cache
    if cache is not None:
        return cache

    default_config = {"commands": {}}

    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        cache = default_config
        save_config(cache)
        return cache

    try:
        content = open_text_file(CONFIG_PATH, "r")
        if content:
            cache = json.loads(content)
        else:
            cache = default_config
            save_config(cache)
    except (OSError, json.JSONDecodeError):
        cache = default_config
        save_config(cache)

    return cache

def save_config(config: dict, update_cache: bool = False) -> None:
    global cache
    if update_cache:
        cache = config

    text = json.dumps(config, indent=4)
    open_text_file(CONFIG_PATH, "w", text=text)

def save_permissions(permissions: dict, update_cache: bool = True) -> None:
    global permissions_cache

    os.makedirs(CONFIG_FOLDER, exist_ok=True)
    content = json.dumps(permissions, indent=4)
    open_text_file(PERMISSIONS_PATH, mode="w", text=content)

    if update_cache:
        permissions_cache = permissions

def load_permissions(default_permissions=None, cache=True):
    global permissions_cache
    if permissions_cache is not None and cache:
        return permissions_cache

    if not os.path.exists(PERMISSIONS_PATH):
        if default_permissions is None:
            default_permissions = PERMISSIONS_DEFAULT
        save_permissions(default_permissions)
        permissions_cache = default_permissions
    else:
        content = open_text_file(PERMISSIONS_PATH, mode="r")
        if content:
            permissions_cache = json.loads(content)
        else:
            permissions_cache = default_permissions or PERMISSIONS_DEFAULT

    return permissions_cache

def reset_permissions(default_permissions=None):
    """Reset permissions.json to default permissions."""
    global permissions_cache

    if default_permissions is None:
        default_permissions = PERMISSIONS_DEFAULT

    open_text_file(PERMISSIONS_PATH, "w", text=json.dumps(default_permissions, indent=4))

    permissions_cache = default_permissions.copy()

def save_rules(rules):
    os.makedirs(CONFIG_FOLDER, exist_ok=True)
    content = "\n".join(line.strip() for line in rules) + "\n"
    open_text_file(RULES_PATH, mode="w", text=content)

def load_rules(default_rules=None):
    global rules_cache
    if rules_cache:
        return rules_cache

    if not os.path.exists(RULES_PATH):
        if default_rules is None:
            default_rules = []
        save_rules(default_rules)
        rules_cache = default_rules
    else:
        content = open_text_file(RULES_PATH, "r")
        if content is None:
            return []
        return [line.strip() for line in content.splitlines() if line.strip()]
    return rules_cache

def save_properties_file(path: str, props: dict) -> bool:
    try:
        content = "\n".join(f"{key}={value}" for key, value in props.items())
        result = open_text_file(path, mode="w", text=content)
        return result is not None
    except Exception as e:
        print(f"Failed to save properties file {path}: {e}")
        return False

def find_and_load_config(
    filename,
    start_path=None,
    forbidden_subdir="multiworld",
    max_depth=20,
    refresh=False
):
    if not hasattr(find_and_load_config, "_cache"):
        find_and_load_config._cache = {}

    if not refresh and filename in find_and_load_config._cache:
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
                        content = open_text_file(candidate_path)
                        config_data = json.loads(content)
                    elif filename.endswith(".properties"):
                        config_data = parse_properties_file(candidate_path)
                    else:
                        raise ValueError(f"Unsupported file type: {filename}")

                    find_and_load_config._cache[filename] = config_data
                    return config_data
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")
                    if refresh:
                        # if forcing reload, don't return stale cache
                        return None
                    return find_and_load_config._cache.get(filename)

        parent = os.path.dirname(current_path)
        if parent == current_path:
            break
        current_path = parent
        depth += 1

    find_and_load_config._cache[filename] = None
    return None

def parse_properties_file(path: str) -> dict:
    props = {}
    content = open_text_file(path)

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            props[key.strip()] = val.strip()
    return props

def open_text_file(path: str, mode: str = "r", text: str = None) -> str | None: # hopefully fixes multiworld issues
    """
    Universal text file handler.
    - For reading: mode="r", returns file content as str.
    - For writing: mode="w", text=<string to write>
    Tries UTF-8, UTF-8-sig, Latin-1, CP1252 automatically.
    """
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    if "r" in mode:
        for enc in encodings:
            try:
                with open(path, mode, encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        return None

    elif "w" in mode and text is not None:
        for enc in encodings:
            try:
                with open(path, mode, encoding=enc) as f:
                    f.write(text)
                    return text
            except UnicodeEncodeError:
                continue
        return None

    else:
        raise ValueError("Invalid mode or missing text for writing.")