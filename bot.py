import logging
import os
import random
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
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
INITIAL_CASH = 1000
EXP_MIN = 5
EXP_MAX = 15
EXP_COOLDOWN_SECONDS = 300
MAX_HP = 200
DAILY_COOLDOWN = 24 * 3600
WEEKLY_COOLDOWN = 7 * 24 * 3600
KP_DAMAGE_RANGE = (5, 10)
SEMAK_DAMAGE_RANGE = (7, 12)

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
    "sandal": {"name": "🩴 Sandal Emak", "price": 2500, "type": "consumable", "desc": "Damage 7-12", "max_stack": 999},
    "luck_potion": {"name": "🧪 Lucky Potion", "price": 5000, "type": "consumable", "desc": "Buff luck +5% (pakai /lp)", "max_stack": 99},
    "shield_3": {"name": "🛡️ Perisai Kelas III", "price": 1000, "type": "consumable", "desc": "Stack max 3, auto saat kena /dor Kelas III", "max_stack": 3},
    "pistol_3": {"name": "🔫 Pistol Kelas III", "price": 5000, "type": "consumable", "desc": "Untuk /dor", "max_stack": 99},
    "potion_red": {"name": "❤️ Potion Merah", "price": 100, "type": "consumable", "desc": "Tambah HP 10% (pakai /pot)", "max_stack": 99},
    "armor_item": {"name": "🦺 Armor", "price": 5000, "type": "consumable", "desc": "Tambah armor +100 (pakai /armor)", "max_stack": 99},
    "bag_small": {"name": "👛 Tas Kecil", "price": 5000, "type": "upgrade", "desc": "+3 slot", "capacity": 3},
    "bag_tenun": {"name": "🛍 Tas Tenun", "price": 10000, "type": "upgrade", "desc": "+5 slot", "capacity": 5},
    "bag_samping": {"name": "💼 Tas Samping", "price": 15000, "type": "upgrade", "desc": "+7 slot", "capacity": 7},
    "bag_sekolah": {"name": "🎒 Tas Sekolah", "price": 20000, "type": "upgrade", "desc": "+10 slot", "capacity": 10},
    "bag_gunung": {"name": "🧳 Koper", "price": 25000, "type": "upgrade", "desc": "+15 slot", "capacity": 15},
}

