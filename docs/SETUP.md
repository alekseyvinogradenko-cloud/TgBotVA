# Setup Guide

## 1. Supabase

1. Создай проект на [supabase.com](https://supabase.com)
2. Перейди в SQL Editor и выполни `supabase/schema.sql`
3. Скопируй `DATABASE_URL` (Settings → Database → Connection string → URI)
4. Скопируй `SUPABASE_URL` и `SUPABASE_SERVICE_KEY` (Settings → API)

## 2. Telegram Bot

Для каждого пространства (Работа, Дом и т.д.):
1. Открой [@BotFather](https://t.me/BotFather)
2. `/newbot` → задай имя и username
3. Скопируй токен

## 3. Backend (Render)

1. Создай аккаунт на [render.com](https://render.com)
2. New → Web Service → подключи репозиторий
3. Root Directory: `backend`
4. Build Command: `pip install poetry && poetry install --no-dev`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Заполни Environment Variables из `.env.example`
7. После деплоя скопируй URL (например `https://assistant-bot.onrender.com`)

## 4. Регистрация бота

После деплоя бэкенда зарегистрируй первое пространство:

```bash
curl -X POST https://your-app.onrender.com/api/workspaces/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Работа",
    "type": "work",
    "telegram_bot_token": "YOUR_BOT_TOKEN",
    "owner_telegram_id": YOUR_TELEGRAM_ID
  }'
```

Найди свой Telegram ID через [@userinfobot](https://t.me/userinfobot).

## 5. Frontend (Vercel)

1. Создай аккаунт на [vercel.com](https://vercel.com)
2. New Project → подключи репозиторий
3. Root Directory: `frontend`
4. Environment Variables:
   - `NEXT_PUBLIC_API_URL` = URL твоего Render-бэкенда
5. Deploy

## 6. Проверка

- Открой бот в Telegram → `/start`
- Создай проект: `/projects` → Новый проект
- Добавь задачу текстом: напиши «Купить молоко завтра»
- Открой веб-интерфейс → должны появиться задачи
