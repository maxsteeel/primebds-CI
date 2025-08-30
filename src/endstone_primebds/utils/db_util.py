import json
import os
import sqlite3
import threading
from dataclasses import dataclass, fields
import time
from typing import List, Tuple, Any, Dict, Optional
from endstone import Player
from endstone.inventory import ItemStack
from endstone.level import Location
from endstone.util import Vector
from endstone_primebds.utils.address_util import same_subnet
from endstone_primebds.utils.mod_util import format_time_remaining
from endstone_primebds.utils.time_util import TimezoneUtils
from endstone_primebds.utils.config_util import find_server_properties, find_and_load_config, parse_properties_file, find_folder
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
    current_dir = os.path.dirname(current_dir)

DB_FOLDER = os.path.join(current_dir, 'plugins', 'primebds_data', "database")
os.makedirs(DB_FOLDER, exist_ok=True)

@dataclass
class ServerData:
    last_shutdown_time: int
    allowlist_profile: str

@dataclass
class NameBans:
    name: str
    banned_time: int
    ban_reason: str

@dataclass
class User:
    xuid: str
    uuid: str
    name: str
    ping: int
    device_os: str
    device_id: str
    unique_id: int
    client_ver: str
    internal_rank: str
    gamemode: int
    xp: int
    perms: str
    is_silent_muted: int
    is_afk: int
    is_vanish: int
    last_messaged: str
    last_join: int
    last_leave: int
    last_logout_pos: str
    last_logout_dim: str
    last_vanish_blob: bytes
    enabled_mt: int
    enabled_ss: int
    enabled_ms: int
    enabled_as: int
    enabled_sc: int

@dataclass
class Alts:
    main_name: str
    main_xuid: str
    alt_name: str
    alt_xuid: str
    expiry: int

@dataclass
class ModLog:
    xuid: str
    name: str
    is_muted: bool
    mute_time: int
    mute_reason: str
    is_banned: bool
    banned_time: int
    ban_reason: str
    ip_address: str
    is_ip_banned: bool
    is_ip_muted: bool
    is_jailed: bool
    jail_time: int
    jail_reason: str
    jail: str
    jail_gamemode: str
    return_jail_pos: str
    return_jail_dim: str

@dataclass
class Warn:
    id: int
    xuid: Optional[str]
    name: Optional[str]
    warn_reason: str
    warn_time: datetime
    added_by: Optional[str]

@dataclass
class Note:
    id: int
    xuid: Optional[str]
    name: Optional[str]
    note: str
    timestamp: datetime
    added_by: Optional[str]

@dataclass
class PunishmentLog:
    id: int
    xuid: str
    name: str
    action_type: str
    reason: str
    timestamp: int
    duration: Optional[int]

@dataclass
class Jails:
    name: str
    pos: str

@dataclass
class Warps:
    name: str
    pos: str
    displayname: str
    category: str
    description: str
    cost: int

@dataclass
class Inventory:
    name: str
    xuid: str
    slot_type: str
    slot: int
    type: str
    amount: int
    damage: int
    display_name: str
    enchants: str
    lore: str
    unbreakable: bool
    data: int

# DB
class DatabaseManager:
    _lock = threading.Lock()

    def __init__(self, db_name: str):
        start_path = os.path.dirname(os.path.abspath(__file__))
        config = find_and_load_config("primebds_data/config.json", start_path, "multiworld", 20, True)
        main_server_properties = find_and_load_config("server.properties", start_path)
        local_server_properties = parse_properties_file(find_server_properties(start_path))

        main_level = main_server_properties.get("level-name", "Unknown")
        level = local_server_properties.get("level-name", "Unknown")

        if main_level.lower() == level.lower():
            self.db_path = os.path.join(DB_FOLDER, db_name if db_name.endswith('.db') else db_name + '.db')
        else:
            multiworld = config.get("modules", {}).get("multiworld", {})
            worlds = multiworld.get("worlds", {})
            is_enabled = worlds[level].get("enabled", False)
            if is_enabled:
                main_root = find_folder("primebds_data/database", start_path, "multiworld", 20, True)
                if main_root:
                    self.db_path = os.path.join(main_root, db_name if db_name.endswith('.db') else db_name + '.db')
                    print("DEBUG: SUB-WORLD DB LINKED")
                else:
                    self.db_path = os.path.join(DB_FOLDER, db_name if db_name.endswith('.db') else db_name + '.db')
            else:
                self.db_path = os.path.join(DB_FOLDER, db_name if db_name.endswith('.db') else db_name + '.db')

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")  # Enable WAL for concurrency
        self.cursor = self.conn.cursor()

    def execute(self, query: str, params: Tuple = (), readonly=False) -> sqlite3.Cursor:
        if readonly:
            read_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = read_conn.cursor()
            cursor.execute(query, params)
            return cursor
        else:
            with self._lock:
                self.cursor.execute(query, params)
                if not query.strip().upper().startswith("SELECT"):
                    self.conn.commit()
                return self.cursor

    def create_table(self, table_name: str, columns: Dict[str, str], unique: list = None):
        column_definitions = ', '.join([f"{col} {dtype}" for col, dtype in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions})"
        with self._lock:
            self.cursor.execute(query)
            self.conn.commit()

        if unique:
            index_name = f"idx_{table_name}_{'_'.join(unique)}"
            cols = ', '.join(unique)
            self.cursor.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name} ({cols})"
            )
            self.conn.commit()


    def insert(self, table_name: str, data: Dict[str, Any]):
        if not data:
            raise ValueError("Insert data cannot be empty")

        with self._lock:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1] for row in self.cursor.fetchall()}

            for col, value in data.items():
                if col not in existing_columns:
                    col_type = "INTEGER" if isinstance(value, (int, bool)) else "REAL" if isinstance(value, float) else "TEXT"
                    default = 0 if col_type == "INTEGER" else 0.0 if col_type == "REAL" else "''"
                    self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type} DEFAULT {default}")

            values = tuple(int(v) if isinstance(v, bool) else v for v in data.values())
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            self.cursor.execute(query, values)
            self.conn.commit()

    def insert_session(self, xuid: str, name: str, start_time: int):
        with self._lock:
            self.cursor.execute(
                "INSERT INTO sessions_log (xuid, name, start_time, end_time) VALUES (?, ?, ?, NULL)",
                (xuid, name, start_time)
            )
            self.conn.commit()

    def ensure_user_table_columns(self):
        with self._lock:
            self.cursor.execute("PRAGMA table_info(users)")
            existing_columns = [col[1] for col in self.cursor.fetchall()]

            for f in fields(User):
                if f.name not in existing_columns:
                    self.cursor.execute(
                        f"ALTER TABLE users ADD COLUMN {f.name} {self.get_sql_type(f.type)} DEFAULT 0"
                    )
            self.conn.commit()

    def get_sql_type(self, py_type):
        mapping = {int: "INTEGER", str: "TEXT", float: "REAL"}
        return mapping.get(py_type, "TEXT")

    def fetch_all(self, table_name: str) -> List[Dict[str, Any]]:
        with self._lock:
            self.cursor.execute(f"SELECT * FROM {table_name}")
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def fetch_by_condition(self, table_name: str, condition: str, params: Tuple) -> List[Dict[str, Any]]:
        with self._lock:
            query = f"SELECT * FROM {table_name} WHERE {condition}"
            self.cursor.execute(query, params)
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        
    def get_column_names(self, table_name: str) -> list[str]:
        with self._lock:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in self.cursor.fetchall()]

    def update(self, table_name: str, updates: Dict[str, Any], condition: str, params: Tuple):
        with self._lock:
            update_clause = ', '.join([f"{col} = ?" for col in updates.keys()])
            query = f"UPDATE {table_name} SET {update_clause} WHERE {condition}"
            all_params = tuple(updates.values()) + (params if isinstance(params, tuple) else (params,))
            self.cursor.execute(query, all_params)
            self.conn.commit()

    def delete(self, table_name: str, condition: str, params: Tuple):
        with self._lock:
            query = f"DELETE FROM {table_name} WHERE {condition}"
            self.cursor.execute(query, params)
            self.conn.commit()

    def close_connection(self):
        self.conn.close()

