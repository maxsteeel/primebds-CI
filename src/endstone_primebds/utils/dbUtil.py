import os
import sqlite3
import threading
import time
from dataclasses import dataclass, fields
from typing import List, Tuple, Any, Dict, Optional
from endstone import ColorFormat
from endstone_primebds.utils.modUtil import format_time_remaining
from endstone_primebds.utils.timeUtil import TimezoneUtils

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
    _thread_local = threading.local()

    def __init__(self, db_name: str):
        """Initialize the database manager (thread-safe)."""
        self.db_path = os.path.join(DB_FOLDER, db_name if db_name.endswith('.db') else db_name + '.db')

    def get_conn(self):
        """Get or create a SQLite connection for the current thread."""
        if not hasattr(self._thread_local, "conn"):
            self._thread_local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._thread_local.cursor = self._thread_local.conn.cursor()
        return self._thread_local.conn, self._thread_local.cursor

    def create_table(self, table_name: str, columns: Dict[str, str]):
        """Create a table if it doesn't exist."""
        conn, cursor = self.get_conn()
        column_definitions = ', '.join([f"{col} {dtype}" for col, dtype in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions})"
        with self._lock:
            cursor.execute(query)
            conn.commit()

    def insert(self, table_name: str, data: Dict[str, Any]):
        """Insert a row into the table, adding missing columns automatically."""
        conn, cursor = self.get_conn()
        with self._lock:
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1] for row in cursor.fetchall()}

            for col in data.keys():
                if col not in existing_columns:
                    value = data[col]
                    if isinstance(value, int):
                        col_type = "INTEGER"
                        default = 0
                    elif isinstance(value, float):
                        col_type = "REAL"
                        default = 0.0
                    elif isinstance(value, bool):
                        col_type = "INTEGER"
                        default = 0
                    else:
                        col_type = "TEXT"
                        default = "''"

                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type} DEFAULT {default}"
                    cursor.execute(alter_sql)

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data.values()])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            cursor.execute(query, tuple(data.values()))
            conn.commit()

    def ensure_user_table_columns(self):
        conn, cursor = self.get_conn()
        with self._lock:
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = [col[1] for col in cursor.fetchall()]

            for f in fields(User):
                if f.name not in existing_columns:
                    cursor.execute(
                        f"ALTER TABLE users ADD COLUMN {f.name} {self.get_sql_type(f.type)} DEFAULT 0"
                    )
            conn.commit()

    def get_sql_type(self, py_type):
        mapping = {int: "INTEGER", str: "TEXT", float: "REAL"}
        return mapping.get(py_type, "TEXT")

    def fetch_all(self, table_name: str) -> List[Dict[str, Any]]:
        conn, cursor = self.get_conn()
        with self._lock:
            cursor.execute(f"SELECT * FROM {table_name}")
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def fetch_by_condition(self, table_name: str, condition: str, params: Tuple) -> List[Dict[str, Any]]:
        conn, cursor = self.get_conn()
        with self._lock:
            query = f"SELECT * FROM {table_name} WHERE {condition}"
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
    def get_column_names(self, table_name: str) -> list[str]:
        """Return a list of column names for the given table."""
        with self._lock:
            conn = self.get_conn()
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
        return columns

    def update(self, table_name: str, updates: Dict[str, Any], condition: str, params: Tuple):
        conn, cursor = self.get_conn()
        with self._lock:
            update_clause = ', '.join([f"{col} = ?" for col in updates.keys()])
            query = f"UPDATE {table_name} SET {update_clause} WHERE {condition}"

            values = tuple(updates.values())
            if not isinstance(params, tuple):
                params = (params,)

            all_params = values + params
            cursor.execute(query, all_params)
            conn.commit()

    def delete(self, table_name: str, condition: str, params: Tuple):
        conn, cursor = self.get_conn()
        with self._lock:
            query = f"DELETE FROM {table_name} WHERE {condition}"
            cursor.execute(query, params)
            conn.commit()

    def close_connection(self):
        """Close the thread-local database connection."""
        if hasattr(self._thread_local, "conn"):
            self._thread_local.conn.close()
            del self._thread_local.conn
            del self._thread_local.cursor

