require('dotenv').config();
const { pool } = require('./db');

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