SECRET_ITEMS = {
    "chest_key": {"name": "🗝️ Kunci Rahasia", "price": 3000, "type": "consumable", "desc": "Kunci untuk event rahasia", "max_stack": 99}
}

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
    "common": {"cash": 250, "token": (0, 2), "items": []},
    "rare": {"cash": 350, "token": (1, 2), "items": ["banana"]},
    "epic": {"cash": 500, "token": (1, 3), "items": ["banana", "sandal"]},
    "legend": {"cash": 750, "token": (2, 3), "items": ["banana", "sandal", "luck_potion"]},
    "myth": {"cash": 1500, "token": (2, 5), "items": ["banana", "sandal", "luck_potion", "armor_item", "pistol_3"]},
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


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def role_for_level(level: int) -> str:
    for start, end, role in ROLE_RANGES:
        if start <= level <= end:
            return role
    return "🎖 Elite Nasional"


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
                daily_last_claim TEXT,
                weekly_last_claim TEXT,
                luck_buff_until TEXT
            )
            """
        )
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
        c.execute("UPDATE users SET level=?, exp=?, role=? WHERE user_id=?", (level, exp, role_for_level(level), user_id))
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


def roll_chest_tier(luck_active: bool) -> str:
    rates = list(CHEST_RATES)
    if luck_active:
        rates = [
            (tier, weight * 1.05 if tier in {"rare", "epic", "legend", "myth"} else weight)
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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if update.effective_chat.type != "private":
        update_chat_member(update.effective_chat.id, user.user_id)
    await update.message.reply_text("Halo! Gunakan /help untuk melihat command user.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Command User\n"
        "/start\n/p atau /profile\n/status\n/inv\n/shop\n/buy <kode_item>\n/pot\n/armor\n/lp\n"
        "/dor <id/@username> atau reply lalu /dor\n/kp <id/@username> atau reply lalu /kp\n/semak <id/@username> atau reply lalu /semak\n"
        "/transfer <id_tujuan> <jumlah>\n/tf <id_tujuan> <jumlah>\n/daily\n/weekly\n/cd\n/lb\n/lbglobal\n/help"
    )
    await update.message.reply_text(text)


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if update.effective_chat.type != "private":
        update_chat_member(update.effective_chat.id, user.user_id)
    dt = datetime.fromisoformat(user.register_at).astimezone(WIB)
    now = datetime.now(WIB)
    msg = (
        f"Nama : {user.name}\n"
        f"Username : {user.username}\n"
        f"ID : {user.user_id}\n"
        f"Cash : {format_int(user.cash)}\n"
        f"Level : {user.level} ({user.exp}/{exp_needed(user.level)})\n"
        f"Role : {user.role or '-'}\n"
        f"Register Date : {dt.strftime('%Y-%m-%d')}\n"
        f"Time : {now.strftime('%H:%M:%S WIB')}"
    )
    await update.message.reply_text(msg)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    buff_list = []
    debuff = "Tidak ada"
    if user.premium:
        buff_list.append("Premium: bonus EXP & reward")
    luck_until = get_luck_buff_until(user.user_id)
    if luck_until and now_utc() < luck_until:
        remaining = str(luck_until - now_utc()).split(".")[0]
        buff_list.append(f"Lucky Potion +5% chest luck ({remaining})")
    if user.hp < int(user.hp_max * 0.2):
        debuff = "⚠️ HP kritis (<20%)"
    buff = ", ".join(buff_list) if buff_list else "Tidak ada"
    text = f"HP : {user.hp}/{user.hp_max}\nArmor : {user.armor}\nBuff : {buff}\nDebuff : {debuff}"
    await update.message.reply_text(text)
    if user.hp < int(user.hp_max * 0.2):
        await update.message.reply_text("🚨 ALERT: HP kamu di bawah 20%, segera gunakan /pot atau /armor.")


async def cmd_inv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute("SELECT item_code, qty FROM inventory WHERE user_id=? AND qty>0 ORDER BY item_code", (user.user_id,)).fetchall()
    lines = [f"🎒 Inventory ({inventory_slots_used(user.user_id)}/{user.inventory_capacity} slot):"]
    if not rows:
        lines.append("- Kosong")
    else:
        for code, qty in rows:
            name = SHOP_ITEMS.get(code, SECRET_ITEMS.get(code, {"name": code}))['name']
            lines.append(f"- {name} x{qty} (`{code}`)")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


def discount_price(user: UserData, price: int) -> int:
    return int(price * 0.7) if user.premium else price


async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    lines = ["🛒 Shop:"]
    buttons = []
    with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
        rows = c.execute(
            """SELECT code, name, type, price, description, is_secret
               FROM shop_catalog
               ORDER BY is_secret ASC, id ASC"""
        ).fetchall()
    secret_printed = False
    for code, name, _type, price_raw, desc, is_secret in rows:
        if is_secret and user.level < 5:
            continue
        if is_secret and not secret_printed:
            lines.append("\n🔐 Secret Shop terbuka:")
            secret_printed = True
        price = discount_price(user, price_raw)
        lines.append(f"- {name} ({desc}) | Harga {format_int(price)} | /buy {code}")
        buttons.append([InlineKeyboardButton(f"Beli {name} - {format_int(price)}", callback_data=f"buy:{code}")])
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


async def buy_item(user: UserData, code: str) -> str:
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

    price = discount_price(user, base_price)
    if user.cash < price:
        return "Cash kamu tidak cukup."

    if item_type == "upgrade":
        with sqlite3.connect(DB_PATH) as conn, closing(conn.cursor()) as c:
            exists = c.execute("SELECT 1 FROM bag_upgrades WHERE user_id=? AND item_code=?", (user.user_id, code)).fetchone()
            if exists:
                return "Upgrade tas ini sudah pernah dibeli."
            c.execute("INSERT INTO bag_upgrades (user_id, item_code) VALUES (?, ?)", (user.user_id, code))
            c.execute("UPDATE users SET cash=cash-?, inventory_capacity=inventory_capacity+? WHERE user_id=?", (price, item['capacity'], user.user_id))
            conn.commit()
        return f"Berhasil beli {name}. Kapasitas inventory +{item['capacity']}."

    if inventory_slots_used(user.user_id) >= user.inventory_capacity and get_item_qty(user.user_id, code) == 0:
        return "Inventory penuh. Upgrade tas dulu di shop."

    max_stack = item.get("max_stack", 999)
    current = get_item_qty(user.user_id, code)
    if current >= max_stack:
        return f"Stack {name} sudah maksimum ({max_stack})."

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET cash=cash-? WHERE user_id=?", (price, user.user_id))
        conn.execute(
            "INSERT INTO inventory (user_id, item_code, qty) VALUES (?, ?, 1) ON CONFLICT(user_id, item_code) DO UPDATE SET qty=qty+1",
            (user.user_id, code),
        )
        conn.commit()
    return f"Berhasil beli {name}."


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("Gunakan: /buy <kode_item>")
        return
    res = await buy_item(user, context.args[0].lower())
    await update.message.reply_text(res)


async def cb_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = ensure_user(query.from_user)
    _, code = query.data.split(":", 1)
    res = await buy_item(user, code)
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET cash=cash-? WHERE user_id=?", (amount, sender.user_id))
        conn.execute("UPDATE users SET cash=cash+? WHERE user_id=?", (amount, target_id))
        conn.commit()
    await update.message.reply_text(f"Transfer berhasil: {format_int(amount)} ke {target_id}")


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
        conn.execute("UPDATE users SET luck_buff_until=? WHERE user_id=?", (until.isoformat(), user.user_id))
        conn.commit()
    await update.message.reply_text("Buff luck +5% aktif selama 60 menit.")


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


async def attack_throw(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str, min_dmg: int, max_dmg: int, label: str):
    user = ensure_user(update.effective_user)
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target tidak valid.")
        return
    if target_id == user.user_id:
        await update.message.reply_text("Tidak bisa menyerang diri sendiri.")
        return
    if not consume_item(user.user_id, code):
        await update.message.reply_text(f"Kamu tidak punya {label}.")
        return
    dmg = random.randint(min_dmg, max_dmg)
    hp, armor, hp_dmg = apply_damage(target_id, dmg)
    await update.message.reply_text(f"{label} dilempar ke {target_id}! Damage {dmg} (kena HP {hp_dmg}). Status target HP {hp}, Armor {armor}.")


async def cmd_kp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await attack_throw(update, context, "banana", KP_DAMAGE_RANGE[0], KP_DAMAGE_RANGE[1], "🍌 Kulit Pisang")


async def cmd_semak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await attack_throw(update, context, "sandal", SEMAK_DAMAGE_RANGE[0], SEMAK_DAMAGE_RANGE[1], "🩴 Sandal Emak")


async def cmd_dor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user(update.effective_user)
    target_id = parse_target(update, context.args)
    if not target_id or not get_user(target_id):
        await update.message.reply_text("Target tidak valid.")
        return
    if target_id == user.user_id:
        await update.message.reply_text("Tidak bisa /dor diri sendiri.")
        return
    if not consume_item(user.user_id, "pistol_3"):
        await update.message.reply_text("Kamu butuh 🔫 Pistol Kelas III untuk /dor.")
        return

    shielded = consume_item(target_id, "shield_3")
    dmg = random.randint(20, 40)
    if shielded:
        dmg = max(0, dmg - random.randint(10, 20))
    hp, armor, hp_dmg = apply_damage(target_id, dmg)
    note = "Target auto pakai 🛡️ Perisai Kelas III." if shielded else "Target tidak punya perisai."
    await update.message.reply_text(f"🔫 Dor! Damage total {dmg} (HP kena {hp_dmg}). {note}\nSisa target: HP {hp}, Armor {armor}")


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
        multi = 2 if user.premium else 1
        cash = base_cash * multi
        exp = base_exp * multi
        token_add = base_token * multi
        chest_msg = ""
        if typ == "weekly":
            luck_active = has_active_luck(user.user_id)
            chest_tier = roll_chest_tier(luck_active)
            reward = CHEST_REWARDS[chest_tier]
            cash += reward["cash"] * multi
            token_bonus = random.randint(reward["token"][0], reward["token"][1]) * multi
            token_add += token_bonus
            got_items = []
            for code in reward["items"]:
                add_item(user.user_id, code, 1)
                got_items.append(SHOP_ITEMS[code]["name"])
            luck_note = " (Lucky Potion aktif)" if luck_active else ""
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
        gain = random.randint(EXP_MIN, EXP_MAX) * (2 if user.premium else 1)
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


async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("/premiumuser <id/@username>")
        return
    uid = resolve_user_by_ref(context.args[0])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET premium=1 WHERE user_id=?", (uid,))
        conn.commit()
    await update.message.reply_text("Premium aktif")


async def cmd_setrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("/setrole <id/@username> <role>")
        return
    uid = resolve_user_by_ref(context.args[0]); role = " ".join(context.args[1:])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET role=? WHERE user_id=?", (role, uid)); conn.commit()
    await update.message.reply_text("Role diperbarui")


async def cmd_clearrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_owner(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("/clearrole <id/@username>")
        return
    uid = resolve_user_by_ref(context.args[0])
    if not uid or not get_user(uid):
        await update.message.reply_text("User tidak ditemukan")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET role='' WHERE user_id=?", (uid,)); conn.commit()
    await update.message.reply_text("Role dihapus")


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
        conn.execute("UPDATE users SET level=?, exp=0, role=? WHERE user_id=?", (level, role_for_level(level), uid)); conn.commit()
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
        conn.execute("UPDATE users SET level=1, exp=0, role=? WHERE user_id=?", (role_for_level(1), uid)); conn.commit()
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
    await update.message.reply_text(f"EXP ditambahkan. Level sekarang: {lvl}")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN belum diset")
    init_db()
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["p", "profile"], cmd_profile))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("inv", cmd_inv))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CallbackQueryHandler(cb_buy, pattern=r"^buy:"))
    app.add_handler(CommandHandler(["transfer", "tf"], cmd_transfer))
    app.add_handler(CommandHandler("pot", cmd_use_pot))
    app.add_handler(CommandHandler("armor", cmd_use_armor))
    app.add_handler(CommandHandler("lp", cmd_use_lucky))
    app.add_handler(CommandHandler("dor", cmd_dor))
    app.add_handler(CommandHandler("kp", cmd_kp))
    app.add_handler(CommandHandler("semak", cmd_semak))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("weekly", cmd_weekly))
    app.add_handler(CommandHandler("cd", cmd_cd))
    app.add_handler(CommandHandler("lb", cmd_lb))
    app.add_handler(CommandHandler("lbglobal", cmd_lbglobal))
    app.add_handler(CommandHandler("help", cmd_help))

    app.add_handler(CommandHandler(["addcoin", "ac"], cmd_addcoin))
    app.add_handler(CommandHandler(["premiumuser", "pu"], cmd_premium))
    app.add_handler(CommandHandler(["setrole", "sr"], cmd_setrole))
    app.add_handler(CommandHandler(["clearrole", "cr"], cmd_clearrole))
    app.add_handler(CommandHandler(["setlevel", "sl"], cmd_setlevel))
    app.add_handler(CommandHandler(["defaultlevel", "dl"], cmd_defaultlevel))
    app.add_handler(CommandHandler(["addexp", "ae"], cmd_addexp))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, passive_exp))

    logger.info("Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
