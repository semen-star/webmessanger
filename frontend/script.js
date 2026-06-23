const API_URL = 'http://localhost:3000/api';

let dialogs = [];
let currentDialogId = null;
let messages = {};

const dialogListEl = document.getElementById('dialogList');
const messagesContainer = document.getElementById('messagesContainer');
const chatUserName = document.getElementById('chatUserName');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const searchInput = document.getElementById('searchDialog');
const newChatBtn = document.getElementById('newChatBtn');

async function loadDialogs() {
  try {
    const response = await fetch(`${API_URL}/dialogs`);
    dialogs = await response.json();
    renderDialogs();
    if (dialogs.length > 0) {
      openDialog(dialogs[0].id);
    }
  } catch (error) {
    console.error('Ошибка загрузки диалогов:', error);
  }
}

async function loadMessages(dialogId) {
  try {
    const response = await fetch(`${API_URL}/messages/${dialogId}`);
    messages = await response.json();
    renderMessages(messages);
  } catch (error) {
    console.error('Ошибка загрузки сообщений:', error);
  }
}

function renderDialogs(filter = '') {
  const filtered = dialogs.filter(d =>
    d.name.toLowerCase().includes(filter.toLowerCase())
  );

  dialogListEl.innerHTML = '';
  filtered.forEach(d => {
    const li = document.createElement('li');
    li.className = `dialog-item${currentDialogId === d.id ? ' active' : ''}`;
    li.dataset.id = d.id;

    li.innerHTML = `
      <span class="dialog-avatar">${d.avatar}</span>
      <div class="dialog-info">
        <div class="dialog-name">${d.name}</div>
        <div class="dialog-lastmsg">${d.lastMessage || 'Напишите сообщение'}</div>
      </div>
      <span class="dialog-time">${d.time || ''}</span>
    `;

    li.addEventListener('click', () => {
      openDialog(d.id);
    });

    dialogListEl.appendChild(li);
  });
}

function openDialog(id) {
  currentDialogId = id;
  const dialog = dialogs.find(d => d.id === id);
  if (!dialog) return;

  chatUserName.textContent = dialog.name;
  renderDialogs();
  loadMessages(id);
}

function renderMessages(msgs) {
  messagesContainer.innerHTML = '';
  if (!msgs || msgs.length === 0) {
    messagesContainer.innerHTML = `<div class="message-placeholder"><p>💬 Напишите первое сообщение</p></div>`;
    return;
  }

  msgs.forEach(msg => {
    const div = document.createElement('div');
    const isOut = msg.from === 'user';
    div.className = `message ${isOut ? 'message--out' : 'message--in'}`;
    div.innerHTML = `
      ${msg.text}
      <span class="message__time">${msg.time || ''}</span>
    `;
    messagesContainer.appendChild(div);
  });

  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || currentDialogId === null) {
    if (!currentDialogId) alert('Сначала выберите диалог!');
    return;
  }

  try {
    const response = await fetch(`${API_URL}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dialogId: currentDialogId, text })
    });

    if (response.ok) {
      messageInput.value = '';
      loadMessages(currentDialogId);
      loadDialogs();
    }
  } catch (error) {
    console.error('Ошибка отправки сообщения:', error);
  }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMessage();
});

searchInput.addEventListener('input', (e) => {
  renderDialogs(e.target.value);
});

newChatBtn.addEventListener('click', () => {
  alert('🚧 В будущем здесь будет создание нового чата / поиск пользователей');
});

loadDialogs();

setInterval(() => {
  if (currentDialogId) {
    loadMessages(currentDialogId);
    loadDialogs();
  }
}, 5000);