class UserDB(DatabaseManager):
    def __init__(self, db_name: str):
        """Initialize the database connection and create tables."""
        super().__init__(db_name)
        self.player_data_cache = {}
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
            'enabled_ss': 'INTEGER'
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

        user = self.get_from_cache(xuid) or self.fetch_one("SELECT * FROM users WHERE xuid = ?", (xuid,))
        if not user:
            data = {
                'xuid': xuid, 'uuid': uuid, 'name': name, 'ping': ping, 'device_os': device,
                'client_ver': client_ver, 'last_join': last_join, 'last_leave': last_leave,
                'internal_rank': internal_rank, 'enabled_ms': 1, 'is_afk': 0, 'enabled_ss': 0
            }
            mod_data = {
                'xuid': xuid, 'name': name, 'is_muted': 0, 'mute_time': 0, 'mute_reason': "None",
                'is_banned': 0, 'banned_time': 0, 'ban_reason': "None", 'ip_address': ip, 'is_ip_banned': 0
            }
            self.insert('users', data)
            self.insert('mod_logs', mod_data)
            for f in fields(User):
                data.setdefault(f.name, f.default if f.default is not None else 0)
            self.player_data_cache[xuid] = data
        else:
            updates = {'uuid': uuid, 'name': name, 'ping': ping, 'device_os': device, 'client_ver': client_ver, 'is_afk': 0}
            self.update('users', updates, 'xuid = ?', (xuid,))
            if xuid in self.player_data_cache:
                self.player_data_cache[xuid].update(updates)
                for f in fields(User):
                    self.player_data_cache[xuid].setdefault(f.name, f.default if f.default is not None else 0)

    def get_from_cache(self, xuid: str, name: str = None) -> Optional[dict]:
        """Private method to check cache for user or mod log data."""
        if xuid in self.player_data_cache:
            cached_data = self.patch_user_fields(self.player_data_cache[xuid])
            self.player_data_cache[xuid] = cached_data

            if name and cached_data.get("name") == name:
                return cached_data
            elif not name:
                return cached_data
        return None
    
    def migrate_user_table(self):
        """Add missing columns to 'users' table according to User dataclass fields."""
        existing_columns = {row[1] for row in self.execute("PRAGMA table_info(users)").fetchall()}
        type_map = {int: "INTEGER", float: "REAL", str: "TEXT", bool: "INTEGER"}

        for f in fields(User):
            if f.name not in existing_columns:
                col_type = type_map.get(f.type, "TEXT")
                default_val = f.default if f.default is not None else 0
                default_literal = f"'{default_val}'" if col_type == "TEXT" else str(default_val)

                try:
                    self.execute(f"ALTER TABLE users ADD COLUMN {f.name} {col_type} DEFAULT {default_literal}")
                    print(f"Added missing column '{f.name}' to users table.")
                except sqlite3.OperationalError as e:
                    print(f"Warning: Could not add column '{f.name}': {e}")

    def patch_user_fields(self, data: dict) -> dict:
        """Clean data dict to only User fields and fill missing with defaults."""
        user_field_names = {f.name for f in fields(User)}

        data = {k: v for k, v in data.items() if k in user_field_names}

        for f in fields(User):
            if f.name not in data:
                if f.default is not None:
                    data[f.name] = f.default
                elif hasattr(f, "default_factory") and f.default_factory is not None:
                    data[f.name] = f.default_factory()
                else:
                    data[f.name] = 0 if f.type in [int, float, bool] else ""

        return data

    def get_online_user(self, xuid: str) -> Optional[User]:
        cached_data = self.get_from_cache(xuid)
        if cached_data:
            return User(**cached_data)

        result = self.fetch_one("SELECT * FROM users WHERE xuid = ?", (xuid,))
        if result:
            column_names = [desc[0] for desc in self.execute("PRAGMA table_info(users)").fetchall()]
            result_dict = self.patch_user_fields(dict(zip(column_names, result)))
            user = User(**result_dict)
            self.player_data_cache[xuid] = user.__dict__
            return user
        return None

    def get_offline_user(self, name: str) -> Optional[User]:
        for xuid, data in self.player_data_cache.items():
            patched_data = self.patch_user_fields(data)
            self.player_data_cache[xuid] = patched_data
            if patched_data.get("name") == name:
                return User(**patched_data)

        result = self.fetch_one("SELECT * FROM users WHERE name = ?", (name,))
        if result:
            column_names = [desc[0] for desc in self.execute("PRAGMA table_info(users)").fetchall()]
            result_dict = self.patch_user_fields(dict(zip(column_names, result)))
            user = User(**result_dict)
            self.player_data_cache[result_dict['xuid']] = user.__dict__
            return user
        return None

    def get_mod_log(self, xuid: str) -> Optional[ModLog]:
        cached = self.get_from_cache(xuid)
        if cached and "mod_log" in cached:
            return cached["mod_log"]
        row = self.fetch_one("SELECT * FROM mod_logs WHERE xuid = ?", (xuid,))
        if row:
            mod_log = ModLog(*row)
            self.player_data_cache.setdefault(xuid, {})["mod_log"] = mod_log
            return mod_log
        return None

    def get_all_users(self) -> list[dict]:
        rows = self.execute("SELECT * FROM users").fetchall()
        columns = [col[0] for col in self.execute("PRAGMA table_info(users)").fetchall()]
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
        return bool(self.fetch_one("SELECT 1 FROM mod_logs WHERE ip_address LIKE ? AND is_ip_banned = 1 LIMIT 1", (f"{ip_base}%",)))

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
        mod_log = self.fetch_one(mod_log_query, (name,))
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
        all_logs = self.execute(punishment_query, (name,)).fetchall()
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

        msg = [f"Punishment Information\n---------------"]

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
        rows = self.execute("SELECT * FROM punishment_logs WHERE name = ?", (name,)).fetchall()
        return [PunishmentLog(*row) for row in rows] if rows else None

    def delete_all_punishment_logs_by_name(self, name: str) -> bool:
        cursor = self.execute("DELETE FROM punishment_logs WHERE name = ?", (name,))
        return cursor.rowcount > 0

    def remove_punishment_log_by_id(self, name: str, log_id: int) -> bool:
        cursor = self.execute("DELETE FROM punishment_logs WHERE name = ? AND id = ?", (name, log_id))
        return cursor.rowcount > 0

    def get_offline_mod_log(self, name: str) -> Optional[ModLog]:
        row = self.fetch_one("SELECT * FROM mod_logs WHERE name = ?", (name,))
        return ModLog(*row) if row else None

    def get_xuid_by_name(self, player_name: str) -> str:
        row = self.fetch_one("SELECT xuid FROM mod_logs WHERE name = ?", (player_name,))
        return row[0] if row else None

    def get_name_by_xuid(self, xuid: str) -> str:
        row = self.fetch_one("SELECT name FROM mod_logs WHERE xuid = ?", (xuid,))
        return row[0] if row else None

    def update_user_data(self, name: str, column: str, value):
        self.update('users', {column: value}, 'name = ?', (name,))
        for xuid, data in self.player_data_cache.items():
            patched = self.patch_user_fields(data)
            self.player_data_cache[xuid] = patched
            if patched.get("name") == name:
                self.player_data_cache[xuid][column] = value
                if column == "name":
                    self.player_data_cache[value] = self.player_data_cache.pop(xuid)
                break

