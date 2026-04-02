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
```

`npm run migrate` akan membuat tabel `users`, `shop_catalog`, dan mengisi semua item shop ke PostgreSQL (upsert by `code`).

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
- EXP grup otomatis: 1 chat = random 5-15 EXP, cooldown 5 menit.
- Inventory default 5 slot + upgrade tas one-time per jenis.
- HP/Armor + alert otomatis saat HP < 20%.
- Shop menampilkan list sederhana (nama item + harga) dengan bubble:
  - 4 slot item per page
  - 1 slot bubble `Next` untuk pindah ke page berikutnya.
- Secret shop terbuka saat level >= 5.
- Daily reward: +150 cash +50 exp (premium double).
- Weekly reward: +500 cash +250 exp +1 token +1 chest random (premium double reward/token).
- Premium privilege: double daily/weekly reward, diskon shop 30%.
- Lucky Potion (`/lp`) aktif 60 menit dan meningkatkan peluang chest tier bagus saat claim weekly.
- Daftar shop diambil dari tabel `shop_catalog` (bukan hardcoded output saja).
- Armor dibeli via `/buy armor_item` dan otomatis terpakai, maksimum armor tetap 100/100.

## Model Shop (Catalog Item)

Struktur tabel:

| id | name   | type        | price |
|----|--------|-------------|-------|
| 1  | potion | consumable  | 100   |
| 2  | sword  | weapon      | 500   |

Tabel ini dibuat otomatis saat bot start (`init_db`) pada nama tabel `shop_catalog`.

## PostgreSQL Table Design (Setara dengan Bot Saat Ini)

Untuk PostgreSQL, gunakan tabel berikut agar setara dengan data game saat ini:

- `users` (profile, level, exp, cash, hp, armor, premium, cooldown claim, buff).
- `inventory` (item per user + qty).
- `bag_upgrades` (riwayat upgrade tas per user).
- `exp_cooldown` (cooldown EXP chat grup per user).
- `chat_users` (mapping user di grup untuk leaderboard lokal).
- `shop_catalog` (daftar item shop + secret item).

Semua table ini sudah disiapkan pada migrasi PostgreSQL (`npm run migrate`) untuk `users` dan `shop_catalog`, sedangkan table lain bisa ditambahkan mengikuti struktur di `bot.py` jika ingin full pindah runtime ke PostgreSQL.
