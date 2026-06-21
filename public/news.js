const API_URL = 'http://localhost:3000/api';

const publishBtn = document.getElementById('publishBtn');
const postInput = document.getElementById('postInput');
const feedPosts = document.getElementById('feedPosts');
const feedTabs = document.querySelectorAll('.feed-tab');

let posts = [];

async function loadPosts() {
  try {
    const response = await fetch(`${API_URL}/posts`);
    posts = await response.json();
    renderPosts();
  } catch (error) {
    console.error('Ошибка загрузки постов:', error);
  }
}

function createPostElement(post) {
  const div = document.createElement('div');
  div.className = 'post-card';
  div.dataset.id = post.id;
  
  const imageHtml = post.hasImage ? `
    <div class="post-card__media">
      <div class="post-card__image" style="background: linear-gradient(135deg, #a8c0ff, #3f2b96);">
        <span>📸</span>
      </div>
    </div>
  ` : '';
  
  div.innerHTML = `
    <div class="post-card__header">
      <div class="post-card__user">
        <span class="post-card__avatar">${post.avatar}</span>
        <div class="post-card__info">
          <span class="post-card__name">${post.user}</span>
          <span class="post-card__time">${post.time}</span>
        </div>
      </div>
      <button class="post-card__menu">⋯</button>
    </div>
    <div class="post-card__content">
      <p>${post.text}</p>
      ${imageHtml}
    </div>
    <div class="post-card__footer">
      <button class="post-action like-btn" data-id="${post.id}">❤️ <span class="like-count">${post.likes}</span></button>
      <button class="post-action">💬 ${post.comments}</button>
      <button class="post-action">↗️ ${post.shares}</button>
    </div>
  `;
  
  const likeBtn = div.querySelector('.like-btn');
  likeBtn.addEventListener('click', async () => {
    try {
      const response = await fetch(`${API_URL}/posts/${post.id}/like`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        const countSpan = likeBtn.querySelector('.like-count');
        countSpan.textContent = data.likes;
        likeBtn.style.color = '#e74c3c';
      }
    } catch (error) {
      console.error('Ошибка лайка:', error);
    }
  });
  
  return div;
}

function renderPosts() {
  feedPosts.innerHTML = '';
  posts.forEach(post => {
    feedPosts.appendChild(createPostElement(post));
  });
}

async function addNewPost(text) {
  try {
    const response = await fetch(`${API_URL}/posts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    
    if (response.ok) {
      const newPost = await response.json();
      posts.unshift(newPost);
      feedPosts.prepend(createPostElement(newPost));
    }
  } catch (error) {
    console.error('Ошибка публикации:', error);
  }
}

publishBtn.addEventListener('click', () => {
  const text = postInput.value.trim();
  if (!text) {
    alert('Напишите что-нибудь!');
    return;
  }
  addNewPost(text);
  postInput.value = '';
});

postInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    publishBtn.click();
  }
});

feedTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    feedTabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
  });
});

loadPosts();

setInterval(loadPosts, 10000);