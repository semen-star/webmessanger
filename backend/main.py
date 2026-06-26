"""
SemkaMes — всё в одном файле: бэкенд + встроенный фронтенд.
Запуск: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import (
    Depends, FastAPI, HTTPException, Query, WebSocket,
    WebSocketDisconnect, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, field_validator
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    String, Text, UniqueConstraint, create_engine, or_, and_,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# ══════════════════════════════════════════════════════════════════
# БД
# ══════════════════════════════════════════════════════════════════
engine = create_engine("sqlite:///./semkames.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase): pass

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ══════════════════════════════════════════════════════════════════
# МОДЕЛИ
# ══════════════════════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"
    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String(50), unique=True, index=True, nullable=False)
    hashed_pw    = Column(String(128), nullable=False)
    display_name = Column(String(100), nullable=False)
    avatar       = Column(String(10), default="👤")
    bio          = Column(Text, default="")
    is_online    = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    posts             = relationship("Post",       back_populates="author",   cascade="all, delete")
    sent_messages     = relationship("Message",    foreign_keys="Message.sender_id",   back_populates="sender")
    received_messages = relationship("Message",    foreign_keys="Message.receiver_id", back_populates="receiver")
    likes             = relationship("Like",       back_populates="user",     cascade="all, delete")

class Post(Base):
    __tablename__ = "posts"
    id         = Column(Integer, primary_key=True, index=True)
    author_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    author   = relationship("User", back_populates="posts")
    likes    = relationship("Like",    back_populates="post", cascade="all, delete")
    comments = relationship("Comment", back_populates="post", cascade="all, delete")

class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "post_id"),)
    id      = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

class Comment(Base):
    __tablename__ = "comments"
    id         = Column(Integer, primary_key=True)
    post_id    = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    post   = relationship("Post", back_populates="comments")
    author = relationship("User")

class Message(Base):
    __tablename__ = "messages"
    id          = Column(Integer, primary_key=True)
    sender_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text        = Column(Text, nullable=False)
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    sender   = relationship("User", foreign_keys=[sender_id],   back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")

Base.metadata.create_all(bind=engine)

# ══════════════════════════════════════════════════════════════════
# JWT + ПАРОЛИ
# ══════════════════════════════════════════════════════════════════
SECRET_KEY = "semkames-secret-key-change-in-production"
ALGORITHM  = "HS256"

def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.encode()).hexdigest() == hashed

def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(User, int(payload["sub"]))
        if not user: raise HTTPException(status_code=401, detail="Пользователь не найден")
        return user
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Токен недействителен")

CurrentUser = Annotated[User, Depends(get_current_user)]

def get_user_from_token_param(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return db.get(User, int(payload["sub"]))
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════
# СХЕМЫ
# ══════════════════════════════════════════════════════════════════
class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str
    avatar: str = "👤"

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserShort(BaseModel):
    id: int; username: str; display_name: str; avatar: str; is_online: bool
    model_config = {"from_attributes": True}

class UserOut(BaseModel):
    id: int; username: str; display_name: str; avatar: str; bio: str; is_online: bool; created_at: datetime
    model_config = {"from_attributes": True}

class PostCreate(BaseModel):
    text: str

class PostOut(BaseModel):
    id: int; text: str; created_at: datetime; author: UserShort
    likes_count: int = 0; comments_count: int = 0; liked_by_me: bool = False
    model_config = {"from_attributes": True}

class CommentCreate(BaseModel):
    text: str

class CommentOut(BaseModel):
    id: int; text: str; created_at: datetime; author: UserShort
    model_config = {"from_attributes": True}

class MessageOut(BaseModel):
    id: int; sender_id: int; receiver_id: int; text: str; is_read: bool; created_at: datetime
    model_config = {"from_attributes": True}

class DialogOut(BaseModel):
    partner: UserShort; last_message: MessageOut | None; unread_count: int

# ══════════════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ
# ══════════════════════════════════════════════════════════════════
app = FastAPI(title="SemkaMes API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ══════════════════════════════════════════════════════════════════
# ФРОНТЕНД (встроен прямо в Python)
# ══════════════════════════════════════════════════════════════════
HTML = r"""<!DOCTYPE html>
<html lang="ru" data-theme="auto">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SemkaMes</title>
<style>
:root{--accent:#6C63FF;--accent2:#4F46E5;--accent-soft:rgba(108,99,255,.12);--bg:#f5f5f7;--bg-panel:#fff;--bg-input:#f0f0f5;--bg-hover:#eeeef6;--text:#1a1a2e;--text2:#5a5a7a;--text3:#9494b0;--border:rgba(0,0,0,.07);--shadow:0 2px 16px rgba(108,99,255,.07);--r:14px}
@media(prefers-color-scheme:dark){html:not([data-theme=light]){--bg:#0f0f17;--bg-panel:#16161f;--bg-input:#1e1e2a;--bg-hover:#1e1e2e;--text:#e8e8f4;--text2:#9090b8;--text3:#5a5a7a;--border:rgba(255,255,255,.06);--shadow:0 2px 16px rgba(0,0,0,.4)}}
html[data-theme=dark]{--bg:#0f0f17;--bg-panel:#16161f;--bg-input:#1e1e2a;--bg-hover:#1e1e2e;--text:#e8e8f4;--text2:#9090b8;--text3:#5a5a7a;--border:rgba(255,255,255,.06);--shadow:0 2px 16px rgba(0,0,0,.4)}
html[data-theme=light]{--bg:#f5f5f7;--bg-panel:#fff;--bg-input:#f0f0f5;--bg-hover:#eeeef6;--text:#1a1a2e;--text2:#5a5a7a;--text3:#9494b0;--border:rgba(0,0,0,.07);--shadow:0 2px 16px rgba(108,99,255,.07)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;overflow:hidden;transition:background .18s,color .18s}

/* AUTH */
.auth-wrap{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:var(--bg);z-index:100}
.auth-card{background:var(--bg-panel);border-radius:20px;padding:40px;width:360px;box-shadow:0 8px 40px rgba(108,99,255,.15);border:1px solid var(--border)}
.auth-logo{text-align:center;margin-bottom:28px}
.auth-logo .icon{font-size:40px;background:linear-gradient(135deg,var(--accent),#a78bfa);border-radius:16px;width:64px;height:64px;display:inline-flex;align-items:center;justify-content:center;margin-bottom:12px}
.auth-logo h1{font-size:22px;font-weight:700}
.auth-logo p{font-size:13px;color:var(--text3);margin-top:4px}
.auth-tabs{display:flex;gap:4px;background:var(--bg-input);border-radius:10px;padding:4px;margin-bottom:24px}
.auth-tab{flex:1;padding:8px;border:none;border-radius:8px;background:transparent;color:var(--text3);font-size:13px;cursor:pointer;font-weight:500;transition:.15s}
.auth-tab.active{background:var(--bg-panel);color:var(--accent);box-shadow:0 1px 4px rgba(0,0,0,.1)}
.field{margin-bottom:14px}
.field label{display:block;font-size:12px;font-weight:600;color:var(--text2);margin-bottom:5px;text-transform:uppercase;letter-spacing:.05em}
.field input{width:100%;padding:11px 14px;border-radius:10px;border:1.5px solid var(--border);background:var(--bg-input);color:var(--text);font-size:14px;outline:none;transition:border-color .15s}
.field input:focus{border-color:var(--accent)}
.btn-primary{width:100%;padding:12px;border-radius:10px;border:none;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;font-size:15px;font-weight:600;cursor:pointer;transition:.15s;margin-top:4px}
.btn-primary:hover{opacity:.9}
.auth-err{color:#ef4444;font-size:13px;text-align:center;margin-top:10px;min-height:20px}

/* APP */
.app{display:none;flex:1;overflow:hidden}
.app.visible{display:flex}

/* SIDEBAR */
.sidebar{width:64px;height:100vh;background:var(--bg-panel);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:16px 0;gap:4px;flex-shrink:0}
.s-logo{width:40px;height:40px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:16px;flex-shrink:0}
.nav-btn{width:44px;height:44px;border-radius:12px;border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:20px;color:var(--text3);transition:.15s;position:relative}
.nav-btn:hover{background:var(--bg-hover);color:var(--text2)}
.nav-btn.active{background:var(--accent-soft);color:var(--accent)}
.nav-btn .badge{position:absolute;top:6px;right:6px;width:8px;height:8px;background:#FF4757;border-radius:50%;border:2px solid var(--bg-panel)}
.s-bottom{margin-top:auto;display:flex;flex-direction:column;align-items:center;gap:4px}
.theme-btn{width:44px;height:44px;border-radius:12px;border:none;background:transparent;cursor:pointer;font-size:18px;color:var(--text3);transition:.15s}
.theme-btn:hover{background:var(--bg-hover)}
.s-avatar{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,var(--accent),#a78bfa);border:none;cursor:pointer;color:#fff;font-size:14px;font-weight:600}

/* PAGES */
.page{display:none;flex:1;overflow:hidden}
.page.active{display:flex}

/* MESSENGER */
.dialogs-panel{width:300px;height:100vh;background:var(--bg-panel);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0}
.dlg-header{padding:20px 16px 12px;display:flex;align-items:center;justify-content:space-between}
.dlg-header h2{font-size:18px;font-weight:600}
.search-wrap{padding:0 12px 12px}
.search-input{width:100%;padding:9px 14px;border-radius:10px;border:1px solid var(--border);background:var(--bg-input);color:var(--text);font-size:14px;outline:none}
.search-input:focus{border-color:var(--accent)}
.dlg-list{flex:1;overflow-y:auto;padding:4px 8px}
.dlg-item{display:flex;align-items:center;gap:12px;padding:10px;border-radius:12px;cursor:pointer;transition:.15s}
.dlg-item:hover{background:var(--bg-hover)}
.dlg-item.active{background:var(--accent-soft)}
.dlg-ava{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;color:#fff;font-weight:600}
.dlg-info{flex:1;min-width:0}
.dlg-name{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dlg-prev{font-size:13px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
.dlg-meta{display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0}
.dlg-time{font-size:11px;color:var(--text3)}
.dlg-unread{min-width:18px;height:18px;background:var(--accent);color:#fff;font-size:11px;font-weight:600;border-radius:9px;padding:0 5px;display:flex;align-items:center;justify-content:center}

/* CHAT */
.chat-area{flex:1;display:flex;flex-direction:column;overflow:hidden;background:var(--bg)}
.chat-topbar{height:62px;padding:0 20px;display:flex;align-items:center;gap:12px;background:var(--bg-panel);border-bottom:1px solid var(--border);flex-shrink:0}
.chat-topbar-name{font-size:15px;font-weight:600}
.chat-topbar-status{font-size:12px;color:#22c55e;margin-top:1px}
.chat-topbar-ava{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:600;color:#fff}
.icon-btn{width:36px;height:36px;border-radius:8px;border:none;background:transparent;color:var(--text3);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:.15s;margin-left:auto}
.icon-btn:hover{background:var(--bg-hover)}
.chat-msgs{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:6px}
.empty-state{margin:auto;text-align:center;color:var(--text3)}
.empty-state .ei{font-size:48px;margin-bottom:12px}
.msg-wrap{display:flex;gap:8px;max-width:68%}
.msg-wrap.out{align-self:flex-end;flex-direction:row-reverse}
.msg-wrap.in{align-self:flex-start}
.msg-bubble{padding:10px 14px;border-radius:18px;font-size:14px;line-height:1.5;max-width:100%}
.msg-wrap.in .msg-bubble{background:var(--bg-panel);color:var(--text);border-bottom-left-radius:4px;border:1px solid var(--border)}
.msg-wrap.out .msg-bubble{background:var(--accent);color:#fff;border-bottom-right-radius:4px}
.msg-time{font-size:11px;margin-top:4px;opacity:.6;text-align:right}
.msg-wrap.in .msg-time{text-align:left;color:var(--text3)}
.msg-mini-ava{width:28px;height:28px;border-radius:50%;align-self:flex-end;font-size:13px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;flex-shrink:0}
.chat-input-bar{padding:12px 16px;background:var(--bg-panel);border-top:1px solid var(--border);display:flex;align-items:center;gap:8px;flex-shrink:0}
.msg-input{flex:1;padding:10px 16px;border-radius:22px;border:1px solid var(--border);background:var(--bg-input);color:var(--text);font-size:14px;outline:none}
.msg-input:focus{border-color:var(--accent)}
.send-btn{width:40px;height:40px;border-radius:50%;border:none;background:var(--accent);color:#fff;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:.15s;flex-shrink:0}
.send-btn:hover{background:var(--accent2);transform:scale(1.05)}

/* NEWS */
.news-wrap{flex:1;display:flex;overflow:hidden}
.news-side{width:240px;flex-shrink:0;padding:20px 12px;border-right:1px solid var(--border);background:var(--bg-panel);overflow-y:auto;display:flex;flex-direction:column;gap:8px}
.news-side h3{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--text3);padding:4px 8px;margin-top:4px}
.ns-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:10px;cursor:pointer;font-size:14px;color:var(--text2);transition:.15s}
.ns-item:hover{background:var(--bg-hover);color:var(--text)}
.ns-item.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.stats-block{padding:12px;border-radius:12px;background:var(--bg-input)}
.stat-row{display:flex;justify-content:space-between;padding:4px 0;font-size:13px}
.stat-val{font-weight:600;color:var(--accent)}
.news-feed{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:16px;max-width:680px}
.feed-top{display:flex;align-items:center;justify-content:space-between}
.feed-top h2{font-size:20px;font-weight:700}
.feed-tabs{display:flex;gap:4px}
.feed-tab{padding:6px 14px;border-radius:8px;border:none;background:transparent;cursor:pointer;font-size:13px;color:var(--text3);transition:.15s}
.feed-tab:hover{background:var(--bg-hover);color:var(--text2)}
.feed-tab.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.create-post{background:var(--bg-panel);border-radius:var(--r);padding:16px;border:1px solid var(--border);box-shadow:var(--shadow)}
.cp-top{display:flex;align-items:center;gap:12px}
.post-ava{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,var(--accent),#a78bfa);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:16px;flex-shrink:0}
.post-inp{flex:1;padding:10px 14px;border-radius:22px;border:1px solid var(--border);background:var(--bg-input);color:var(--text);font-size:14px;outline:none}
.post-inp:focus{border-color:var(--accent)}
.cp-acts{display:flex;justify-content:flex-end;margin-top:12px;padding-top:12px;border-top:1px solid var(--border)}
.pub-btn{padding:8px 18px;border-radius:8px;border:none;background:var(--accent);color:#fff;font-size:13px;font-weight:600;cursor:pointer;transition:.15s}
.pub-btn:hover{background:var(--accent2)}
.post-card{background:var(--bg-panel);border-radius:var(--r);border:1px solid var(--border);box-shadow:var(--shadow);overflow:hidden;transition:box-shadow .15s}
.post-card:hover{box-shadow:0 4px 32px rgba(108,99,255,.13)}
.pc-head{display:flex;align-items:center;justify-content:space-between;padding:16px 16px 12px}
.pc-user{display:flex;align-items:center;gap:10px}
.pc-ava{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px}
.pc-name{font-size:14px;font-weight:600}
.pc-time{font-size:12px;color:var(--text3);margin-top:2px}
.pc-body{padding:0 16px 12px;font-size:14px;line-height:1.6}
.pc-foot{display:flex;gap:4px;padding:8px 10px;border-top:1px solid var(--border)}
.react-btn{display:flex;align-items:center;gap:6px;padding:7px 12px;border-radius:8px;border:none;background:transparent;color:var(--text3);font-size:13px;cursor:pointer;transition:.15s}
.react-btn:hover{background:var(--bg-hover);color:var(--text)}
.react-btn.liked{color:#FF4757;background:rgba(255,71,87,.08)}

/* SEARCH USERS */
.user-search-result{padding:4px 8px}
.usr-item{display:flex;align-items:center;gap:10px;padding:10px;border-radius:10px;cursor:pointer;transition:.15s}
.usr-item:hover{background:var(--bg-hover)}
.usr-ava{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:17px;background:var(--bg-input)}

*{scrollbar-width:thin;scrollbar-color:var(--border) transparent}
</style>
</head>
<body>

<!-- AUTH -->
<div class="auth-wrap" id="authWrap">
  <div class="auth-card">
    <div class="auth-logo">
      <div class="icon">💬</div>
      <h1>SemkaMes</h1>
      <p>Мессенджер нового поколения</p>
    </div>
    <div class="auth-tabs">
      <button class="auth-tab active" onclick="switchTab('login')">Войти</button>
      <button class="auth-tab" onclick="switchTab('register')">Регистрация</button>
    </div>
    <div id="loginForm">
      <div class="field"><label>Логин</label><input id="l_username" placeholder="your_login" autocomplete="username"/></div>
      <div class="field"><label>Пароль</label><input id="l_password" type="password" placeholder="••••••" autocomplete="current-password"/></div>
      <button class="btn-primary" onclick="doLogin()">Войти</button>
    </div>
    <div id="regForm" style="display:none">
      <div class="field"><label>Логин</label><input id="r_username" placeholder="your_login"/></div>
      <div class="field"><label>Имя</label><input id="r_name" placeholder="Иван Иванов"/></div>
      <div class="field"><label>Пароль</label><input id="r_password" type="password" placeholder="••••••"/></div>
      <button class="btn-primary" onclick="doRegister()">Зарегистрироваться</button>
    </div>
    <div class="auth-err" id="authErr"></div>
  </div>
</div>

<!-- APP -->
<div class="app" id="app">
  <!-- Sidebar -->
  <nav class="sidebar">
    <div class="s-logo">💬</div>
    <button class="nav-btn active" id="navMsg" onclick="showPage('messenger')" title="Мессенджер">💬</button>
    <button class="nav-btn" id="navNews" onclick="showPage('news')" title="Новости">📰</button>
    <button class="nav-btn" id="navFriends" onclick="showPage('friends')" title="Друзья">👥</button>
    <div class="s-bottom">
      <button class="theme-btn" onclick="cycleTheme()" id="themeBtn">🌙</button>
      <button class="s-avatar" id="sAvatar" title="Профиль">??</button>
    </div>
  </nav>

  <!-- Мессенджер -->
  <div class="page active" id="pageMessenger">
    <div class="dialogs-panel">
      <div class="dlg-header"><h2>Сообщения</h2></div>
      <div class="search-wrap">
        <input class="search-input" placeholder="Найти пользователя..." id="userSearchInput" oninput="searchUsers(this.value)"/>
      </div>
      <div id="userSearchResult" class="user-search-result"></div>
      <div class="dlg-list" id="dlgList"></div>
    </div>
    <div class="chat-area" id="chatArea">
      <div class="empty-state"><div class="ei">💬</div><div>Выберите диалог</div></div>
    </div>
  </div>

  <!-- Новости -->
  <div class="page" id="pageNews">
    <div class="news-wrap">
      <aside class="news-side">
        <h3>Лента</h3>
        <div class="ns-item active" onclick="setNewsTab(this)"><span>📰</span> Моя лента</div>
        <div class="ns-item" onclick="setNewsTab(this)"><span>🔥</span> Популярное</div>
        <div class="ns-item" onclick="setNewsTab(this)"><span>⭐</span> Избранное</div>
        <h3>Статистика</h3>
        <div class="stats-block">
          <div class="stat-row"><span>Постов</span><span class="stat-val" id="myPostsCount">0</span></div>
          <div class="stat-row"><span>Лайков</span><span class="stat-val" id="myLikesCount">0</span></div>
        </div>
      </aside>
      <div class="news-feed">
        <div class="feed-top">
          <h2>Новости</h2>
          <div class="feed-tabs">
            <button class="feed-tab active">Все</button>
            <button class="feed-tab">Лучшее</button>
          </div>
        </div>
        <div class="create-post">
          <div class="cp-top">
            <div class="post-ava" id="postAva">?</div>
            <input class="post-inp" placeholder="Что у вас нового?" id="postInput"/>
          </div>
          <div class="cp-acts">
            <button class="pub-btn" onclick="publishPost()">Опубликовать</button>
          </div>
        </div>
        <div id="feedPosts"></div>
      </div>
    </div>
  </div>

  <!-- Друзья -->
  <div class="page" id="pageFriends">
    <div style="margin:auto;text-align:center;color:var(--text3)">
      <div style="font-size:48px;margin-bottom:12px">👥</div>
      <div>Раздел в разработке</div>
    </div>
  </div>
</div>

<script>
const API = '';  // бэк на том же хосте
let TOKEN = localStorage.getItem('token') || '';
let ME = null;
let activeDialogId = null;
let ws = null;

// ── AUTH ──────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((t,i) => t.classList.toggle('active', (tab==='login'?i===0:i===1)));
  document.getElementById('loginForm').style.display = tab==='login' ? '' : 'none';
  document.getElementById('regForm').style.display   = tab==='register' ? '' : 'none';
  document.getElementById('authErr').textContent = '';
}

async function doLogin() {
  const username = document.getElementById('l_username').value.trim();
  const password = document.getElementById('l_password').value;
  if (!username || !password) { showErr('Заполните все поля'); return; }
  const r = await fetch(`${API}/api/auth/login`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username, password})
  });
  const data = await r.json();
  if (!r.ok) { showErr(data.detail || 'Ошибка входа'); return; }
  TOKEN = data.access_token;
  localStorage.setItem('token', TOKEN);
  await initApp();
}

async function doRegister() {
  const username     = document.getElementById('r_username').value.trim();
  const display_name = document.getElementById('r_name').value.trim();
  const password     = document.getElementById('r_password').value;
  if (!username || !display_name || !password) { showErr('Заполните все поля'); return; }
  const r = await fetch(`${API}/api/auth/register`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username, display_name, password})
  });
  const data = await r.json();
  if (!r.ok) { showErr(data.detail || 'Ошибка регистрации'); return; }
  TOKEN = data.access_token;
  localStorage.setItem('token', TOKEN);
  await initApp();
}

function showErr(msg) { document.getElementById('authErr').textContent = msg; }

async function initApp() {
  const r = await fetch(`${API}/api/users/me`, {headers:{Authorization:`Bearer ${TOKEN}`}});
  if (!r.ok) { localStorage.removeItem('token'); return; }
  ME = await r.json();
  document.getElementById('authWrap').style.display = 'none';
  document.getElementById('app').classList.add('visible');
  document.getElementById('sAvatar').textContent = ME.avatar;
  document.getElementById('postAva').textContent = ME.avatar;
  loadDialogs();
  loadFeed();
  connectWS();
}

// ── WEBSOCKET ────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/api/messages/ws?token=${TOKEN}`);
  ws.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.error) return;
    // Если открыт нужный диалог — добавить сообщение
    const partnerId = msg.sender_id === ME.id ? msg.receiver_id : msg.sender_id;
    if (activeDialogId === partnerId) appendMessage(msg);
    loadDialogs(); // обновить список диалогов
  };
  ws.onclose = () => setTimeout(connectWS, 3000); // переподключение
}

// ── ДИАЛОГИ ──────────────────────────────────────────────────
async function loadDialogs() {
  const r = await fetch(`${API}/api/messages/dialogs`, {headers:{Authorization:`Bearer ${TOKEN}`}});
  if (!r.ok) return;
  const dialogs = await r.json();
  const list = document.getElementById('dlgList');
  list.innerHTML = dialogs.map(d => `
    <div class="dlg-item${activeDialogId===d.partner.id?' active':''}" onclick="openDialog(${d.partner.id},'${d.partner.display_name}','${d.partner.avatar}')">
      <div class="dlg-ava" style="background:${strColor(d.partner.username)}">${d.partner.avatar}</div>
      <div class="dlg-info">
        <div class="dlg-name">${d.partner.display_name}</div>
        <div class="dlg-prev">${d.last_message ? d.last_message.text : ''}</div>
      </div>
      <div class="dlg-meta">
        <div class="dlg-time">${d.last_message ? fmtTime(d.last_message.created_at) : ''}</div>
        ${d.unread_count ? `<div class="dlg-unread">${d.unread_count}</div>` : ''}
      </div>
    </div>
  `).join('');
}

async function openDialog(userId, name, avatar) {
  activeDialogId = userId;
  loadDialogs();
  const r = await fetch(`${API}/api/messages/history/${userId}`, {headers:{Authorization:`Bearer ${TOKEN}`}});
  const msgs = r.ok ? await r.json() : [];

  document.getElementById('chatArea').innerHTML = `
    <div class="chat-topbar">
      <div class="chat-topbar-ava" style="background:${strColor(name)}">${avatar}</div>
      <div>
        <div class="chat-topbar-name">${name}</div>
        <div class="chat-topbar-status">в сети</div>
      </div>
      <button class="icon-btn" onclick="activeDialogId=null;document.getElementById('chatArea').innerHTML='<div class=empty-state><div class=ei>💬</div><div>Выберите диалог</div></div>'">✕</button>
    </div>
    <div class="chat-msgs" id="msgList">
      ${msgs.map(m => renderMsg(m, avatar, strColor(name))).join('')}
    </div>
    <div class="chat-input-bar">
      <input class="msg-input" placeholder="Сообщение..." id="msgInput" onkeydown="if(event.key==='Enter')sendMsg(${userId})"/>
      <button class="send-btn" onclick="sendMsg(${userId})">➤</button>
    </div>
  `;
  const ml = document.getElementById('msgList');
  if (ml) ml.scrollTop = ml.scrollHeight;
}

function renderMsg(m, partnerAvatar, color) {
  const out = m.sender_id === ME.id;
  const time = fmtTime(m.created_at);
  if (out) return `<div class="msg-wrap out"><div><div class="msg-bubble">${esc(m.text)}</div><div class="msg-time">${time} ✓✓</div></div></div>`;
  return `<div class="msg-wrap in">
    <div class="msg-mini-ava" style="background:${color}">${partnerAvatar}</div>
    <div><div class="msg-bubble">${esc(m.text)}</div><div class="msg-time">${time}</div></div>
  </div>`;
}

function appendMessage(msg) {
  const ml = document.getElementById('msgList');
  if (!ml) return;
  // получим аватар партнёра из диалога
  const partnerAvatar = '👤';
  const color = '#6C63FF';
  const div = document.createElement('div');
  div.innerHTML = renderMsg(msg, partnerAvatar, color);
  ml.appendChild(div.firstElementChild);
  ml.scrollTop = ml.scrollHeight;
}

function sendMsg(toId) {
  const input = document.getElementById('msgInput');
  const text = input.value.trim();
  if (!text || !ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({to: toId, text}));
  input.value = '';
}

// ── ПОИСК ПОЛЬЗОВАТЕЛЕЙ ──────────────────────────────────────
let searchTimer;
async function searchUsers(q) {
  clearTimeout(searchTimer);
  const res = document.getElementById('userSearchResult');
  if (!q.trim()) { res.innerHTML = ''; return; }
  searchTimer = setTimeout(async () => {
    const r = await fetch(`${API}/api/users/search?q=${encodeURIComponent(q)}`, {headers:{Authorization:`Bearer ${TOKEN}`}});
    if (!r.ok) return;
    const users = await r.json();
    res.innerHTML = users.map(u => `
      <div class="usr-item" onclick="openDialog(${u.id},'${u.display_name}','${u.avatar}');document.getElementById('userSearchInput').value='';document.getElementById('userSearchResult').innerHTML=''">
        <div class="usr-ava">${u.avatar}</div>
        <div>
          <div style="font-size:14px;font-weight:600">${u.display_name}</div>
          <div style="font-size:12px;color:var(--text3)">@${u.username}</div>
        </div>
      </div>
    `).join('') || '<div style="padding:10px;color:var(--text3);font-size:13px">Не найдено</div>';
  }, 300);
}

// ── НОВОСТИ ──────────────────────────────────────────────────
async function loadFeed() {
  const r = await fetch(`${API}/api/posts/feed`, {headers:{Authorization:`Bearer ${TOKEN}`}});
  if (!r.ok) return;
  const posts = await r.json();
  renderFeed(posts);
}

function renderFeed(posts) {
  document.getElementById('feedPosts').innerHTML = posts.map(p => `
    <div class="post-card" id="pc-${p.id}">
      <div class="pc-head">
        <div class="pc-user">
          <div class="pc-ava">${p.author.avatar}</div>
          <div><div class="pc-name">${p.author.display_name}</div><div class="pc-time">${fmtTime(p.created_at)}</div></div>
        </div>
      </div>
      <div class="pc-body">${esc(p.text)}</div>
      <div class="pc-foot">
        <button class="react-btn${p.liked_by_me?' liked':''}" onclick="toggleLike(${p.id})">${p.liked_by_me?'❤️':'🤍'} ${p.likes_count}</button>
        <button class="react-btn">💬 ${p.comments_count}</button>
      </div>
    </div>
  `).join('') || '<div style="color:var(--text3);text-align:center;padding:40px">Постов пока нет. Напишите первый!</div>';
}

async function publishPost() {
  const input = document.getElementById('postInput');
  const text = input.value.trim();
  if (!text) return;
  const r = await fetch(`${API}/api/posts`, {
    method:'POST', headers:{Authorization:`Bearer ${TOKEN}`,'Content-Type':'application/json'},
    body: JSON.stringify({text})
  });
  if (r.ok) { input.value = ''; loadFeed(); }
}

async function toggleLike(postId) {
  const r = await fetch(`${API}/api/posts/${postId}/like`, {method:'POST', headers:{Authorization:`Bearer ${TOKEN}`}});
  if (r.ok) loadFeed();
}

// ── НАВИГАЦИЯ ────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const pages = {messenger:'pageMessenger', news:'pageNews', friends:'pageFriends'};
  const navs  = {messenger:'navMsg', news:'navNews', friends:'navFriends'};
  document.getElementById(pages[name]).classList.add('active');
  document.getElementById(navs[name]).classList.add('active');
  if (name === 'news') loadFeed();
}

function setNewsTab(el) {
  document.querySelectorAll('.ns-item').forEach(x => x.classList.remove('active'));
  el.classList.add('active');
}

// ── ТЕМА ────────────────────────────────────────────────────
const themes = ['auto','light','dark'], icons = {auto:'🌙',light:'☀️',dark:'🌑'};
let ti = 0;
function cycleTheme() {
  ti = (ti+1) % 3;
  document.documentElement.setAttribute('data-theme', themes[ti]);
  document.getElementById('themeBtn').textContent = icons[themes[ti]];
}

// ── UTILS ────────────────────────────────────────────────────
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmtTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'});
  return d.toLocaleDateString('ru',{day:'numeric',month:'short'});
}
function strColor(s) {
  let h = 0; for (let c of String(s)) h = (h*31 + c.charCodeAt(0)) & 0xFFFFFF;
  const colors = ['#6C63FF','#f43f5e','#10b981','#f59e0b','#3b82f6','#8b5cf6','#ec4899'];
  return colors[Math.abs(h) % colors.length];
}

// ── СТАРТ ────────────────────────────────────────────────────
if (TOKEN) initApp();
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML

# ══════════════════════════════════════════════════════════════════
# API РОУТЫ
# ══════════════════════════════════════════════════════════════════
@app.post("/api/auth/register", response_model=TokenResponse, status_code=201, tags=["auth"])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    body.username = body.username.strip().lower()
    if len(body.username) < 3:
        raise HTTPException(status_code=400, detail="Логин минимум 3 символа")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Логин уже занят")
    user = User(username=body.username, hashed_pw=hash_password(body.password),
                display_name=body.display_name, avatar=body.avatar)
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_token(user.id)}

@app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username.strip().lower()).first()
    if not user or not verify_password(body.password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return {"access_token": create_token(user.id)}

@app.get("/api/users/me", response_model=UserOut, tags=["users"])
def get_me(current_user: CurrentUser): return current_user

@app.get("/api/users/search", response_model=list[UserShort], tags=["users"])
def search_users(q: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    like = f"%{q}%"
    return db.query(User).filter(
        (User.username.ilike(like)) | (User.display_name.ilike(like)),
        User.id != current_user.id
    ).limit(20).all()

@app.get("/api/users/{user_id}", response_model=UserOut, tags=["users"])
def get_user(user_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u: raise HTTPException(status_code=404, detail="Не найден")
    return u

def _enrich(post, me):
    return PostOut(id=post.id, text=post.text, created_at=post.created_at, author=post.author,
                   likes_count=len(post.likes), comments_count=len(post.comments),
                   liked_by_me=any(l.user_id==me.id for l in post.likes))

@app.get("/api/posts/feed", response_model=list[PostOut], tags=["posts"])
def get_feed(current_user: CurrentUser, skip: int=0, limit: int=30, db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
    return [_enrich(p, current_user) for p in posts]

@app.post("/api/posts", response_model=PostOut, status_code=201, tags=["posts"])
def create_post(body: PostCreate, current_user: CurrentUser, db: Session = Depends(get_db)):
    if not body.text.strip(): raise HTTPException(status_code=400, detail="Текст пустой")
    p = Post(author_id=current_user.id, text=body.text.strip())
    db.add(p); db.commit(); db.refresh(p)
    return _enrich(p, current_user)

@app.post("/api/posts/{post_id}/like", response_model=PostOut, tags=["posts"])
def toggle_like(post_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    p = db.get(Post, post_id)
    if not p: raise HTTPException(status_code=404, detail="Пост не найден")
    like = db.query(Like).filter(Like.user_id==current_user.id, Like.post_id==post_id).first()
    if like: db.delete(like)
    else: db.add(Like(user_id=current_user.id, post_id=post_id))
    db.commit(); db.refresh(p)
    return _enrich(p, current_user)

@app.delete("/api/posts/{post_id}", status_code=204, tags=["posts"])
def delete_post(post_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    p = db.get(Post, post_id)
    if not p: raise HTTPException(status_code=404)
    if p.author_id != current_user.id: raise HTTPException(status_code=403)
    db.delete(p); db.commit()

class ConnectionManager:
    def __init__(self): self.active: dict[int, WebSocket] = {}
    async def connect(self, uid, ws):
        await ws.accept(); self.active[uid] = ws
    def disconnect(self, uid): self.active.pop(uid, None)
    async def send_to(self, uid, data):
        ws = self.active.get(uid)
        if ws:
            try: await ws.send_text(json.dumps(data, ensure_ascii=False, default=str))
            except: self.disconnect(uid)

manager = ConnectionManager()

@app.websocket("/api/messages/ws")
async def ws_endpoint(websocket: WebSocket, token: Annotated[str, Query()]):
    db = SessionLocal(); user = None
    try:
        user = get_user_from_token_param(token, db)
        if not user: await websocket.close(code=4001); return
        await manager.connect(user.id, websocket)
        user.is_online = True; db.commit()
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                to_id = int(data["to"]); text = str(data["text"]).strip()
                if not text: continue
            except: await websocket.send_text(json.dumps({"error":"Неверный формат"})); continue
            if not db.get(User, to_id): await websocket.send_text(json.dumps({"error":"Пользователь не найден"})); continue
            msg = Message(sender_id=user.id, receiver_id=to_id, text=text)
            db.add(msg); db.commit(); db.refresh(msg)
            payload = {"id":msg.id,"sender_id":msg.sender_id,"receiver_id":msg.receiver_id,
                       "text":msg.text,"is_read":msg.is_read,"created_at":msg.created_at.isoformat()}
            await manager.send_to(user.id, payload)
            await manager.send_to(to_id, payload)
    except WebSocketDisconnect: pass
    finally:
        if user: manager.disconnect(user.id); user.is_online=False; db.commit()
        db.close()

@app.get("/api/messages/dialogs", response_model=list[DialogOut], tags=["messages"])
def get_dialogs(current_user: CurrentUser, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(
        or_(Message.sender_id==current_user.id, Message.receiver_id==current_user.id)
    ).order_by(Message.created_at.desc()).all()
    seen = set(); dialogs = []
    for msg in msgs:
        pid = msg.receiver_id if msg.sender_id==current_user.id else msg.sender_id
        if pid in seen: continue
        seen.add(pid)
        partner = db.get(User, pid)
        unread = db.query(Message).filter(Message.sender_id==pid, Message.receiver_id==current_user.id, Message.is_read==False).count()
        dialogs.append(DialogOut(partner=partner, last_message=msg, unread_count=unread))
    return dialogs

@app.get("/api/messages/history/{user_id}", response_model=list[MessageOut], tags=["messages"])
def get_history(user_id: int, current_user: CurrentUser, db: Session = Depends(get_db), skip: int=0, limit: int=50):
    msgs = db.query(Message).filter(or_(
        and_(Message.sender_id==current_user.id, Message.receiver_id==user_id),
        and_(Message.sender_id==user_id, Message.receiver_id==current_user.id)
    )).order_by(Message.created_at.asc()).offset(skip).limit(limit).all()
    for m in msgs:
        if m.receiver_id==current_user.id and not m.is_read: m.is_read=True
    db.commit(); return msgs

@app.get("/api/health")
def health(): return {"status": "ok"}
