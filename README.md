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
4. Jalankan bot:
   ```bash
   python bot.py
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
- `/premiumuser` atau `/pu <id/@username>`
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
