require('dotenv').config();
const { pool } = require('./db');

(async () => {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      telegram_id BIGINT PRIMARY KEY,
      full_name TEXT
    );
  `);

  console.log("Migration done");
  await pool.end();
})();
