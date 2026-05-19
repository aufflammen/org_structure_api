# API организационной структуры

REST API для управления **деревом подразделений** и **сотрудниками** компании.
Реализовано на FastAPI, асинхронном SQLAlchemy 2.x, PostgreSQL и Alembic.

## О проекте

Сервис предоставляет HTTP API для:

- создания и изменения иерархии подразделений;
- получения поддерева с настраиваемой глубиной и списком сотрудников;
- удаления подразделений в режимах **cascade** (каскад) и **reassign** (переназначение сотрудников);
- добавления сотрудников в конкретное подразделение.

Базовый URL по умолчанию: `http://localhost:8000` (порт настраивается через `API_PORT` в Docker Compose).

## Возможности

- Иерархия подразделений с уникальностью имени в рамках одного родителя
- Рекурсивная выдача дерева с настраиваемой глубиной (1–5) и опциональным списком сотрудников
- Безопасное перемещение подразделений с проверкой циклов (HTTP 409)
- Удаление подразделения:
    - **cascade** — каскадное удаление поддерева и сотрудников (FK `ON DELETE CASCADE`)
    - **reassign** — удаление только указанного узла; сотрудники этого узла переводятся в
      целевое подразделение; прямые дочерние узлы поднимаются к родителю удаляемого
- Структурированные HTTP-логи (метод, путь, статус, длительность)

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

## Структура проекта

```text
org_structure_api/
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
│   ├── utils/
│   │   └── exceptions.py      # доменные исключения
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

## Архитектура

Слоистая архитектура с разделением ответственности:

```text
HTTP Request
    → Middleware (app/main.py)          # логирование: метод, путь, статус, duration_ms
    → Router (app/api/routers/)         # валидация через Pydantic-схемы
    → Service (app/services/)           # бизнес-правила, доменные исключения
    → Repository (app/repositories/)    # доступ к SQL через async-сессию
    → SQLAlchemy Models (app/models/)   
    → PostgreSQL
