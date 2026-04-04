import logging
import os
import random
import sqlite3
import asyncio
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram import ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationHandlerStop,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WIB = timezone(timedelta(hours=7))
DB_PATH = os.getenv("DB_PATH", "bot.db")
OWNER_IDS = {int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip().isdigit()}
INITIAL_CASH = 5000
EXP_MIN = 5
EXP_MAX = 15
EXP_COOLDOWN_SECONDS = 300
MAX_HP = 200
MAX_ARMOR = 100
DAILY_COOLDOWN = 24 * 3600
WEEKLY_COOLDOWN = 7 * 24 * 3600
KP_DAMAGE_RANGE = (5, 10)
SEMAK_DAMAGE_RANGE = (5, 10)
DOR_COOLDOWN_SECONDS = 60
DEATH_COMBAT_COOLDOWN_SECONDS = 180

ROLE_RANGES = [
    (1, 5, "💩 Manusia Antah Berantah"), (6, 10, "👩🏿‍🦲 Super Gembel"), (11, 15, "👩🏾‍🦲 Gembel"),
    (16, 20, "👩🏽‍🦲 Gembel Elite"), (21, 25, "👩🏼‍🦲 Jelata"), (26, 30, "🪔 Pengemis Pemula"),
    (31, 40, "🪔 Pengemis Biasa"), (41, 45, "🪔 Pengemis Senior"), (46, 50, "🪔 Pengemis Profesional"),
    (51, 55, "👨🏾‍🦲 Pemulung Pemula"), (56, 60, "👨🏽‍🦲 Pemulung Biasa"), (61, 65, "👨🏼‍🦲 Pemulung Senior"),
    (66, 70, "👨🏻‍🦲 Pemulung Profesional"), (71, 75, "🧌 Miskin"), (76, 80, "👫 Rakyat Biasa"),
    (81, 85, "🎎 Rakyat Menengah Kebawah"), (86, 90, "👷🏻 Rakyat Menengah"), (91, 95, "🤵🏻‍♀ Orang Kaya"),
    (96, 100, "👩🏻‍🚀 Kaum Elite"), (101, 110, "Bangsawan"), (111, 120, "🥉 Konglomerat III"),
    (121, 130, "🥈 Konglomerat II"), (131, 140, "🥇 Konglomerat I"), (141, 149, "🎖 Elite Nasional"),
    (150, 9999, "🐛 Naga"),
]

SHOP_ITEMS = {
    "banana": {"name": "🍌 Kulit Pisang", "price": 200, "type": "consumable", "desc": "Damage 5-10", "max_stack": 999},
    "sandal": {"name": "🩴 Sandal Emak", "price": 200, "type": "consumable", "desc": "Damage 5-10", "max_stack": 999},
    "ramal_scroll": {"name": "🔮 Ramal", "price": 200, "type": "consumable", "desc": "Sekali pakai untuk intip inventory target (/ramal)", "max_stack": 99},
    "luck_potion": {"name": "🧪 Lucky Potion", "price": 5000, "type": "consumable", "desc": "Buff luck +5% (pakai /lp)", "max_stack": 99},
    "luck_potion_med": {"name": "⚗️ Luck Potion Med", "price": 7500, "type": "consumable", "desc": "Buff luck +15% (pakai /lpm)", "max_stack": 99},
    "random_chest": {"name": "🎁 Random Chest", "price": 5000, "type": "consumable", "desc": "Buka chest acak sesuai rate weekly", "max_stack": 99},
    "shield_3": {"name": "🛡️ Perisai Kelas III", "price": 2000, "type": "consumable", "desc": "Shield level III, aktif otomatis saat kena /dor", "max_stack": 99},
    "shield_2": {"name": "🛡️ Perisai Kelas II", "price": 4000, "type": "consumable", "desc": "Shield level II, aktif otomatis saat kena /dor", "max_stack": 99},
    "shield_1": {"name": "🛡️ Perisai Kelas I", "price": 5000, "type": "consumable", "desc": "Shield level I, aktif otomatis saat kena /dor", "max_stack": 99},
    "pistol_3": {"name": "🔫 Pistol Kelas III", "price": 5000, "type": "consumable", "desc": "Damage 10-20, curi cash 500 (exp +100)", "max_stack": 99},
    "pistol_2": {"name": "🔫 Pistol Kelas II", "price": 7500, "type": "consumable", "desc": "Damage 30-40, curi cash 1500 (exp +200)", "max_stack": 99},
    "pistol_1": {"name": "🔫 Pistol Kelas I", "price": 10000, "type": "consumable", "desc": "Damage 50-70, curi cash 2500 (exp +300)", "max_stack": 99},
    "potion_red": {"name": "❤️ Potion Merah", "price": 100, "type": "consumable", "desc": "Tambah HP 10% (pakai /pot)", "max_stack": 99},
    "potion_red_big": {"name": "💖 Potion Merah Besar", "price": 1000, "type": "consumable", "desc": "Pulihkan HP 100% (pakai /potbig)", "max_stack": 99},
    "armor_item": {"name": "🦺 Armor", "price": 5000, "type": "consumable", "desc": "Tambah armor +100 (pakai /armor)", "max_stack": 99},
    "bag_small": {"name": "👛 Tas Kecil", "price": 5000, "type": "upgrade", "desc": "+3 slot", "capacity": 3},
    "bag_tenun": {"name": "🛍 Tas Tenun", "price": 10000, "type": "upgrade", "desc": "+5 slot", "capacity": 5},
    "bag_samping": {"name": "💼 Tas Samping", "price": 15000, "type": "upgrade", "desc": "+7 slot", "capacity": 7},
    "bag_sekolah": {"name": "🎒 Tas Sekolah", "price": 20000, "type": "upgrade", "desc": "+10 slot", "capacity": 10},
    "bag_gunung": {"name": "🧳 Koper", "price": 25000, "type": "upgrade", "desc": "+15 slot", "capacity": 15},
    "premium_1w": {"name": "⭐ Premium 1W", "price": 50000, "type": "service", "desc": "Aktif premium 1 minggu (7 hari)"},
}

PISTOL_CONFIG = {
    3: {"code": "pistol_3", "name": "🔫 Pistol Kelas III", "damage": (10, 20), "steal": (100, 500), "exp": 100},
    2: {"code": "pistol_2", "name": "🔫 Pistol Kelas II", "damage": (30, 40), "steal": (750, 1500), "exp": 200},
    1: {"code": "pistol_1", "name": "🔫 Pistol Kelas I", "damage": (50, 70), "steal": (1000, 2500), "exp": 300},
}

SHIELD_CONFIG = {
    3: {"code": "shield_3", "name": "🛡️ Perisai Kelas III"},
    2: {"code": "shield_2", "name": "🛡️ Perisai Kelas II"},
    1: {"code": "shield_1", "name": "🛡️ Perisai Kelas I"},
}

SHIELD_PISTOL_EFFECTS = {
    # (shield_class, pistol_class): (damage_reduce_percent, steal_reduce_percent)
    (3, 3): (10, 30),
    (3, 2): (10, 10),
    (3, 1): (10, 5),
    (2, 3): (50, 100),
    (2, 2): (20, 30),
    (2, 1): (10, 5),
    (1, 3): (75, 100),
    (1, 2): (50, 50),
    (1, 1): (30, 30),
}

SPECIAL_ITEMS = {
    "sniper_owner": {"name": "🎯 Sniper Owner", "max_stack": 1},
}

REDEEM_DEFAULT_REWARDS = {
    "token": ("token", 1),
    "random chest": ("item", ("random_chest", 1)),
    "random_chest": ("item", ("random_chest", 1)),
    "cash": ("cash", 5000),
    "exp": ("exp", 100),
    "kunci rahasia": ("item", ("chest_key", 1)),
    "peti rahasia": ("item", ("secret_chest", 1)),
}

ITEM_ALIASES = {
    "kulit pisang": "banana",
    "sandal emak": "sandal",
    "ramal": "ramal_scroll",
    "lucky potion": "luck_potion",
    "luck potion med": "luck_potion_med",
    "random chest": "random_chest",
    "perisai kelas iii": "shield_3",
    "perisai kelas ii": "shield_2",
    "perisai kelas i": "shield_1",
    "pistol kelas iii": "pistol_3",
    "pistol kelas ii": "pistol_2",
    "pistol kelas i": "pistol_1",
    "potion merah": "potion_red",
    "potion merah besar": "potion_red_big",
    "armor": "armor_item",
    "premium 1w": "premium_1w",
    "premium 1 minggu": "premium_1w",
    "kunci rahasia": "chest_key",
    "peti rahasia": "secret_chest",
    "bom": "bomb_item",
    "awm": "awm_item",
    "nuklir": "nuke_item",
}

SECRET_ITEMS = {
    "chest_key": {"name": "🗝️ Kunci Rahasia", "price": 3000, "token_price": 3, "type": "consumable", "desc": "Kunci pembuka Peti Rahasia", "max_stack": 99},
    "secret_chest": {"name": "🎁 Peti Rahasia", "price": 5000, "token_price": 5, "type": "consumable", "desc": "Buka dengan /open + Kunci Rahasia", "max_stack": 99},
    "bomb_item": {"name": "💣 Bom", "price": 25000, "token_price": 25, "type": "consumable", "desc": "Pakai /bom", "max_stack": 99},
    "awm_item": {"name": "🎯 AWM", "price": 70000, "token_price": 70, "type": "consumable", "desc": "Pakai /piw", "max_stack": 99},
    "nuke_item": {"name": "☢️ Nuklir", "price": 100000, "token_price": 100, "type": "consumable", "desc": "Pakai /dhuar", "max_stack": 99},
    "anti_radiation": {"name": "🧪 Anti Radiasi", "price": 50000, "token_price": 50, "type": "consumable", "desc": "Counter /dhuar", "max_stack": 99},
    "bomb_defuser": {"name": "🧰 Penjinak Bom", "price": 10000, "token_price": 10, "type": "consumable", "desc": "Counter /bom", "max_stack": 99},
    "armor_plus": {"name": "🛡️ Armor Plus", "price": 30000, "token_price": 30, "type": "consumable", "desc": "Counter /piw", "max_stack": 99},
}

CHEST_DROP_TABLE = [
    ("bomb_item", 5.0),
    ("awm_item", 1.5),
    ("nuke_item", 0.5),
    ("anti_radiation", 2.5),
    ("bomb_defuser", 10.0),
    ("armor_plus", 3.0),
]

CHEST_RATES = [
    ("uncommon", 43.0),
    ("common", 33.0),
    ("rare", 13.0),
    ("epic", 7.5),
    ("legend", 3.0),
    ("myth", 0.0015),
]

CHEST_REWARDS = {
    "uncommon": {"cash": 150, "token": (0, 1), "items": []},
    "common": {"cash": 250, "token": (0, 2), "items": ["banana"]},
    "rare": {"cash": 350, "token": (1, 2), "items": ["banana", "sandal", "shield_3"]},
    "epic": {"cash": 500, "token": (2, 5), "items": ["banana", "sandal", "shield_3", "pistol_3"]},
    "legend": {"cash": 750, "token": (3, 5), "items": ["banana", "sandal", "shield_2", "pistol_2"]},
    "myth": {"cash": 1500, "token": (5, 10), "items": ["banana", "sandal", "shield_1", "pistol_1"], "bonus_awm_chance": 0.2},
}


