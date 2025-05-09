# ASQ API CHAT

## Запуск программы

Для запуска проекта выполните следующую команду:

```bash
docker-compose up -d --build
```

## API-запросы

Все маршруты используют префикс `/chat`.

### Аутентификация

#### Регистрация
```http
POST /chat/register
Content-Type: application/json

{
  "username": "maks",
  "email": "maks@example.com",
  "password": "secret"
}
```

#### Получение токена
```http
POST /chat/token
Content-Type: application/x-www-form-urlencoded

username=john@example.com&password=secret
```

---

### Чаты

#### Создание чата
```http
POST /chat/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "creator_id": 1,
  "second_email": "dima@example.com"
}
```

#### Поиск чата по имени
```http
POST /chat/find-chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "id": 1,
  "name": "maks"
}
```

#### История сообщений
```http
GET /chat/history/1?limit=50&offset=0
Authorization: Bearer <token>
```

---

### Группы

#### Создание группы
```http
POST /chat/group
Authorization: Bearer <token>
Content-Type: application/json

{
  "creator_id": 1,
  "name": "team chat",
  "participant_ids": [1, 2]
}
```

#### Добавление пользователя в группу
```http
POST /chat/group/add-user
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": 1
  "group_id": 1,
  "second_email": "dima@example.com"
}
```

#### История группы
```http
GET /chat/group-history/1?limit=50&offset=0
Authorization: Bearer <token>
```

#### Отправка сообщения в группу
```http
POST /chat/group-message
Authorization: Bearer <token>
Content-Type: application/json

{
  "chat_id": 1,
  "sender_id": 1,
  "text": "Hello group!"
}
```

---

### WebSocket

#### Подключение к чату
```text
ws://localhost:8000/chat/ws/1?token=<access_token>
```

**Формат сообщения:**
```json
{
  "chat_id": 1,
  "sender_id": 1,
  "text": "Hello!"
}
```

---

> Все защищённые маршруты требуют JWT-токен в заголовке `Authorization: Bearer <token>`.
