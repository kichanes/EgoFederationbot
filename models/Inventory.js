const mongoose = require('mongoose');

const InventorySchema = new mongoose.Schema(
  {
    user_id: { type: Number, required: true, index: true },
    item_code: { type: String, required: true },
    qty: { type: Number, required: true, default: 0 },
  },
  { collection: 'inventory', versionKey: false }
);

InventorySchema.index({ user_id: 1, item_code: 1 }, { unique: true });

module.exports = mongoose.model('Inventory', InventorySchema);
