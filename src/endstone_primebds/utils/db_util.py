import os
import sqlite3
import threading
import time
from dataclasses import dataclass, fields
from typing import List, Tuple, Any, Dict, Optional
from endstone import ColorFormat
from endstone.util import Vector
from endstone_primebds.utils.mod_util import format_time_remaining
from endstone_primebds.utils.time_util import TimezoneUtils
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
while not (os.path.exists(os.path.join(current_dir, 'plugins')) and os.path.exists(os.path.join(current_dir, 'worlds'))):
    current_dir = os.path.dirname(current_dir)

DB_FOLDER = os.path.join(current_dir, 'plugins', 'primebds_data')
os.makedirs(DB_FOLDER, exist_ok=True)

@dataclass
class User:
    xuid: str
    uuid: str
    name: str
    ping: int
    device_os: str
    client_ver: str
    last_join: int
    last_leave: int
    internal_rank: str
    enabled_ms: int
    is_afk: int
    enabled_ss: int
    is_vanish: int
    last_logout_pos: str
    last_logout_dim: str
    last_vanish_blob: bytes

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
class GriefAction:
    id: int
    xuid: str
    action: str
    location: str
    dim: str
    timestamp: int
    block_type: str
    block_state: str

# DB
class DatabaseManager:
    _lock = threading.Lock()

    def __init__(self, db_name: str):
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

    def create_table(self, table_name: str, columns: Dict[str, str]):
        column_definitions = ', '.join([f"{col} {dtype}" for col, dtype in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions})"
        with self._lock:
            self.cursor.execute(query)
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

class UserDB(DatabaseManager):
    def __init__(self, db_name: str):
        """Initialize the database connection and create tables."""
        super().__init__(db_name)
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
            'client_ver': 'TEXT',
            'last_join': 'INTEGER',
            'last_leave': 'INTEGER',
            'internal_rank': 'TEXT',
            'enabled_ms': 'INTEGER',
            'is_afk': 'INTEGER',
            'enabled_ss': 'INTEGER',
            'is_vanish': 'INTEGER',
            'last_logout_pos': 'TEXT',
            'last_logout_dim': 'TEXT',
            'last_vanish_blob': 'BLOB'
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
            'is_ip_banned': 'INTEGER'
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

    def save_user(self, player):
        """Primary data saving for users."""
        xuid = player.xuid
        uuid = str(player.unique_id)
        name = player.name
        ping = player.ping
        device = player.device_os
        client_ver = player.game_version
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
                'xuid': xuid, 'uuid': uuid, 'name': name, 'ping': ping, 'device_os': device,
                'client_ver': client_ver, 'last_join': last_join, 'last_leave': last_leave,
                'internal_rank': internal_rank, 'enabled_ms': 1, 'is_afk': 0, 'enabled_ss': 0,
                'is_vanish': 0, 'last_logout_dim': "Overworld", 'last_vanish_blob': None
            }
            mod_data = {
                'xuid': xuid, 'name': name, 'is_muted': 0, 'mute_time': 0, 'mute_reason': "None",
                'is_banned': 0, 'banned_time': 0, 'ban_reason': "None", 'ip_address': ip, 'is_ip_banned': 0
            }
            self.insert('users', data)
            self.insert('mod_logs', mod_data)
        else:
            # Existing user: update
            updates = {
                'uuid': uuid, 'name': name, 'ping': ping, 
                'device_os': device, 'client_ver': client_ver, 'is_afk': 0
            }
            self.update('users', updates, 'xuid = ?', (xuid,))

    def migrate_user_table(self):
        """Add missing columns to 'users' table according to User dataclass fields."""
        existing_columns = {row[1] for row in self.execute("PRAGMA table_info(users)").fetchall()}
        type_map = {int: "INTEGER", float: "REAL", str: "TEXT", bool: "INTEGER"}

        for f in fields(User):
            if f.name not in existing_columns:
                col_type = type_map.get(f.type, "TEXT")

                # Default based on type
                if col_type == "TEXT":
                    default_val = ""  # empty string for text
                else:
                    default_val = 0   # 0 for int, float, bool

                # Convert boolean defaults to 0/1
                if isinstance(default_val, bool):
                    default_val = int(default_val)

                # Wrap text defaults in quotes
                default_literal = f"'{default_val}'" if col_type == "TEXT" else str(default_val)

                try:
                    self.execute(
                        f"ALTER TABLE users ADD COLUMN {f.name} {col_type} DEFAULT {default_literal}"
                    )
                    print(f"Added missing column '{f.name}' to users table.")
                except sqlite3.OperationalError as e:
                    print(f"Warning: Could not add column '{f.name}': {e}")

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
        else:
            print(f"[DEBUG] No user found in DB for {xuid}")
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

    def add_ban(self, xuid, expiration: int, reason: str, ip_ban: bool = False):
        self.update('mod_logs', {'is_banned': 1, 'banned_time': expiration, 'ban_reason': reason, 'is_ip_banned': ip_ban}, 'xuid = ?', (xuid,))
        self.insert('punishment_logs', {
            'xuid': xuid, 'name': self.get_name_by_xuid(xuid), 'action_type': 'Ban',
            'reason': reason, 'timestamp': int(time.time()), 'duration': expiration
        })

    def add_mute(self, xuid: str, expiration: int, reason: str):
        self.update('mod_logs', {'is_muted': 1, 'mute_time': expiration, 'mute_reason': reason}, 'xuid = ?', (xuid,))
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

    def remove_mute(self, name: str):
        self.update('mod_logs', {'is_muted': 0, 'mute_time': 0, 'mute_reason': "None"}, 'name = ?', (name,))
        self.insert('punishment_logs', {
            'xuid': self.get_xuid_by_name(name), 'name': name, 'action_type': 'Unmute',
            'reason': 'Mute Expired', 'timestamp': int(time.time()), 'duration': 0
        })

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

        is_muted, mute_time, mute_reason, is_banned, banned_time, ban_reason, is_ip_banned = mod_log
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
                    f"§oDate Issued: §7{formatted_time}{ColorFormat.RESET}"
                )
            elif action_type == "Mute" and is_muted and mute_time > current_time and "Mute" not in active_punishments:
                mute_expires_in = format_time_remaining(mute_time, True)
                active_punishments["Mute"] = (
                    timestamp,
                    f"{ColorFormat.BLUE}Mute §7- §e{mute_reason} "
                    f"§7(§e{mute_expires_in}§7)\n"
                    f"§oDate Issued: §7{formatted_time}{ColorFormat.RESET}"
                )
            else:
                past_punishments.append(
                    f"{ColorFormat.BLUE}{action_type} §7- §e{reason} "
                    f"§7(§eEXPIRED§7)\n"
                    f"§oDate Issued: §7{formatted_time}{ColorFormat.RESET}"
                )

        per_page = 5
        total_pages = (len(past_punishments) + per_page - 1) // per_page
        start, end = (page - 1) * per_page, (page - 1) * per_page + per_page
        paginated_past = past_punishments[start:end]

        msg = [f""]

        if active_punishments:
            msg.append(f"{ColorFormat.GREEN}Active §6Punishments for §e{name}§6:")
            for _, entry in active_punishments.values():
                msg.append(f"§7- {entry}")
            msg.append("§6---------------")

        msg.append(f"{ColorFormat.DARK_RED}Past §6Punishments for §e{name}§6:§r")
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

    def update_user_data(self, name: str, column: str, value):
        if isinstance(value, Vector):
            x, y, z = value.x, value.y, value.z
            value = f"{x},{y},{z}"
        self.update('users', {column: value}, 'name = ?', (name,))

