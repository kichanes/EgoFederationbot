require('dotenv').config();
const { pool } = require('./db');

(async () => {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      telegram_id BIGINT PRIMARY KEY,
      full_name TEXT
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS shop_catalog (
      id BIGSERIAL PRIMARY KEY,
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      type TEXT NOT NULL,
      price INTEGER NOT NULL,
      description TEXT DEFAULT '',
      is_secret BOOLEAN DEFAULT FALSE
    );
  `);

  await pool.query(`
    INSERT INTO shop_catalog (code, name, type, price, description, is_secret) VALUES
      ('banana', '🍌 Kulit Pisang', 'consumable', 200, 'Damage 5-10', FALSE),
      ('sandal', '🩴 Sandal Emak', 'consumable', 2500, 'Damage 7-12', FALSE),
      ('luck_potion', '🧪 Lucky Potion', 'consumable', 5000, 'Buff luck +5% (pakai /lp)', FALSE),
      ('shield_3', '🛡️ Perisai Kelas III', 'consumable', 1000, 'Stack max 3, auto saat kena /dor Kelas III', FALSE),
      ('pistol_3', '🔫 Pistol Kelas III', 'consumable', 5000, 'Untuk /dor', FALSE),
      ('potion_red', '❤️ Potion Merah', 'consumable', 100, 'Tambah HP 10% (pakai /pot)', FALSE),
      ('armor_item', '🦺 Armor', 'consumable', 5000, 'Tambah armor +100 (pakai /armor)', FALSE),
      ('bag_small', '👛 Tas Kecil', 'upgrade', 5000, '+3 slot', FALSE),
      ('bag_tenun', '🛍 Tas Tenun', 'upgrade', 10000, '+5 slot', FALSE),
      ('bag_samping', '💼 Tas Samping', 'upgrade', 15000, '+7 slot', FALSE),
      ('bag_sekolah', '🎒 Tas Sekolah', 'upgrade', 20000, '+10 slot', FALSE),
      ('bag_gunung', '🧳 Koper', 'upgrade', 25000, '+15 slot', FALSE),
      ('chest_key', '🗝️ Kunci Rahasia', 'consumable', 3000, 'Kunci untuk event rahasia', TRUE)
    ON CONFLICT (code) DO UPDATE SET
      name = EXCLUDED.name,
      type = EXCLUDED.type,
      price = EXCLUDED.price,
      description = EXCLUDED.description,
      is_secret = EXCLUDED.is_secret;
  `);

  console.log("Migration done");
  await pool.end();
})();
