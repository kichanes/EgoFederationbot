const mongoose = require('mongoose');

const ExpCooldownSchema = new mongoose.Schema(
  {
    _id: { type: Number, required: true }, // user_id
    last_gain: { type: Date, default: null },
  },
  { collection: 'exp_cooldown', versionKey: false }
);

module.exports = mongoose.model('ExpCooldown', ExpCooldownSchema);