class grieflog(DatabaseManager):
    def __init__(self, db_name: str):
        super().__init__(db_name)
        self.create_tables()

    def create_tables(self):
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

    def get_latest_logout(self, player_name: str):
        row = self.fetchone("""
            SELECT * FROM actions_log
            WHERE name = ? AND action = 'Logout'
            ORDER BY timestamp DESC
            LIMIT 1
        """, (player_name,))
        if not row:
            return None
        columns = self.get_column_names('actions_log')
        return dict(zip(columns, row))

    def set_user_toggle(self, xuid: str, name: str):
        existing_toggle = self.get_user_toggle(xuid, name)
        if existing_toggle:
            new_toggle = not existing_toggle[3]  # Assuming 'inspect_mode' at index 3
            self.update('user_toggles', {'inspect_mode': new_toggle}, 'xuid = ?', (xuid,))
        else:
            self.insert('user_toggles', {'xuid': xuid, 'name': name, 'inspect_mode': True})

    def get_user_toggle(self, xuid: str, name: str):
        row = self.fetchone("SELECT * FROM user_toggles WHERE xuid = ?", (xuid,))
        if row is None:
            self.execute(
                "INSERT INTO user_toggles (xuid, name, inspect_mode) VALUES (?, ?, ?)",
                (xuid, name, 0)
            )
            self.commit()
            row = self.fetchone("SELECT * FROM user_toggles WHERE xuid = ?", (xuid,))
        return row

    def fetch_all_as_dicts(self, query: str, params: tuple = ()):
        rows = self.execute(query, params).fetchall()
        columns = self.get_column_names('actions_log')
        result = []
        for row in rows:
            d = {columns[i]: row[i] for i in range(len(columns))}
            if all(c in columns for c in ('x', 'y', 'z')):
                d['location'] = f"{d['x']},{d['y']},{d['z']}"
            result.append(d)
        return result

    def get_logs_by_coordinates(self, x: float, y: float, z: float, player_name: str = None):
        query = "SELECT * FROM actions_log WHERE x = ? AND y = ? AND z = ?"
        params = (x, y, z)
        if player_name:
            query += " AND name = ?"
            params += (player_name,)
        return self.fetch_all_as_dicts(query, params)

    def get_logs_by_player(self, player_name: str):
        return self.fetch_all_as_dicts("SELECT * FROM actions_log WHERE name = ?", (player_name,))

    def get_logs_within_radius(self, x: float, y: float, z: float, radius: float):
        query = """
            SELECT * FROM actions_log
            WHERE (POWER(x - ?, 2) + POWER(y - ?, 2) + POWER(z - ?, 2)) <= POWER(?, 2)
        """
        return self.fetch_all_as_dicts(query, (x, y, z, radius))

    def log_action(self, xuid: str, name: str, action: str, location, timestamp: int,
                   block_type: str = None, block_state: str = None, dim: str = None):
        if hasattr(location, 'x') and hasattr(location, 'y') and hasattr(location, 'z'):
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
            'block_type': block_type,
            'block_state': block_state,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        self.insert('actions_log', data)

    def start_session(self, xuid: str, name: str, start_time: int):
        current_session = self.get_current_session(xuid)
        if current_session:
            self.end_session(xuid, int(time.time()))
        self.insert('sessions_log', {'xuid': xuid, 'name': name, 'start_time': start_time, 'end_time': None})

    def end_session(self, xuid: str, end_time: int):
        self.execute(
            "UPDATE sessions_log SET end_time = ? WHERE xuid = ? AND end_time IS NULL",
            (end_time, xuid)
        )
        self.commit()

    def get_current_session(self, xuid: str):
        return self.fetchone(
            "SELECT * FROM sessions_log WHERE xuid = ? AND end_time IS NULL ORDER BY start_time DESC LIMIT 1",
            (xuid,)
        )

    def get_user_sessions(self, xuid: str):
        rows = self.execute("SELECT start_time, end_time FROM sessions_log WHERE xuid = ?", (xuid,)).fetchall()
        now = int(time.time())
        result = []
        for start_time, end_time in rows:
            duration = (now - start_time) if end_time is None else (end_time - start_time)
            result.append({'start_time': start_time, 'end_time': end_time, 'duration': duration})
        return result

    def get_total_playtime(self, xuid: str):
        rows = self.execute("SELECT start_time, end_time FROM sessions_log WHERE xuid = ?", (xuid,)).fetchall()
        now = int(time.time())
        total_time = 0
        for start_time, end_time in rows:
            total_time += (end_time - start_time) if end_time else (now - start_time)
        return total_time

    def get_all_playtimes(self):
        users = self.execute("SELECT xuid, name FROM sessions_log GROUP BY name").fetchall()
        result = []
        for xuid, name in users:
            total_playtime = self.get_total_playtime(xuid)
            result.append({'xuid': xuid, 'name': name, 'total_playtime': total_playtime})
        return result

    def delete_logs_older_than_seconds(self, seconds: int, sendPrint=False):
        threshold = int(time.time()) - seconds
        count = self.fetchone("SELECT COUNT(*) FROM actions_log")[0]
        if count == 0:
            if sendPrint:
                print("[PrimeBDS] No logs to delete.")
            return 0

        self.execute("DELETE FROM actions_log WHERE timestamp < ?", (threshold,))
        self.commit()

        if sendPrint:
            # Format time string
            units = [("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)]
            for unit, val in units:
                if seconds >= val:
                    amount = seconds // val
                    time_string = f"{amount} {unit}{'s' if amount > 1 else ''}"
                    break
            print(f"[primebds - grieflog] Purged logs older than {time_string}")
        return self.fetchone("SELECT COUNT(*) FROM actions_log")[0]

    def delete_logs_within_seconds(self, seconds: int):
        threshold = int(time.time()) - seconds
        self.execute("DELETE FROM actions_log WHERE timestamp >= ?", (threshold,))
        self.commit()

    def delete_all_logs(self):
        self.execute("DELETE FROM actions_log WHERE 1")
        self.commit()
