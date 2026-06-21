const express = require('express');
const router = express.Router();
const db = require('../data/db');

router.get('/dialogs', (req, res) => {
  res.json(db.dialogs);
});

router.get('/messages/:dialogId', (req, res) => {
  const dialogId = parseInt(req.params.dialogId);
  const messages = db.messages[dialogId] || [];
  res.json(messages);
});

router.post('/messages', (req, res) => {
  const { dialogId, text } = req.body;
  if (!dialogId || !text) {
    return res.status(400).json({ error: 'dialogId и text обязательны' });
  }

  const newMessage = {
    id: Date.now(),
    from: 'user',
    text: text,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    timestamp: new Date().toISOString()
  };

  if (!db.messages[dialogId]) {
    db.messages[dialogId] = [];
  }
  db.messages[dialogId].push(newMessage);

  const dialog = db.dialogs.find(d => d.id === dialogId);
  if (dialog) {
    dialog.lastMessage = text;
    dialog.time = newMessage.time;
  }

  setTimeout(() => {
    const replies = ['Отлично!', 'Понял, сделаю', 'Спасибо!', 'Ок, жду', 'Хорошо, договорились', '👍', 'Да, давай', 'А когда?'];
    const randomReply = replies[Math.floor(Math.random() * replies.length)];
    const replyMessage = {
      id: Date.now() + 1,
      from: 'partner',
      text: randomReply,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      timestamp: new Date().toISOString()
    };
    db.messages[dialogId].push(replyMessage);
    if (dialog) {
      dialog.lastMessage = randomReply;
      dialog.time = replyMessage.time;
    }
  }, 800 + Math.random() * 1200);

  res.status(201).json(newMessage);
});

router.get('/posts', (req, res) => {
  res.json(db.posts);
});

router.post('/posts', (req, res) => {
  const { text } = req.body;
  if (!text) {
    return res.status(400).json({ error: 'text обязателен' });
  }

  const newPost = {
    id: Date.now(),
    user: 'Стариков Семён',
    avatar: '👤',
    time: 'только что',
    text: text,
    hasImage: false,
    likes: 0,
    comments: 0,
    shares: 0,
    timestamp: new Date().toISOString()
  };

  db.posts.unshift(newPost);
  res.status(201).json(newPost);
});

router.post('/posts/:postId/like', (req, res) => {
  const postId = parseInt(req.params.postId);
  const post = db.posts.find(p => p.id === postId);
  if (!post) {
    return res.status(404).json({ error: 'Пост не найден' });
  }
  post.likes += 1;
  res.json({ likes: post.likes });
});

module.exports = router;