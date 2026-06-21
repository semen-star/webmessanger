const express = require('express');
const path = require('path');
const cors = require('cors');
const apiRoutes = require('./routes/api');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(express.static(path.join(__dirname, 'public')));

app.use('/api', apiRoutes);

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/news', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'news.html'));
});

app.listen(PORT, () => {
  console.log(`🚀 Сервер SemkaMes запущен на http://localhost:${PORT}`);
  console.log(`📱 Мессенджер: http://localhost:${PORT}/`);
  console.log(`📰 Новости: http://localhost:${PORT}/news`);
});