class grieflog(DatabaseManager):
    """Handles actions related to grief logs and session tracking."""

    def __init__(self, db_name: str):
        """Initialize the database connection and create tables."""
        super().__init__(db_name)
        self.create_tables()

    def create_tables(self):
        """Create tables if they don't exist."""
        action_log_columns = {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'xuid': 'TEXT',
            'name': 'TEXT',
            'action': 'TEXT',
            'x': 'REAL',
            'y': 'REAL',
            'z': 'REAL',
            'dim': 'TEXT',
            'timestamp': 'INTEGER',
            'block_type': 'TEXT',
            'block_state': 'TEXT'
        }
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
        self.create_table('actions_log', action_log_columns)
        self.create_table('sessions_log', session_log_columns)
        self.create_table('user_toggles', user_toggle_columns)

    def set_user_toggle(self, xuid: str, name: str):
        """Toggles the inspect mode for a player."""
        existing_toggle = self.get_user_toggle(xuid, name)

        if existing_toggle:
            new_toggle = not existing_toggle[3]  # 'inspect_mode' assumed at index 3
            updates = {'inspect_mode': new_toggle}
            condition = 'xuid = ?'
            params = (xuid,)

            try:
                self.update('user_toggles', updates, condition, params)
            except Exception as e:
                print(f"Error updating data: {e}")
        else:
            data = {'xuid': xuid, 'name': name, 'inspect_mode': True}
            try:
                self.insert('user_toggles', data)
            except Exception as e:
                print(f"Error inserting data: {e}")

    def get_user_toggle(self, xuid: str, name: str):
        """Gets the current inspect mode toggle for a player.
        If no result exists, insert a new default value with name and inspect_mode.
        """
        query = "SELECT * FROM user_toggles WHERE xuid = ?"
        cursor = self.execute(query, (xuid,))
        result = cursor.fetchone()

        if result is None:
            default_value = 0
            insert_query = """
                INSERT INTO user_toggles (xuid, name, inspect_mode) 
                VALUES (?, ?, ?)
            """
            self.execute(insert_query, (xuid, name, default_value))

            cursor = self.execute(query, (xuid,))
            result = cursor.fetchone()

        return result

    def fetch_all_as_dicts(self, query: str, params: tuple = ()) -> list[dict]:
        """Helper to run a query and return list of dicts keyed by column name."""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()

        # Get columns from the query (better to run PRAGMA on actions_log only if query references that table)
        # We can extract table name from query but to keep simple, run PRAGMA on actions_log anyway
        pragma_cursor = self.execute("PRAGMA table_info(actions_log);")
        columns = [col[1] for col in pragma_cursor.fetchall()]

        result = []
        for row in rows:
            row_dict = {columns[i]: row[i] for i in range(len(columns))}
            if 'x' in columns and 'y' in columns and 'z' in columns:
                row_dict['location'] = f"{row_dict['x']},{row_dict['y']},{row_dict['z']}"
            result.append(row_dict)

        return result

    def get_logs_by_coordinates(self, x: float, y: float, z: float, player_name: str = None) -> list[dict]:
        query = "SELECT * FROM actions_log WHERE x = ? AND y = ? AND z = ?"
        params = (x, y, z)
        if player_name:
            query += " AND name = ?"
            params += (player_name,)
        return self.fetch_all_as_dicts(query, params)

    def get_logs_by_player(self, player_name: str) -> list[dict]:
        query = "SELECT * FROM actions_log WHERE name = ?"
        return self.fetch_all_as_dicts(query, (player_name,))

    def get_logs_within_radius(self, x: float, y: float, z: float, radius: float) -> list[dict]:
        query = """
        SELECT * FROM actions_log
        WHERE (POWER(x - ?, 2) + POWER(y - ?, 2) + POWER(z - ?, 2)) <= POWER(?, 2)
        """
        params = (x, y, z, radius)
        return self.fetch_all_as_dicts(query, params)

    def log_action(self, xuid: str, name: str, action: str, location, timestamp: int, block_type: str = None,
                   block_state: str = None, dim: str = None):
        """Logs an action performed by a player, stores x, y, z as separate coordinates, and includes block data if available."""
        if isinstance(location, Vector):
            x, y, z = location.x, location.y, location.z
        else:
            x, y, z = map(float, location.split(','))

        data = {
            'xuid': xuid,
            'name': name,
            'action': action,
            'x': x,
            'y': y,
            'z': z,
            'dim': dim,
            'timestamp': timestamp,
        }
        if block_type:
            data['block_type'] = block_type
        if block_state:
            data['block_state'] = block_state

        self.insert('actions_log', data)

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
        for start_time, end_time in sessions:
            if end_time:
                total_time += end_time - start_time
            else:
                total_time += int(time.time()) - start_time

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

    def delete_logs_older_than_seconds(self, seconds: int, sendPrint=False):
        current_time = datetime.utcnow()

        count_query = "SELECT COUNT(*) FROM actions_log"
        cursor = self.execute(count_query)
        count_result = cursor.fetchone()
        count = count_result[0] if count_result else 0

        if count == 0:
            if sendPrint:
                print("[PrimeBDS] No logs to delete.")
            return 0

        select_logs_query = "SELECT id, timestamp FROM actions_log"
        cursor = self.execute(select_logs_query)
        logs_to_delete = cursor.fetchall()

        deleted_count = 0
        for log_id, log_timestamp in logs_to_delete:
            log_time = datetime.utcfromtimestamp(log_timestamp)
            time_diff = (current_time - log_time).total_seconds()
            if time_diff > seconds:
                delete_query = "DELETE FROM actions_log WHERE id = ?"
                self.execute(delete_query, (log_id,))
                deleted_count += 1

        if sendPrint:
            time_units = [
                ("day", 86400),
                ("hour", 3600),
                ("minute", 60),
                ("second", 1)
            ]
            for unit, value in time_units:
                if seconds >= value:
                    amount = seconds // value
                    time_string = f"{amount} {unit}{'s' if amount > 1 else ''}"
                    break
            print(f"[primebds - grieflog] Purged {deleted_count} logs older than {time_string}")

        return deleted_count

    def delete_logs_within_seconds(self, seconds: int):
        current_time = datetime.utcnow()

        select_logs_query = "SELECT id, timestamp FROM actions_log"
        cursor = self.execute(select_logs_query)
        logs_to_delete = cursor.fetchall()

        deleted_count = 0
        for log_id, log_timestamp in logs_to_delete:
            log_time = datetime.utcfromtimestamp(log_timestamp)
            time_diff = (current_time - log_time).total_seconds()
            if time_diff <= seconds:
                delete_query = "DELETE FROM actions_log WHERE id = ?"
                self.execute(delete_query, (log_id,))
                deleted_count += 1

        return deleted_count

    def delete_all_logs(self):
        self.delete('actions_log', '1', ())
