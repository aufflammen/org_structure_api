# API организационной структуры

REST API для управления **деревом подразделений** и **сотрудниками** компании. Реализовано на FastAPI, асинхронном
SQLAlchemy 2.x, PostgreSQL и Alembic.

## Возможности

- Иерархия подразделений с уникальностью имени в рамках одного родителя
- Рекурсивная выдача дерева с настраиваемой глубиной (1–5) и опциональным списком сотрудников
- Безопасное перемещение подразделений с проверкой циклов (HTTP 409)
- Удаление подразделения:
    - **cascade** — каскадное удаление поддерева и сотрудников (FK `ON DELETE CASCADE`)
    - **reassign** — перенос сотрудников поддерева в целевое подразделение, дочерние узлы поднимаются к родителю
      удаляемого узла
- Структурированные HTTP-логи (метод, путь, статус, длительность)
- OpenAPI-документация: `/docs`

## Стек

| Слой        | Технология                     |
|-------------|--------------------------------|
| Runtime     | Python 3.12                    |
| Web         | FastAPI, Uvicorn               |
| БД          | PostgreSQL 17, asyncpg         |
| ORM         | SQLAlchemy 2.x (async)         |
| Миграции    | Alembic                        |
| Валидация   | Pydantic v2, pydantic-settings |
| Логирование | structlog (JSON)               |
| Тесты       | pytest, pytest-asyncio, httpx  |

## Архитектура

Слоистая архитектура с разделением ответственности:

```text
HTTP Request
    → Router (app/api/routers/)
    → Service (app/services/)      # бизнес-правила, доменные исключения
    → Repository (app/repositories/) # доступ к данным, без бизнес-логики
    → SQLAlchemy Models (app/models/)
    → PostgreSQL
```

Доменные ошибки (`DomainNotFoundError`, `DomainConflictError`, `DomainBadRequestError`) перехватываются в `app/main.py`и
преобразуются в HTTP 404 / 409 / 400 с телом `{"detail": "..."}`.

## Структура проекта

```text
org_structure_api_cursor/
├── app/
│   ├── api/
│   │   ├── dependencies.py    # DI: сессия БД, сервисы
│   │   └── routers/
│   │       ├── department.py  # CRUD подразделений, дерево
│   │       └── employee.py    # создание сотрудников
│   ├── core/
│   │   ├── config.py          # настройки из .env
│   │   ├── database.py        # async engine, сессии
│   │   └── logger.py          # structlog
│   ├── enums/
│   │   ├── delete_mode.py     # cascade | reassign
│   │   └── env.py             # prod | test
│   ├── models/                # SQLAlchemy ORM
│   ├── repositories/          # запросы к БД
│   ├── schemas/               # Pydantic DTO
│   ├── services/              # бизнес-логика
│   ├── utils/exceptions.py    # доменные исключения
│   └── main.py                # FastAPI app, middleware, handlers
├── migration/                 # Alembic
│   └── versions/
├── tests/                     # pytest
├── alembic.ini
├── compose.yaml               # prod-like: api + postgres + pgadmin
├── compose.test.yaml          # только PostgreSQL для тестов
├── Dockerfile
├── entrypoint.sh              # alembic upgrade + uvicorn
├── requirements.txt
├── .env.example
└── .env.test
```

## Требования

- Python 3.12+
- Docker и Docker Compose

## Установка через Docker Compose

1. Скопируйте файл окружения:

   ```bash
   cp .env.example .env
   ```

2. При необходимости измените пароли и порты в `.env`.

3. Запустите стек:

   ```bash
   docker compose up --build
   ```

API: `http://localhost:8000` (порт задаётся `API_PORT`).

При старте контейнера `entrypoint.sh` выполняет `alembic upgrade head`, затем запускает Uvicorn.

## Настройка окружения

### Переменные (`.env.example`)

| Переменная          | Описание                                          |
|---------------------|---------------------------------------------------|
| `ENV`               | Окружение: `prod` или `test`                      |
| `POSTGRES_DB`       | Имя базы данных                                   |
| `POSTGRES_USER`     | Пользователь БД                                   |
| `POSTGRES_PASSWORD` | Пароль                                            |
| `POSTGRES_HOST`     | Хост (`postgres` в Compose, `localhost` локально) |
| `POSTGRES_PORT`     | Порт PostgreSQL                                   |
| `API_PORT`          | Публикуемый порт API (по умолчанию 8000)          |
| `PGADMIN_*`         | Учётные данные pgAdmin (опционально)              |

