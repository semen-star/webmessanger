# SemkaMes — бэкенд

## Структура проекта

```
semkames/
├── backend/
│   ├── main.py          # точка входа
│   ├── database.py      # подключение к SQLite
│   ├── models.py        # таблицы БД
│   ├── schemas.py       # Pydantic схемы
│   ├── auth.py          # JWT + bcrypt
│   ├── requirements.txt
│   └── routers/
│       ├── auth.py      # POST /api/auth/register, /login
│       ├── users.py     # GET/PATCH /api/users/...
│       ├── posts.py     # GET/POST /api/posts/...
│       └── messages.py  # GET /api/messages/... + WS
└── frontend/
    └── semkames.html    # весь фронт в одном файле
```

## Запуск на Windows

### 1. Установить Python 3.11+
Скачать с https://python.org, при установке отметить "Add to PATH".

### 2. Создать виртуальное окружение и установить зависимости

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Запустить сервер

```bat
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Сервер будет доступен на http://localhost:8000

### 4. Swagger-документация API

Открыть в браузере: http://localhost:8000/docs

Там можно протестировать все эндпоинты прямо в браузере без Postman.

---

## API — краткий справочник

### Авторизация
| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/auth/register` | Регистрация |
| POST | `/api/auth/login` | Вход, получить JWT токен |

### Пользователи
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/users/me` | Мой профиль |
| PATCH | `/api/users/me` | Обновить профиль |
| GET | `/api/users/search?q=...` | Поиск пользователей |
| GET | `/api/users/{id}` | Профиль пользователя |
| POST | `/api/users/{id}/friend-request` | Отправить заявку в друзья |
| GET | `/api/users/me/friends` | Список друзей |

### Посты и лента
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/posts/feed` | Лента (посты друзей + свои) |
| POST | `/api/posts` | Создать пост |
| DELETE | `/api/posts/{id}` | Удалить свой пост |
| POST | `/api/posts/{id}/like` | Лайк / анлайк |
| GET | `/api/posts/{id}/comments` | Комментарии |
| POST | `/api/posts/{id}/comments` | Добавить комментарий |

### Сообщения
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/messages/dialogs` | Список диалогов |
| GET | `/api/messages/history/{user_id}` | История переписки |
| WS | `/api/messages/ws?token=<JWT>` | WebSocket чат |

### WebSocket — формат сообщений

**Отправить:**
```json
{ "to": 2, "text": "Привет!" }
```

**Получить** (и отправителю, и получателю):
```json
{
  "id": 42,
  "sender_id": 1,
  "receiver_id": 2,
  "text": "Привет!",
  "is_read": false,
  "created_at": "2024-06-24T14:30:00"
}
```

---

## Переезд на сервер (Linux)

1. Установить PostgreSQL, создать БД
2. В `database.py` заменить строку:
   ```python
   DATABASE_URL = "postgresql://user:password@localhost/semkames"
   ```
3. Убрать `connect_args` — он нужен только для SQLite
4. В `auth.py` заменить `SECRET_KEY` на случайную строку (генерить через `openssl rand -hex 32`)
5. Запустить через systemd или Docker + nginx как reverse proxy
