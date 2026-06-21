const dialogs = [
  {
    id: 1,
    name: 'Анна',
    avatar: '👩',
    lastMessage: 'Привет! Как дела?',
    time: '12:34',
  },
  {
    id: 2,
    name: 'Сергей',
    avatar: '🧑',
    lastMessage: 'Скинь фотку с вчерашней встречи',
    time: '11:20',
  },
  {
    id: 3,
    name: 'Мария',
    avatar: '👩‍💻',
    lastMessage: 'Ок, договорились 👍',
    time: 'вчера',
  },
];

const messages = {
  1: [
    { id: 1, from: 'user', text: 'Привет!', time: '12:30', timestamp: '2026-06-22T12:30:00Z' },
    { id: 2, from: 'partner', text: 'Привет! Как дела?', time: '12:34', timestamp: '2026-06-22T12:34:00Z' },
  ],
  2: [
    { id: 3, from: 'user', text: 'Сергей, привет!', time: '11:10', timestamp: '2026-06-22T11:10:00Z' },
    { id: 4, from: 'partner', text: 'Скинь фотку с вчерашней встречи', time: '11:20', timestamp: '2026-06-22T11:20:00Z' },
  ],
  3: [
    { id: 5, from: 'partner', text: 'Мария, ты будешь на встрече?', time: '10:00', timestamp: '2026-06-22T10:00:00Z' },
    { id: 6, from: 'user', text: 'Да, буду. Ок, договорились 👍', time: '10:05', timestamp: '2026-06-22T10:05:00Z' },
  ],
};

const posts = [
  {
    id: 1,
    user: 'Анна Петрова',
    avatar: '👩',
    time: '2 часа назад',
    text: 'Сегодня был прекрасный день! Прогулка по парку, встретила старых друзей. Как же здорово, когда погода радует ☀️',
    hasImage: true,
    likes: 24,
    comments: 7,
    shares: 3,
    timestamp: '2026-06-22T10:00:00Z'
  },
  {
    id: 2,
    user: 'Сергей Иванов',
    avatar: '🧑',
    time: '5 часов назад',
    text: 'Запустил новый проект! Наконец-то первая версия готова к тестированию. Буду рад фидбеку от всех желающих 🚀',
    hasImage: true,
    likes: 15,
    comments: 12,
    shares: 5,
    timestamp: '2026-06-22T07:00:00Z'
  },
  {
    id: 3,
    user: 'Мария Соколова',
    avatar: '👩‍💻',
    time: 'вчера',
    text: 'Новая книга просто потрясающая! "Искусство программирования" — must read для всех разработчиков. Уже на 200 странице 📚',
    hasImage: false,
    likes: 32,
    comments: 9,
    shares: 12,
    timestamp: '2026-06-21T18:00:00Z'
  }
];

module.exports = { dialogs, messages, posts };