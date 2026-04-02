require('dotenv').config();
const Database = require('better-sqlite3');
const { MongoClient } = require('mongodb');

const SQLITE_PATH = process.env.DB_PATH || 'bot.db';
const MONGODB_URI = process.env.MONGODB_URI;
const MONGODB_DB = process.env.MONGODB_DB || 'egofederationbot';

if (!MONGODB_URI) {
  console.error('MONGODB_URI is required');
  process.exit(1);
}

function toDateOrNull(v) {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

(async () => {
  const sqlite = new Database(SQLITE_PATH, { readonly: true });
  const client = new MongoClient(MONGODB_URI);

  try {
    await client.connect();
    const db = client.db(MONGODB_DB);

    const usersRows = sqlite.prepare('SELECT * FROM users').all();
    const usersDocs = usersRows.map((r) => ({
      _id: r.user_id,
      name: r.name,
      username: r.username,
      cash: r.cash,
      level: r.level,
      exp: r.exp,
      role: r.role,
      register_at: toDateOrNull(r.register_at),
      inventory_capacity: r.inventory_capacity,
      hp: r.hp,
      hp_max: r.hp_max,
      armor: r.armor,
      token: r.token,
      premium: Boolean(r.premium),
      premium_until: toDateOrNull(r.premium_until),
      daily_last_claim: toDateOrNull(r.daily_last_claim),
      weekly_last_claim: toDateOrNull(r.weekly_last_claim),
      luck_buff_until: toDateOrNull(r.luck_buff_until),
    }));

    const invRows = sqlite.prepare('SELECT * FROM inventory').all();
    const invDocs = invRows.map((r) => ({ user_id: r.user_id, item_code: r.item_code, qty: r.qty }));

    const bagRows = sqlite.prepare('SELECT * FROM bag_upgrades').all();
    const bagDocs = bagRows.map((r) => ({ user_id: r.user_id, item_code: r.item_code }));

    const expRows = sqlite.prepare('SELECT * FROM exp_cooldown').all();
    const expDocs = expRows.map((r) => ({ _id: r.user_id, last_gain: toDateOrNull(r.last_gain) }));

    const chatRows = sqlite.prepare('SELECT * FROM chat_users').all();
    const chatDocs = chatRows.map((r) => ({ chat_id: r.chat_id, user_id: r.user_id }));

    const shopRows = sqlite.prepare('SELECT * FROM shop_catalog').all();
    const shopDocs = shopRows.map((r) => ({
      code: r.code,
      name: r.name,
      type: r.type,
      price: r.price,
      description: r.description,
      is_secret: Boolean(r.is_secret),
    }));

    await db.collection('users').deleteMany({});
    await db.collection('inventory').deleteMany({});
    await db.collection('bag_upgrades').deleteMany({});
    await db.collection('exp_cooldown').deleteMany({});
    await db.collection('chat_users').deleteMany({});
    await db.collection('shop_catalog').deleteMany({});

    if (usersDocs.length) await db.collection('users').insertMany(usersDocs);
    if (invDocs.length) await db.collection('inventory').insertMany(invDocs);
    if (bagDocs.length) await db.collection('bag_upgrades').insertMany(bagDocs);
    if (expDocs.length) await db.collection('exp_cooldown').insertMany(expDocs);
    if (chatDocs.length) await db.collection('chat_users').insertMany(chatDocs);
    if (shopDocs.length) await db.collection('shop_catalog').insertMany(shopDocs);

    await db.collection('inventory').createIndex({ user_id: 1, item_code: 1 }, { unique: true });
    await db.collection('bag_upgrades').createIndex({ user_id: 1, item_code: 1 }, { unique: true });
    await db.collection('chat_users').createIndex({ chat_id: 1, user_id: 1 }, { unique: true });
    await db.collection('shop_catalog').createIndex({ code: 1 }, { unique: true });

    console.log('SQLite -> MongoDB migration done');
    console.log(`users=${usersDocs.length}, inventory=${invDocs.length}, bag_upgrades=${bagDocs.length}, exp_cooldown=${expDocs.length}, chat_users=${chatDocs.length}, shop_catalog=${shopDocs.length}`);
  } catch (err) {
    console.error('Migration error:', err);
    process.exitCode = 1;
  } finally {
    sqlite.close();
    await client.close();
  }
})();