@dataclass
class UserData:
    user_id: int
    name: str
    username: str
    cash: int
    level: int
    exp: int
    role: str
    register_at: str
    inventory_capacity: int
    hp: int
    hp_max: int
    armor: int
    token: int
    premium: int


KP_QUOTES = [
    "Matane, cok!",
    "Huelahdalah, opo iki cok!",
    "Cangkeme o asu",
    "Lah, iki opo sih cok!",
    "Naon si anying!",
]

SEMAK_QUOTES = [
    "Matane, cok!",
    "Huelahdalah, opo iki cok!",
    "Cangkeme o asu",
    "Lah, iki opo sih cok!",
    "O Asu, Sendal sopo iki cok!",
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_wib_str() -> str:
    return datetime.now(WIB).date().isoformat()


def format_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def role_for_level(level: int) -> str:
    for start, end, role in ROLE_RANGES:
        if start <= level <= end:
            return role
    return "🎖 Elite Nasional"


def parse_premium_duration(token: str) -> Optional[timedelta]:
    t = token.strip().lower()
    mapping = {
        "1w": timedelta(days=7),
        "1m": timedelta(days=30),
        "3m": timedelta(days=90),
        "6m": timedelta(days=180),
        "12m": timedelta(days=365),
        "1y": timedelta(days=365),
    }
    return mapping.get(t)


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT,
                cash INTEGER DEFAULT {INITIAL_CASH},
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                role TEXT DEFAULT '💩 Manusia Antah Berantah',
                register_at TEXT NOT NULL,
                inventory_capacity INTEGER DEFAULT 5,
                hp INTEGER DEFAULT {MAX_HP},
                hp_max INTEGER DEFAULT {MAX_HP},
                armor INTEGER DEFAULT 0,
                token INTEGER DEFAULT 0,
                premium INTEGER DEFAULT 0,
                bank_cash INTEGER DEFAULT 0,
                radiation_until TEXT,
                daily_last_claim TEXT,
                weekly_last_claim TEXT,
                luck_buff_until TEXT,
                luck_buff_rate INTEGER DEFAULT 0,
                premium_until TEXT,
                role_locked INTEGER DEFAULT 0,
                random_chest_buy_count INTEGER DEFAULT 0,
                random_chest_buy_date TEXT
            )
            """
        )
        user_columns = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
        if "premium_until" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN premium_until TEXT")
        if "bank_cash" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN bank_cash INTEGER DEFAULT 0")
        if "radiation_until" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN radiation_until TEXT")
        if "luck_buff_rate" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN luck_buff_rate INTEGER DEFAULT 0")
        if "role_locked" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN role_locked INTEGER DEFAULT 0")
        if "random_chest_buy_count" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN random_chest_buy_count INTEGER DEFAULT 0")
        if "random_chest_buy_date" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN random_chest_buy_date TEXT")
        if "death_cooldown_until" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN death_cooldown_until TEXT")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_catalog (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT DEFAULT '',
                is_secret INTEGER DEFAULT 0
            )
            """
        )
        columns = {row[1] for row in c.execute("PRAGMA table_info(shop_catalog)").fetchall()}
        if "code" not in columns:
            c.execute("ALTER TABLE shop_catalog ADD COLUMN code TEXT")
        if "description" not in columns:
            c.execute("ALTER TABLE shop_catalog ADD COLUMN description TEXT DEFAULT ''")
        if "is_secret" not in columns:
            c.execute("ALTER TABLE shop_catalog ADD COLUMN is_secret INTEGER DEFAULT 0")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                qty INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, item_code)
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS bag_upgrades (
                user_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                PRIMARY KEY (user_id, item_code)
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS exp_cooldown (
                user_id INTEGER PRIMARY KEY,
                last_gain TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_users (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS dor_cooldown (
                user_id INTEGER PRIMARY KEY,
                last_used TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                currency_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                before_balance INTEGER NOT NULL,
                after_balance INTEGER NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_shop_tx_user_created ON shop_transactions(user_id, created_at DESC)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shop_tx_idem ON shop_transactions(user_id, idempotency_key) WHERE idempotency_key IS NOT NULL")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                reward_spec TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS redeem_claims (
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                claimed_at TEXT NOT NULL,
                PRIMARY KEY (code, user_id)
            )
            """
        )
        seed_items = []
        idx = 1
        for code, item in SHOP_ITEMS.items():
            seed_items.append((idx, code, item["name"], item["type"], item["price"], item["desc"], 0))
            idx += 1
        for code, item in SECRET_ITEMS.items():
            seed_items.append((idx, code, item["name"], item["type"], item["price"], item["desc"], 1))
            idx += 1
        c.executemany(
            """INSERT INTO shop_catalog (id, code, name, type, price, description, is_secret)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(code) DO UPDATE SET
                 name=excluded.name,
                 type=excluded.type,
                 price=excluded.price,
                 description=excluded.description,
                 is_secret=excluded.is_secret""",
            seed_items,
        )
        conn.commit()


def get_user(user_id: int) -> Optional[UserData]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return None
        return UserData(*row[:14])


def get_balance(user_id: int, currency: str) -> int:
    field = "token" if currency == "token" else "cash"
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(f"SELECT {field} FROM users WHERE user_id=?", (user_id,)).fetchone()
        return int(row[0]) if row else 0


def log_shop_transaction(
    user_id: int,
    item_code: str,
    currency_type: str,
    amount: int,
    before_balance: int,
    after_balance: int,
    status: str,
    idempotency_key: Optional[str] = None,
):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO shop_transactions
            (user_id, item_code, currency_type, amount, before_balance, after_balance, status, idempotency_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                item_code,
                currency_type,
                amount,
                before_balance,
                after_balance,
                status,
                idempotency_key,
                now_utc().isoformat(),
            ),
        )
        conn.commit()


def ensure_user(tg_user) -> UserData:
    user = get_user(tg_user.id)
    if user:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET name=?, username=? WHERE user_id=?", (tg_user.full_name, f"@{tg_user.username}" if tg_user.username else "-", tg_user.id))
            conn.commit()
        return get_user(tg_user.id)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO users (user_id, name, username, cash, level, exp, role, register_at, inventory_capacity, hp, hp_max, armor, token, premium)
               VALUES (?, ?, ?, ?, 1, 0, ?, ?, 5, ?, ?, 0, 0, 0)""",
            (
                tg_user.id,
                tg_user.full_name,
                f"@{tg_user.username}" if tg_user.username else "-",
                INITIAL_CASH,
                role_for_level(1),
                now_utc().isoformat(),
                MAX_HP,
                MAX_HP,
            ),
        )
        conn.commit()
    return get_user(tg_user.id)


def update_chat_member(chat_id: int, user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO chat_users (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
        conn.commit()


def exp_needed(level: int) -> int:
    return level * 100


def add_exp(user_id: int, amount: int) -> Tuple[int, int]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        level, exp = c.execute("SELECT level, exp FROM users WHERE user_id=?", (user_id,)).fetchone()
        exp += amount
        up = 0
        while exp >= exp_needed(level):
            exp -= exp_needed(level)
            level += 1
            up += 1
        current_role, role_locked = c.execute("SELECT role, role_locked FROM users WHERE user_id=?", (user_id,)).fetchone()
        new_role = current_role if role_locked else role_for_level(level)
        c.execute("UPDATE users SET level=?, exp=?, role=? WHERE user_id=?", (level, exp, new_role, user_id))
        conn.commit()
        return level, up


def add_cash(user_id: int, amount: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET cash=cash+? WHERE user_id=?", (amount, user_id))
        conn.commit()


def add_item(user_id: int, code: str, qty: int = 1):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO inventory (user_id, item_code, qty) VALUES (?, ?, ?)
               ON CONFLICT(user_id, item_code) DO UPDATE SET qty=qty+excluded.qty""",
            (user_id, code, qty),
        )
        conn.commit()


def item_name(code: str) -> str:
    item = SHOP_ITEMS.get(code) or SECRET_ITEMS.get(code) or SPECIAL_ITEMS.get(code)
    return item["name"] if item else code


def normalize_key(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def resolve_item_code(token: str) -> Optional[str]:
    raw = token.strip().lower()
    if raw in SHOP_ITEMS or raw in SECRET_ITEMS or raw in SPECIAL_ITEMS:
        return raw
    key = normalize_key(raw)
    if key in ITEM_ALIASES:
        return ITEM_ALIASES[key]
    for code, item in {**SHOP_ITEMS, **SECRET_ITEMS, **SPECIAL_ITEMS}.items():
        if normalize_key(item["name"]) == key:
            return code
    return None


def user_tag(user_id: int) -> str:
    user = get_user(user_id)
    if not user:
        return "@unknown"
    if user.username and user.username != "-":
        return user.username
    safe_name = "".join(ch for ch in user.name.lower().replace(" ", "_") if ch.isalnum() or ch == "_")
    return f"@{safe_name[:20] or 'user'}"


def get_item_qty(user_id: int, code: str) -> int:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT qty FROM inventory WHERE user_id=? AND item_code=?", (user_id, code)).fetchone()
        return row[0] if row else 0


def consume_item(user_id: int, code: str, qty: int = 1) -> bool:
    current = get_item_qty(user_id, code)
    if current < qty:
        return False
    with sqlite3.connect(DB_PATH) as conn:
        left = current - qty
        if left == 0:
            conn.execute("DELETE FROM inventory WHERE user_id=? AND item_code=?", (user_id, code))
        else:
            conn.execute("UPDATE inventory SET qty=? WHERE user_id=? AND item_code=?", (left, user_id, code))
        conn.commit()
    return True


def parse_redeem_reward_spec(spec: str):
    rewards = []
    for part in [p.strip() for p in spec.split("+") if p.strip()]:
        qty = 1
        key = part.lower()
        if ":" in key:
            left, right = key.rsplit(":", 1)
            if right.strip().isdigit():
                key = left.strip()
                qty = max(1, int(right.strip()))
        key = normalize_key(key)
        reward = REDEEM_DEFAULT_REWARDS.get(key)
        if reward:
            reward_type, value = reward
            if reward_type == "item":
                item_code, base_qty = value
                rewards.append(("item", item_code, base_qty * qty))
            else:
                rewards.append((reward_type, int(value) * qty))
            continue
        item_code = resolve_item_code(key)
        if item_code:
            rewards.append(("item", item_code, qty))
            continue
        return None, f"Reward tidak dikenali: '{part}'."
    return rewards, None


def get_best_pistol_class(user_id: int) -> Optional[int]:
    for cls in (3, 2, 1):
        if get_item_qty(user_id, PISTOL_CONFIG[cls]["code"]) > 0:
            return cls
    return None


def get_best_shield_class(user_id: int) -> Optional[int]:
    for cls in (1, 2, 3):
        if get_item_qty(user_id, SHIELD_CONFIG[cls]["code"]) > 0:
            return cls
    return None


def pistol_vs_shield_result(pistol_class: int, shield_class: Optional[int], raw_damage: int, raw_steal: int) -> Tuple[int, int]:
    if not shield_class:
        return raw_damage, raw_steal
    dmg_red, steal_red = SHIELD_PISTOL_EFFECTS.get((shield_class, pistol_class), (0, 0))
    final_damage = max(0, int(round(raw_damage * (1 - (dmg_red / 100)))))
    final_steal = max(0, int(round(raw_steal * (1 - (steal_red / 100)))))
    return final_damage, final_steal


def steal_cash(attacker_id: int, target_id: int, amount: int) -> Tuple[int, int]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        target_cash = c.execute("SELECT cash FROM users WHERE user_id=?", (target_id,)).fetchone()[0]
        if amount <= 0:
            return 0, target_cash
        stolen = min(target_cash, amount)
        if stolen > 0:
            c.execute("UPDATE users SET cash=cash-? WHERE user_id=?", (stolen, target_id))
            c.execute("UPDATE users SET cash=cash+? WHERE user_id=?", (stolen, attacker_id))
            conn.commit()
        return stolen, target_cash


def inventory_slots_used(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        return c.execute("SELECT COUNT(*) FROM inventory WHERE user_id=? AND qty>0", (user_id,)).fetchone()[0]


def get_luck_buff_until(user_id: int) -> Optional[datetime]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT luck_buff_until FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]:
            return None
        return datetime.fromisoformat(row[0])


def has_active_luck(user_id: int) -> bool:
    until = get_luck_buff_until(user_id)
    return bool(until and now_utc() < until)


def get_luck_buff_rate(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT luck_buff_until, luck_buff_rate FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]:
            return 0
        until = datetime.fromisoformat(row[0])
        if now_utc() >= until:
            return 0
        return row[1] or 0


def get_premium_until(user_id: int) -> Optional[datetime]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT premium_until FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]:
            return None
        return datetime.fromisoformat(row[0])


def is_premium_active(user_id: int) -> bool:
    until = get_premium_until(user_id)
    if until and now_utc() < until:
        return True
    return False


def roll_chest_tier(luck_bonus_percent: int = 0) -> str:
    rates = list(CHEST_RATES)
    if luck_bonus_percent > 0:
        factor = 1 + (luck_bonus_percent / 100)
        rates = [
            (tier, weight * factor if tier in {"rare", "epic", "legend", "myth"} else weight)
            for tier, weight in rates
        ]
    total = sum(weight for _, weight in rates)
    r = random.uniform(0, total)
    upto = 0.0
    for tier, weight in rates:
        upto += weight
        if r <= upto:
            return tier
    return rates[0][0]


def parse_target(update: Update, args: list[str]) -> Optional[int]:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    if not args:
        return None
    token = args[0].strip()
    if token.startswith("@"):
        with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
            row = c.execute("SELECT user_id FROM users WHERE username=?", (token,)).fetchone()
            return row[0] if row else None
    if token.isdigit():
        return int(token)
    return None


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


def in_same_group(chat_id: int, user_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT 1 FROM chat_users WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        return bool(row)


def check_dor_cooldown(user_id: int) -> Optional[int]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT last_used FROM dor_cooldown WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]:
            return None
        elapsed = (now_utc() - datetime.fromisoformat(row[0])).total_seconds()
        if elapsed < DOR_COOLDOWN_SECONDS:
            return int(DOR_COOLDOWN_SECONDS - elapsed)
    return None


def set_dor_used(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO dor_cooldown (user_id, last_used) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET last_used=excluded.last_used",
            (user_id, now_utc().isoformat()),
        )
        conn.commit()


def death_cooldown_remaining(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT death_cooldown_until FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row[0]:
            return 0
        until = datetime.fromisoformat(row[0])
        remain = int((until - now_utc()).total_seconds())
        if remain > 0:
            return remain
        c.execute("UPDATE users SET death_cooldown_until=NULL WHERE user_id=?", (user_id,))
        conn.commit()
        return 0


def activate_death_cooldown(user_id: int, seconds: int = DEATH_COMBAT_COOLDOWN_SECONDS) -> Tuple[int, int]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        hp_max = c.execute("SELECT hp_max FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        until = now_utc() + timedelta(seconds=seconds)
        c.execute("UPDATE users SET hp=?, death_cooldown_until=? WHERE user_id=?", (hp_max, until.isoformat(), user_id))
        conn.commit()
        return hp_max, seconds


async def ensure_can_attack(update: Update, user_id: int) -> bool:
    remain = death_cooldown_remaining(user_id)
    if remain <= 0:
        return True
    await update.message.reply_text(f"⏳ Kamu masih cooldown pasca-mati {remain} detik, belum bisa menyerang.")
    return False


async def ensure_target_attackable(update: Update, target_id: int) -> bool:
    remain = death_cooldown_remaining(target_id)
    if remain <= 0:
        return True
    await update.message.reply_text(f"🛡️ Target {user_tag(target_id)} sedang cooldown pasca-mati ({remain} detik), tidak bisa diserang.")
    return False


async def post_damage_effects(update: Update, context: ContextTypes.DEFAULT_TYPE, target_id: int, hp: int, cause: str):
    target_tag = user_tag(target_id)
    if hp > 0:
        if hp < int(MAX_HP * 0.2):
            await update.message.reply_text(
                f"⚠️ HP target ({target_tag}) kritis (<20%). Segera beli /buy potion_red lalu pakai /pot."
            )
        return
    hp_now, cooldown_sec = activate_death_cooldown(target_id)
    await update.message.reply_text(
        f"☠️ User {target_tag} telah mati. Penyebab: {cause}.\n"
        f"❤️ HP dipulihkan ke {hp_now}. User masuk cooldown combat {cooldown_sec} detik (tidak bisa menyerang/diserang)."
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if update.effective_chat.type != "private":
        update_chat_member(update.effective_chat.id, user.user_id)
    await update.message.reply_text("Halo! Gunakan /help untuk melihat command user.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Command User\n"
        "/start\n/p atau /profile (bisa /p @username atau reply)\n/status\n/inv\n/shop\n/secretshop atau /ss\n/buy <kode_item/nama_item>\n/open\n/pot\n/potbig\n/lp\n/lpm\n/ramal <id/@username>\n"
        "/dor <id/@username> atau reply lalu /dor\n/aim <id/@username> atau reply lalu /aim (owner only)\n"
        "/bom <id/@username>\n/piw <id/@username>\n/dhuar\n"
        "/kp <id/@username> atau reply lalu /kp\n/semak <id/@username> atau reply lalu /semak\n"
        "/transfer <id_tujuan> <jumlah>\n/tf <id_tujuan> <jumlah>\n"
        "/bank\n/deposit atau /dp <jumlah>\n/withdraw atau /wd <jumlah>\n"
        "/daily\n/weekly\n/cd\n/lb\n/lbglobal\n/redeem <kode>\n/info <item|command>\n/help"
    )
    if update.effective_chat.type == "private":
        await update.message.reply_text(text)
        return
    try:
        await context.bot.send_message(update.effective_user.id, text)
        await update.message.reply_text("📩 Daftar command dikirim ke chat pribadi bot.")
    except Exception:
        await update.message.reply_text("Gagal kirim DM. Silakan start bot di private chat dulu, lalu ulangi /help.")


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Gunakan: /info <nama item|command>")
        return
    raw = " ".join(context.args).strip()
    query = raw.lower().lstrip("/")
    command_info = {
        "pot": "Pakai Potion Merah untuk memulihkan HP 10%.",
        "potbig": "Pakai Potion Merah Besar untuk memulihkan HP penuh.",
        "lp": "Aktifkan lucky buff +5% untuk chest.",
        "lpm": "Aktifkan lucky buff +15% untuk chest.",
        "buy": "Beli item dari shop: /buy <kode_item>.",
        "open": "Buka Peti Rahasia (butuh Kunci Rahasia).",
        "dor": "Menembak target menggunakan pistol terbaik di inventory.",
        "redeem": "Klaim kode redeem: /redeem <kode>.",
        "info": "Lihat info item/command: /info <nama>.",
    }
    if query in command_info:
        await update.message.reply_text(f"ℹ️ /{query}\n{command_info[query]}")
        return
    item_code = resolve_item_code(raw)
    if not item_code:
        await update.message.reply_text("Item/command tidak ditemukan.")
        return
    item = SHOP_ITEMS.get(item_code) or SECRET_ITEMS.get(item_code) or SPECIAL_ITEMS.get(item_code, {})
    usage_map = {
        "potion_red": "/pot",
        "potion_red_big": "/potbig",
        "armor_item": "Dibeli untuk isi armor ke 100 (otomatis saat pembelian).",
        "premium_1w": "Beli via /buy premium_1w (aktif premium 7 hari).",
        "luck_potion": "/lp",
        "luck_potion_med": "/lpm",
        "secret_chest": "/open",
        "bomb_item": "/bom <target>",
        "awm_item": "/piw <target>",
        "nuke_item": "/dhuar",
    }
    use_text = usage_map.get(item_code, "Tidak ada command khusus (otomatis/consumable umum).")
    await update.message.reply_text(
        f"ℹ️ {item.get('name', item_code)} (`{item_code}`)\n"
        f"Deskripsi: {item.get('desc', '-')}\n"
        f"Cara pakai: {use_text}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester = ensure_user(update.effective_user)
    target = requester
    target_id = parse_target(update, context.args)
    if target_id:
        found = get_user(target_id)
        if found:
            target = found
    if update.effective_chat.type != "private":
        update_chat_member(update.effective_chat.id, requester.user_id)
    dt = datetime.fromisoformat(target.register_at).astimezone(WIB)
    now = datetime.now(WIB)
    premium_until = get_premium_until(target.user_id)
    premium_text = "Tidak aktif"
    if premium_until and now_utc() < premium_until:
        remain = str(premium_until - now_utc()).split(".")[0]
        premium_text = f"Aktif ({remain})"
    msg = (
        f"Nama : {target.name}\n"
        f"Username : {target.username}\n"
        f"ID : {target.user_id}\n"
        f"Cash : {format_int(target.cash)}\n"
        f"Level : {target.level} ({target.exp}/{exp_needed(target.level)})\n"
        f"Role : {target.role or '-'}\n"
        f"Premium : {premium_text}\n"
        f"Register Date : {dt.strftime('%Y-%m-%d')}\n"
        f"Time : {now.strftime('%H:%M:%S WIB')}"
    )
    premium_buttons = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Buy Premium", url="https://t.me/Noturkichan"),
            InlineKeyboardButton("Buy Token", url="https://t.me/Noturkichan"),
            InlineKeyboardButton("Buy Cash", url="https://t.me/Noturkichan"),
        ]]
    )
    await update.message.reply_text(msg, reply_markup=premium_buttons)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    buff_list = []
    debuff = "Tidak ada"
    premium_until = get_premium_until(user.user_id)
    if premium_until and now_utc() < premium_until:
        p_remain = str(premium_until - now_utc()).split(".")[0]
        buff_list.append(f"Premium aktif ({p_remain})")
    luck_until = get_luck_buff_until(user.user_id)
    if luck_until and now_utc() < luck_until:
        remaining = str(luck_until - now_utc()).split(".")[0]
        buff_list.append(f"Lucky buff +{get_luck_buff_rate(user.user_id)}% chest luck ({remaining})")
    if get_item_qty(user.user_id, "bomb_defuser") > 0:
        buff_list.append("Penjinak Bom siap")
    if get_item_qty(user.user_id, "armor_plus") > 0:
        buff_list.append("Armor Plus siap")
    if get_item_qty(user.user_id, "anti_radiation") > 0:
        buff_list.append("Anti Radiasi siap")
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rad = c.execute("SELECT radiation_until FROM users WHERE user_id=?", (user.user_id,)).fetchone()[0]
    if rad:
        rad_until = datetime.fromisoformat(rad)
        if now_utc() < rad_until:
            debuff = f"☢️ Radiasi aktif ({str(rad_until - now_utc()).split('.')[0]})"
    death_cd = death_cooldown_remaining(user.user_id)
    if death_cd > 0:
        debuff = f"🕒 Cooldown pasca-mati aktif ({death_cd} detik)."
    if user.hp < int(user.hp_max * 0.2):
        debuff = "⚠️ HP kritis (<20%)"
    buff = ", ".join(buff_list) if buff_list else "Tidak ada"
    text = f"HP : {user.hp}/{user.hp_max}\nArmor : {user.armor}/{MAX_ARMOR}\nBuff : {buff}\nDebuff : {debuff}"
    await update.message.reply_text(text)
    if user.hp < int(user.hp_max * 0.2):
        await update.message.reply_text("🚨 ALERT: HP kamu di bawah 20%, segera beli /buy potion_red lalu pakai /pot.")


async def cmd_inv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute("SELECT item_code, qty FROM inventory WHERE user_id=? AND qty>0 ORDER BY item_code", (user.user_id,)).fetchall()
    lines = [
        f"🎫 Token : {format_int(user.token)}",
        f"🎒 Inventory ({inventory_slots_used(user.user_id)}/{user.inventory_capacity} slot):",
    ]
    if not rows:
        lines.append("- Kosong")
    else:
        for code, qty in rows:
            name = item_name(code)
            lines.append(f"- {name} x{qty} (`{code}`)")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


def discount_price(user: UserData, price: int) -> int:
    return int(price * 0.7) if is_premium_active(user.user_id) else price


async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    await send_shop_page(update, user, page=0)


def fetch_shop_rows(user: UserData):
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute(
            """SELECT code, name, type, price, description, is_secret
               FROM shop_catalog
               WHERE is_secret=0
               ORDER BY type ASC, id ASC"""
        ).fetchall()
    return rows


async def send_shop_page(update: Update, user: UserData, page: int, from_callback: bool = False):
    rows = fetch_shop_rows(user)
    per_page = 4
    total_pages = max(1, (len(rows) + per_page - 1) // per_page)
    page = page % total_pages
    start = page * per_page
    chunk = rows[start:start + per_page]

    lines = [f"🛒 Shop (Page {page + 1}/{total_pages}):"]
    for code, name, item_type, price_raw, desc, is_secret in chunk:
        tag = " [Secret]" if is_secret else ""
        item = SHOP_ITEMS.get(code) or SECRET_ITEMS.get(code) or {}
        token_price = item.get("token_price")
        if is_secret and token_price is not None:
            lines.append(f"- {name}{tag} | {item_type} | Harga {token_price} token\n  ↳ {desc}")
        else:
            price = discount_price(user, price_raw)
            lines.append(f"- {name}{tag} | {item_type} | Harga {format_int(price)}\n  ↳ {desc}")

    buttons = []
    for code, name, _type, price_raw, _desc, is_secret in chunk:
        item = SHOP_ITEMS.get(code) or SECRET_ITEMS.get(code) or {}
        token_price = item.get("token_price")
        buy_key = uuid.uuid4().hex[:8]
        if is_secret and token_price is not None:
            label = f"{name} ({token_price} token)"
        else:
            price = discount_price(user, price_raw)
            label = f"{name} ({format_int(price)})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"buy:{code}:{buy_key}")])

    if total_pages > 1:
        buttons.append([InlineKeyboardButton("➡️ Next", callback_data=f"shop:{page + 1}")])

    text = "\n".join(lines)
    if from_callback and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_shop_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = ensure_user(query.from_user)
    _, raw_page = query.data.split(":", 1)
    page = int(raw_page) if raw_page.isdigit() else 0
    await send_shop_page(update, user, page=page, from_callback=True)


async def buy_item(user: UserData, code: str, idempotency_key: Optional[str] = None) -> str:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute(
            "SELECT name, type, price, description, is_secret FROM shop_catalog WHERE code=?",
            (code,),
        ).fetchone()
    if not row:
        return "Kode item tidak ditemukan / belum terbuka."
    name, item_type, base_price, _desc, is_secret = row
    if is_secret and user.level < 5:
        return "Kode item tidak ditemukan / belum terbuka."

    item = SHOP_ITEMS.get(code) or SECRET_ITEMS.get(code)
    if not item:
        return "Item belum dipetakan ke gameplay."

    token_price = item.get("token_price")
    currency_type = "token" if is_secret and token_price is not None else "cash"
    amount = token_price if currency_type == "token" else discount_price(user, base_price)
    if idempotency_key:
        with sqlite3.connect(DB_PATH) as conn:
            tx = conn.execute(
                "SELECT status FROM shop_transactions WHERE user_id=? AND idempotency_key=?",
                (user.user_id, idempotency_key),
            ).fetchone()
        if tx:
            return "Pembelian ini sudah diproses sebelumnya."
    before_balance = get_balance(user.user_id, currency_type)
    if is_secret and token_price is not None:
        if user.token < token_price:
            log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
            return "Token kamu tidak cukup."
    else:
        price = discount_price(user, base_price)
        if user.cash < price:
            log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
            return "Cash kamu tidak cukup."

    if item_type == "upgrade":
        price = discount_price(user, base_price)
        with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
            exists = c.execute("SELECT 1 FROM bag_upgrades WHERE user_id=? AND item_code=?", (user.user_id, code)).fetchone()
            if exists:
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_duplicate_upgrade", idempotency_key)
                return "Upgrade tas ini sudah pernah dibeli."
            c.execute("INSERT INTO bag_upgrades (user_id, item_code) VALUES (?, ?)", (user.user_id, code))
            updated = c.execute(
                "UPDATE users SET cash=cash-?, inventory_capacity=inventory_capacity+? WHERE user_id=? AND cash>=?",
                (price, item['capacity'], user.user_id, price),
            )
            if updated.rowcount == 0:
                conn.rollback()
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
                return "Cash kamu tidak cukup."
            conn.commit()
        after_balance = get_balance(user.user_id, currency_type)
        log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, after_balance, "success", idempotency_key)
        return f"Berhasil beli {name}. Kapasitas inventory +{item['capacity']}."

    if code == "armor_item":
        price = discount_price(user, base_price)
        with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
            armor_now = c.execute("SELECT armor FROM users WHERE user_id=?", (user.user_id,)).fetchone()[0]
            if armor_now >= MAX_ARMOR:
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_armor_full", idempotency_key)
                return "Armor kamu masih penuh (100/100), tidak bisa beli armor lagi sekarang."
            updated = conn.execute(
                "UPDATE users SET cash=cash-?, armor=? WHERE user_id=? AND cash>=?",
                (price, MAX_ARMOR, user.user_id, price),
            )
            if updated.rowcount == 0:
                conn.rollback()
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
                return "Cash kamu tidak cukup."
            conn.commit()
        after_balance = get_balance(user.user_id, currency_type)
        log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, after_balance, "success", idempotency_key)
        return f"Berhasil beli 🦺 Armor. Armor diisi ulang ke {MAX_ARMOR}/{MAX_ARMOR}."

    if code == "random_chest":
        today = today_wib_str()
        luck_rate = get_luck_buff_rate(user.user_id)
        chest_tier = roll_chest_tier(luck_rate)
        reward = CHEST_REWARDS[chest_tier]
        token_bonus = random.randint(reward["token"][0], reward["token"][1])
        got_items = []
        reward_item_codes = list(reward["items"])
        bonus_awm = reward.get("bonus_awm_chance")
        if bonus_awm and random.random() <= bonus_awm:
            reward_item_codes.append("awm_item")
        with sqlite3.connect(DB_PATH) as conn:
            updated = conn.execute(
                """
                UPDATE users
                SET cash=cash-?+?,
                    token=token+?,
                    random_chest_buy_count=
                        CASE
                            WHEN random_chest_buy_date=? THEN random_chest_buy_count+1
                            ELSE 1
                        END,
                    random_chest_buy_date=?
                WHERE user_id=?
                  AND cash>=?
                  AND (CASE WHEN random_chest_buy_date=? THEN random_chest_buy_count ELSE 0 END) < 5
                """,
                (price, reward["cash"], token_bonus, today, today, user.user_id, price, today),
            )
            if updated.rowcount == 0:
                conn.rollback()
                reason_row = conn.execute(
                    "SELECT cash, random_chest_buy_count, random_chest_buy_date FROM users WHERE user_id=?",
                    (user.user_id,),
                ).fetchone()
                if not reason_row:
                    log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_user_not_found", idempotency_key)
                    return "User tidak ditemukan."
                cash_now, daily_count, last_buy_date = reason_row
                effective_count = daily_count if last_buy_date == today else 0
                if effective_count >= 5:
                    log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_daily_limit", idempotency_key)
                    return "⚠️ Random Chest hanya bisa dibeli 5 kali per hari. Coba lagi besok."
                if cash_now < price:
                    log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
                    return "Cash kamu tidak cukup."
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_unknown", idempotency_key)
                return "Gagal memproses pembelian Random Chest. Coba lagi."
            for item_code in reward_item_codes:
                conn.execute(
                    "INSERT INTO inventory (user_id, item_code, qty) VALUES (?, ?, 1) ON CONFLICT(user_id, item_code) DO UPDATE SET qty=qty+1",
                    (user.user_id, item_code),
                )
                got_items.append(item_name(item_code))
            conn.commit()
        after_balance = get_balance(user.user_id, currency_type)
        log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, after_balance, "success", idempotency_key)
        luck_note = f" (Lucky +{luck_rate}% aktif)" if luck_rate > 0 else ""
        item_note = f" | Item: {', '.join(got_items)}" if got_items else ""
        return f"Berhasil beli 🎁 Random Chest dan langsung dibuka!\nChest {chest_tier}{luck_note}: +{reward['cash']} cash, +{token_bonus} token{item_note}\nSisa {currency_type}: {format_int(after_balance)}"

    if code == "premium_1w":
        price = discount_price(user, base_price)
        now = now_utc()
        with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
            current_until_row = c.execute("SELECT premium_until FROM users WHERE user_id=?", (user.user_id,)).fetchone()
            current_until = datetime.fromisoformat(current_until_row[0]) if current_until_row and current_until_row[0] else None
            start_from = current_until if current_until and current_until > now else now
            new_until = start_from + timedelta(days=7)
            updated = conn.execute(
                "UPDATE users SET cash=cash-?, premium=1, premium_until=? WHERE user_id=? AND cash>=?",
                (price, new_until.isoformat(), user.user_id, price),
            )
            if updated.rowcount == 0:
                conn.rollback()
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
                return "Cash kamu tidak cukup."
            conn.commit()
        after_balance = get_balance(user.user_id, currency_type)
        log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, after_balance, "success", idempotency_key)
        return f"✅ Premium 1 minggu aktif sampai {new_until.astimezone(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')}.\nSisa cash: {format_int(after_balance)}"

    if inventory_slots_used(user.user_id) >= user.inventory_capacity and get_item_qty(user.user_id, code) == 0:
        return "Inventory penuh. Upgrade tas dulu di shop."

    max_stack = item.get("max_stack", 999)
    current = get_item_qty(user.user_id, code)
    if current >= max_stack:
        log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_max_stack", idempotency_key)
        return f"Stack {name} sudah maksimum ({max_stack})."

    with sqlite3.connect(DB_PATH) as conn:
        if is_secret and token_price is not None:
            updated = conn.execute(
                "UPDATE users SET token=token-? WHERE user_id=? AND token>=?",
                (token_price, user.user_id, token_price),
            )
            if updated.rowcount == 0:
                conn.rollback()
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
                return "Token kamu tidak cukup."
        else:
            price = discount_price(user, base_price)
            updated = conn.execute(
                "UPDATE users SET cash=cash-? WHERE user_id=? AND cash>=?",
                (price, user.user_id, price),
            )
            if updated.rowcount == 0:
                conn.rollback()
                log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, before_balance, "failed_insufficient", idempotency_key)
                return "Cash kamu tidak cukup."
        conn.execute(
            "INSERT INTO inventory (user_id, item_code, qty) VALUES (?, ?, 1) ON CONFLICT(user_id, item_code) DO UPDATE SET qty=qty+1",
            (user.user_id, code),
        )
        conn.commit()
    after_balance = get_balance(user.user_id, currency_type)
    log_shop_transaction(user.user_id, code, currency_type, amount, before_balance, after_balance, "success", idempotency_key)
    if is_secret and token_price is not None:
        return f"Berhasil beli {name} pakai {token_price} token. Sisa token: {format_int(after_balance)}"
    return f"Berhasil beli {name}. Sisa cash: {format_int(after_balance)}"


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("Gunakan: /buy <kode_item/nama_item>")
        return
    raw_item = " ".join(context.args).strip()
    code = resolve_item_code(raw_item) or raw_item.lower()
    res = await buy_item(user, code)
    await update.message.reply_text(res)


async def cb_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = ensure_user(query.from_user)
    payload = query.data.split(":")
    code = payload[1] if len(payload) > 1 else ""
    idem_key = payload[2] if len(payload) > 2 else None
    res = await buy_item(user, code, idempotency_key=idem_key)
    try:
        await query.edit_message_text(res)
    except Exception:
        await query.message.reply_text(res)


async def cmd_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = ensure_user(update.effective_user)
    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        await update.message.reply_text("Gunakan: /transfer <id_tujuan> <jumlah>")
        return
    target_id = int(context.args[0]); amount = int(context.args[1])
    if amount <= 0 or sender.cash < amount:
        await update.message.reply_text("Jumlah tidak valid / cash tidak cukup.")
        return
    if not get_user(target_id):
        await update.message.reply_text("User tujuan belum terdaftar.")
        return
    tax = max(1, int(amount * 0.1))
    received = amount - tax
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET cash=cash-? WHERE user_id=?", (amount, sender.user_id))
        conn.execute("UPDATE users SET cash=cash+? WHERE user_id=?", (received, target_id))
        conn.commit()
    await update.message.reply_text(
        f"_Transfer berhasil: {format_int(amount)} ke ID {target_id} | Pajak 10%: {format_int(tax)} | Diterima: {format_int(received)}_",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    text = f"🏦 Bank {user.username}\nSaldo bank: {format_int(get_bank_cash(user.user_id))}\nCash dompet: {format_int(user.cash)}"
    if update.effective_chat.type == "private":
        await update.message.reply_text(text)
        return
    try:
        await context.bot.send_message(user.user_id, text)
        await update.message.reply_text("📩 Saldo bank dikirim ke chat pribadi bot.")
    except Exception:
        await update.message.reply_text("Gagal kirim DM. Silakan start bot di private chat dulu, lalu ulangi /bank.")


def get_bank_cash(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT bank_cash FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row[0] if row else 0


async def cmd_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Gunakan: /deposit <jumlah>")
        return
    amount = int(context.args[0])
    if amount <= 0 or user.cash < amount:
        await update.message.reply_text("Jumlah tidak valid / cash tidak cukup.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET cash=cash-?, bank_cash=bank_cash+? WHERE user_id=?", (amount, amount, user.user_id))
        conn.commit()
    await update.message.reply_text(f"🏦 Deposit berhasil: {format_int(amount)}")


async def cmd_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Gunakan: /withdraw <jumlah>")
        return
    amount = int(context.args[0])
    bank_cash = get_bank_cash(user.user_id)
    if amount <= 0 or bank_cash < amount:
        await update.message.reply_text("Jumlah tidak valid / saldo bank tidak cukup.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET cash=cash+?, bank_cash=bank_cash-? WHERE user_id=?", (amount, amount, user.user_id))
        conn.commit()
    await update.message.reply_text(f"🏦 Withdraw berhasil: {format_int(amount)}")


async def cmd_secretshop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if update.effective_chat.type != "private":
        await update.message.reply_text("🔒 Gunakan /ss di chat pribadi bot ya.")
        return
    if user.level < 5:
        await update.message.reply_text("🔒 Secret shop terbuka saat level 5.")
        return
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute(
            """SELECT code, name, description
               FROM shop_catalog
               WHERE is_secret=1
               ORDER BY id ASC"""
        ).fetchall()
    if not rows:
        await update.message.reply_text("Secret shop belum tersedia.")
        return
    lines = [f"🕵️ Secret Shop (Token kamu: {user.token})"]
    buttons = []
    for code, name, _desc in rows:
        item = SECRET_ITEMS.get(code, {})
        token_price = item.get("token_price", 1)
        lines.append(f"- {name} | Harga {token_price} token")
        buttons.append([InlineKeyboardButton(f"{name} ({token_price} token)", callback_data=f"buy:{code}")])
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not consume_item(user.user_id, "secret_chest"):
        await update.message.reply_text("Kamu tidak punya 🎁 Peti Rahasia.")
        return
    if not consume_item(user.user_id, "chest_key"):
        add_item(user.user_id, "secret_chest", 1)
        await update.message.reply_text("Kamu tidak punya 🗝️ Kunci Rahasia untuk membuka peti.")
        return

    cash_reward = random.randint(1000, 5000)
    exp_reward = random.randint(500, 2000)
    token_reward = random.randint(1, 5)
    add_cash(user.user_id, cash_reward)
    add_exp(user.user_id, exp_reward)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET token=token+? WHERE user_id=?", (token_reward, user.user_id))
        conn.commit()

    bonus_items = []
    for code, chance in CHEST_DROP_TABLE:
        if random.random() <= (chance / 100):
            add_item(user.user_id, code, 1)
            bonus_items.append(item_name(code))
    bonus_text = f"\nBonus item: {', '.join(bonus_items)}" if bonus_items else "\nBonus item: tidak ada"
    await update.message.reply_text(
        f"🎁 Peti dibuka!\nCash +{format_int(cash_reward)}\nEXP +{format_int(exp_reward)}\nToken +{token_reward}{bonus_text}"
    )


async def apply_nuke_debuff(target_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    if death_cooldown_remaining(target_id) > 0:
        return
    until = now_utc() + timedelta(seconds=10)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET radiation_until=? WHERE user_id=?", (until.isoformat(), target_id))
        conn.commit()
    for _ in range(10):
        await asyncio.sleep(1)
        with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
            if death_cooldown_remaining(target_id) > 0:
                return
            row = c.execute("SELECT hp, hp_max FROM users WHERE user_id=?", (target_id,)).fetchone()
            if not row:
                return
            hp, hp_max = row
            if hp <= 0:
                return
            burn = max(1, int(hp_max * 0.1))
            hp = max(0, hp - burn)
            c.execute("UPDATE users SET hp=? WHERE user_id=?", (hp, target_id))
            conn.commit()
            if hp <= 0:
                await handle_death_background(chat_id, target_id, context, "Radiasi nuklir")
                return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET radiation_until=NULL WHERE user_id=?", (target_id,))
        conn.commit()


async def cmd_bom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not await ensure_can_attack(update, user.user_id):
        return
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target tidak valid.")
        return
    if not await ensure_target_attackable(update, target_id):
        return
    if target_id == user.user_id:
        await update.message.reply_text("Tidak bisa /bom diri sendiri.")
        return
    if not consume_item(user.user_id, "bomb_item"):
        await update.message.reply_text("Kamu tidak punya 💣 Bom.")
        return
    add_exp(user.user_id, 500)
    if consume_item(target_id, "bomb_defuser"):
        await update.message.reply_text("Yahaha Ga jadi kena, wleeee! 🤪")
        return
    dmg = random.randint(50, 100)
    steal_amount = random.randint(1000, 3000)
    hp, armor, hp_dmg = apply_damage(target_id, dmg)
    stolen, _ = steal_cash(user.user_id, target_id, steal_amount)
    target_tag = user_tag(target_id)
    await update.message.reply_text(
        f"💣 BOOM ke {target_tag}! Damage {dmg} (HP kena {hp_dmg}). Curi cash {format_int(stolen)}. EXP +500.\nSisa target: HP {hp}, Armor {armor}"
    )
    await post_damage_effects(update, context, target_id, hp, "Kena /bom")


async def cmd_piw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not await ensure_can_attack(update, user.user_id):
        return
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target tidak valid.")
        return
    if not await ensure_target_attackable(update, target_id):
        return
    if target_id == user.user_id:
        await update.message.reply_text("Tidak bisa /piw diri sendiri.")
        return
    if not consume_item(user.user_id, "awm_item"):
        await update.message.reply_text("Kamu tidak punya 🎯 AWM.")
        return
    add_exp(user.user_id, 1000)
    dmg = 300
    if consume_item(target_id, "armor_plus"):
        await update.message.reply_text("Waduh, hampir aja wafat! 😱")
        dmg = int(dmg * 0.7)
    steal_amount = random.randint(1000, 5000)
    hp, armor, hp_dmg = apply_damage(target_id, dmg)
    stolen, _ = steal_cash(user.user_id, target_id, steal_amount)
    target_tag = user_tag(target_id)
    await update.message.reply_text(
        f"🎯 PIW ke {target_tag}! Damage {dmg} (HP kena {hp_dmg}). Curi cash {format_int(stolen)}. EXP +1000.\nSisa target: HP {hp}, Armor {armor}"
    )
    await post_damage_effects(update, context, target_id, hp, "Kena /piw")


async def cmd_dhuar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in {"group", "supergroup"}:
        await update.message.reply_text("/dhuar hanya bisa digunakan di grup.")
        return
    user = ensure_user(update.effective_user)
    if not await ensure_can_attack(update, user.user_id):
        return
    if not consume_item(user.user_id, "nuke_item"):
        await update.message.reply_text("Kamu tidak punya ☢️ Nuklir.")
        return
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute("SELECT user_id FROM chat_users WHERE chat_id=? LIMIT 20", (update.effective_chat.id,)).fetchall()
    target_ids = [r[0] for r in rows]
    random.shuffle(target_ids)
    target_ids = target_ids[:10]
    if not target_ids:
        await update.message.reply_text("Tidak ada target di lokasi.")
        return
    lines = ["☢️ DHUAR! Nuklir meledak!"]
    for tid in target_ids:
        if death_cooldown_remaining(tid) > 0:
            lines.append(f"- {user_tag(tid)}: sedang cooldown pasca-mati, aman dari serangan.")
            continue
        hp, armor, hp_dmg = apply_damage(tid, 100)
        if consume_item(tid, "anti_radiation"):
            lines.append(f"- {user_tag(tid)}: kena damage 100 (HP kena {hp_dmg}). Preet, Mati aja lu yang nge dhuar 😤")
        else:
            lines.append(f"- {user_tag(tid)}: kena damage 100 (HP kena {hp_dmg}) + debuff radiasi 10 detik.")
            asyncio.create_task(apply_nuke_debuff(tid, update.effective_chat.id, context))
        await post_damage_effects(update, context, tid, hp, "Kena /dhuar")
    await update.message.reply_text("\n".join(lines))


async def cmd_use_pot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not consume_item(user.user_id, "potion_red"):
        await update.message.reply_text("Kamu tidak punya Potion Merah.")
        return
    heal = max(1, int(user.hp_max * 0.1))
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET hp=MIN(hp+?, hp_max) WHERE user_id=?", (heal, user.user_id))
        conn.commit()
    await update.message.reply_text(f"Kamu memakai Potion Merah. HP +{heal} (10% dari max HP {user.hp_max}).")


async def cmd_use_big_pot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not consume_item(user.user_id, "potion_red_big"):
        await update.message.reply_text("Kamu tidak punya Potion Merah Besar.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET hp=hp_max WHERE user_id=?", (user.user_id,))
        conn.commit()
    await update.message.reply_text("💖 Potion Merah Besar dipakai. HP pulih 100%.")


async def cmd_ramal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not consume_item(user.user_id, "ramal_scroll"):
        await update.message.reply_text("Kamu butuh 🔮 Ramal untuk mengintip inventory target.")
        return
    target_id = parse_target(update, context.args)
    target = get_user(target_id) if target_id else None
    if not target:
        add_item(user.user_id, "ramal_scroll", 1)
        await update.message.reply_text("Target tidak valid. Item Ramal dikembalikan.")
        return
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute("SELECT item_code, qty FROM inventory WHERE user_id=? AND qty>0 ORDER BY item_code", (target.user_id,)).fetchall()
    lines = [f"🔮 Hasil ramal inventory {user_tag(target.user_id)}:"]
    if not rows:
        lines.append("- Kosong")
    else:
        for code, qty in rows:
            lines.append(f"- {item_name(code)} x{qty}")
    await update.message.reply_text("\n".join(lines))


async def cmd_use_armor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not consume_item(user.user_id, "armor_item"):
        await update.message.reply_text("Kamu tidak punya Armor item.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET armor=armor+100 WHERE user_id=?", (user.user_id,))
        conn.commit()
    await update.message.reply_text("Armor +100 berhasil dipakai.")


async def cmd_use_lucky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not consume_item(user.user_id, "luck_potion"):
        await update.message.reply_text("Kamu tidak punya Lucky Potion.")
        return
    until = now_utc() + timedelta(minutes=60)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET luck_buff_until=?, luck_buff_rate=5 WHERE user_id=?", (until.isoformat(), user.user_id))
        conn.commit()
    await update.message.reply_text("Buff luck +5% aktif selama 60 menit.")


async def cmd_use_lucky_med(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not consume_item(user.user_id, "luck_potion_med"):
        await update.message.reply_text("Kamu tidak punya Luck Potion Med.")
        return
    until = now_utc() + timedelta(minutes=60)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET luck_buff_until=?, luck_buff_rate=15 WHERE user_id=?", (until.isoformat(), user.user_id))
        conn.commit()
    await update.message.reply_text("Buff luck +15% aktif selama 60 menit.")


def apply_damage(target_id: int, dmg: int) -> Tuple[int, int, int]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        hp, armor = c.execute("SELECT hp, armor FROM users WHERE user_id=?", (target_id,)).fetchone()
        remaining = dmg
        armor_loss = min(armor, remaining)
        armor -= armor_loss
        remaining -= armor_loss
        hp = max(0, hp - remaining)
        c.execute("UPDATE users SET hp=?, armor=? WHERE user_id=?", (hp, armor, target_id))
        conn.commit()
        return hp, armor, remaining


async def attack_throw(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str, min_dmg: int, max_dmg: int, label: str, quotes: Optional[list[str]] = None):
    user = ensure_user(update.effective_user)
    if not await ensure_can_attack(update, user.user_id):
        return
    if update.effective_chat.type in {"group", "supergroup"}:
        update_chat_member(update.effective_chat.id, user.user_id)
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target tidak valid.")
        return
    if update.effective_chat.type in {"group", "supergroup"} and not update.message.reply_to_message and not in_same_group(update.effective_chat.id, target_id):
        await update.message.reply_text("Target harus berada di grup yang sama.")
        return
    if target_id == user.user_id:
        await update.message.reply_text("Tidak bisa menyerang diri sendiri.")
        return
    if not await ensure_target_attackable(update, target_id):
        return
    if not consume_item(user.user_id, code):
        await update.message.reply_text(f"Kamu tidak punya {label}.")
        return
    dmg = random.randint(min_dmg, max_dmg)
    hp, armor, hp_dmg = apply_damage(target_id, dmg)
    target_tag = user_tag(target_id)
    quote = f'\n💬 "{random.choice(quotes)}"' if quotes else ""
    await update.message.reply_text(f"{label} dilempar ke {target_tag}! Damage {dmg} (kena HP {hp_dmg}). Status target HP {hp}, Armor {armor}.{quote}")
    await post_damage_effects(update, context, target_id, hp, f"Kena {label}")


async def cmd_kp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await attack_throw(update, context, "banana", KP_DAMAGE_RANGE[0], KP_DAMAGE_RANGE[1], "🍌 Kulit Pisang", KP_QUOTES)


async def cmd_semak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await attack_throw(update, context, "sandal", SEMAK_DAMAGE_RANGE[0], SEMAK_DAMAGE_RANGE[1], "🩴 Sandal Emak", SEMAK_QUOTES)


async def cmd_dor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in {"group", "supergroup"}:
        await update.message.reply_text("/dor hanya bisa digunakan di grup.")
        return
    user = ensure_user(update.effective_user)
    if not await ensure_can_attack(update, user.user_id):
        return
    update_chat_member(update.effective_chat.id, user.user_id)
    remain_cd = check_dor_cooldown(user.user_id)
    if remain_cd is not None:
        await update.message.reply_text(f"/dor masih cooldown {remain_cd} detik.")
        return
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target tidak valid.")
        return
    if not await ensure_target_attackable(update, target_id):
        return
    if not update.message.reply_to_message and not in_same_group(update.effective_chat.id, target_id):
        await update.message.reply_text("Target harus berada di grup yang sama.")
        return
    if target_id == user.user_id:
        await update.message.reply_text("Tidak bisa /dor diri sendiri.")
        return
    pistol_class = get_best_pistol_class(user.user_id)
    if not pistol_class:
        await update.message.reply_text("Kamu butuh pistol (Kelas III/II/I) untuk /dor.")
        return
    pistol = PISTOL_CONFIG[pistol_class]
    consume_item(user.user_id, pistol["code"])

    raw_damage = random.randint(pistol["damage"][0], pistol["damage"][1])
    raw_steal = random.randint(pistol["steal"][0], pistol["steal"][1])
    shield_class = get_best_shield_class(target_id)
    shield_note = "Target tidak punya perisai."
    if shield_class:
        consume_item(target_id, SHIELD_CONFIG[shield_class]["code"])
        shield_note = f"Target auto pakai {SHIELD_CONFIG[shield_class]['name']}."
    final_damage, final_steal = pistol_vs_shield_result(pistol_class, shield_class, raw_damage, raw_steal)
    hp, armor, hp_dmg = apply_damage(target_id, final_damage)
    stolen, target_cash_before = steal_cash(user.user_id, target_id, final_steal)
    add_exp(user.user_id, pistol["exp"])
    set_dor_used(user.user_id)
    kriminal_note = ""
    if final_steal > 0 and target_cash_before <= 0:
        kriminal_note = "\n⚠️ Peringatan: target tidak punya cash tersisa. Pelaku /dor tercatat sebagai kriminal keji."
    target_tag = user_tag(target_id)
    await update.message.reply_text(
        f"{pistol['name']} ditembakkan ke {target_tag}!\n"
        f"Damage: {raw_damage} -> {final_damage} (HP kena {hp_dmg})\n"
        f"Curian cash: {format_int(raw_steal)} -> {format_int(final_steal)} | Berhasil curi: {format_int(stolen)}\n"
        f"EXP didapat: +{pistol['exp']}\n"
        f"{shield_note}\n"
        f"Sisa target: HP {hp}, Armor {armor}, Cash {format_int(max(0, target_cash_before - stolen))}"
        f"{kriminal_note}"
    )
    await post_damage_effects(update, context, target_id, hp, "Ditembak /dor")


async def claim_reward(update: Update, context: ContextTypes.DEFAULT_TYPE, typ: str):
    user = ensure_user(update.effective_user)
    last_field = "daily_last_claim" if typ == "daily" else "weekly_last_claim"
    cooldown = timedelta(seconds=DAILY_COOLDOWN if typ == "daily" else WEEKLY_COOLDOWN)
    base_cash, base_exp = (150, 50) if typ == "daily" else (500, 250)
    base_token = 0 if typ == "daily" else 1

    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        last = c.execute(f"SELECT {last_field} FROM users WHERE user_id=?", (user.user_id,)).fetchone()[0]
        now = now_utc()
        if last and now - datetime.fromisoformat(last) < cooldown:
            left = cooldown - (now - datetime.fromisoformat(last))
            await update.message.reply_text(f"Masih cooldown. Sisa: {left}")
            return
        multi = 2 if is_premium_active(user.user_id) else 1
        cash = base_cash * multi
        exp = base_exp * multi
        token_add = base_token * multi
        chest_msg = ""
        if typ == "weekly":
            luck_rate = get_luck_buff_rate(user.user_id)
            chest_tier = roll_chest_tier(luck_rate)
            reward = CHEST_REWARDS[chest_tier]
            cash += reward["cash"] * multi
            token_bonus = random.randint(reward["token"][0], reward["token"][1]) * multi
            token_add += token_bonus
            got_items = []
            for code in reward["items"]:
                add_item(user.user_id, code, 1)
                got_items.append(SHOP_ITEMS[code]["name"])
            bonus_awm = reward.get("bonus_awm_chance")
            if bonus_awm and random.random() <= bonus_awm:
                add_item(user.user_id, "awm_item", 1)
                got_items.append(SECRET_ITEMS["awm_item"]["name"])
            luck_note = f" (Lucky +{luck_rate}% aktif)" if luck_rate > 0 else ""
            item_note = f" | Item: {', '.join(got_items)}" if got_items else ""
            chest_msg = f"\n🎁 Chest {chest_tier}{luck_note}: +{reward['cash'] * multi} cash, +{token_bonus} token{item_note}"
        c.execute(f"UPDATE users SET {last_field}=?, cash=cash+?, token=token+? WHERE user_id=?", (now.isoformat(), cash, token_add, user.user_id))
        conn.commit()
    new_lvl, up = add_exp(user.user_id, exp)
    up_msg = f"\n⬆️ Level up ke {new_lvl}" if up else ""
    await update.message.reply_text(f"Claim {typ} berhasil: +{cash} cash +{exp} exp +{token_add} token{chest_msg}{up_msg}")


async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await claim_reward(update, context, "daily")


async def cmd_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await claim_reward(update, context, "weekly")


async def cmd_cd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        daily, weekly = c.execute("SELECT daily_last_claim, weekly_last_claim FROM users WHERE user_id=?", (user.user_id,)).fetchone()
    now = now_utc()
    def remain(last, days):
        if not last:
            return "Siap claim"
        delta = timedelta(days=days) - (now - datetime.fromisoformat(last))
        return "Siap claim" if delta.total_seconds() <= 0 else str(delta)
    await update.message.reply_text(f"Daily: {remain(daily, 1)}\nWeekly: {remain(weekly, 7)}")


async def render_lb(update: Update, context: ContextTypes.DEFAULT_TYPE, global_lb: bool):
    limit = 10
    if context.args and context.args[0].isdigit():
        limit = min(100, max(1, int(context.args[0])))

    user = ensure_user(update.effective_user)
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        if global_lb:
            rows = c.execute("SELECT user_id, name, level, exp FROM users ORDER BY level DESC, exp DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = c.execute(
                """SELECT u.user_id, u.name, u.level, u.exp FROM users u
                   JOIN chat_users cu ON cu.user_id=u.user_id
                   WHERE cu.chat_id=? ORDER BY u.level DESC, u.exp DESC LIMIT ?""",
                (update.effective_chat.id, limit),
            ).fetchall()
    title = "🌍 Leaderboard Global" if global_lb else "🏠 Leaderboard Lokal"
    text = [f"{title} (Top {limit})"]
    for i, (uid, name, lvl, exp) in enumerate(rows, 1):
        text.append(f"{i}. {name} ({uid}) - Lv.{lvl} ({exp}/{exp_needed(lvl)})")

    msg = "\n".join(text)
    if limit == 100:
        try:
            await context.bot.send_message(user.user_id, msg)
            await update.message.reply_text("Top 100 dikirim ke chat pribadi bot.")
        except Exception:
            await update.message.reply_text("Gagal kirim DM. Start bot via private chat dulu.")
    else:
        await update.message.reply_text(msg)


async def cmd_lb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_lb(update, context, False)


async def cmd_lbglobal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await render_lb(update, context, True)


async def passive_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type == "private":
        return
    user = ensure_user(update.effective_user)
    update_chat_member(update.effective_chat.id, user.user_id)

    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT last_gain FROM exp_cooldown WHERE user_id=?", (user.user_id,)).fetchone()
        now = now_utc()
        if row and row[0] and now - datetime.fromisoformat(row[0]) < timedelta(seconds=EXP_COOLDOWN_SECONDS):
            return
        # EXP chat grup: 1 chat = random 5-15 EXP, cooldown 5 menit
        gain = random.randint(EXP_MIN, EXP_MAX)
        c.execute("INSERT INTO exp_cooldown (user_id, last_gain) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET last_gain=excluded.last_gain", (user.user_id, now.isoformat()))
        conn.commit()
    lvl, up = add_exp(user.user_id, gain)
    if up:
        await update.message.reply_text(f"{update.effective_user.mention_html()} naik level ke {lvl}!", parse_mode=ParseMode.HTML)


def resolve_user_by_ref(token: str) -> Optional[int]:
    if token.isdigit():
        return int(token)
    if token.startswith("@"):
        with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
            row = c.execute("SELECT user_id FROM users WHERE username=?", (token,)).fetchone()
            return row[0] if row else None
    return None


async def require_owner(update: Update) -> bool:
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Khusus owner.")
        return False
    return True


def is_damage_command_in_private(command_text: str, chat_type: str) -> bool:
    if chat_type != "private":
        return False
    cmd = command_text.split()[0].lower().lstrip("/")
    return cmd in {"kp", "semak", "bom", "piw", "dor", "aim", "dhuar"}


async def guard_user_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.message.text.startswith("/"):
        return
    user = ensure_user(update.effective_user)
    cmd_name = update.message.text.split()[0].lower().lstrip("/")
    dead_whitelist = {"start", "help", "unmute", "info"}
    if user.hp <= 0:
        if cmd_name in dead_whitelist:
            return
        await update.message.reply_text(
            "☠️ Kamu sedang mati, jadi tidak bisa menggunakan command apa pun.\n"
            "Pulihkan HP dulu sebelum memakai command lagi."
        )
        raise ApplicationHandlerStop
    if is_damage_command_in_private(update.message.text, update.effective_chat.type):
        await update.message.reply_text(
            "❌ Tidak bisa menyerang melalui chat pribadi bot. Gunakan command serangan di grup."
        )
        raise ApplicationHandlerStop


async def is_owner_or_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if is_owner(update.effective_user.id):
        return True
    if update.effective_chat.type not in {"group", "supergroup"}:
        return False
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in {"administrator", "creator"}
    except Exception:
        return False


async def restore_hp_to_max(user_id: int) -> Tuple[int, int]:
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        hp_max = c.execute("SELECT hp_max FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        c.execute("UPDATE users SET hp=? WHERE user_id=?", (hp_max, user_id))
        conn.commit()
        return hp_max, hp_max


async def run_unmute_flow(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> Tuple[int, int]:
    perms = ChatPermissions(can_send_messages=True)
    await context.bot.restrict_chat_member(chat_id, user_id, permissions=perms)
    return await restore_hp_to_max(user_id)


async def revive_after_mute(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    user_id = data.get("user_id")
    if not chat_id or not user_id:
        return
    try:
        hp_now, hp_max = await run_unmute_flow(context, chat_id, user_id)
        await context.bot.send_message(
            chat_id,
            f"🔊 /unmute otomatis dijalankan untuk {user_tag(user_id)}. HP dipulihkan {hp_now}/{hp_max}.",
        )
    except Exception:
        pass


async def handle_death_background(chat_id: int, target_id: int, context: ContextTypes.DEFAULT_TYPE, cause: str):
    tag = user_tag(target_id)
    try:
        hp_now, cooldown_sec = activate_death_cooldown(target_id)
        await context.bot.send_message(
            chat_id,
            f"☠️ User {tag} telah mati. Penyebab: {cause}.\n"
            f"❤️ HP dipulihkan ke {hp_now}. Cooldown combat {cooldown_sec} detik aktif.",
        )
    except Exception:
        pass


async def cmd_oinv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("Gunakan: /oinv <id/@username>")
        return
    uid = resolve_user_by_ref(context.args[0])
    target = get_user(uid) if uid else None
    if not target:
        await update.message.reply_text("User tidak ditemukan.")
        return
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute("SELECT item_code, qty FROM inventory WHERE user_id=? AND qty>0 ORDER BY item_code", (uid,)).fetchall()
    inv_lines = ["- Kosong"] if not rows else [f"- {item_name(code)} x{qty} (`{code}`)" for code, qty in rows]
    text = (
        f"🕵️ OINV {target.name} ({target.user_id})\n"
        f"Username: {target.username}\n"
        f"Role: {target.role}\n"
        f"Level: {target.level} ({target.exp}/{exp_needed(target.level)})\n"
        f"HP/Armor: {target.hp}/{target.hp_max} | {target.armor}/{MAX_ARMOR}\n"
        f"Cash: {format_int(target.cash)}\n"
        f"Bank: {format_int(get_bank_cash(target.user_id))}\n"
        f"Token: {format_int(target.token)}\n"
        f"Inventory ({inventory_slots_used(target.user_id)}/{target.inventory_capacity}):\n"
        + "\n".join(inv_lines)
    )
    await update.message.reply_text(text)


async def cmd_credeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Gunakan: /credeem <kode> <reward + reward2 ...>")
        return
    code = context.args[0].strip().upper()
    reward_spec = " ".join(context.args[1:]).strip()
    rewards, err = parse_redeem_reward_spec(reward_spec)
    if err or not rewards:
        await update.message.reply_text(err or "Reward tidak valid.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute("SELECT 1 FROM redeem_codes WHERE code=?", (code,)).fetchone()
        if exists:
            await update.message.reply_text("Kode redeem sudah ada. Pakai kode lain.")
            return
        conn.execute(
            "INSERT INTO redeem_codes (code, reward_spec, created_by, created_at, active) VALUES (?, ?, ?, ?, 1)",
            (code, reward_spec, update.effective_user.id, now_utc().isoformat()),
        )
        conn.commit()
    await update.message.reply_text(f"✅ Redeem code dibuat: {code}\nReward: {reward_spec}")


async def cmd_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if len(context.args) != 1:
        await update.message.reply_text("Gunakan: /redeem <kode>")
        return
    code = context.args[0].strip().upper()
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        row = c.execute("SELECT reward_spec, active FROM redeem_codes WHERE code=?", (code,)).fetchone()
        if not row:
            await update.message.reply_text("Kode redeem tidak ditemukan.")
            return
        reward_spec, active = row
        if not active:
            await update.message.reply_text("Kode redeem sudah tidak aktif.")
            return
        claimed = c.execute("SELECT 1 FROM redeem_claims WHERE code=? AND user_id=?", (code, user.user_id)).fetchone()
        if claimed:
            await update.message.reply_text("Kamu sudah pernah memakai kode ini (1x per user).")
            return
        rewards, err = parse_redeem_reward_spec(reward_spec)
        if err or not rewards:
            await update.message.reply_text("Kode redeem rusak/invalid. Hubungi owner.")
            return
        messages = []
        for reward in rewards:
            if reward[0] == "item":
                _, item_code, qty = reward
                conn.execute(
                    """INSERT INTO inventory (user_id, item_code, qty) VALUES (?, ?, ?)
                       ON CONFLICT(user_id, item_code) DO UPDATE SET qty=qty+excluded.qty""",
                    (user.user_id, item_code, qty),
                )
                messages.append(f"{item_name(item_code)} x{qty}")
            elif reward[0] == "cash":
                amt = reward[1]
                conn.execute("UPDATE users SET cash=cash+? WHERE user_id=?", (amt, user.user_id))
                messages.append(f"Cash {format_int(amt)}")
            elif reward[0] == "token":
                amt = reward[1]
                conn.execute("UPDATE users SET token=token+? WHERE user_id=?", (amt, user.user_id))
                messages.append(f"Token {amt}")
            elif reward[0] == "exp":
                amt = reward[1]
                lvl, _ = add_exp(user.user_id, amt)
                messages.append(f"EXP {amt} (Lv sekarang {lvl})")
        c.execute(
            "INSERT INTO redeem_claims (code, user_id, claimed_at) VALUES (?, ?, ?)",
            (code, user.user_id, now_utc().isoformat()),
        )
        conn.commit()
    await update.message.reply_text(f"🎉 Redeem berhasil ({code})\nHadiah: " + ", ".join(messages))


async def cmd_addcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        await update.message.reply_text("/addcoin <id_user> <jumlah>")
        return
    uid, amt = int(context.args[0]), int(context.args[1])
    if not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    add_cash(uid, amt)
    await update.message.reply_text("OK")


async def cmd_addtoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 2 or not context.args[1].isdigit():
        await update.message.reply_text("/addtoken <id/@username> <jumlah>")
        return
    uid = resolve_user_by_ref(context.args[0])
    amt = int(context.args[1])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    if amt <= 0:
        await update.message.reply_text("Jumlah token harus lebih dari 0.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET token=token+? WHERE user_id=?", (amt, uid))
        conn.commit()
    await update.message.reply_text(f"Token ditambahkan: +{amt} ke {uid}")


async def cmd_auditbuy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("/auditbuy <id/@username>")
        return
    uid = resolve_user_by_ref(context.args[0])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT item_code, currency_type, amount, before_balance, after_balance, status, created_at
            FROM shop_transactions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 10
            """,
            (uid,),
        ).fetchall()
    if not rows:
        await update.message.reply_text("Belum ada transaksi shop untuk user ini.")
        return
    lines = [f"🧾 10 transaksi terakhir user {uid}:"]
    for code, currency, amount, before, after, status, created_at in rows:
        ts = datetime.fromisoformat(created_at).astimezone(WIB).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(
            f"- {ts} | {code} | {currency} {format_int(amount)} | {format_int(before)} -> {format_int(after)} | {status}"
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_heal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    user = ensure_user(update.effective_user)
    target_id = parse_target(update, context.args) or user.user_id
    target = get_user(target_id)
    if not target:
        await update.message.reply_text("Target tidak valid.")
        return
    hp_max = target.hp_max
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET hp=? WHERE user_id=?", (hp_max, target_id))
        conn.commit()
    await update.message.reply_text(f"❤️ {user_tag(target_id)} di-heal ke {hp_max}/{hp_max}.")


async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 2:
        await update.message.reply_text("/premiumuser <id/@username> <durasi: 1w|1m|3m|6m|12m|1y>")
        return
    uid = resolve_user_by_ref(context.args[0])
    dur = parse_premium_duration(context.args[1])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    if not dur:
        await update.message.reply_text("Durasi tidak valid. Gunakan: 1w, 1m, 3m, 6m, 12m, atau 1y.")
        return
    now = now_utc()
    until = now + dur
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET premium=1, premium_until=? WHERE user_id=?", (until.isoformat(), uid))
        conn.commit()
    await update.message.reply_text(f"Premium aktif sampai {until.astimezone(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')}")


async def cmd_setrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    actor_id = update.effective_user.id
    actor_is_owner = is_owner(actor_id)
    actor_is_premium = is_premium_active(actor_id)

    if actor_is_owner:
        if len(context.args) < 2:
            await update.message.reply_text("/setrole <id/@username> <role>")
            return
        uid = resolve_user_by_ref(context.args[0]); role = " ".join(context.args[1:])
        if not uid or not get_user(uid):
            await update.message.reply_text("User tidak ditemukan")
            return
    else:
        if not actor_is_premium:
            await update.message.reply_text("Khusus owner atau user premium (untuk diri sendiri).")
            return
        if not context.args:
            await update.message.reply_text("/setrole <role_baru> (premium hanya untuk diri sendiri)")
            return
        uid = actor_id
        role = " ".join(context.args)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET role=?, role_locked=1 WHERE user_id=?", (role, uid)); conn.commit()
    if actor_is_owner:
        await update.message.reply_text("Role diperbarui")
    else:
        await update.message.reply_text("Role kamu diperbarui (mode premium).")


async def cmd_clearrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("/clearrole <id/@username>")
        return
    uid = resolve_user_by_ref(context.args[0])
    target = get_user(uid) if uid else None
    if not uid or not target:
        await update.message.reply_text("User tidak ditemukan")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET role=?, role_locked=0 WHERE user_id=?", (role_for_level(target.level), uid)); conn.commit()
    await update.message.reply_text("Role custom dihapus (kembali ke role level)")


async def cmd_setlevel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 2 or not context.args[1].isdigit():
        await update.message.reply_text("/setlevel <id/@username> <level>")
        return
    uid = resolve_user_by_ref(context.args[0]); level = max(1, int(context.args[1]))
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    with sqlite3.connect(DB_PATH) as conn:
        current_role, role_locked = conn.execute("SELECT role, role_locked FROM users WHERE user_id=?", (uid,)).fetchone()
        new_role = current_role if role_locked else role_for_level(level)
        conn.execute("UPDATE users SET level=?, exp=0, role=? WHERE user_id=?", (level, new_role, uid)); conn.commit()
    await update.message.reply_text("Level diatur")


async def cmd_defaultlevel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("/defaultlevel <id/@username>")
        return
    uid = resolve_user_by_ref(context.args[0])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    with sqlite3.connect(DB_PATH) as conn:
        current_role, role_locked = conn.execute("SELECT role, role_locked FROM users WHERE user_id=?", (uid,)).fetchone()
        new_role = current_role if role_locked else role_for_level(1)
        conn.execute("UPDATE users SET level=1, exp=0, role=? WHERE user_id=?", (new_role, uid)); conn.commit()
    await update.message.reply_text("Level default")


async def cmd_addexp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 2 or not context.args[1].isdigit():
        await update.message.reply_text("/addexp <id/@username> <jumlah_exp>")
        return
    uid = resolve_user_by_ref(context.args[0]); amt = int(context.args[1])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    lvl, _ = add_exp(uid, amt)
    target = get_user(uid)
    if not target:
        await update.message.reply_text(f"EXP ditambahkan. Level sekarang: {lvl}")
        return
    await update.message.reply_text(
        f"EXP ditambahkan. Level sekarang: {lvl}. EXP: {target.exp}/{exp_needed(target.level)}"
    )


async def cmd_additem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    args = list(context.args)
    target_id = parse_target(update, args)
    if update.message.reply_to_message:
        args = list(context.args)
    else:
        if target_id is None:
            await update.message.reply_text("Gunakan: /additem <id/@username> <nama/kode_item> [qty] atau reply user lalu /additem <nama/kode_item> [qty]")
            return
        args = args[1:]
    if not args:
        await update.message.reply_text("Masukkan nama/kode item.")
        return
    qty = 1
    if args and args[-1].isdigit():
        qty = max(1, int(args[-1]))
        args = args[:-1]
    item_query = " ".join(args).strip()
    if not item_query:
        await update.message.reply_text("Masukkan nama/kode item.")
        return
    item_code = resolve_item_code(item_query)
    if not item_code:
        await update.message.reply_text("Item tidak ditemukan.")
        return
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target user tidak valid.")
        return
    add_item(target_id, item_code, qty)
    await update.message.reply_text(f"✅ Item diberikan: {item_name(item_code)} x{qty} ke {user_tag(target_id)}.")


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in {"group", "supergroup"}:
        await update.message.reply_text("/mute hanya bisa digunakan di grup.")
        return
    if not await require_owner(update):
        return
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Gunakan: /mute <id/@username> [durasi_menit] atau reply command.")
        return
    if target_id == update.effective_user.id:
        await update.message.reply_text("Tidak bisa mute diri sendiri.")
        return
    minutes = 3
    if context.args:
        minute_arg = context.args[-1]
        if minute_arg.isdigit():
            minutes = max(1, min(1440, int(minute_arg)))
    try:
        until = now_utc() + timedelta(minutes=minutes)
        perms = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(update.effective_chat.id, target_id, permissions=perms, until_date=until)
        await update.message.reply_text(f"🔇 User {user_tag(target_id)} dimute selama {minutes} menit.")
    except Exception:
        await update.message.reply_text("Gagal mute user. Pastikan bot admin dan punya izin restrict member.")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in {"group", "supergroup"}:
        await update.message.reply_text("/unmute hanya bisa digunakan di grup.")
        return
    if not await is_owner_or_admin(update, context):
        await update.message.reply_text("Khusus owner/admin grup.")
        return
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Gunakan: /unmute <id/@username> atau reply command.")
        return
    try:
        hp_now, hp_max = await run_unmute_flow(context, update.effective_chat.id, target_id)
        await update.message.reply_text(f"🔊 User {user_tag(target_id)} telah di-unmute. HP dipulihkan {hp_now}/{hp_max}.")
    except Exception:
        await update.message.reply_text("Gagal unmute user. Pastikan bot admin dan punya izin restrict member.")


async def cmd_sniper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    user = ensure_user(update.effective_user)
    if get_item_qty(user.user_id, "sniper_owner") > 0:
        await update.message.reply_text("🎯 Sniper sudah aktif permanen di inventory owner.")
        return
    add_item(user.user_id, "sniper_owner", 1)
    await update.message.reply_text("🎯 Sniper owner ditambahkan permanen ke inventory. Gunakan /aim.")


async def cmd_aim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in {"group", "supergroup"}:
        await update.message.reply_text("/aim hanya bisa digunakan di grup.")
        return
    if not await require_owner(update):
        return
    user = ensure_user(update.effective_user)
    if not await ensure_can_attack(update, user.user_id):
        return
    if get_item_qty(user.user_id, "sniper_owner") <= 0:
        await update.message.reply_text("Kamu belum punya sniper. Gunakan /sniper dulu.")
        return
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target tidak valid.")
        return
    if not await ensure_target_attackable(update, target_id):
        return
    if not update.message.reply_to_message and not in_same_group(update.effective_chat.id, target_id):
        await update.message.reply_text("Target harus berada di grup yang sama.")
        return
    if target_id == user.user_id:
        await update.message.reply_text("Tidak bisa /aim diri sendiri.")
        return
    hp, armor, hp_dmg = apply_damage(target_id, 999)
    target_tag = user_tag(target_id)
    await update.message.reply_text(
        f"( -_•)ᡕᠵデᡁ᠊╾━💥 Target Lock! ({target_tag})\nDamage 999 (HP kena {hp_dmg}).\nSisa target: HP {hp}, Armor {armor}"
    )
    await post_damage_effects(update, context, target_id, hp, "Ditembak /aim (Sniper)")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN belum diset")
    init_db()
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.COMMAND, guard_user_state), group=-1)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["p", "profile"], cmd_profile))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("inv", cmd_inv))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler(["secretshop", "ss"], cmd_secretshop))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("open", cmd_open))
    app.add_handler(CallbackQueryHandler(cb_buy, pattern=r"^buy:"))
    app.add_handler(CallbackQueryHandler(cb_shop_page, pattern=r"^shop:"))
    app.add_handler(CommandHandler(["transfer", "tf"], cmd_transfer))
    app.add_handler(CommandHandler("bank", cmd_bank))
    app.add_handler(CommandHandler(["deposit", "dp"], cmd_deposit))
    app.add_handler(CommandHandler(["withdraw", "wd"], cmd_withdraw))
    app.add_handler(CommandHandler("ramal", cmd_ramal))
    app.add_handler(CommandHandler("pot", cmd_use_pot))
    app.add_handler(CommandHandler("potbig", cmd_use_big_pot))
    app.add_handler(CommandHandler("lp", cmd_use_lucky))
    app.add_handler(CommandHandler("lpm", cmd_use_lucky_med))
    app.add_handler(CommandHandler("dor", cmd_dor))
    app.add_handler(CommandHandler("bom", cmd_bom))
    app.add_handler(CommandHandler("piw", cmd_piw))
    app.add_handler(CommandHandler("dhuar", cmd_dhuar))
    app.add_handler(CommandHandler("aim", cmd_aim))
    app.add_handler(CommandHandler("kp", cmd_kp))
    app.add_handler(CommandHandler("semak", cmd_semak))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("weekly", cmd_weekly))
    app.add_handler(CommandHandler("cd", cmd_cd))
    app.add_handler(CommandHandler("lb", cmd_lb))
    app.add_handler(CommandHandler("lbglobal", cmd_lbglobal))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("redeem", cmd_redeem))
    app.add_handler(CommandHandler("help", cmd_help))

    app.add_handler(CommandHandler(["addcoin", "ac"], cmd_addcoin))
    app.add_handler(CommandHandler(["addtoken", "at"], cmd_addtoken))
    app.add_handler(CommandHandler("auditbuy", cmd_auditbuy))
    app.add_handler(CommandHandler("heal", cmd_heal))
    app.add_handler(CommandHandler(["premiumuser", "pu"], cmd_premium))
    app.add_handler(CommandHandler(["setrole", "sr"], cmd_setrole))
    app.add_handler(CommandHandler(["clearrole", "cr"], cmd_clearrole))
    app.add_handler(CommandHandler(["setlevel", "sl"], cmd_setlevel))
    app.add_handler(CommandHandler(["defaultlevel", "dl"], cmd_defaultlevel))
    app.add_handler(CommandHandler(["addexp", "ae"], cmd_addexp))
    app.add_handler(CommandHandler(["additem", "ai"], cmd_additem))
    app.add_handler(CommandHandler("oinv", cmd_oinv))
    app.add_handler(CommandHandler("credeem", cmd_credeem))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("sniper", cmd_sniper))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, passive_exp))

    logger.info("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
