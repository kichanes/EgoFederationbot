const mongoose = require('mongoose');

const ShopCatalogSchema = new mongoose.Schema(
  {
    code: { type: String, required: true, unique: true, index: true },
    name: { type: String, required: true },
    type: { type: String, required: true, enum: ['consumable', 'upgrade'] },
    price: { type: Number, required: true },
    description: { type: String, default: '' },
    is_secret: { type: Boolean, default: false },
  },
  { collection: 'shop_catalog', versionKey: false }
);

module.exports = mongoose.model('ShopCatalog', ShopCatalogSchema);