```

Доменные ошибки (`DomainBadRequestError400`, `DomainNotFoundError404`, `DomainConflictError409`)
перехватываются в `app/main.py` и преобразуются в HTTP 400 / 404 / 409 с телом `{"detail": "..."}`.

Ошибки валидации Pydantic/FastAPI возвращают HTTP **422** в стандартном формате FastAPI
(массив `detail` с полями `loc`, `msg`, `type`).

## Установка

### Требования

- Docker и Docker Compose

### Docker Compose

1. Скопируйте файл с переменными окружения:

   ```bash
   cp .env.example .env
   ```

2. При необходимости измените пароли и порты в `.env`.

3. Запустите:

   ```bash
   docker compose up --build
   ```

## Запуск

| Действие                     | Команда                                                    |
|------------------------------|------------------------------------------------------------|
| Compose (API + БД + pgAdmin) | `docker compose up --build`                                |
| Health check                 | `curl http://localhost:8000/health`                        |
| OpenAPI JSON                 | `http://localhost:8000/openapi.json`                       |
| Swagger UI                   | [http://localhost:8000/docs](http://localhost:8000/docs)   |
| ReDoc                        | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

## Переменные окружения (`.env.example`)

| Переменная                 | Описание                                           |
|----------------------------|----------------------------------------------------|
| `ENV`                      | Окружение: `prod` или `test`                       |
| `POSTGRES_DB`              | Имя базы данных                                    |
| `POSTGRES_USER`            | Пользователь БД                                    |
| `POSTGRES_PASSWORD`        | Пароль                                             |
| `POSTGRES_HOST`            | Хост (`postgres` в Compose, `localhost` локально)  |
| `POSTGRES_PORT`            | Порт PostgreSQL                                    |
| `API_PORT`                 | Публикуемый порт API в Compose (по умолчанию 8000) |
| `PGADMIN_DEFAULT_EMAIL`    | Email для pgAdmin (Compose)                        |
| `PGADMIN_DEFAULT_PASSWORD` | Пароль pgAdmin                                     |
| `PGADMIN_PORT`             | Порт pgAdmin в Compose                             |

> Для тестов используется файл `.env.test` - поднимается отдельная БД на другом порту,
> чтобы не пересекаться с prod PostgreSQL на 5432.

## API Documentation

Общие соглашения:

| Аспект                                          | Значение                                                                                  |
|-------------------------------------------------|-------------------------------------------------------------------------------------------|
| Content-Type запросов с телом                   | `application/json`                                                                        |
| Формат дат                                      | ISO 8601: `YYYY-MM-DD` (`hired_at`), `YYYY-MM-DDTHH:MM:SS` (`created_at`, timezone-aware) |
| Пустые строки в `name`, `full_name`, `position` | Обрезаются; пустая строка после trim → **422**                                            |
| Ошибки домена                                   | `{"detail": "<сообщение>"}`                                                               |
| Ошибки валидации                                | `{"detail": [<объекты FastAPI/Pydantic>]}`                                                |

### `GET /health`

Проверка доступности сервиса.

### `POST /departments/`

Создание подразделения с опциональным родителем.

#### Request Body

| Поле        | Тип         | Обязательное | Описание                                                                 |
|-------------|-------------|--------------|--------------------------------------------------------------------------|
| `name`      | str         | Да           | Название (1–200 символов; пробелы по краям обрезаются)                   |
| `parent_id` | int \| null | Нет          | ID родительского подразделения; `null` или отсутствие — корневой уровень |

### `GET /departments/{department_id}`

Получение подразделения и вложенного поддерева с заданной глубиной.

#### Path Parameters

| Параметр        | Тип | Обязательное | Описание         |
|-----------------|-----|--------------|------------------|
| `department_id` | int | Да           | ID подразделения |

#### Query Parameters

| Параметр            | Тип  | Обязательное | По умолчанию | Описание                                             |
|---------------------|------|--------------|--------------|------------------------------------------------------|
| `depth`             | int  | Нет          | `1`          | Глубина обхода детей: от **1** до **5** включительно |
| `include_employees` | bool | Нет          | `true`       | Включать список сотрудников в каждом узле            |

При `depth=1` возвращаются только прямые дочерние подразделения; у листьев `children` — пустой массив.
Сотрудники в узле сортируются по `created_at`.

### `PATCH /departments/{department_id}`

Частичное обновление названия и/или родителя подразделения.

#### Path Parameters

| Параметр        | Тип | Обязательное | Описание         |
|-----------------|-----|--------------|------------------|
| `department_id` | int | Да           | ID подразделения |

#### Request Body

Все поля опциональны; обновляются только переданные поля.

| Поле        | Тип         | Обязательное | Описание                              |
|-------------|-------------|--------------|---------------------------------------|
| `name`      | str         | Нет          | Новое название (1–200 символов; trim) |
| `parent_id` | int \| null | Нет          | Новый родитель                        |

> **Примечание:** при передаче `"parent_id": null` сервис интерпретирует значение как «не менять родителя»
> (логика `payload.parent_id or department.parent_id`). Явный перенос в корень через `null` в текущей
> реализации **не поддерживается**.

Если имя и родитель не изменились, возвращается текущая сущность без ошибки (**200**).

### `DELETE /departments/{department_id}`

Удаление подразделения в режиме **cascade** или **reassign**.

#### Path Parameters

| Параметр        | Тип | Обязательное | Описание                    |
|-----------------|-----|--------------|-----------------------------|
| `department_id` | int | Да           | ID удаляемого подразделения |

#### Query Parameters

| Параметр                    | Тип | Обязательное | Описание                                                                                   |
|-----------------------------|-----|--------------|--------------------------------------------------------------------------------------------|
| `mode`                      | str | Да           | `cascade` или `reassign`                                                                   |
| `reassign_to_department_id` | int | Условно      | Обязателен при `mode=reassign` — ID подразделения для перевода сотрудников удаляемого узла |

#### Режимы удаления

**`mode=cascade`**

- удаляется указанное подразделение;
- рекурсивно удаляются все дочерние подразделения;
- удаляются все сотрудники удаляемого подразделения и дочерних (каскад FK `ON DELETE CASCADE`).

**`mode=reassign`**

- удаляется только указанное подразделение;
- сотрудники **только** удаляемого подразделения переводятся в `reassign_to_department_id`;
- прямые дочерние подразделения не удаляются и получают `parent_id`, равный `parent_id` удаляемого узла;
- сотрудники дочерних подразделений **не** переносятся.

##### Схема удаления

Было:

```text
HQ
└── Sales (удаляется)
    ├── East
    └── West
```

После `DELETE <Sales_id>?mode=cascade`:

```text
HQ           # сотрудники Sales, East и West удалены
```

После `DELETE <Sales_id>?mode=reassign&reassign_to_department_id=<HQ_id>`:

```text
HQ           # сотрудники Sales — в HQ
├── East
└── West
```

### `POST /departments/{department_id}/employees/`

Создание сотрудника в указанном подразделении.

#### Path Parameters

| Параметр        | Тип | Обязательное | Описание         |
|-----------------|-----|--------------|------------------|
| `department_id` | int | Да           | ID подразделения |

#### Request Body

| Поле        | Тип        | Обязательное | Описание                         |
|-------------|------------|--------------|----------------------------------|
| `full_name` | str        | Да           | ФИО (1–200 символов; trim)       |
| `position`  | str        | Да           | Должность (1–200 символов; trim) |
| `hired_at`  | str (date) | Нет          | Дата приёма (`YYYY-MM-DD`)       |

## Тесты

### Требования

- Python 3.12+
- Docker и Docker Compose

### Подготовка

Установка виртуального окружения и зависимостей

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Запуск отдельной БД

```bash
docker compose -f compose.test.yaml --env-file .env.test up -d
```

### Запуск тестов

```bash
pytest -v
```
