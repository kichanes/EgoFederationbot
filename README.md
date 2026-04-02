# Ego Federation Telegram Bot

Bot Telegram RPG ringan dengan fitur profile, EXP otomatis, currency, inventory, combat, shop, claim reward, leaderboard, dan command owner.

## Setup

1. Install dependency:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy env:
   ```bash
   cp .env.example .env
   ```
3. Isi `.env`:
   - `BOT_TOKEN`
   - `OWNER_IDS` (pisahkan koma bila lebih dari 1 owner)
   - `DB_PATH` (opsional)
   - `DATABASE_URL` (opsional, untuk cek koneksi PostgreSQL via Node.js helper)
   - `PGSSL` (opsional, isi `true` jika koneksi PostgreSQL perlu SSL)
   - `MONGODB_URI` (opsional, untuk migrasi SQLite -> MongoDB)
   - `MONGODB_DB` (opsional, default: `egofederationbot`)
4. Jalankan bot:
   ```bash
   python bot.py
   ```

## Cek Koneksi DB (Node.js)

Script helper `db-check.js` sudah ditambahkan untuk test koneksi PostgreSQL:

```bash
npm install
npm start
npm run migrate
npm run migrate:mongo
```

`npm run migrate` akan membuat tabel `users`, `shop_catalog`, dan mengisi semua item shop ke PostgreSQL (upsert by `code`).
`npm run migrate:mongo` akan copy data dari SQLite (`DB_PATH`) ke MongoDB (`MONGODB_URI`/`MONGODB_DB`) untuk collection: `users`, `inventory`, `bag_upgrades`, `exp_cooldown`, `chat_users`, `shop_catalog`.

Isi `.env` minimal dengan:

```env
DATABASE_URL=postgres://user:password@host:5432/dbname
PGSSL=false
```

## Command User

- `/start`
- `/p` atau `/profile`
- `/status`
- `/inv`
- `/shop`
- `/buy <kode_item>`
- `/pot`
- `/armor`
- `/lp`
- `/dor <id/@username>` atau reply lalu `/dor`
- `/kp <id/@username>` atau reply lalu `/kp`
- `/semak <id/@username>` atau reply lalu `/semak`
- `/transfer <id_tujuan> <jumlah>`
- `/tf <id_tujuan> <jumlah>`
- `/daily`
- `/weekly`
- `/cd`
- `/lb`
- `/lbglobal`
- `/lb 100` atau `/lbglobal 100` (dikirim via DM)
- `/help`

## Command Owner (hanya dokumentasi README)

- `/addcoin` atau `/ac <id_user> <jumlah>`
- `/premiumuser` atau `/pu <id/@username> <durasi>`
  - durasi: `1m`, `3m`, `6m`, `12m`, atau `1y`
- `/setrole` atau `/sr <id/@username> <role>`
- `/clearrole` atau `/cr <id/@username>`
- `/setlevel` atau `/sl <id/@username> <level>`
- `/defaultlevel` atau `/dl <id/@username>`
- `/addexp` atau `/ae <id/@username> <jumlah_exp>`

## Catatan Fitur

- Profile: nama, username, id, cash, level, role, register date, time WIB.
- EXP grup otomatis: 5-15 tiap 5 menit (premium double).
- Inventory default 5 slot + upgrade tas one-time per jenis.
- HP/Armor + alert otomatis saat HP < 20%.
- Shop menampilkan list + bubble tombol beli.
- Secret shop terbuka saat level >= 5.
- Daily reward: +150 cash +50 exp (premium double).
- Weekly reward: +500 cash +250 exp +1 token +1 chest random (premium double reward/token).
- Premium privilege: double EXP, double daily/weekly reward, diskon shop 30%.
- Lucky Potion (`/lp`) aktif 60 menit dan meningkatkan peluang chest tier bagus saat claim weekly.
- Daftar shop diambil dari tabel `shop_catalog` (bukan hardcoded output saja).

## Model Shop (Catalog Item)

Struktur tabel:

| id | name   | type        | price |
|----|--------|-------------|-------|
| 1  | potion | consumable  | 100   |
| 2  | sword  | weapon      | 500   |

Tabel ini dibuat otomatis saat bot start (`init_db`) pada nama tabel `shop_catalog`.

## MongoDB Collection Design (Setara dengan Bot Saat Ini)

