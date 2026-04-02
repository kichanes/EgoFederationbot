const mongoose = require('mongoose');

const UserSchema = new mongoose.Schema(
  {
    _id: { type: Number, required: true }, // telegram_id
    name: { type: String, required: true },
    username: { type: String, default: '-' },
    cash: { type: Number, default: 1000 },
    level: { type: Number, default: 1 },
    exp: { type: Number, default: 0 },
    role: { type: String, default: '💩 Manusia Antah Berantah' },
    register_at: { type: Date, default: Date.now },
    inventory_capacity: { type: Number, default: 5 },
    hp: { type: Number, default: 200 },
    hp_max: { type: Number, default: 200 },
    armor: { type: Number, default: 0 },
    token: { type: Number, default: 0 },
    premium: { type: Boolean, default: false },
    premium_until: { type: Date, default: null },
    daily_last_claim: { type: Date, default: null },
    weekly_last_claim: { type: Date, default: null },
    luck_buff_until: { type: Date, default: null },
  },
  { collection: 'users', versionKey: false }
);

module.exports = mongoose.model('User', UserSchema);
