"""
EnglishCard - Приложение для изучения английского языка

"""

import streamlit as st
import psycopg2
from pandas.core.interchange.dataframe_protocol import DataFrame
from psycopg2.errors import UniqueViolation
from psycopg2.extras import execute_values, DictCursorBase, RealDictCursor
import pandas as pd
import random


# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="EnglishCard - Изучение английского",
    page_icon="📚",
    layout="wide"
)
st.title("📚EnglishCard — Изучение английского")

st.markdown("""
### Привет 👋

Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном
для себя темпе.

У тебя есть возможность использовать тренажёр как конструктор и собирать свою
собственную базу для обучения. Для этого воспользуйся инструментами:

- ➕ добавить слово
- 🗑️ удалить слово

**Ну что, начнём ⬇️**
""")

# ============================================================
# РАБОТА С БАЗОЙ ДАННЫХ
# ============================================================

def get_db_connection():
    """
    Реализует подключение к PostgreSQL
    Параметры подключения:
    - host: localhost
    - database: english_card
    - user: postgres
    - password: postgres
    Возвращает сonn
    """
    conn = psycopg2.connect(database = 'EnglishCard', user = 'postgres', password = 'vik481623' ,host = 'localhost')
    return conn

#Создание подключения

conn = get_db_connection()

def init_database(conn):
    """
    Создает БД EnglishCard. Реализует создание таблиц, если они не существуют:
    1. users (id, username, created_at)
    2. common_words (id, russian_word, english_word, created_at)
    3. user_words (id, user_id, russian_word, english_word, created_at)
    4. learning_stats (id, user_id, word_id, word_type, correct_answers, total_attempts, last_reviewed)

    Заполняет таблицу common_words начальными словами
    """
    with conn.cursor() as cur:
        # cur.execute("""DROP TABLE IF EXISTS users CASCADE;
        # DROP TABLE IF EXISTS common_words CASCADE;
        # DROP TABLE IF EXISTS user_words CASCADE;
        # DROP TABLE IF EXISTS learning_stats CASCADE;""")
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username VARCHAR(40) UNIQUE NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now())""")
        cur.execute("""CREATE TABLE IF NOT EXISTS common_words(
        id SERIAL PRIMARY KEY,
        russian_word VARCHAR(100) NOT NULL,
        english_word VARCHAR (100) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE (russian_word,english_word))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS user_words (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        russian_word VARCHAR(100),
        english_word VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE(russian_word,english_word))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS learning_stats(
            id              SERIAL PRIMARY KEY,
            user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            word_id         INTEGER NOT NULL,
            word_type       VARCHAR(10) NOT NULL CHECK (word_type IN ('common', 'user')),
            correct_answers INTEGER NOT NULL DEFAULT 0,
            total_attempts  INTEGER NOT NULL DEFAULT 0,
            last_reviewed   TIMESTAMPTZ DEFAULT now(),
            UNIQUE (user_id, word_id, word_type))""")
        print("Таблицы успешно созданы")
        words = [
            ('she', 'она'),
            ('he', 'он'),
            ('they', 'они'),
            ('I', 'я'),
            ('you', 'ты'),
            ('red', 'красный'),
            ('white', 'белый'),
            ('blue', 'синий'),
            ('green', 'зелёный'),
            ('black', 'чёрный'),
        ]

        execute_values(cur, "INSERT INTO common_words (english_word, russian_word) "
                            "VALUES %s "
                            "ON CONFLICT (english_word, russian_word) DO NOTHING",words)
    conn.commit()
    print('Общие слова добавлены')

def login_user(username):
    """
    Реализует вход пользователя
    Если пользователь существует - возвращает его id
    Если нет - создает нового пользователя и возвращает его id
    """
    with conn.cursor() as cur:
        cur.execute("""SELECT id FROM users 
        WHERE username = %s;""",(username,))
        row = cur.fetchone()
        if row is not None:
            print("Пользователь уже существует")
            return row[0]
        cur.execute("""INSERT INTO users(username) VALUES (%s) RETURNING id;""",
                    (username,))
        new_id = cur.fetchone()[0]
    conn.commit()
    print("Пользователь добавлен")
    return new_id

def get_user_words(user_id):
    """
    Получает все слова пользователя (общие + персональные)
    Возвращает список словарей: [{'id': 1, 'russian_word': 'красный', 'english_word': 'red', 'word_type': 'common'}, ...]
    """
    with conn.cursor() as cur:
        cur.execute("""SELECT id,english_word,russian_word, 'user' AS word_type
                       FROM user_words
                       WHERE user_id = %s
                       UNION ALL
                       SELECT id,english_word,russian_word,'common' AS word_type
                       FROM common_words""",(user_id,)
                    )
        rows = cur.fetchall()

    return [{'id' : row[0],
             'english_word': row[1],
             'russian_word' : row[2],
             'word_type' : row[3],
             }
            for row in rows]


def add_personal_word(user_id, russian_word, english_word):
    """
    Добавляет персональное слово для пользователя
    Проверяет, нет ли уже такого слова
    Возвращает True/False
    """
    with conn.cursor() as cur:
        cur.execute("""SELECT 1 FROM common_words
                       WHERE  LOWER(english_word) = LOWER(%s)
                       UNION ALL
                       SELECT 2 FROM user_words
                       WHERE user_id = %s AND LOWER(english_word) = LOWER(%s)""",
                    (english_word, user_id,english_word))
        row = cur.fetchone()
        if row is not None:
            print('Слово уже существует')
            return False
        cur.execute("""INSERT INTO user_words(user_id,russian_word,english_word)
                       VALUES (%s,%s,%s)""",
                    (user_id,russian_word,english_word))
    conn.commit()
    return True


def delete_personal_word(user_id, word_id):
    """
    Удаляет персональное слово пользователя
    Возвращает True/False
    """
    with conn.cursor() as cur:
        cur.execute("""DELETE FROM user_words
                       WHERE user_id = %s AND id = %s""",
                    (user_id,word_id))
        deleted = cur.rowcount
    if deleted == 0:
        print("Слово для удаления отсутствует в базе")
        return False
    conn.commit()
    print("Слово успешно удалено")
    return True




def update_stats(user_id, word_id, word_type, is_correct):
    """
    Обновляет статистику изучения слова:
    - если записи для пары(user_id,word_id,word_type) нет - создает ее фиксируя одну попытку,
    -если запись есть - обновляет ее (total_attempts +1, если ответ корректный: is_correct +1)

    Args:
        -user_id
        -word_id
        -word_type
        -is_correct
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO learning_stats
                (user_id, word_id, word_type,
                 correct_answers, total_attempts, last_reviewed)
            VALUES (%s, %s, %s, %s, 1, now())
            ON CONFLICT (user_id, word_id, word_type) DO UPDATE
                SET total_attempts  = learning_stats.total_attempts + 1,
                    correct_answers = learning_stats.correct_answers
                                      + %s,
                    last_reviewed   = now()
            """,
            (
                user_id, word_id, word_type,
                1 if is_correct else 0,
                1 if is_correct else 0,
            ),
        )
    conn.commit()
    print("Статистика успешно обновлена")


def get_statistics(user_id):
    """
    Получает статистику пользователя
    Возвращает словарь со статистикой, где ключами выступают:
     user_id, word_id, word_type,correct_answers,total_attempts, last_reviewed

     Args:user_id
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT
                             ls.user_id, 
                             ls.word_id,
                             ls.word_type, 
                             ls.correct_answers, 
                             ls.total_attempts, 
                             ls.last_reviewed,
                             COALESCE (cw.english_word,uw.english_word) AS english_word,
                             COALESCE (cw.russian_word,uw.russian_word) AS russian_word
                             FROM learning_stats ls
                             LEFT JOIN common_words cw ON ls.word_type = 'common' AND ls.word_id = cw.id
                             LEFT JOIN user_words uw ON ls.word_type = 'user' AND ls.word_id = uw.id
                             WHERE ls.user_id = %s
                             ORDER BY ls.last_reviewed DESC""",(user_id,))
        rows = cur.fetchall()

    return  rows
#
# # ============================================================
# # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# # ============================================================
#
def generate_options(correct_word, all_words,n_option=4):
    """
    Генерирует 4 варианта ответа для викторины
    Один вариант - правильный перевод, остальные - случайные слова из словаря
    Если слов не хватает, добавляет слова-заглушки
    """
    pool = [w for w in all_words if (w["english_word"] != correct_word["english_word"])
            and not(w["word_type"] == correct_word["word_type"] and w["id"] == correct_word["id"])]
    k = n_option -1

    if len(pool) >= k:
        distractors = random.sample(pool, k=k)
    else:
        distractors = pool[:]
        # Добираем заглушками до нужного количества
        while len(distractors) < k:
            distractors.append({
                "id": None,
                "english_word": "",
                "russian_word": "—",
                "word_type": "dummy",
            })

    options = [correct_word] + distractors
    random.shuffle(options)
    return {"question":correct_word,"options" : options}

# # ============================================================
# # ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# # ============================================================
#
def render_sidebar():
    """
    Создает боковую панель с авторизацией
    - Поле для ввода имени
    - Кнопка входа
    - Приветствие после входа
    - Кнопка выхода
    """
    with st.sidebar:
        st.header("Авторизация")
        if "username" not in st.session_state:
            st.session_state.username = None
        if st.session_state.username is None:
            name = st.sidebar.text_input("Введите ваше имя:", key = "login_input")
            if st.button("Войти",key = "login_btn"):
                if not name.strip():
                    st.warning("Введите, пожалуйста, имя")

                else:
                    st.session_state.username = name.strip()
                    st.balloons()
                    st.rerun()
        else:
            st.success(f"Привет, {st.session_state.username}! 👋")
            st.caption("Добро пожаловать в EnglishCard")
            st.session_state.user_id = login_user(st.session_state.username)


            if st.button("Выйти", key="logout_btn"):
                st.session_state.username = None
                st.rerun()

    return st.session_state.username, st.session_state.user_id

def _new_study_round(user_id):
    """ Готовит раунд викторины:
    -Пул слов для изучения, если слов нет: выводит пользователю информационное сообщение
    -Выбор случайного слова для вопроса викторины
    -Подготовка опций для ответа на вопрос
     Arg: user_id """
    words = get_user_words(user_id)
    pool = [w for w in words if w.get('russian_word') and w.get('english_word')]
    if not pool:
        st.session_state.round_error = "Нет слов для изучения"
        return
    correct = random.choice(pool)
    round_data = generate_options(correct,words,4)
    st.session_state.study_round = round_data
    st.session_state.study_answered = None
    st.session_state.picked_id = None
    st.session_state.round_error = None


#
def render_study_tab(user_id):
    """
    Создает вкладку изучения слов:
    - Отображение текущего слова на русском
    - 4 кнопки с вариантами перевода
    - Обработка правильных/неправильных ответов
    - Кнопка следующего слова
    Обрабатывает ответ пользователя и обновляет статистику в БД и в st.session_state.

    """
    st.title("Изучение слов")

    if st.session_state.get("study_score") is None:
        st.session_state.study_score = 0
    if st.session_state.get("study_total") is None:
        st.session_state.study_total = 0
    if "study_round" not in st.session_state:
        _new_study_round(user_id)

    if st.session_state.get("study_error"):
        st.warning(st.session_state.study_error)

    round_data = st.session_state.study_round
    correct = round_data['question']
    options = round_data['options']
    answered = st.session_state.study_answered

    st.subheader (f'Как переводится **{correct["russian_word"]}**?')
    st.caption (f'Правильно {st.session_state.study_score} из {st.session_state.study_total}')

    for i,opt in enumerate(options):
        label = opt['english_word'] or "-"
        is_correct = (opt["id"] is not None and opt["id"] == correct["id"]and opt["word_type"] == correct["word_type"])

        if answered is None:
            if st.button(label, key=f'study_opt_{i}_{correct["id"]}_{correct["word_type"]}',use_container_width=True):
                if correct["word_type"] in ("common", "user"):
                    update_stats(
                        user_id,
                        correct["id"],
                        correct["word_type"],
                        is_correct,
                    )

                st.session_state.study_total += 1
                st.session_state.picked_id = opt["id"]

                if is_correct:
                    st.session_state.study_score += 1
                    st.session_state.study_answered = "correct"
                    st.rerun()
                else:
                    st.session_state.study_answered = "wrong"
                    st.rerun()
        else:
            if is_correct:
                st.success(f'{label} ✔')
            elif opt["id"] is not None and opt['id'] == st.session_state.picked_id:
                st.error(f'{label}✘')
            else:
                st.write(label)
    if answered == "correct":
        st.success("Верно!")
    elif answered == "wrong":
        st.error(f"Неверно! Правильный ответ {correct['english_word']}")
    if answered is not None:
        if st.button("Следующее слово", key="next"):
            _new_study_round(user_id)
            st.rerun()


def render_add_word_tab(user_id):
    """
    Создает вкладку добавления слова
    - Поле для ввода слова на русском
    - Поле для ввода перевода
    - Кнопка добавления
    - Уведомление об успешном добавлении
    Исключает ввод дублей, выводя пользователю сообщение, что введенное им слово уже существует

    """
    st.title("Добавление слова")

    msg = st.session_state.pop("add_flash",None)
    if msg:
        st.success("Слово успешно создано")
    if "form_version" not in st.session_state:
        st.session_state.form_version = 0
    v = st.session_state.form_version

    russian_word = st.text_input("Введите слово на русском:", key=f"add_ru{v}").strip()
    english_word = st.text_input("Введите слово на английском:",key=f"add_en{v}").strip()

    if st.button("Добавить слово",key="add_word_btn"):
        if not russian_word or not english_word:
            st.warning("Заполните оба поля")
        else:
            try:
                ok = add_personal_word(user_id,russian_word,english_word)
                if ok:
                    st.session_state.add_flash = "Слово успешно создано"
                    st.session_state.form_version += 1
                    st.rerun()
                else:
                    st.warning("Такое слово уже существует")
            except UniqueViolation:
                conn.rollback()
                st.warning("Такое слово уже есть в вашем словаре.")
            except Exception as e:
                conn.rollback()
                st.error(f"Не удалось добавить слово: {e}")


def render_delete_word_tab(user_id):
    """
    Создает вкладку удаления слова:
    - Выпадающий список с персональными словами пользователя
    - Кнопка удаления
    - Подтверждение удаления
    """
    st.title("Удаление персональных слов")

    msg = st.session_state.pop("delete_flash",None)
    if msg:
        st.success(msg)
    # if "delete_flash" in st.session_state:
    #     st.success(st.session_state.pop("delete_flash"))
    words = get_user_words(user_id)
    personal_words = [word for word in words if word['word_type'] == 'user']
    if not personal_words:
        st.info("У вас пока нет личных слов для удаления.")
        return

    selected_word = st.selectbox("Выберете слово для удаления:",options=personal_words,
                                 format_func=lambda w:f"{w['russian_word']}→{w['english_word']}")
    if selected_word:
        if st.button('Удалить слово',key="delete_word_btn"):
            st.session_state.delete_confirm_id= selected_word["id"]
            st.session_state.delete_confirm_label = (
                f"{selected_word['russian_word']} → {selected_word['english_word']}"
            )
            st.rerun()
        if "delete_confirm_id" in st.session_state:
            st.warning(f"Удалить слово {st.session_state.delete_confirm_label}?"
                       f" Действие нельзя отменить")
            col_yes,col_no = st.columns(2)
            with col_yes:
                if st.button("Да, удалить",key="yes_delete"):
                    try:
                        d = delete_personal_word(user_id,st.session_state.delete_confirm_id)
                        if d:
                            st.session_state.delete_flash = "Слово удалено."
                            st.session_state.pop("delete_confirm_id", None)
                            st.session_state.pop("delete_confirm_label", None)
                            st.rerun()
                        else:
                            "Слово не удалено"

                    except Exception as e:
                        st.error(f"Не удалось удалить слово: {e}")
            with col_no:
                if st.button("Отмена", key="delete_confirm_no"):
                    st.session_state.pop("delete_confirm_id", None)
                    st.session_state.pop("delete_confirm_label", None)
                    st.rerun()


def render_statistics_tab(user_id):
    """
    Создает вкладку статистики:
    - Количество изученных слов
    - Количество попыток
    - Процент правильных ответов
    - История последних попыток
    """
    st.title("Моя статистика")
    rows = get_statistics(user_id)
    if not rows:
        st.info("Пока нет статистики, приступите к изучению слов")
        return
    else:
        study_words = len(rows)
        total_attempts = sum(r["total_attempts"] for r in rows)
        correct_answers = sum(r["correct_answers"] for r in rows)
        percent = (round(correct_answers/total_attempts,1) if total_attempts > 0 else 0.0)
        col1,col2,col3 = st.columns(3)
        col1.metric("Изучено слов", study_words)
        col2.metric("Количество правильных ответов",correct_answers)
        col3.metric("Процент правильных ответов",f"{percent}%")
        st.subheader("Последние попытки")
        history = [
            {
                'слово': r['russian_word'],
                'перевод': r['english_word'],
                'верно' : r['correct_answers'],
                'всего' : r['total_attempts'],
                'когда' : (r ['last_reviewed'].strftime("%d.%m.%Y %H:%M")
                           if r['last_reviewed'] else "-")
            }
            for r in rows]
        st.dataframe(history, hide_index=True, use_container_width=True)

#
# def render_schema():
#     """
#     TODO: Реализовать отображение схемы базы данных (дополнительное требование)
#     """
#     pass
#
#
# # ============================================================
# # ГЛАВНАЯ ФУНКЦИЯ
# # ============================================================
#
def main():
    """
    Главная функция приложения
    Выполняет:
    1. Инициализацию схемы БД (таблицы + стартовый набор слов).
    2. Настройку состояния сессии Streamlit (user_id, username).
    3. Отрисовку боковой панели с формой авторизации.
    4. Основной контент:
       - для авторизованных — 4 вкладки (Изучение, Добавить, Удалить, Статистика);
       - для неавторизованных — приветственное сообщение с приглашением войти.

    Все данные о пользователе хранятся в st.session_state и переживают
    rerun Streamlit. Соединение с БД получается через get_db_connection(),
    во всех функциях используется глобального conn полученный в get_db_connection().

    """

    st.title("📚 EnglishCard - Изучай английский с удовольствием!")

    #  Инициализация состояния сессии

    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

    # Инициализация БД
    init_database(conn)

    # Боковая панель с авторизацией

    render_sidebar()

    # Основной контент в зависимости от авторизации
    if st.session_state.user_id:
        # Создание вкладок
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Изучение", "➕ Добавить слово", "🗑️ Удалить слово", "📊 Статистика"])
        with tab1:
            render_study_tab(st.session_state.user_id)
        with tab2:
            render_add_word_tab(st.session_state.user_id)
        with tab3:
            render_delete_word_tab(st.session_state.user_id)
        with tab4:
            render_statistics_tab(st.session_state.user_id)
    else:
        st.info("👋 Войдите или зарегистрируйтесь в боковой панели, чтобы начать учить слова.")


if __name__ == "__main__":
    main()