Berikut struktur collection MongoDB jika kamu ingin memigrasikan semua data dari SQLite:

### 1) `users`

Menyimpan seluruh info user utama: profile, progress, economy, status, dan cooldown.

| Field | Type | Keterangan |
|---|---|---|
| `_id` | `Long` / `String` | Telegram user id (disarankan sama dengan `user_id`) |
| `name` | `String` | Nama user Telegram |
| `username` | `String` | Username Telegram (`@username`) |
| `cash` | `Number` | Uang user |
| `level` | `Number` | Level user |
| `exp` | `Number` | EXP saat ini |
| `role` | `String` | Role user |
| `register_at` | `Date` | Tanggal register |
| `inventory_capacity` | `Number` | Kapasitas inventory |
| `hp` | `Number` | HP saat ini |
| `hp_max` | `Number` | HP maksimum |
| `armor` | `Number` | Armor saat ini |
| `token` | `Number` | Token user |
| `premium` | `Boolean` | Flag premium (legacy) |
| `premium_until` | `Date` / `null` | Batas waktu premium |
| `daily_last_claim` | `Date` / `null` | Terakhir claim daily |
| `weekly_last_claim` | `Date` / `null` | Terakhir claim weekly |
| `luck_buff_until` | `Date` / `null` | Durasi buff Lucky Potion |

Contoh dokumen:

```json
{
  "_id": 5258274019,
  "name": "Kichan ego",
  "username": "@NoturKichan",
  "cash": 1000,
  "level": 1,
  "exp": 7,
  "role": "🎖 Elite Nasional",
  "register_at": "2026-03-31T12:21:46.000Z",
  "inventory_capacity": 5,
  "hp": 200,
  "hp_max": 200,
  "armor": 100,
  "token": 0,
  "premium": false,
  "premium_until": null,
  "daily_last_claim": null,
  "weekly_last_claim": null,
  "luck_buff_until": null
}
```

### 2) `inventory`

| Field | Type | Keterangan |
|---|---|---|
| `_id` | `ObjectId` | ID dokumen |
| `user_id` | `Long` / `String` | Relasi ke user |
| `item_code` | `String` | Kode item (`banana`, `pistol_3`, dst.) |
| `qty` | `Number` | Jumlah item |

Index disarankan: `{ user_id: 1, item_code: 1 }` unik.

### 3) `bag_upgrades`

| Field | Type | Keterangan |
|---|---|---|
| `_id` | `ObjectId` | ID dokumen |
| `user_id` | `Long` / `String` | Relasi ke user |
| `item_code` | `String` | Kode upgrade tas yang sudah dibeli |

Index disarankan: `{ user_id: 1, item_code: 1 }` unik.

### 4) `exp_cooldown`

| Field | Type | Keterangan |
|---|---|---|
| `_id` | `Long` / `String` | User id (biar 1 user = 1 dokumen) |
| `last_gain` | `Date` | Waktu terakhir dapat EXP pasif |

### 5) `chat_users`

| Field | Type | Keterangan |
|---|---|---|
| `_id` | `ObjectId` | ID dokumen |
| `chat_id` | `Long` / `String` | ID grup/chat |
| `user_id` | `Long` / `String` | User yang pernah tercatat di chat |

Index disarankan: `{ chat_id: 1, user_id: 1 }` unik.

### 6) `shop_catalog`

| Field | Type | Keterangan |
|---|---|---|
| `_id` | `ObjectId` | ID dokumen |
| `code` | `String` | Kode item |
| `name` | `String` | Nama item |
| `type` | `String` | `consumable` / `upgrade` |
| `price` | `Number` | Harga |
| `description` | `String` | Deskripsi item |
| `is_secret` | `Boolean` | Item secret shop atau bukan |

Index disarankan: `{ code: 1 }` unik.

### Mongoose Schema Siap Pakai

File schema sudah disediakan di folder `models/`:

- `models/User.js`
- `models/Inventory.js`
- `models/BagUpgrade.js`
- `models/ExpCooldown.js`
- `models/ChatUser.js`
- `models/ShopCatalog.js`
- `models/index.js` (helper koneksi + export semua model)

Contoh pakai:

```js
const { connectMongo, User, ShopCatalog } = require('./models');

await connectMongo(process.env.MONGODB_URI, process.env.MONGODB_DB);
const me = await User.findById(5258274019);
const items = await ShopCatalog.find({ is_secret: false });
```
