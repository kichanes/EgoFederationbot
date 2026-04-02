const mongoose = require('mongoose');

const User = require('./User');
const Inventory = require('./Inventory');
const BagUpgrade = require('./BagUpgrade');
const ExpCooldown = require('./ExpCooldown');
const ChatUser = require('./ChatUser');
const ShopCatalog = require('./ShopCatalog');

async function connectMongo(uri, dbName = 'egofederationbot') {
  await mongoose.connect(uri, { dbName });
}

module.exports = {
  mongoose,
  connectMongo,
  User,
  Inventory,
  BagUpgrade,
  ExpCooldown,
  ChatUser,
  ShopCatalog,
};
