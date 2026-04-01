require('dotenv').config();
const { spawn } = require('child_process');

const child = spawn('python', ['bot.py'], { stdio: 'inherit' });

child.on('exit', (code) => process.exit(code ?? 0));
child.on('error', (err) => {
  console.error('Failed to start bot.py:', err);
  process.exit(1);
});
