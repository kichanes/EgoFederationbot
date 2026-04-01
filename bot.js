try {
  require('dotenv').config();
} catch (_) {
  // optional in restricted environments
}
const { spawn } = require('child_process');

if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log('Usage: npm start');
  console.log('Starts Telegram bot by running python bot.py');
  process.exit(0);
}

const child = spawn('python', ['bot.py'], { stdio: 'inherit' });

child.on('exit', (code) => process.exit(code ?? 0));
child.on('error', (err) => {
  console.error('Failed to start bot.py:', err);
  process.exit(1);
});
