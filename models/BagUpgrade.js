const mongoose = require('mongoose');

const BagUpgradeSchema = new mongoose.Schema(
  {
    user_id: { type: Number, required: true, index: true },
    item_code: { type: String, required: true },
  },
  { collection: 'bag_upgrades', versionKey: false }
);

BagUpgradeSchema.index({ user_id: 1, item_code: 1 }, { unique: true });

module.exports = mongoose.model('BagUpgrade', BagUpgradeSchema);