Вложенная конфигурация БД загружается через префикс `POSTGRES_` (см. `app/core/config.py`).


> Для тестов используется отдельная БД и порт, чтобы не пересекаться с dev/prod PostgreSQL на 5432.

## Запуск API

| Действие                     | Команда                                                          |
|------------------------------|------------------------------------------------------------------|
| Compose (API + БД + pgAdmin) | `docker compose up --build`                                      |
| Только БД для тестов         | `docker compose -f compose.test.yaml --env-file .env.test up -d` |
| Health check                 | `curl http://localhost:8000/health`                              |
| Swagger                      | `http://localhost:8000/docs`                                     |

## Пайплайн обработки запросов

1. **Middleware** (`app/main.py`) — логирует каждый запрос: метод, путь, статус, `duration_ms`.
2. **Router** — валидирует тело/query через Pydantic-схемы.
3. **Service** — проверяет бизнес-правила (циклы, дубликаты имён, существование родителя).
4. **Repository** — выполняет SQL через async-сессию.
5. **Commit** — фиксируется в сервисе после успешной операции.
6. **Response** — сериализация Pydantic `response_model` или пустое тело `204`.

### Создание подразделения

- Обрезка пробелов в `name`
- Проверка существования `parent_id` (если не `null`)
- Уникальность `(name, parent_id)` на уровне БД и сервиса

### Получение дерева

- `GET /departments/{id}?depth=1..5&include_employees=true|false`
- Рекурсивная сборка детей до указанной глубины
- Сотрудники сортируются по `created_at`

### Обновление (PATCH)

- Частичное обновление: учитываются только переданные поля (`model_fields_set`)
- `parent_id: null` — явный перенос в корень
- Запрет циклов и самоссылки

### Удаление

| mode       | Поведение                                                                                                                             |
|------------|---------------------------------------------------------------------------------------------------------------------------------------|
| `cascade`  | Удаление узла; дочерние подразделения и сотрудники удаляются каскадом FK                                                              |
| `reassign` | Сотрудники всего поддерева → `reassign_to_department_id`; прямые дети → родитель удаляемого узла; затем удаляется только целевой узел |

## Входные и выходные данные

### Подразделение (создание)

**Запрос** `POST /departments/`:

```json
{
  "name": "Engineering",
  "parent_id": null
}
```

**Ответ** `201`:

```json
{
  "id": 1,
  "name": "Engineering",
  "parent_id": null,
  "created_at": "2026-05-16T12:00:00+00:00"
}
```

### Дерево

**Ответ** `GET /departments/{id}`:

```json
{
  "id": 1,
  "name": "Root",
  "employees": [],
  "children": [
    {
      "id": 2,
      "name": "Child",
      "employees": [
        {
          "id": 1,
          "department_id": 2,
          "full_name": "Jane Doe",
          "position": "Engineer",
          "hired_at": "2024-06-01",
          "created_at": "2026-05-16T12:00:00+00:00"
        }
      ],
      "children": []
    }
  ]
}
```

### Сотрудник

**Запрос** `POST /departments/{department_id}/employees/`:

```json
{
  "full_name": "Ada Lovelace",
  "position": "Developer",
  "hired_at": "2024-01-15"
}
```

### Ошибки

```json
{
  "detail": "Department cycle detected"
}
```

| Код | Когда                                                              |
|-----|--------------------------------------------------------------------|
| 400 | Невалидный режим удаления, отсутствует `reassign_to_department_id` |
| 404 | Сущность не найдена                                                |
| 409 | Дубликат имени, цикл, конфликт reassign                            |
| 422 | Ошибка валидации Pydantic                                          |

## Тесты

### Подготовка

```bash
pip install -r requirements.txt
docker compose -f compose.test.yaml --env-file .env.test up -d
```

### Запуск

```bash
pytest -v
pytest -v tests/test_departments.py
pytest -v tests/test_department_service.py   # unit без БД
```

Тесты загружают `.env.test`, проверяют `ENV=test`, создают схему через ORM metadata и очищают данные `TRUNCATE` после
каждого теста.