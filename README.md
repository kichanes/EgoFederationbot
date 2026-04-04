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
- `/secretshop` atau `/ss`
- `/buy <kode_item/nama_item>`
- `/open`
- `/pot`
- `/potbig`
- `/lp`
- `/lpm`
- `/ramal <id/@username>`
- `/dor <id/@username>` atau reply lalu `/dor`
- `/bom <id/@username>`
- `/piw <id/@username>`
- `/dhuar`
- `/kp <id/@username>` atau reply lalu `/kp`
- `/semak <id/@username>` atau reply lalu `/semak`
- `/transfer <id_tujuan> <jumlah>`
- `/tf <id_tujuan> <jumlah>`
- `/bank`
- `/deposit <jumlah>` atau `/dp <jumlah>`
- `/withdraw <jumlah>` atau `/wd <jumlah>`
- `/daily`
- `/weekly`
- `/cd`
- `/lb`
- `/lbglobal`
- `/lb 100` atau `/lbglobal 100` (dikirim via DM)
- `/info <nama item|command>`
- `/redeem <kode>`
- `/help`

## Command Owner (hanya dokumentasi README)

- `/addcoin` atau `/ac <id_user> <jumlah>`
- `/addtoken` atau `/at <id/@username> <jumlah>`
- `/heal <id/@username>` atau reply command (owner only)
- `/premiumuser` atau `/pu <id/@username> <durasi>`
  - durasi: `1w`, `1m`, `3m`, `6m`, `12m`, atau `1y`
- `/setrole` atau `/sr <id/@username> <role>`
- `/clearrole` atau `/cr <id/@username>`
- `/setlevel` atau `/sl <id/@username> <level>`
- `/defaultlevel` atau `/dl <id/@username>`
- `/addexp` atau `/ae <id/@username> <jumlah_exp>`
- `/additem` atau `/ai <id/@username> <nama/kode_item> [qty]`
  - bisa juga reply user lalu `/additem <nama/kode_item> [qty]`
- `/oinv <id/@username>` (cek profile ringkas + inventory + bank user target)
- `/credeem <kode> <reward + reward2 + ...>`
- `/mute <id/@username> [durasi_menit]` atau reply command (default 3 menit)
- `/unmute <id/@username>` atau reply command
- `/sniper` (memberikan sniper permanen ke owner)
- `/aim <id/@username>` atau reply command (owner only)

## Catatan Fitur

- Profile: nama, username, id, cash, level, role, register date, time WIB.
- User baru langsung dapat cash awal `5000`.
- EXP grup otomatis: 1 chat = random 5-15 EXP, cooldown 5 menit.
- Inventory default 5 slot + upgrade tas one-time per jenis.
- HP/Armor + alert otomatis saat HP < 20%.
- Saat user mati di grup: user dimute 3 menit, lalu bot otomatis jalankan alur unmute (setara `/unmute`) dan memulihkan HP ke max.
- Shop menampilkan list sederhana (nama item + harga) dengan bubble:
  - 4 slot item per page
  - 1 slot bubble `Next` untuk pindah ke page berikutnya.
- Secret shop terpisah dari shop biasa.
- Shop biasa punya item tambahan: 🎁 Random Chest, 💖 Potion Merah Besar, ⚗️ Luck Potion Med, 🔮 Ramal, ⭐ Premium 1W (`premium_1w`, harga 50.000 cash).
- Secret shop terbuka saat level >= 5.
- `/help` dan `/ss` diarahkan ke chat pribadi bot.
- `/bank` diarahkan ke chat pribadi bot.
- Item secret shop dibeli menggunakan token.
- Transfer antar user dikenakan pajak 10%.
- Tambahan secret shop: Peti Rahasia, Bom, AWM, Nuklir, Anti Radiasi, Penjinak Bom, Armor Plus.
- Daily reward: +150 cash +50 exp (premium double).
- Weekly reward: +500 cash +250 exp +1 token +1 chest random (premium double reward/token).
- Premium privilege: double daily/weekly reward, diskon shop 30%.
- Profile menampilkan tombol CTA `Buy Premium`, `Buy Token`, `Buy Cash` ke `https://t.me/Noturkichan`.
- Lucky Potion (`/lp`) aktif 60 menit dan meningkatkan peluang chest tier bagus saat claim weekly.
- Daftar shop diambil dari tabel `shop_catalog` (bukan hardcoded output saja).
- Armor dibeli via `/buy armor_item` dan otomatis terpakai, maksimum armor tetap 100/100.
- Redeem system:
  - Owner bisa buat kode via `/credeem`.
  - User klaim via `/redeem <kode>`.
  - 1 kode hanya bisa dipakai 1x per user.
  - Reward redeem bisa campuran (contoh: `Token + random chest + Cash + Exp + kunci rahasia + peti rahasia`) termasuk dukungan alias item.

## Troubleshooting

### Chat bot "hilang" setelah 15 detik

Jika pesan bot terlihat hilang otomatis setelah 15 detik, biasanya penyebabnya adalah fitur **Auto-Delete Messages** di Telegram (level chat/grup), bukan karena logic bot.

Langkah cek:

1. Buka profil chat/grup tempat bot dipakai.
2. Masuk ke pengaturan **Auto-Delete Messages**.
3. Ubah timer dari **15 seconds** ke **Off** (atau durasi lain sesuai kebutuhan).

Catatan:

- Bot ini tidak menghapus pesan user/bot secara otomatis dalam kode utama.
- Jika fitur auto-delete aktif di chat, semua pesan (termasuk balasan bot) bisa ikut terhapus.

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
