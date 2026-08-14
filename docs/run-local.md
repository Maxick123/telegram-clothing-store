# Локальный запуск

1. Установите Docker Desktop и включите режим Linux containers.
2. Скопируйте `.env.example` в `.env` и замените `POSTGRES_PASSWORD` и `JWT_SECRET` на уникальные значения.
3. Для оплаты заполните тестовые `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY`; без них инфраструктура всё равно запускается.
4. Выполните `docker compose up --build -d`.
5. Откройте `http://localhost:8080/health`; ожидаемый ответ: `{"status":"ok"}`.

Проверка статуса: `docker compose ps`.

Остановка без удаления данных: `docker compose down`.
