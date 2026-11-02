# EnglishCard — Изучение английского языка

Streamlit-приложение для изучения английского слов с отслеживанием прогресса.

## Возможности

- 📖 Тренажёр с вариантами ответов (4 варианта)
- ➕ Добавление персональных слов
- 🗑️ Удаление персональных слов
- 📊 Статистика обучения

## Схема базы данных

### ER-диаграмма

```
┌──────────────────────┐       ┌─────────────────────────┐
│       users          │       │      common_words       │
├──────────────────────┤       ├─────────────────────────┤
│ PK id        SERIAL  │       │ PK id        SERIAL     │
│    username  VARCHAR │       │    russian_word  VARCHAR│
│         created_at   │       │    english_word  VARCHAR│
│                      │       │         created_at      │
│                      │       │    UNIQUE(russian_word, │
└──────────┬───────────┘       │            english_word)│
           │                   └─────────────────────────┘
           │ 1
           │ │
           │ │
     N ────┘
           │ 1
           │ │
           │
┌──────────▼───────────┐       ┌───────────────────────────────┐
│     user_words       │       │       learning_stats          │
├──────────────────────┤       ├───────────────────────────────┤
│ PK id        SERIAL  │       │ PK id        SERIAL           │
│ FK user_id   INT     │──────▶│    user_id       INT          │
│    russian_word  VCH │       │    word_id       INT          │
│    english_word  VCH │       │    word_type     VARCHAR      │
│         created_at   │       │    correct_answers INT       │
│    UNIQUE(russian_   │       │    total_attempts  INT        │
│       _word,english_ │       │    last_reviewed   TIMESTAMPTZ│
│             word)    │       │    UNIQUE(user_id,word_id,    │
└──────────────────────┘       │               word_type)      │
                               └───────────────────────────────┘
```

### Описание таблиц

#### `users` — Пользователи

| Колонка      | Тип         | Ограничения                       |
|-------------|-------------|----------------------------------|
| `id`        | SERIAL      | PRIMARY KEY                      |
| `username`  | VARCHAR(40) | UNIQUE, NOT NULL                 |
| `created_at`| TIMESTAMPTZ | DEFAULT now()                    |

#### `common_words` — Общий словарь

| Колонка        | Тип         | Ограничения                                  |
|---------------|-------------|---------------------------------------------|
| `id`          | SERIAL      | PRIMARY KEY                                  |
| `russian_word`| VARCHAR(100)| NOT NULL                                     |
| `english_word`| VARCHAR(100)| NOT NULL                                     |
| `created_at`  | TIMESTAMPTZ | DEFAULT now()                                |

`UNIQUE (russian_word, english_word)`

#### `user_words` — Персональные слова

| Колонка        | Тип         | Ограничения                                  |
|---------------|-------------|---------------------------------------------|
| `id`          | SERIAL      | PRIMARY KEY                                  |
| `user_id`     | INTEGER     | NOT NULL, FK → `users(id) ON DELETE CASCADE` |
| `russian_word`| VARCHAR(100)|                                             |
| `english_word`| VARCHAR(100)|                                             |
| `created_at`  | TIMESTAMPTZ | DEFAULT now()                                |

`UNIQUE (russian_word, english_word)`

#### `learning_stats` — Статистика обучения

| Колонка           | Тип          | Ограничения                                   |
|------------------|--------------|----------------------------------------------|
| `id`             | SERIAL       | PRIMARY KEY                                   |
| `user_id`        | INTEGER      | NOT NULL, FK → `users(id) ON DELETE CASCADE`  |
| `word_id`        | INTEGER      | NOT NULL                                      |
| `word_type`      | VARCHAR(10)  | NOT NULL, CHECK IN ('common', 'user')         |
| `correct_answers`| INTEGER      | NOT NULL, DEFAULT 0                           |
| `total_attempts` | INTEGER      | NOT NULL, DEFAULT 0                           |
| `last_reviewed`  | TIMESTAMPTZ  | DEFAULT now()                                 |

`UNIQUE (user_id, word_id, word_type)`

### Связи

| Связь                                    | Тип        | Поведение при удалении     |
|-----------------------------------------|------------|---------------------------|
| `user_words.user_id` → `users.id`       | Внешний ключ | CASCADE                  |
| `learning_stats.user_id` → `users.id`   | Внешний ключ | CASCADE                  |

> `word_id` в `learning_stats` ссылается на `id` либо в `common_words`, либо в `user_words` (определяется по `word_type`).

## Установка

```powershell
pip install -r requerements.txt
```

## Запуск

```powershell
streamlit run main.py
```

## Подключение к БД

| Параметр   | Значение         |
|-----------|------------------|
| host      | localhost        |
| database  | EnglishCard      |
| user      | postgres         |
| password  | postgres         |
