const mongoose = require('mongoose');

const ChatUserSchema = new mongoose.Schema(
  {
    chat_id: { type: Number, required: true, index: true },
    user_id: { type: Number, required: true },
  },
  { collection: 'chat_users', versionKey: false }
);

ChatUserSchema.index({ chat_id: 1, user_id: 1 }, { unique: true });

module.exports = mongoose.model('ChatUser', ChatUserSchema);
