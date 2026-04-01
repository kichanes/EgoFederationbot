require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.PGSSL === 'true' ? { rejectUnauthorized: false } : false,
});

(async () => {
  try {
    const res = await pool.query('SELECT NOW()');
    console.log('DB CONNECTED:', res.rows[0]);
  } catch (err) {
    console.error('DB ERROR:', err);
  } finally {
    await pool.end();
  }
})();