class ServerDB(DatabaseManager):
    def __init__(self, db_name: str):
        super().__init__(db_name)
        self.db_name = db_name
        self.create_tables()

    def migrate_table(self, table_name: str, data_cls):
        """Add missing columns to a table according to the dataclass fields."""
        existing_columns = {row[1] for row in self.execute(f"PRAGMA table_info({table_name})").fetchall()}
        type_map = {int: "INTEGER", float: "REAL", str: "TEXT", bool: "INTEGER"}

        for f in fields(data_cls):
            if f.name not in existing_columns:
                col_type = type_map.get(f.type, "TEXT")

                # Default values based on type
                if col_type == "TEXT":
                    default_val = ""
                else:
                    default_val = 0

                # Convert boolean defaults to 0/1 if needed
                if isinstance(default_val, bool):
                    default_val = int(default_val)

                # Wrap text defaults in quotes
                default_literal = f"'{default_val}'" if col_type == "TEXT" else str(default_val)

                try:
                    self.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {f.name} {col_type} DEFAULT {default_literal}"
                    )
                    # Optionally log success here
                except sqlite3.OperationalError as e:
                    print(f"Warning: Could not add column '{f.name}' to {table_name}: {e}")

    def create_tables(self):
        server_info_columns = {
            'id': 'INTEGER PRIMARY KEY CHECK (id = 1)',
            'last_shutdown_time': 'INTEGER',
            'allowlist_profile': 'TEXT'
        }
        self.create_table('server_info', server_info_columns)

        name_ban_columns = {
            'id': 'INTEGER PRIMARY KEY CHECK (id = 1)',
            'name': 'TEXT',
            'banned_time': 'INTEGER',
            'ban_reason': 'TEXT'
        }
        self.create_table('name_bans', name_ban_columns)

        jails_columns = {
            'name': 'TEXT UNIQUE NOT NULL',
            'pos': 'TEXT'
        }
        self.create_table('jails', jails_columns)

        warps_columns = {
            'name': 'TEXT UNIQUE NOT NULL',
            'pos': 'TEXT',
            'displayname': 'TEXT',
            'category': 'TEXT',
            'description': 'TEXT',
            'cost': 'REAL DEFAULT 0'
        }
        self.create_table('warps', warps_columns)
        self.execute("INSERT OR IGNORE INTO server_info (id, last_shutdown_time) VALUES (1, 0)")
        self.conn.commit()

    def update_server_info(self, column: str, value):
        """
        Generalized update function for a column in server_info table.
        """
        query = f"UPDATE server_info SET {column} = ? WHERE id = 1"
        self.execute(query, (value,))
        self.conn.commit()

    def get_server_info(self) -> Optional["ServerData"]:
        """
        Fetches the row from server_info (id=1), converts to ServerData object.
        Automatically excludes any columns not in the ServerData dataclass.
        Returns None if no row found.
        """
        result = self.execute("SELECT * FROM server_info WHERE id = 1").fetchone()
        if result:
            column_info = self.execute("PRAGMA table_info(server_info)").fetchall()
            column_names = [row[1] for row in column_info]
            raw_data = dict(zip(column_names, result))

            server_fields = {f.name for f in fields(ServerData)}
            filtered_data = {k: v for k, v in raw_data.items() if k in server_fields}

            server_data = ServerData(**filtered_data)
            return server_data

        return None

    def encode_location(self, loc: Location) -> str:
        """Convert Location to JSON string."""
        return json.dumps({
            'x': loc.x,
            'y': loc.y,
            'z': loc.z,
            'dimension': loc.dimension.name, 
            'pitch': loc.pitch,
            'yaw': loc.yaw
        })

    def decode_location(self, pos_str: str, server) -> Location:
        """Parse JSON string back to Location object."""
        data = json.loads(pos_str)

        dimension_name = data['dimension']
        dimension_obj = server.level.get_dimension(dimension_name)

        return Location(
            x=data['x'],
            y=data['y'],
            z=data['z'],
            dimension=dimension_obj,
            pitch=data['pitch'],
            yaw=data['yaw']
        )

    def add_name(self, name: str, ban_reason: str = "Negative Behavior", ban_duration: int = 100 * 31536000):
        """
        Add a name to the bans list.
        - ban_duration: seconds from now (0 = permanent)
        - ban_reason: reason string
        """
        banned_until = int(time.time()) + ban_duration if ban_duration > 0 else 0
        try:
            self.execute(
                "INSERT OR REPLACE INTO name_bans (name, banned_time, ban_reason) VALUES (?, ?, ?)",
                (name, banned_until, ban_reason),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding name: {e}")

    def remove_name(self, name: str):
        """Remove a name from the bans list"""
        self.execute("DELETE FROM name_bans WHERE name = ?", (name,))
        self.conn.commit()

    def check_nameban(self, name: str) -> bool:
        """
        Check if a name is currently banned
        Respects ban duration
        """
        self.execute("SELECT banned_time FROM name_bans WHERE name = ? LIMIT 1", (name,))
        row = self.cursor.fetchone()
        if row is None:
            return False

        banned_time = row[0]
        return time.time() < banned_time

    def clear_names(self):
        """Clear all bans"""
        self.execute("DELETE FROM name_bans")
        self.conn.commit()

    def get_ban_info(self, name: str) -> Optional[NameBans]:
        result = self.execute("SELECT * FROM name_bans WHERE name = ? LIMIT 1", (name,)).fetchone()
        if result:
            column_info = self.execute("PRAGMA table_info(name_bans)").fetchall()
            column_names = [row[1] for row in column_info]

            raw_data = dict(zip(column_names, result))

            ban_fields = {f.name for f in fields(NameBans)}
            filtered_data = {k: v for k, v in raw_data.items() if k in ban_fields}

            return NameBans(**filtered_data)

        return None
    
    def get_all_bans(self) -> List[NameBans]:
        """
        Fetch all rows from name_bans and return as list of NameBans objects.
        Automatically filters only dataclass fields.
        """
        results = self.execute("SELECT * FROM name_bans").fetchall()
        if not results:
            return []

        column_info = self.execute("PRAGMA table_info(name_bans)").fetchall()
        column_names = [row[1] for row in column_info]

        ban_fields = {f.name for f in fields(NameBans)}
        all_bans = []
        for row in results:
            raw_data = dict(zip(column_names, row))
            filtered_data = {k: v for k, v in raw_data.items() if k in ban_fields}
            all_bans.append(NameBans(**filtered_data))

        return all_bans

    def create_jail(self, name: str, location: Location) -> bool:
        # Check if jail name exists
        if self.execute("SELECT 1 FROM jails WHERE name = ?", (name,)).fetchone():
            return False

        pos_str = self.encode_location(location)
        self.execute(
            "INSERT INTO jails (name, pos) VALUES (?, ?)",
            (name, pos_str)
        )
        self.conn.commit()
        return True
    
    def get_all_jails(self, server) -> dict[str, dict]:
        jails = {}
        rows = self.execute("SELECT name, pos FROM jails").fetchall()
        for name, pos_str in rows:
            pos = self.decode_location(pos_str, server) if pos_str else None
            jails[name] = {
                'pos': pos
            }
        return jails

    def get_jail(self, name: str, server) -> dict | None:
        row = self.execute("SELECT name, pos FROM jails WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        name, pos_str = row
        pos = self.decode_location(pos_str, server) if pos_str else None
        return {
            "name": name,
            "pos": pos
        }

    def delete_jail(self, name: str) -> bool:
        cur = self.execute("DELETE FROM jails WHERE name = ?", (name,))
        self.conn.commit()
        return cur.rowcount > 0

    def create_warp(self, name: str, location: Location, displayname: str = None, category: str = None, description: str = None, cost: float = 0.0) -> bool:
        # Check if warp name exists
        if self.execute("SELECT 1 FROM warps WHERE name = ?", (name,)).fetchone():
            return False

        pos_str = self.encode_location(location)
        self.execute(
            '''
            INSERT INTO warps (name, pos, displayname, category, description, cost)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (name, pos_str, displayname, category, description, cost)
        )
        self.conn.commit()
        return True
    
    def update_warp_pos(self, name: str, location: Location) -> bool:
        if not self.execute("SELECT 1 FROM warps WHERE name = ?", (name,)).fetchone():
            return False  # Warp does not exist
        pos_str = self.encode_location(location)
        self.execute("UPDATE warps SET pos = ? WHERE name = ?", (pos_str, name))
        self.conn.commit()
        return True

    def update_warp_displayname(self, name: str, displayname: str) -> bool:
        if not self.execute("SELECT 1 FROM warps WHERE name = ?", (name,)).fetchone():
            return False
        self.execute("UPDATE warps SET displayname = ? WHERE name = ?", (displayname, name))
        self.conn.commit()
        return True

    def update_warp_category(self, name: str, category: str) -> bool:
        if not self.execute("SELECT 1 FROM warps WHERE name = ?", (name,)).fetchone():
            return False
        self.execute("UPDATE warps SET category = ? WHERE name = ?", (category, name))
        self.conn.commit()
        return True

    def update_warp_description(self, name: str, description: str) -> bool:
        if not self.execute("SELECT 1 FROM warps WHERE name = ?", (name,)).fetchone():
            return False
        self.execute("UPDATE warps SET description = ? WHERE name = ?", (description, name))
        self.conn.commit()
        return True

    def update_warp_cost(self, name: str, cost: float) -> bool:
        if not self.execute("SELECT 1 FROM warps WHERE name = ?", (name,)).fetchone():
            return False
        self.execute("UPDATE warps SET cost = ? WHERE name = ?", (cost, name))
        self.conn.commit()
        return True

    def get_warp(self, name: str, server) -> dict | None:
        row = self.execute(
            "SELECT name, pos, displayname, category, description, cost FROM warps WHERE name = ?",
            (name,)
        ).fetchone()
        if row is None:
            return None

        name, pos_str, displayname, category, description, cost = row
        pos = self.decode_location(pos_str, server) if pos_str else None

        return {
            'name': name,
            'pos': pos,
            'displayname': displayname,
            'category': category,
            'description': description,
            'cost': cost
        }

    def get_all_warps(self, server) -> dict[str, dict]:
        warps = {}
        rows = self.execute("SELECT name, pos, displayname, category, description, cost FROM warps").fetchall()
        for name, pos_str, displayname, category, description, cost in rows:
            pos = self.decode_location(pos_str, server) if pos_str else None
            warps[name] = {
                'pos': pos,
                'displayname': displayname,
                'category': category,
                'description': description,
                'cost': cost
            }
        return warps

    def delete_warp(self, name: str) -> bool:
        cur = self.execute("DELETE FROM warps WHERE name = ?", (name,))
        self.conn.commit()
        return cur.rowcount > 0

class UserDB(DatabaseManager):
    def __init__(self, db_name: str):
        """Initialize the database connection and create tables."""
        super().__init__(db_name)
        self.jailed_cache = {}
        self.db_name = db_name
        self.create_tables()

    def create_tables(self):
        """Create tables if they don't exist."""
        user_info_columns = {
            'xuid': 'TEXT PRIMARY KEY',
            'uuid': 'TEXT',
            'name': 'TEXT',
            'ping': 'INTEGER',
            'device_os': 'TEXT',
            'device_id': 'TEXT',
            'client_ver': 'TEXT',
            'last_join': 'INTEGER',
            'last_leave': 'INTEGER',
            'internal_rank': 'TEXT',
            'enabled_ms': 'INTEGER',
            'is_silent_muted': 'INTEGER',
            'is_afk': 'INTEGER',
            'enabled_ss': 'INTEGER',
            'is_vanish': 'INTEGER',
            'last_messaged': 'TEXT',
            'last_logout_pos': 'TEXT',
            'last_logout_dim': 'TEXT',
            'last_vanish_blob': 'BLOB',
            'unique_id': 'INTEGER',
            'enabled_mt': 'INTEGER',
            'enabled_as': 'INTEGER',
            'enabled_sc': 'INTEGER',
            'perms': 'TEXT',
            'gamemode': 'INTEGER',
            'xp': 'INTEGER'
        }
        self.create_table('users', user_info_columns)

        moderation_log_columns = {
            'xuid': 'TEXT PRIMARY KEY',
            'name': 'TEXT',
            'is_muted': 'INTEGER',
            'mute_time': 'INTEGER',
            'mute_reason': 'TEXT',
            'is_banned': 'INTEGER',
            'banned_time': 'INTEGER',
            'ban_reason': 'TEXT',
            'ip_address': 'TEXT',
            'is_ip_banned': 'INTEGER',
            'is_ip_muted': 'INTEGER',
            'is_jailed': 'INTEGER',
            'jail_time': 'INTEGER',
            'jail_reason': 'TEXT',
            'jail': 'TEXT',
            'jail_gamemode': 'INTEGER',
            'return_jail_pos': 'TEXT',
            'return_jail_dim': 'TEXT'
        }
        self.create_table('mod_logs', moderation_log_columns)

        punishment_log_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'xuid': 'TEXT',
            'name': 'TEXT',
            'action_type': 'TEXT',
            'reason': 'TEXT',
            'timestamp': 'INTEGER',
            'duration': 'INTEGER'
        }
        self.create_table('punishment_logs', punishment_log_columns)

        mod_notes_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'xuid': 'TEXT',
            'name': 'TEXT',
            'note': 'TEXT',
            'timestamp': 'INTEGER',
            'added_by': 'TEXT'
        }
        self.create_table('mod_notes', mod_notes_columns)

        alt_log_columns = {
            'main_name': 'TEXT',
            'main_xuid': 'TEXT',
            'alt_name': 'TEXT',
            'alt_xuid': 'TEXT',
            'expiry': 'INTEGER'
        }
        self.create_table('alt_logs', alt_log_columns, unique=['main_xuid', 'alt_xuid'])

        warn_log_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'xuid': 'TEXT',
            'name': 'TEXT',
            'warn_reason': 'TEXT',
            'warn_time': 'INTEGER',
            'added_by': 'TEXT'
        }
        self.create_table('warn_logs', warn_log_columns)

        inventory_columns = {
            'xuid': 'TEXT',
            'name': 'TEXT',
            'type': 'TEXT',
            'amount': 'INTEGER',
            'damage': 'INTEGER',
            'display_name': 'TEXT',
            'enchants': 'TEXT', 
            'lore': 'TEXT', 
            'unbreakable': 'INTEGER',
            'slot_type': 'TEXT',
            'slot': 'INTEGER',
            'data': 'INTEGER'
        }
        self.create_table('inventories', inventory_columns)
        self.create_table('ender_chests', inventory_columns)

    def save_user(self, player: Player):
        """Primary data saving for users."""
        xuid = player.xuid
        uuid = str(player.unique_id)
        unique_id = player.id
        name = player.name
        ping = player.ping
        device_os = player.device_os
        device_id = player.device_id
        client_ver = player.game_version
        gamemode = player.game_mode.value
        last_join = int(time.time())
        last_leave = 0
        ip = str(player.address)
        internal_rank = "Operator" if player.is_op else "Default"

        # Check cache or database
        user = self.execute(
            "SELECT * FROM users WHERE xuid = ?", 
            (xuid,)
        ).fetchone()

        if not user:
            # New user: insert into both tables
            data = {
                'xuid': xuid, 'uuid': uuid, 'name': name, 'ping': ping, 'device_os': device_os, 'device_id': device_id,
                'client_ver': client_ver, 'last_join': last_join, 'last_leave': last_leave, 
                'internal_rank': internal_rank, 'enabled_ms': 1, 'is_afk': 0, 'enabled_ss': 0,
                'is_vanish': 0, 'last_logout_dim': "Overworld", 'last_vanish_blob': None, 'unique_id': unique_id,
                'enabled_as': 0, 'enabled_sc': 0, 'enabled_mt': 1, 'gamemode': gamemode
            }
            mod_data = {
                'xuid': xuid, 'name': name, 'is_muted': 0, 'mute_time': 0, 'mute_reason': "None",
                'is_banned': 0, 'banned_time': 0, 'ban_reason': "None", 'ip_address': ip, 'is_ip_banned': 0,
                'is_ip_muted': 0, 'is_jailed': 0, 'jail_time': 0, 'jail_reason': "None", 'jail': 'None'
            }
            self.insert('users', data)
            self.insert('mod_logs', mod_data)
        else:
            # Existing user: update
            user_updates = {
                'unique_id': unique_id, 'uuid': uuid, 'name': name, 'ping': ping, 
                'device_os': device_os, 'device_id': device_id, 'client_ver': client_ver, 'is_afk': 0,
                'gamemode': gamemode
            }
            mod_updates = {
                'name': name, 'ip_address': ip
            }
            self.update('users', user_updates, 'xuid = ?', (xuid,))
            self.update('mod_logs', mod_updates, 'xuid = ?', (xuid,))

    def migrate_table(self, table_name: str, data_cls):
        """Add missing columns to a table according to the dataclass fields."""
        existing_columns = {row[1] for row in self.execute(f"PRAGMA table_info({table_name})").fetchall()}
        type_map = {int: "INTEGER", float: "REAL", str: "TEXT", bool: "INTEGER"}

        for f in fields(data_cls):
            if f.name not in existing_columns:
                col_type = type_map.get(f.type, "TEXT")

                # Default values based on type
                if col_type == "TEXT":
                    default_val = ""
                else:
                    default_val = 0

                # Convert boolean defaults to 0/1 if needed
                if isinstance(default_val, bool):
                    default_val = int(default_val)

                # Wrap text defaults in quotes
                default_literal = f"'{default_val}'" if col_type == "TEXT" else str(default_val)

                try:
                    self.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {f.name} {col_type} DEFAULT {default_literal}"
                    )
                    # Optionally log success here
                except sqlite3.OperationalError as e:
                    print(f"Warning: Could not add column '{f.name}' to {table_name}: {e}")

    def patch_user_fields(self, data: dict) -> dict:
        """Ensure user data fields are properly typed with safe defaults, no overwriting existing non-None fields."""
        type_defaults = {
            int: 0,
            float: 0.0,
            str: "",
            bool: 0
        }

        patched_data = {}
        for field in fields(User):
            val = data.get(field.name, None)

            if val is None:
                # Missing or None → use default
                patched_data[field.name] = type_defaults.get(field.type, None)
            else:
                # Value exists → keep as is, no casting
                patched_data[field.name] = val

        return patched_data

    def get_online_user(self, xuid: str) -> Optional[User]:
        result = self.execute(
            "SELECT * FROM users WHERE xuid = ?", 
            (xuid,), readonly=True
        ).fetchone()
        if result:
            column_info = self.execute("PRAGMA table_info(users)").fetchall()
            column_names = [row[1] for row in column_info]
            raw_data = dict(zip(column_names, result))
            result_dict = self.patch_user_fields(raw_data)
            user = User(**result_dict)

            return user
        return None
    
    def get_online_user_by_unique_id(self, unique_id: str) -> Optional[User]:
        result = self.execute(
            "SELECT * FROM users WHERE unique_id = ?", 
            (unique_id,), readonly=True
        ).fetchone()
        if result:
            column_info = self.execute("PRAGMA table_info(users)").fetchall()
            column_names = [row[1] for row in column_info]
            raw_data = dict(zip(column_names, result))
            result_dict = self.patch_user_fields(raw_data)
            user = User(**result_dict)

            return user
        return None

    def get_offline_user(self, name: str) -> Optional[User]:
        result = self.execute(
            "SELECT * FROM users WHERE name = ?", 
            (name,), readonly=True
        ).fetchone()
        if result:
            column_names = [row[1] for row in self.execute("PRAGMA table_info(users)").fetchall()]
            result_dict = self.patch_user_fields(dict(zip(column_names, result)))
            user = User(**result_dict)
            return user
        return None
    
    def check_and_update_mute(self, xuid: str, name: str) -> int:
        """Checks if a player is muted and updates the database if the mute has expired."""
        mute_row = self.execute(
            "SELECT is_muted, mute_time FROM mod_logs WHERE xuid = ?", 
            (xuid,), readonly=True
        ).fetchone()

        if mute_row:
            is_muted, mute_time = mute_row
            if is_muted:
                if mute_time < datetime.now().timestamp():
                    self.remove_mute(name)
                    return 0 
                return 1 
            return 0 
        return 0

    def get_mod_log(self, xuid: str) -> Optional[ModLog]:
        row = self.execute(
            "SELECT * FROM mod_logs WHERE xuid = ?", 
            (xuid,), readonly=True
        ).fetchone()
        if row:
            mod_log = ModLog(*row)
            return mod_log
        return None

    def get_all_users(self) -> list[dict]:
        rows = self.execute("SELECT * FROM users", readonly=True).fetchall()
        columns = [col[1] for col in self.execute("PRAGMA table_info(users)").fetchall()]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_alts(self, ip: str, device_id: str, exclude_xuid: str) -> list[dict]:
        now = int(time.time())
        self.execute("DELETE FROM alt_logs WHERE expiry < ?", (now,))

        query = """
            SELECT u.name, u.xuid, COALESCE(m.ip_address, '') AS ip_address, u.device_id
            FROM users u
            LEFT JOIN mod_logs m ON u.xuid = m.xuid
            WHERE u.xuid != ?
        """
        rows = self.execute(query, (exclude_xuid,), readonly=True).fetchall()
        columns = ["name", "xuid", "ip_address", "device_id"]

        results = []
        for row in rows:
            alt = dict(zip(columns, row))
            if (
                (alt["ip_address"] and ip and same_subnet(ip, alt["ip_address"])) or
                (device_id and alt["device_id"] and alt["device_id"] == device_id)
            ):
                results.append(alt)

        extra_rows = self.execute(
            """
            SELECT alt_name, alt_xuid FROM alt_logs
            WHERE main_xuid = ? AND expiry >= ?
            """,
            (exclude_xuid, now),
            readonly=True
        ).fetchall()

        for alt_name, alt_xuid in extra_rows:
            if not any(r["xuid"] == alt_xuid for r in results):
                results.append({"name": alt_name, "xuid": alt_xuid,
                                "ip_address": "", "device_id": ""})

        return results
    
    def check_alts(self, main_xuid: str, main_name: str, ip: str, device_id: str):
        """Check for alt accounts and update alt_logs with 90-day expiry."""
        now = int(time.time())
        expiry_time = now + 90 * 24 * 60 * 60  # 90 days in seconds

        alts = self.get_alts(ip, device_id, exclude_xuid=main_xuid)

        for alt in alts:
            self.execute(
                """
                INSERT INTO alt_logs (main_name, main_xuid, alt_name, alt_xuid, expiry)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(main_xuid, alt_xuid) DO UPDATE SET expiry=excluded.expiry
                """,
                (main_name, main_xuid, alt["name"], alt["xuid"], expiry_time),
            )

    def add_ban(self, xuid, expiration: int, reason: str, ip_ban: bool = False):
        self.update('mod_logs', {'is_banned': 1, 'banned_time': expiration, 'ban_reason': reason, 'is_ip_banned': ip_ban}, 'xuid = ?', (xuid,))
        self.insert('punishment_logs', {
            'xuid': xuid, 'name': self.get_name_by_xuid(xuid), 'action_type': 'Ban',
            'reason': reason, 'timestamp': int(time.time()), 'duration': expiration
        })

    def add_mute(self, xuid: str, expiration: int, reason: str, ip_mute: bool = False):
        self.update('mod_logs', {'is_muted': 1, 'mute_time': expiration, 'mute_reason': reason, 'is_ip_muted': ip_mute }, 'xuid = ?', (xuid,))
        self.insert('punishment_logs', {
            'xuid': xuid, 'name': self.get_name_by_xuid(xuid), 'action_type': 'Mute',
            'reason': reason, 'timestamp': int(time.time()), 'duration': expiration
        })

    def remove_ban(self, name: str):
        self.update('mod_logs', {'is_banned': 0, 'banned_time': 0, 'ban_reason': "None", 'is_ip_banned': 0}, 'name = ?', (name,))
        self.insert('punishment_logs', {
            'xuid': self.get_xuid_by_name(name), 'name': name, 'action_type': 'Unban',
            'reason': 'Ban Removed', 'timestamp': int(time.time()), 'duration': 0
        })

    def check_ip_ban(self, ip: str) -> bool:
        ip_base = ip.split(':')[0]
        row = self.execute(
            "SELECT 1 FROM mod_logs WHERE ip_address LIKE ? AND is_ip_banned = 1 LIMIT 1",
            (f"{ip_base}%",), readonly=True
        ).fetchone()
        return bool(row)
    
    def check_ip_mute(self, ip: str) -> tuple[bool, Optional[int], Optional[str]]:
        ip_base = ip.split(':')[0]

        row = self.execute(
            "SELECT name, mute_time, mute_reason FROM mod_logs "
            "WHERE ip_address LIKE ? AND is_ip_muted = 1 "
            "ORDER BY mute_time DESC LIMIT 1",
            (f"{ip_base}%",), readonly=True
        ).fetchone()

        if row:
            name, mute_time, mute_reason = row

            if mute_time < datetime.now().timestamp():
                # Expired — unmute the original player
                self.update(
                    'mod_logs',
                    {'is_muted': 0, 'mute_time': 0, 'mute_reason': "None", "is_ip_muted": 0},
                    'name = ?',
                    (name,)
                )
                self.insert(
                    'punishment_logs',
                    {
                        'xuid': self.get_xuid_by_name(name),
                        'name': name,
                        'action_type': 'Unmute',
                        'reason': 'Mute Expired',
                        'timestamp': int(time.time()),
                        'duration': 0
                    }
                )
                return False, None, None

            return True, mute_time, mute_reason

        return False, None, None

    def remove_mute(self, name: str):
        self.update('mod_logs', {'is_muted': 0, 'mute_time': 0, 'mute_reason': "None", "is_ip_muted": 0}, 'name = ?', (name,))
        self.insert('punishment_logs', {
            'xuid': self.get_xuid_by_name(name), 'name': name, 'action_type': 'Unmute',
            'reason': 'Mute Expired', 'timestamp': int(time.time()), 'duration': 0
        })

    def refresh_jail_cache(self):
        """Load all currently jailed players into the cache."""
        current_time = int(time.time())
        rows = self.db.execute(
            "SELECT xuid, jail_time FROM mod_logs WHERE is_jailed = 1 AND jail_time > ?",
            (current_time,), readonly=True
        ).fetchall()

        self.jailed_cache = {xuid: jail_time for xuid, jail_time in rows}

    def add_jail(self, xuid: str, expiration: int, reason: str, jail: str = None, jail_gamemode: str = None, jail_pos: Vector = None, jail_dim: str = None):
        """Jail a player, optionally storing the return position and dimension."""
        update_data = {
            'is_jailed': 1,
            'jail_time': expiration,
            'jail_reason': reason
        }

        if jail_gamemode:
            update_data['jail_gamemode'] = jail_gamemode

        if jail:
            update_data['jail'] = jail

        if jail_pos is not None:
            if isinstance(jail_pos, Vector):
                x, y, z = jail_pos.x, jail_pos.y, jail_pos.z
                update_data['return_jail_pos'] = f"{x},{y},{z}"
            else:
                update_data['return_jail_pos'] = str(jail_pos)

        if jail_dim:
            update_data['return_jail_dim'] = jail_dim

        self.update('mod_logs', update_data, 'xuid = ?', (xuid,))
        self.insert(
            'punishment_logs',
            {
                'xuid': xuid,
                'name': self.get_name_by_xuid(xuid),
                'action_type': 'Jail',
                'reason': reason,
                'timestamp': int(time.time()),
                'duration': expiration
            }
        )

    def remove_jail(self, name: str):
        """Unjail a player and log the action."""
        self.update(
            'mod_logs',
            {
                'is_jailed': 0,
                'jail_time': 0,
                'jail_reason': "None",
                'jail_gamemode': "None",
                'return_jail_pos': None,
                'return_jail_dim': None
            },
            'name = ?',
            (name,)
        )
        self.insert(
            'punishment_logs',
            {
                'xuid': self.get_xuid_by_name(name),
                'name': name,
                'action_type': 'Unjail',
                'reason': 'Jail Removed',
                'timestamp': int(time.time()),
                'duration': 0
            }
        )

    def force_unjail(self, xuid: str):
        self.execute(
            "UPDATE mod_logs SET jail_time = ?, is_jailed = 1 WHERE xuid = ?",
            (int(time.time()) - 1, xuid)
        )

        # Also invalidate the cache for immediate effect
        if xuid in self.jailed_cache:
            self.jailed_cache[xuid] = int(time.time()) - 1

    def check_jailed(self, xuid: str) -> tuple[bool, bool]:
        """
        Check if a player is jailed.
        Returns:
            (is_jailed, is_expired)
            - is_jailed: True if the DB or cache indicates the player was jailed.
            - is_expired: True if the jail_time has passed.
        """
        current_time = int(time.time())

        # Clean up expired cache entries
        expired = [k for k, t in self.jailed_cache.items() if t <= current_time]
        for k in expired:
            self.jailed_cache.pop(k, None)

        # Check cached jail time
        if xuid in self.jailed_cache:
            jail_time = self.jailed_cache[xuid]
            return True, jail_time <= current_time

        # Query DB for jail info
        row = self.execute(
            "SELECT jail_time FROM mod_logs WHERE xuid = ? AND is_jailed = 1 LIMIT 1",
            (xuid,), readonly=True
        ).fetchone()

        if row:
            jail_time = row[0]
            self.jailed_cache[xuid] = jail_time
            return True, jail_time <= current_time

        return False, False
    
    def print_punishment_history(self, name: str, page: int = 1):
        """Prints punishment history for a named player"""

        mod_log_query = """
            SELECT is_muted, mute_time, mute_reason, is_banned, banned_time, ban_reason, is_ip_banned
            FROM mod_logs
            WHERE name = ?
        """
        mod_log = self.execute(mod_log_query, (name,), readonly=True).fetchone()
        if not mod_log:
            return False

        # Unpack known fields and capture optional jail fields in a tuple
        (is_muted, mute_time, mute_reason,
        is_banned, banned_time, ban_reason, is_ip_banned, *jail_fields) = mod_log

        # Handle optional jail fields safely
        if len(jail_fields) == 3:
            is_jailed, jail_time, jail_reason = jail_fields
        else:
            is_jailed = jail_time = jail_reason = None
            
        current_time = int(time.time())

        punishment_query = """
            SELECT action_type, reason, timestamp, duration
            FROM punishment_logs
            WHERE name = ?
            AND NOT (action_type = 'Unmute' AND reason = 'Mute Expired')
            ORDER BY timestamp DESC
        """
        all_logs = self.execute(punishment_query, (name,), readonly=True).fetchall()
        if not all_logs:
            return False

        active_punishments = {}
        past_punishments = []

        for action_type, reason, timestamp, duration in all_logs:
            formatted_time = TimezoneUtils.convert_to_timezone(timestamp, 'EST')

            if action_type == "Ban" and is_banned and banned_time > current_time and "Ban" not in active_punishments:
                ban_expires_in = format_time_remaining(banned_time)
                ip_ban_status = "IP " if is_ip_banned else ""
                active_punishments["Ban"] = (
                    timestamp,
                    f"§c{ip_ban_status}Ban §7- §e{ban_reason} "
                    f"§7(§e{ban_expires_in}§7)\n"
                    f"§oDate Issued: §7{formatted_time}§r"
                )
            elif action_type == "Mute" and is_muted and mute_time > current_time and "Mute" not in active_punishments:
                mute_expires_in = format_time_remaining(mute_time, True)
                active_punishments["Mute"] = (
                    timestamp,
                    f"§bMute §7- §e{mute_reason} "
                    f"§7(§e{mute_expires_in}§7)\n"
                    f"§oDate Issued: §7{formatted_time}§r"
                )
            elif action_type == "Jail" and is_jailed and jail_time > current_time and "Jail" not in active_punishments:
                jail_expires_in = format_time_remaining(jail_time)
                active_punishments["Jail"] = (
                    timestamp,
                    f"§vJail §7- §e{jail_reason} "
                    f"§7(§e{jail_expires_in}§7)\n"
                    f"§oDate Issued: §7{formatted_time}§r"
                )
            else:
                past_punishments.append(
                    f"§9{action_type} §7- §e{reason} "
                    f"§7(§eEXPIRED§7)\n"
                    f"§oDate Issued: §7{formatted_time}§r"
                )

        per_page = 5
        total_pages = (len(past_punishments) + per_page - 1) // per_page
        start, end = (page - 1) * per_page, (page - 1) * per_page + per_page
        paginated_past = past_punishments[start:end]

        msg = [f""]

        if active_punishments:
            msg.append(f"§aActive §6Punishments for §e{name}§6:")
            for _, entry in active_punishments.values():
                msg.append(f"§7- {entry}")
            msg.append("§6---------------")

        msg.append(f"§4Past §6Punishments for §e{name}§6:§r")
        msg.extend(f"§7- {entry}" for entry in paginated_past)
        msg.append("§6---------------")

        if page < total_pages:
            msg.append(f"§8Use §e/punishments {name} {page + 1} §8for more.")

        return "\n".join(msg)

    def get_punishment_logs(self, name: str) -> Optional[List[PunishmentLog]]:
        rows = self.execute("SELECT * FROM punishment_logs WHERE name = ?", (name,), readonly=True).fetchall()
        return [PunishmentLog(*row) for row in rows] if rows else None

    def delete_all_punishment_logs_by_name(self, name: str) -> bool:
        cursor = self.execute("DELETE FROM punishment_logs WHERE name = ?", (name,))
        return cursor.rowcount > 0

    def remove_punishment_log_by_id(self, name: str, log_id: int) -> bool:
        cursor = self.execute("DELETE FROM punishment_logs WHERE name = ? AND id = ?", (name, log_id))
        return cursor.rowcount > 0

    def get_offline_mod_log(self, name: str) -> Optional[ModLog]:
        row = self.execute("SELECT * FROM mod_logs WHERE name = ?", (name,), readonly=True).fetchone()
        return ModLog(*row) if row else None

    def get_xuid_by_name(self, player_name: str) -> str:
        row = self.execute("SELECT xuid FROM mod_logs WHERE name = ?", (player_name,), readonly=True).fetchone()
        return row[0] if row else None

    def get_name_by_xuid(self, xuid: str) -> str:
        row = self.execute("SELECT name FROM mod_logs WHERE xuid = ?", (xuid,), readonly=True).fetchone()
        return row[0] if row else None

    def add_note(self, note: str, added_by: str, xuid: Optional[str] = None, name: Optional[str] = None):
        if not xuid and not name:
            raise ValueError("Must provide either xuid or name")

        timestamp = int(time.time())

        self.execute(
            "INSERT INTO mod_notes (xuid, name, note, added_by, timestamp) VALUES (?, ?, ?, ?, ?)",
            (xuid, name, note, added_by, timestamp)
        )

    def get_notes(self, xuid: Optional[str] = None, name: Optional[str] = None) -> list[Note]:
        if not xuid and not name:
            raise ValueError("Must provide either xuid or name")

        if xuid:
            rows = self.execute(
                "SELECT id, xuid, name, note, timestamp, added_by FROM mod_notes WHERE xuid = ? ORDER BY timestamp ASC",
                (xuid,), readonly=True
            ).fetchall()
        else:
            rows = self.execute(
                "SELECT id, xuid, name, note, timestamp, added_by FROM mod_notes WHERE name = ? ORDER BY timestamp ASC",
                (name,), readonly=True
            ).fetchall()

        return [Note(*row) for row in rows]

    def remove_note_by_id(self, note_id: int) -> bool:
        result = self.execute("DELETE FROM mod_notes WHERE id = ?", (note_id,))
        return result.rowcount > 0

    def clear_notes(self, xuid: str) -> None:
        self.execute("DELETE FROM mod_notes WHERE xuid = ?", (xuid,))

    def get_latest_active_warning(self, xuid: Optional[str] = None, name: Optional[str] = None) -> Optional[dict]:
        """Retrieves the most recent active warning for a player."""
        if not xuid and not name:
            raise ValueError("Must provide either xuid or name")

        now = int(time.time())
        condition = "xuid = ?" if xuid else "name = ?"
        params = (xuid,) if xuid else (name,)

        query = f"""
            SELECT * FROM warn_logs
            WHERE {condition}
            AND (warn_time = 0 OR warn_time > ?)
            ORDER BY warn_time DESC
            LIMIT 1
        """
        params = params + (now,)

        row = self.execute(query, params, readonly=True).fetchone()
        if row:
            columns = [desc[0] for desc in self.execute(query, params, readonly=True).description]
            return dict(zip(columns, row))
        return None

    def add_warning(self, reason: str, added_by: str, duration: int, xuid: Optional[str] = None, name: Optional[str] = None) -> None:
        """Adds a warning"""
        if not xuid and not name:
            raise ValueError("Must provide either xuid or name")

        if not xuid:
            xuid = self.get_xuid_by_name(name)
        if not name:
            name = self.get_name_by_xuid(xuid)

        timestamp = int(time.time())
        expiration = 0 if duration == 0 else timestamp + duration

        self.execute(
            "INSERT INTO warn_logs (xuid, name, warn_reason, warn_time, added_by) VALUES (?, ?, ?, ?, ?)",
            (xuid, name, reason, expiration, added_by)
        )

    def get_warnings(self, xuid: Optional[str] = None, name: Optional[str] = None, include_expired: bool = False) -> list[dict]:
        """Retrieves warnings for a player."""
        if not xuid and not name:
            raise ValueError("Must provide either xuid or name")

        now = int(time.time())
        condition = "xuid = ?" if xuid else "name = ?"
        params = (xuid,) if xuid else (name,)

        if include_expired:
            query = f"SELECT * FROM warn_logs WHERE {condition} ORDER BY warn_time ASC"
        else:
            query = f"SELECT * FROM warn_logs WHERE {condition} AND (warn_time = 0 OR warn_time > ?) ORDER BY warn_time ASC"
            params = params + (now,)

        rows = self.execute(query, params, readonly=True).fetchall()
        columns = [desc[0] for desc in self.execute(query, params, readonly=True).description]

        return [dict(zip(columns, row)) for row in rows]

    def expire_warning_by_id(self, warn_id: int) -> bool:
        """Marks a warning as expired by setting warn_time to 0"""
        result = self.execute(
            "UPDATE warn_logs SET warn_time = 0 WHERE id = ?",
            (warn_id,)
        )
        return result.rowcount > 0

    def delete_warning_by_id(self, warn_id: int) -> bool:
        """Deletes a warning entirely from the logs"""
        result = self.execute(
            "DELETE FROM warn_logs WHERE id = ?",
            (warn_id,)
        )
        return result.rowcount > 0

    def expire_warnings(self, xuid: str) -> None:
        """Expires all warnings for a given XUID by setting warn_time to 0"""
        self.execute(
            "UPDATE warn_logs SET warn_time = 0 WHERE xuid = ?",
            (xuid,)
        )

    def delete_warnings(self, xuid: str) -> None:
        """Deletes all warnings for a given XUID"""
        self.execute(
            "DELETE FROM warn_logs WHERE xuid = ?",
            (xuid,)
        )

    def set_permissions(self, xuid: str, permissions: dict):
        """Overwrite all permissions for a player."""
        perms_json = json.dumps(permissions)
        self.execute(
            "UPDATE users SET perms = ? WHERE xuid = ?",
            (perms_json, xuid)
        )

    def get_permissions(self, xuid: str) -> dict:
        """Get all permissions for a player using execute."""
        cursor = self.execute("SELECT perms FROM users WHERE xuid = ?", (xuid,))
        row = cursor.fetchone()
        if not row or not row[0]:
            return {}
        return json.loads(row[0])

    def set_permission(self, xuid: str, permission: str, allowed: bool):
        """Set one permission in the perms JSON."""
        perms = self.get_permissions(xuid)
        perms[permission] = allowed
        self.set_permissions(xuid, perms)
        
    def delete_permission(self, xuid: str, permission: str):
        """Delete a permission from the perms JSON."""
        perms = self.get_permissions(xuid)
        if permission in perms:
            del perms[permission]
            self.set_permissions(xuid, perms)

    def save_inventory(self, player: Player) -> None:
        try:
            player_data = {
                "xuid": player.xuid,
                "name": player.name,
                "inventory": [player.inventory.get_item(i) for i in range(player.inventory.size)],
                "armor": {
                    "helmet": getattr(player.inventory, "helmet", None),
                    "chestplate": getattr(player.inventory, "chestplate", None),
                    "leggings": getattr(player.inventory, "leggings", None),
                    "boots": getattr(player.inventory, "boots", None),
                    "offhand": getattr(player.inventory, "item_in_off_hand", None)
                }
            }
        except Exception as e:
            print(f"[Inventory Save] {player.name} inventory could not be saved: {e}")

        values = []

        for i, item in enumerate(player_data["inventory"]):
            if not item:
                continue
            try:
                meta = getattr(item, "item_meta", None) or {}
                values.append((
                    player_data["xuid"],
                    player_data["name"],
                    "slot",
                    i,
                    str(getattr(item, "type", "minecraft:air")),
                    getattr(item, "amount", 1),
                    getattr(meta, "damage", 0),
                    getattr(meta, "display_name", ""),
                    json.dumps(getattr(meta, "enchants", {})),
                    json.dumps(getattr(meta, "lore", [])),
                    getattr(meta, "is_unbreakable", False),
                    getattr(item, "data", None)
                ))
            except Exception as e:
                print(f"[Inventory Save] Failed to save slot {i} for {player.name}: {e}")
                continue

        for slot_type, item in player_data["armor"].items():
            if not item:
                continue
            try:
                meta = getattr(item, "item_meta", None) or {}
                values.append((
                    player_data["xuid"],
                    player_data["name"],
                    slot_type,
                    0,
                    str(getattr(item, "type", "minecraft:air")),
                    getattr(item, "amount", 1),
                    getattr(meta, "damage", 0),
                    getattr(meta, "display_name", ""),
                    json.dumps(getattr(meta, "enchants", {})),
                    json.dumps(getattr(meta, "lore", [])),
                    getattr(meta, "is_unbreakable", False),
                    getattr(item, "data", None)
                ))
            except Exception as e:
                print(f"[Inventory Save] Failed to save {slot_type} for {player.name}: {e}")
                continue

        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM inventories WHERE xuid = ?", (player_data["xuid"],))
            if values:
                cursor.executemany("""
                    INSERT INTO inventories
                    (xuid, name, slot_type, slot, type, amount, damage, display_name, enchants, lore, unbreakable, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, values)
                self.conn.commit()

    def get_inventory(self, xuid: str) -> list[dict]:
        """Fetch inventory rows as flat dicts ready for load_inventory."""
        self.cursor.execute("SELECT * FROM inventories WHERE xuid = ?", (xuid,))
        rows = self.cursor.fetchall()
        items = []

        for row in rows:
            try:

                try:
                    enchants = {} if not row[6] or row[6] in ("null", "0") else eval(row[6])
                except Exception:
                    enchants = {}

                try:
                    lore = [] if not row[7] or row[7] in ("null", "0") else eval(row[7])
                except Exception:
                    lore = []

                items.append({
                    "xuid": row[0] or None,
                    "name": row[1] or None,
                    "slot_type": row[9] or "slot",
                    "slot": int(row[10]) or 0,
                    "type": row[2] or "minecraft:air",
                    "amount": int(row[3]) if row[3] not in (None, 'null') else 1,
                    "damage": int(row[4]) if row[4] not in (None, 'null') else 0,
                    "display_name": row[5] or None,
                    "enchants": enchants,
                    "lore": lore,
                    "unbreakable": bool(row[8]) if row[8] not in (None, 'null') else False,
                    "data": int(row[11])
                })

            except Exception as e:
                print(f"[WARN] Failed to load inventory row for {xuid}: {e}, row={row}")
                continue

        return items

    def save_enderchest(self, player: Player) -> None:
        player_data = {
            "xuid": player.xuid,
            "name": player.name,
            "inventory": [player.ender_chest.get_item(i) for i in range(player.ender_chest.size)],
        }

        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM ender_chests WHERE xuid = ?", (player_data["xuid"],))
            values = []

            for i, item in enumerate(player_data["inventory"]):
                if not item:
                    continue
                meta = item.item_meta
                values.append((
                    player_data["xuid"],
                    player_data["name"],
                    "slot",
                    i,
                    str(item.type) or "minecraft:air",
                    item.amount or 1,
                    meta.damage,
                    meta.display_name,
                    json.dumps(meta.enchants),
                    json.dumps(meta.lore),
                    meta.is_unbreakable,
                    item.data
                ))

            # Insert all at once
            cursor.executemany("""
                INSERT INTO ender_chests
                (xuid, name, slot_type, slot, type, amount, damage, display_name, enchants, lore, unbreakable, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            self.conn.commit()

    def get_enderchest(self, xuid: str) -> list[dict]:
        self.cursor.execute("SELECT * FROM ender_chests WHERE xuid = ?", (xuid,))
        rows = self.cursor.fetchall()
        items = []

        for row in rows:
            try:

                try:
                    enchants = {} if not row[6] or row[6] in ("null", "0") else eval(row[6])
                except Exception:
                    enchants = {}

                try:
                    lore = [] if not row[7] or row[7] in ("null", "0") else eval(row[7])
                except Exception:
                    lore = []

                items.append({
                    "xuid": row[0] or None,
                    "name": row[1] or None,
                    "slot_type": row[9] or "slot",
                    "slot": int(row[10]) or 0,
                    "type": row[2] or "minecraft:air",
                    "amount": int(row[3]) if row[3] not in (None, 'null') else 1,
                    "damage": int(row[4]) if row[4] not in (None, 'null') else 0,
                    "display_name": row[5] or None,
                    "enchants": enchants,
                    "lore": lore,
                    "unbreakable": bool(row[8]) if row[8] not in (None, 'null') else False,
                    "data": int(row[11])
                })

            except Exception as e:
                print(f"[WARN] Failed to load ender chestrow for {xuid}: {e}, row={row}")
                continue

        return items
    
    def load_inventory(self, player: Player) -> None:
        """Apply DB inventory to player object"""
        items = self.get_inventory(player.xuid)
        inv = player.inventory

        for entry in items:
            try:
                slot_type = entry.get("slot_type", "slot")
                slot = entry.get("slot", 0)
                item = ItemStack(entry["type"], int(entry.get("amount", 1)), int(entry.get("data", 0)))
                new_meta = item.item_meta

                if new_meta:
                    new_meta.display_name = entry.get("display_name") or None
                    new_meta.lore = entry.get("lore") or []
                    new_meta.damage = entry.get("damage") or 0
                    new_meta.is_unbreakable = bool(entry.get("unbreakable")) or False

                    enchants = entry.get("enchants") or {}
                    for ench_name, level in enchants.items():
                        new_meta.add_enchant(ench_name, level, True)

                item.set_item_meta(new_meta)

                if slot_type == "helmet":
                    inv.helmet = item
                elif slot_type == "chestplate":
                    inv.chestplate = item
                elif slot_type == "leggings":
                    inv.leggings = item
                elif slot_type == "boots":
                    inv.boots = item
                elif slot_type == "offhand":
                    inv.item_in_off_hand = item
                elif slot_type == "slot":
                    inv.set_item(slot, item)

            except Exception as e:
                print(f"Failed to load item for player {player.name} ({player.xuid}): {e}, entry={entry}")
                continue

    def load_enderchest(self, player: Player) -> None:
        """Apply DB inventory to player object"""
        items = self.get_enderchest(player.xuid)
        inv = player.ender_chest

        for entry in items:
            try:
                item = ItemStack(entry["type"], entry.get("amount", 1), entry.get("data", 0))
                new_meta = item.item_meta

                if new_meta:
                    new_meta.display_name = entry.get("display_name")
                    new_meta.lore = entry.get("lore") or None
                    new_meta.damage = entry.get("damage") or 0
                    new_meta.is_unbreakable = bool(entry.get("unbreakable")) or False

                    enchants = entry.get("enchants") or {}
                    for ench_name, level in enchants.items():
                        new_meta.add_enchant(ench_name, level, True)

                item.set_item_meta(new_meta)

                slot_type = entry.get("slot_type", "slot")
                slot = entry.get("slot", 0)
                inv.set_item(slot, item)

            except Exception as e:
                print(f"Failed to load item for player {player.name} ({player.xuid}): {e}, entry={entry}")
                continue

    def update_user_data(self, name: str, column: str, value):
        if isinstance(value, Vector):
            x, y, z = value.x, value.y, value.z
            value = f"{x},{y},{z}"
        self.update('users', {column: value}, 'name = ?', (name,))

    def update_mod_data(self, name: str, column: str, value):
        if isinstance(value, Vector):
            x, y, z = value.x, value.y, value.z
            value = f"{x},{y},{z}"
        self.update('mod_logs', {column: value}, 'name = ?', (name,))

class sessionDB(DatabaseManager):
    """Session tracking."""

    def __init__(self, db_name: str):
        """Initialize the database connection and create tables."""
        super().__init__(db_name)
        self.create_tables()

    def create_tables(self):
        """Create tables if they don't exist."""
        session_log_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'xuid': 'TEXT',
            'name': 'TEXT',
            'start_time': 'INTEGER',
            'end_time': 'INTEGER'
        }
        user_toggle_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'xuid': 'TEXT',
            'name': 'TEXT',
            'inspect_mode': 'BOOLEAN'
        }
        self.create_table('sessions_log', session_log_columns)
        self.create_table('user_toggles', user_toggle_columns)

    def fetch_all_as_dicts(self, query: str, params: tuple = ()) -> list[dict]:
        """Helper to run a query and return list of dicts keyed by column name."""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()

        pragma_cursor = self.execute("PRAGMA table_info(actions_log);")
        columns = [col[1] for col in pragma_cursor.fetchall()]

        result = []
        for row in rows:
            row_dict = {columns[i]: row[i] for i in range(len(columns))}
            if 'x' in columns and 'y' in columns and 'z' in columns:
                row_dict['location'] = f"{row_dict['x']},{row_dict['y']},{row_dict['z']}"
            result.append(row_dict)

        return result

    def start_session(self, xuid: str, name: str, start_time: int):
        """Logs the start of a player session and automatically ends any previous sessions in case of a crash."""
        current_session = self.get_current_session(xuid)
        if current_session:
            self.end_session(xuid, int(time.time()))

        data = {
            'xuid': xuid,
            'name': name,
            'start_time': start_time,
            'end_time': None
        }
        self.insert('sessions_log', data)

    def end_session(self, xuid: str, end_time: int):
        query = """
            UPDATE sessions_log
            SET end_time = ?
            WHERE xuid = ? AND end_time IS NULL
        """
        self.execute(query, (end_time, xuid))

    def get_current_session(self, xuid: str):
        query = "SELECT * FROM sessions_log WHERE xuid = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1"
        cursor = self.execute(query, (xuid,), readonly=True)
        result = cursor.fetchone()
        return result or None

    def get_user_sessions(self, xuid: str) -> list[dict]:
        query = "SELECT start_time, end_time FROM sessions_log WHERE xuid = ?"
        cursor = self.execute(query, (xuid,), readonly=True)
        sessions = cursor.fetchall()

        result = []
        for start_time, end_time in sessions:
            if end_time is None:
                duration = int(time.time()) - start_time
                end_time_display = None
            else:
                duration = end_time - start_time
                end_time_display = end_time

            result.append({
                'start_time': start_time,
                'end_time': end_time_display,
                'duration': duration
            })
        return result

    def get_total_playtime(self, xuid: str) -> int:
        query = "SELECT start_time, end_time FROM sessions_log WHERE xuid = ?"
        cursor = self.execute(query, (xuid,), readonly=True)
        sessions = cursor.fetchall()

        total_time = 0
        now = int(time.time())

        for start_time, end_time in sessions:
            if not isinstance(start_time, (int, float)) or start_time <= 0 or start_time > now:
                continue 

            if end_time:
                if not isinstance(end_time, (int, float)) or end_time <= 0 or end_time < start_time:
                    continue
                total_time += int(end_time - start_time)
            else:
                total_time += int(now - start_time)

        return total_time

    def get_all_playtimes(self) -> list[dict]:
        query = "SELECT DISTINCT xuid, name FROM sessions_log"
        cursor = self.execute(query, readonly=True)  # readonly for faster non-blocking SELECT
        users = cursor.fetchall()

        result = []
        for xuid, name in users:
            total_playtime = self.get_total_playtime(xuid)
            result.append({
                'xuid': xuid,
                'name': name,
                'total_playtime': total_playtime
            })
        return result