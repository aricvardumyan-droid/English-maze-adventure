import arcade
import random
import time
import sqlite3
import os
import math
from typing import List, Tuple
from dataclasses import dataclass

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
SCREEN_TITLE = "English Maze Adventure"

SPRITE_SIZE = 64
GRID_PIXEL_SIZE = SPRITE_SIZE

PLAYER_SPEED = 280
ENEMY_SPEED = 120
NUM_LEVELS = 5
KEYS_PER_LEVEL = 5

GRAVITY = 0.8
JUMP_POWER = 22
MAX_JUMP_HEIGHT = 300
ON_GROUND_HEIGHT = 40

SOUND_ENABLED = True
FOOTSTEP_INTERVAL = 0.3

LEVEL_DIFFICULTY = {
    1: {"enemies": 1, "platforms": 5, "enemy_speed": ENEMY_SPEED},
    2: {"enemies": 2, "platforms": 5, "enemy_speed": ENEMY_SPEED * 1.2},
    3: {"enemies": 3, "platforms": 5, "enemy_speed": ENEMY_SPEED * 1.4},
    4: {"enemies": 4, "platforms": 5, "enemy_speed": ENEMY_SPEED * 1.6},
    5: {"enemies": 5, "platforms": 5, "enemy_speed": ENEMY_SPEED * 1.8},
}

BACKGROUND_COLOR = arcade.color.DARK_SLATE_GRAY
TEXT_COLOR = arcade.color.WHITE
BUTTON_NORMAL = arcade.color.STEEL_BLUE
BUTTON_HOVER = arcade.color.LIGHT_STEEL_BLUE
BUTTON_CLICKED = arcade.color.ROYAL_BLUE

ENGLISH_LEVELS = {
    "A1": "Beginner",
    "A2": "Elementary",
    "B1": "Intermediate",
    "B2": "Upper-Intermediate",
    "C1": "Advanced",
    "C2": "Proficiency"
}

LEVEL_SCORES = {
    "A1": 10,
    "A2": 20,
    "B1": 30,
    "B2": 40,
    "C1": 50,
    "C2": 60
}


def get_keys_text(keys_needed: int) -> str:
    if keys_needed % 10 == 1 and keys_needed % 100 != 11:
        return "ключ"
    elif 2 <= keys_needed % 10 <= 4 and (keys_needed % 100 < 10 or keys_needed % 100 >= 20):
        return "ключа"
    else:
        return "ключей"


@dataclass
class EnglishQuestion:
    id: str
    level: str
    question_type: str
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    hint: str


class PhysicsEngine:

    def __init__(self):
        self.gravity = GRAVITY
        self.damping = 0.9
        self.player_speed = PLAYER_SPEED
        self.player_width = 35
        self.player_height = 50

    def check_collision_with_walls(self, player_x, player_y, walls):
        player_left = player_x - self.player_width // 2
        player_right = player_x + self.player_width // 2
        player_bottom = player_y - self.player_height // 2
        player_top = player_y + self.player_height // 2

        for wall_x, wall_y, wall_width, wall_height in walls:
            # Границы стены
            wall_left = wall_x - wall_width // 2
            wall_right = wall_x + wall_width // 2
            wall_bottom = wall_y - wall_height // 2
            wall_top = wall_y + wall_height // 2

            if (player_right > wall_left and
                    player_left < wall_right and
                    player_top > wall_bottom and
                    player_bottom < wall_top):
                return True
        return False

    def check_collision_with_wall_sides(self, player_x, player_y, wall):
        wall_x, wall_y, wall_width, wall_height = wall

        player_left = player_x - self.player_width // 2
        player_right = player_x + self.player_width // 2
        player_bottom = player_y - self.player_height // 2
        player_top = player_y + self.player_height // 2

        wall_left = wall_x - wall_width // 2
        wall_right = wall_x + wall_width // 2
        wall_bottom = wall_y - wall_height // 2
        wall_top = wall_y + wall_height // 2

        overlap_left = player_right - wall_left
        overlap_right = wall_right - player_left
        overlap_top = wall_top - player_bottom
        overlap_bottom = player_top - wall_bottom

        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

        if min_overlap == overlap_left:
            return "left", overlap_left
        elif min_overlap == overlap_right:
            return "right", overlap_right
        elif min_overlap == overlap_top:
            return "top", overlap_top
        else:
            return "bottom", overlap_bottom

    def check_collision_with_walls_at(self, x, y, walls):
        return self.check_collision_with_walls(x, y, walls)

    def check_collision_with_platform(self, player_x, player_y, platform):
        player_left = player_x - self.player_width // 2
        player_right = player_x + self.player_width // 2
        player_bottom = player_y - self.player_height // 2
        player_top = player_y + self.player_height // 2

        left = platform.center_x - platform.width // 2
        right = platform.center_x + platform.width // 2
        bottom = platform.center_y - platform.height // 2
        top = platform.center_y + platform.height // 2

        return (player_right > left and
                player_left < right and
                player_top > bottom and
                player_bottom < top)

    def apply_gravity(self, velocity_y, on_ground, delta_time):
        if not on_ground:
            velocity_y -= self.gravity * delta_time * 60
            if velocity_y < -15:
                velocity_y = -15
        else:
            velocity_y = 0
        return velocity_y

    def apply_movement(self, player_x, player_y, dx, dy, walls, platforms, delta_time):
        if dx == 0 and dy == 0:
            return player_x, player_y, self.check_on_ground(player_x, player_y, platforms)

        move_speed = self.player_speed * delta_time

        new_x = player_x
        new_y = player_y

        if dx != 0:
            new_x = player_x + dx * move_speed
            if self.check_collision_with_walls(new_x, player_y, walls):
                new_x = player_x

        if dy != 0:
            new_y = player_y + dy * move_speed
            if self.check_collision_with_walls(player_x, new_y, walls):
                new_y = player_y

        on_ground = self.check_on_ground(new_x, new_y, platforms)

        if not on_ground and dy <= 0:
            if new_y < 45 + self.player_height // 2:
                new_y = 45 + self.player_height // 2
                on_ground = True

        return new_x, new_y, on_ground

    def check_on_ground(self, player_x, player_y, platforms):
        for platform in platforms:
            if self.check_collision_with_platform(player_x, player_y, platform):
                player_bottom = player_y - self.player_height // 2
                platform_top = platform.center_y + platform.height // 2

                if abs(player_bottom - platform_top) < 5:
                    return True
        return False


class PlayerDatabase:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.db_path = "data/player_progress.db"
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                current_level INTEGER DEFAULT 1,
                current_keys INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                english_level TEXT DEFAULT 'A1',
                games_played INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                wrong_answers INTEGER DEFAULT 0,
                sound_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS level_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                level_number INTEGER,
                completion_time REAL,
                stars INTEGER,
                keys_collected INTEGER,
                correct_answers INTEGER,
                FOREIGN KEY (player_id) REFERENCES players(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS high_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                level INTEGER NOT NULL,
                english_level TEXT,
                date_achieved TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS english_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_level TEXT NOT NULL,
                question_type TEXT NOT NULL,
                question_text TEXT NOT NULL,
                option1 TEXT NOT NULL,
                option2 TEXT NOT NULL,
                option3 TEXT NOT NULL,
                option4 TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                explanation TEXT NOT NULL,
                hint TEXT NOT NULL,
                difficulty INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_level_type ON english_questions(question_level, question_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_level ON english_questions(question_level)')

        conn.commit()
        conn.close()

        self.initialize_questions()

    def initialize_questions(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM english_questions')
        count = cursor.fetchone()[0]

        if count == 0:
            print("База данных вопросов пуста. Загружаем базовые вопросы...")
            self.load_sample_questions()
        else:
            print(f"В базе данных уже есть {count} вопросов.")

        conn.close()

    def load_sample_questions(self):
        sample_questions = []

        # A1 вопросы
        a1_questions = [
            ('A1', 'vocabulary', 'What is "apple" in Russian?', 'Яблоко', 'Банан', 'Апельсин', 'Груша', 'Яблоко',
             '"Apple" = яблоко', 'Common fruit', 1),
            ('A1', 'grammar', 'I ___ a student.', 'am', 'is', 'are', 'be', 'am', 'I am', 'First person', 1),
            ('A1', 'vocabulary', 'What color is "red"?', 'Красный', 'Синий', 'Зеленый', 'Желтый', 'Красный',
             'Red = красный', 'Primary color', 1),
            ('A1', 'vocabulary', 'What is "book" in Russian?', 'Книга', 'Тетрадь', 'Ручка', 'Стол', 'Книга',
             'Book = книга', 'You read it', 1),
            ('A1', 'grammar', 'She ___ a teacher.', 'am', 'is', 'are', 'be', 'is', 'She is', 'Third person', 1),
            ('A1', 'grammar', 'We ___ friends.', 'am', 'is', 'are', 'be', 'are', 'We are', 'Plural', 1),
            ('A1', 'vocabulary', 'What is "house" in Russian?', 'Дом', 'Квартира', 'Офис', 'Школа', 'Дом',
             'House = дом', 'Building', 1),
            ('A1', 'grammar', 'He ___ happy.', 'am', 'is', 'are', 'be', 'is', 'He is', 'Third person', 1),
            ('A1', 'vocabulary', 'What is "water" in Russian?', 'Вода', 'Сок', 'Молоко', 'Чай', 'Вода', 'Water = вода',
             'Essential', 1),
            ('A1', 'grammar', 'They ___ students.', 'am', 'is', 'are', 'be', 'are', 'They are', 'Plural', 1),
            ('A1', 'grammar', 'My name ___ John.', 'am', 'is', 'are', 'be', 'is', 'Name is', 'Third person', 1),
            ('A1', 'vocabulary', 'What is "dog" in Russian?', 'Собака', 'Кошка', 'Птица', 'Рыба', 'Собака',
             'Dog = собака', 'Pet', 1),
            ('A1', 'grammar', 'I ___ from London.', 'am', 'is', 'are', 'be', 'am', 'I am from', 'First person', 1),
            ('A1', 'vocabulary', 'What is "table" in Russian?', 'Стол', 'Стул', 'Кровать', 'Шкаф', 'Стол',
             'Table = стол', 'Furniture', 1),
            ('A1', 'grammar', 'It ___ a cat.', 'am', 'is', 'are', 'be', 'is', 'It is', 'Neutral', 1),
            ('A1', 'vocabulary', 'What is "pen" in Russian?', 'Ручка', 'Карандаш', 'Линейка', 'Ластик', 'Ручка',
             'Pen = ручка', 'Writing', 1),
            ('A1', 'grammar', 'You ___ welcome.', 'am', 'is', 'are', 'be', 'are', 'You are', 'Second person', 1),
            ('A1', 'vocabulary', 'What is "school" in Russian?', 'Школа', 'Университет', 'Библиотека', 'Больница',
             'Школа', 'School = школа', 'Education', 1),
            ('A1', 'grammar', 'The sky ___ blue.', 'am', 'is', 'are', 'be', 'is', 'Sky is', 'Third person', 1),
            ('A1', 'vocabulary', 'What is "computer" in Russian?', 'Компьютер', 'Телефон', 'Телевизор', 'Холодильник',
             'Компьютер', 'Computer = компьютер', 'Technology', 1),
            ('A1', 'grammar', 'I ___ 20 years old.', 'am', 'is', 'are', 'be', 'am', 'I am', 'Age', 1),
            ('A1', 'vocabulary', 'What is "mother" in Russian?', 'Мама', 'Папа', 'Сестра', 'Брат', 'Мама',
             'Mother = мама', 'Family', 1),
            ('A1', 'grammar', 'She ___ my sister.', 'am', 'is', 'are', 'be', 'is', 'She is', 'Family relation', 1),
            ('A1', 'vocabulary', 'What is "car" in Russian?', 'Машина', 'Автобус', 'Поезд', 'Самолет', 'Машина',
             'Car = машина', 'Transport', 1),
            ('A1', 'grammar', 'We ___ at home.', 'am', 'is', 'are', 'be', 'are', 'We are', 'Location', 1),
            ('A1', 'vocabulary', 'What is "friend" in Russian?', 'Друг', 'Враг', 'Коллега', 'Знакомый', 'Друг',
             'Friend = друг', 'Relationships', 1),
            ('A1', 'grammar', 'He ___ a doctor.', 'am', 'is', 'are', 'be', 'is', 'He is', 'Profession', 1),
            ('A1', 'vocabulary', 'What is "city" in Russian?', 'Город', 'Деревня', 'Страна', 'Улица', 'Город',
             'City = город', 'Geography', 1),
            ('A1', 'grammar', 'They ___ here.', 'am', 'is', 'are', 'be', 'are', 'They are', 'Location', 1),
            ('A1', 'vocabulary', 'What is "time" in Russian?', 'Время', 'Место', 'Деньги', 'Работа', 'Время',
             'Time = время', 'Concepts', 1),
            ('A1', 'grammar', 'I ___ hungry.', 'am', 'is', 'are', 'be', 'am', 'I am', 'Feeling', 1),
            ('A1', 'vocabulary', 'What is "money" in Russian?', 'Деньги', 'Время', 'Здоровье', 'Удача', 'Деньги',
             'Money = деньги', 'Finance', 1),
            ('A1', 'grammar', 'She ___ beautiful.', 'am', 'is', 'are', 'be', 'is', 'She is', 'Description', 1),
            ('A1', 'vocabulary', 'What is "work" in Russian?', 'Работа', 'Учеба', 'Отдых', 'Хобби', 'Работа',
             'Work = работа', 'Activity', 1),
            ('A1', 'grammar', 'You ___ right.', 'am', 'is', 'are', 'be', 'are', 'You are', 'Agreement', 1),
            ('A1', 'vocabulary', 'What is "day" in Russian?', 'День', 'Ночь', 'Утро', 'Вечер', 'День', 'Day = день',
             'Time', 1),
            ('A1', 'grammar', 'It ___ cold.', 'am', 'is', 'are', 'be', 'is', 'It is', 'Weather', 1),
            ('A1', 'vocabulary', 'What is "night" in Russian?', 'Ночь', 'День', 'Утро', 'Полдень', 'Ночь',
             'Night = ночь', 'Time', 1),
            ('A1', 'grammar', 'We ___ ready.', 'am', 'is', 'are', 'be', 'are', 'We are', 'State', 1),
            ('A1', 'vocabulary', 'What is "year" in Russian?', 'Год', 'Месяц', 'Неделя', 'День', 'Год', 'Year = год',
             'Time', 1),
            ('A1', 'grammar', 'He ___ tall.', 'am', 'is', 'are', 'be', 'is', 'He is', 'Description', 1),
            ('A1', 'vocabulary', 'What is "month" in Russian?', 'Месяц', 'Год', 'Неделя', 'День', 'Месяц',
             'Month = месяц', 'Time', 1),
            ('A1', 'grammar', 'They ___ busy.', 'am', 'is', 'are', 'be', 'are', 'They are', 'State', 1),
            ('A1', 'vocabulary', 'What is "week" in Russian?', 'Неделя', 'Месяц', 'Год', 'День', 'Неделя',
             'Week = неделя', 'Time', 1),
            ('A1', 'grammar', 'I ___ sorry.', 'am', 'is', 'are', 'be', 'am', 'I am', 'Apology', 1),
            ('A1', 'vocabulary', 'What is "hour" in Russian?', 'Час', 'Минута', 'Секунда', 'Время', 'Час', 'Hour = час',
             'Time', 1),
            ('A1', 'grammar', 'She ___ late.', 'am', 'is', 'are', 'be', 'is', 'She is', 'Time', 1),
            ('A1', 'vocabulary', 'What is "minute" in Russian?', 'Минута', 'Час', 'Секунда', 'День', 'Минута',
             'Minute = минута', 'Time', 1),
            ('A1', 'grammar', 'You ___ early.', 'am', 'is', 'are', 'be', 'are', 'You are', 'Time', 1),
            ('A1', 'vocabulary', 'What is "second" in Russian?', 'Секунда', 'Минута', 'Час', 'Время', 'Секунда',
             'Second = секунда', 'Time', 1),
        ]
        sample_questions.extend(a1_questions)

        # A2 вопросы
        a2_questions = [
            ('A2', 'grammar', 'They ___ watching TV now.', 'is', 'am', 'are', 'be', 'are', 'They are watching',
             'Present Continuous', 2),
            ('A2', 'vocabulary', 'Opposite of "big"?', 'Small', 'Large', 'Huge', 'Giant', 'Small', 'Small ≠ big',
             'Antonyms', 2),
            ('A2', 'grammar', 'I ___ to school every day.', 'go', 'goes', 'going', 'went', 'go', 'I go',
             'Present Simple', 2),
            ('A2', 'translation', 'How do you say "быстрый" in English?', 'Fast', 'Slow', 'Quickly', 'Rapid', 'Fast',
             'Fast = быстрый', 'Adjectives', 2),
            ('A2', 'grammar', 'She usually ___ coffee in the morning.', 'drink', 'drinks', 'drinking', 'drank',
             'drinks', 'She drinks', 'Third person s', 2),
            ('A2', 'grammar', 'I ___ reading a book.', 'am', 'is', 'are', 'be', 'am', 'I am reading',
             'Present Continuous', 2),
            ('A2', 'grammar', 'We ___ playing football.', 'am', 'is', 'are', 'be', 'are', 'We are playing',
             'Present Continuous', 2),
            ('A2', 'grammar', 'He ___ running fast.', 'am', 'is', 'are', 'be', 'is', 'He is running',
             'Present Continuous', 2),
            ('A2', 'vocabulary', 'What is the opposite of "hot"?', 'Cold', 'Warm', 'Cool', 'Freezing', 'Cold',
             'Cold ≠ hot', 'Temperature', 2),
            ('A2', 'grammar', 'I have ___ apple.', 'a', 'an', 'the', 'some', 'an', 'an before vowel', 'Articles', 2),
            ('A2', 'grammar', 'She ___ to music now.', 'listen', 'listens', 'listening', 'is listening', 'is listening',
             'Present Continuous', 'Now', 2),
            ('A2', 'vocabulary', 'What is the opposite of "day"?', 'Night', 'Morning', 'Evening', 'Afternoon', 'Night',
             'Night ≠ day', 'Time', 2),
            ('A2', 'grammar', 'They ___ dinner at 7 pm.', 'have', 'has', 'having', 'had', 'have', 'They have',
             'Present Simple', 2),
            ('A2', 'grammar', 'I ___ like coffee.', 'doesn\'t', 'don\'t', 'isn\'t', 'aren\'t', 'don\'t',
             'I don\'t like', 'Negation', 2),
            ('A2', 'vocabulary', 'What is "interesting" in Russian?', 'Интересный', 'Скучный', 'Сложный', 'Простой',
             'Интересный', 'Interesting = интересный', 'Adjectives', 2),
            ('A2', 'grammar', 'She ___ speak French.', 'can', 'could', 'should', 'would', 'can', 'She can',
             'Modal verbs', 2),
            ('A2', 'grammar', 'We ___ to the cinema yesterday.', 'go', 'went', 'going', 'gone', 'went', 'We went',
             'Past Simple', 2),
            ('A2', 'vocabulary', 'What is the opposite of "young"?', 'Old', 'New', 'Small', 'Big', 'Old', 'Old ≠ young',
             'Age', 2),
            ('A2', 'grammar', 'I ___ my homework every day.', 'do', 'does', 'doing', 'did', 'do', 'I do',
             'Present Simple', 2),
            ('A2', 'grammar', 'He ___ basketball well.', 'play', 'plays', 'playing', 'played', 'plays', 'He plays',
             'Third person s', 2),
            ('A2', 'grammar', 'They ___ English lessons.', 'have', 'has', 'having', 'had', 'have', 'They have',
             'Present Simple', 2),
            ('A2', 'vocabulary', 'What is "difficult" in Russian?', 'Сложный', 'Легкий', 'Интересный', 'Скучный',
             'Сложный', 'Difficult = сложный', 'Adjectives', 2),
            ('A2', 'grammar', 'I ___ want to go.', 'doesn\'t', 'don\'t', 'isn\'t', 'aren\'t', 'don\'t', 'I don\'t want',
             'Negation', 2),
            ('A2', 'vocabulary', 'What is the opposite of "good"?', 'Bad', 'Better', 'Best', 'Nice', 'Bad',
             'Bad ≠ good', 'Antonyms', 2),
            ('A2', 'grammar', 'She ___ breakfast at 8 am.', 'eat', 'eats', 'eating', 'ate', 'eats', 'She eats',
             'Third person s', 2),
            ('A2', 'grammar', 'We ___ swimming on weekends.', 'go', 'goes', 'going', 'went', 'go', 'We go',
             'Present Simple', 2),
            ('A2', 'vocabulary', 'What is "expensive" in Russian?', 'Дорогой', 'Дешевый', 'Красивый', 'Современный',
             'Дорогой', 'Expensive = дорогой', 'Adjectives', 2),
            ('A2', 'grammar', 'He ___ drive a car.', 'can', 'could', 'should', 'would', 'can', 'He can', 'Ability', 2),
            ('A2', 'grammar', 'They ___ their grandparents last week.', 'visit', 'visited', 'visiting', 'visits',
             'visited', 'They visited', 'Past Simple', 2),
            ('A2', 'vocabulary', 'What is the opposite of "rich"?', 'Poor', 'Wealthy', 'Happy', 'Sad', 'Poor',
             'Poor ≠ rich', 'Antonyms', 2),
            ('A2', 'grammar', 'I ___ understand you.', 'doesn\'t', 'don\'t', 'isn\'t', 'aren\'t', 'don\'t',
             'I don\'t understand', 'Negation', 2),
            ('A2', 'vocabulary', 'What is "beautiful" in Russian?', 'Красивый', 'Страшный', 'Большой', 'Маленький',
             'Красивый', 'Beautiful = красивый', 'Adjectives', 2),
            ('A2', 'grammar', 'She ___ a letter now.', 'write', 'writes', 'writing', 'is writing', 'is writing',
             'Present Continuous', 'Now', 2),
            ('A2', 'grammar', 'We ___ lunch together.', 'have', 'has', 'having', 'had', 'have', 'We have',
             'Present Simple', 2),
            ('A2', 'vocabulary', 'What is the opposite of "happy"?', 'Sad', 'Glad', 'Joyful', 'Excited', 'Sad',
             'Sad ≠ happy', 'Emotions', 2),
            ('A2', 'grammar', 'He ___ his room every Saturday.', 'clean', 'cleans', 'cleaning', 'cleaned', 'cleans',
             'He cleans', 'Third person s', 2),
            ('A2', 'grammar', 'They ___ in London last year.', 'live', 'lived', 'living', 'lives', 'lived',
             'They lived', 'Past Simple', 2),
            ('A2', 'vocabulary', 'What is "important" in Russian?', 'Важный', 'Неважный', 'Интересный', 'Скучный',
             'Важный', 'Important = важный', 'Adjectives', 2),
            ('A2', 'grammar', 'I ___ usually tired in the evening.', 'am', 'is', 'are', 'be', 'am', 'I am', 'Feeling',
             2),
            ('A2', 'vocabulary', 'What is the opposite of "begin"?', 'Finish', 'Start', 'Continue', 'Stop', 'Finish',
             'Finish ≠ begin', 'Verbs', 2),
            ('A2', 'grammar', 'She ___ shopping every Friday.', 'go', 'goes', 'going', 'went', 'goes', 'She goes',
             'Third person s', 2),
            ('A2', 'grammar', 'We ___ a new car last month.', 'buy', 'bought', 'buying', 'buys', 'bought', 'We bought',
             'Past Simple', 2),
            ('A2', 'vocabulary', 'What is "dangerous" in Russian?', 'Опасный', 'Безопасный', 'Интересный', 'Скучный',
             'Опасный', 'Dangerous = опасный', 'Adjectives', 2),
            ('A2', 'grammar', 'He ___ to work by bus.', 'go', 'goes', 'going', 'went', 'goes', 'He goes',
             'Third person s', 2),
            ('A2', 'grammar', 'They ___ to the beach yesterday.', 'go', 'went', 'going', 'gone', 'went', 'They went',
             'Past Simple', 2),
            ('A2', 'vocabulary', 'What is the opposite of "open"?', 'Close', 'Start', 'Begin', 'Enter', 'Close',
             'Close ≠ open', 'Verbs', 2),
            ('A2', 'grammar', 'I ___ a shower every morning.', 'take', 'takes', 'taking', 'took', 'take', 'I take',
             'Present Simple', 2),
            ('A2', 'grammar', 'She ___ her phone at home.', 'leave', 'left', 'leaving', 'leaves', 'left', 'She left',
             'Past Simple', 2),
            ('A2', 'vocabulary', 'What is "possible" in Russian?', 'Возможный', 'Невозможный', 'Интересный', 'Скучный',
             'Возможный', 'Possible = возможный', 'Adjectives', 2),
            ('A2', 'grammar', 'We ___ our friends tomorrow.', 'meet', 'meets', 'meeting', 'will meet', 'will meet',
             'We will meet', 'Future', 2),
        ]
        sample_questions.extend(a2_questions)

        # B1 вопросы
        b1_questions = [
            ('B1', 'grammar', 'If I ___ you, I would study more.', 'was', 'were', 'am', 'is', 'were',
             'Second conditional', 'Conditional', 3),
            ('B1', 'grammar', 'She has ___ to London.', 'been', 'gone', 'went', 'go', 'been', 'Has been',
             'Present Perfect', 3),
            ('B1', 'grammar', 'I ___ my keys yesterday.', 'lose', 'lost', 'losed', 'losing', 'lost', 'Past simple',
             'Irregular verbs', 3),
            ('B1', 'grammar', 'He ___ already eaten.', 'has', 'have', 'had', 'having', 'has', 'Has eaten',
             'Present Perfect', 3),
            ('B1', 'grammar', 'We ___ for 2 hours.', 'have waited', 'has waited', 'waiting', 'waited', 'have waited',
             'Have waited', 'Duration', 3),
            ('B1', 'grammar', 'By next year, I ___ English for 5 years.', 'will study', 'will have studied', 'studied',
             'study', 'will have studied', 'Future Perfect', 'Tenses', 3),
            ('B1', 'grammar', 'If it rains, we ___ cancel the picnic.', 'will', 'would', 'shall', 'should', 'will',
             'First conditional', 'Conditional', 3),
            ('B1', 'grammar', 'She wishes she ___ taller.', 'was', 'were', 'is', 'be', 'were', 'Wishes', 'Subjunctive',
             3),
            ('B1', 'grammar', 'I\'m used to ___ early.', 'wake up', 'waking up', 'woke up', 'woken up', 'waking up',
             'Used to + ing', 'Gerund', 3),
            ('B1', 'grammar', 'He ___ rather stay home.', 'would', 'will', 'shall', 'should', 'would', 'Would rather',
             'Preferences', 3),
            ('B1', 'grammar', 'The movie was ___ than I expected.', 'interesting', 'more interesting',
             'most interesting', 'interestinger', 'more interesting', 'Comparative', 'Adjectives', 3),
            ('B1', 'grammar', 'I ___ a car since 2010.', 'have had', 'had', 'have', 'has', 'have had',
             'Present Perfect', 'Duration', 3),
            ('B1', 'grammar', 'She ___ be here by now.', 'should', 'would', 'could', 'might', 'should',
             'Should for expectation', 'Modal verbs', 3),
            ('B1', 'grammar', 'If I had known, I ___ come.', 'would have', 'will have', 'would', 'will', 'would have',
             'Third conditional', 'Conditional', 3),
            ('B1', 'grammar', 'He asked me where ___ .', 'I live', 'do I live', 'did I live', 'I lived', 'I lived',
             'Reported speech', 'Indirect questions', 3),
            ('B1', 'grammar', 'By the time we arrived, they ___ .', 'had left', 'left', 'have left', 'leave',
             'had left', 'Past Perfect', 'Tenses', 3),
            ('B1', 'grammar', 'I look forward to ___ you.', 'see', 'seeing', 'saw', 'seen', 'seeing',
             'Look forward to + ing', 'Gerund', 3),
            ('B1', 'grammar', 'She\'s the woman ___ helped me.', 'which', 'who', 'whom', 'whose', 'who',
             'Relative clause', 'Pronouns', 3),
            ('B1', 'grammar', 'I wish I ___ more time.', 'have', 'had', 'has', 'having', 'had', 'Wishes', 'Subjunctive',
             3),
            ('B1', 'grammar', 'It\'s time we ___ .', 'leave', 'left', 'leaving', 'have left', 'left', 'It\'s time',
             'Subjunctive', 3),
            ('B1', 'grammar', 'I\'d rather you ___ that.', 'don\'t do', 'didn\'t do', 'won\'t do', 'not do',
             'didn\'t do', 'Would rather', 'Preferences', 3),
            ('B1', 'grammar', 'This is ___ book I\'ve ever read.', 'good', 'better', 'the best', 'best', 'the best',
             'Superlative', 'Adjectives', 3),
            ('B1', 'grammar', 'He ___ if he had more time.', 'will help', 'would help', 'helps', 'helped', 'would help',
             'Second conditional', 'Conditional', 3),
            ('B1', 'grammar', 'She\'s used to ___ in the city.', 'live', 'lives', 'living', 'lived', 'living',
             'Used to + ing', 'Gerund', 3),
            ('B1', 'grammar', 'I ___ you if I need help.', 'will call', 'would call', 'called', 'call', 'will call',
             'First conditional', 'Conditional', 3),
            ('B1', 'grammar', 'He suggested ___ to the cinema.', 'go', 'going', 'to go', 'went', 'going',
             'Suggest + ing', 'Gerund', 3),
            ('B1', 'grammar', 'If I were you, I ___ that.', 'won\'t do', 'wouldn\'t do', 'didn\'t do', 'don\'t do',
             'wouldn\'t do', 'Second conditional', 'Conditional', 3),
            ('B1', 'grammar', 'She ___ have told me earlier.', 'should', 'would', 'could', 'might', 'should',
             'Should for advice', 'Modal verbs', 3),
            ('B1', 'grammar', 'I regret ___ you.', 'tell', 'telling', 'to tell', 'told', 'telling', 'Regret + ing',
             'Gerund', 3),
            ('B1', 'grammar', 'He denied ___ the money.', 'take', 'taking', 'took', 'taken', 'taking', 'Deny + ing',
             'Gerund', 3),
            ('B1', 'grammar', 'I\'ll call you when I ___ home.', 'get', 'will get', 'got', 'getting', 'get',
             'Time clause', 'Tenses', 3),
            ('B1', 'grammar', 'She ___ the report by tomorrow.', 'finish', 'will finish', 'finishes',
             'will have finished', 'will have finished', 'Future Perfect', 'Tenses', 3),
            ('B1', 'grammar', 'If he ___ harder, he would pass.', 'studies', 'studied', 'study', 'will study',
             'studied', 'Second conditional', 'Conditional', 3),
            ('B1', 'grammar', 'I can\'t help ___ about it.', 'think', 'thinking', 'to think', 'thought', 'thinking',
             'Can\'t help + ing', 'Gerund', 3),
            ('B1', 'grammar', 'He admitted ___ wrong.', 'be', 'being', 'to be', 'been', 'being', 'Admit + ing',
             'Gerund', 3),
            ('B1', 'grammar', 'She avoided ___ him.', 'meet', 'meeting', 'to meet', 'met', 'meeting', 'Avoid + ing',
             'Gerund', 3),
            ('B1', 'grammar', 'I\'m considering ___ a new job.', 'look for', 'looking for', 'to look for', 'looked for',
             'looking for', 'Consider + ing', 'Gerund', 3),
            ('B1', 'grammar', 'He delayed ___ a decision.', 'make', 'making', 'to make', 'made', 'making',
             'Delay + ing', 'Gerund', 3),
            ('B1', 'grammar', 'She enjoys ___ novels.', 'read', 'reading', 'to read', 'reads', 'reading', 'Enjoy + ing',
             'Gerund', 3),
            ('B1', 'grammar', 'He finished ___ the report.', 'write', 'writing', 'to write', 'wrote', 'writing',
             'Finish + ing', 'Gerund', 3),
            ('B1', 'grammar', 'I imagine ___ there.', 'live', 'living', 'to live', 'lived', 'living', 'Imagine + ing',
             'Gerund', 3),
            ('B1', 'grammar', 'She mentioned ___ him before.', 'meet', 'meeting', 'to meet', 'met', 'meeting',
             'Mention + ing', 'Gerund', 3),
            ('B1', 'grammar', 'He missed ___ the train.', 'catch', 'catching', 'to catch', 'caught', 'catching',
             'Miss + ing', 'Gerund', 3),
            ('B1', 'grammar', 'I practice ___ English every day.', 'speak', 'speaking', 'to speak', 'spoke', 'speaking',
             'Practice + ing', 'Gerund', 3),
            ('B1', 'grammar', 'She quit ___ last year.', 'smoke', 'smoking', 'to smoke', 'smoked', 'smoking',
             'Quit + ing', 'Gerund', 3),
            ('B1', 'grammar', 'He recalled ___ her somewhere.', 'see', 'seeing', 'to see', 'saw', 'seeing',
             'Recall + ing', 'Gerund', 3),
            ('B1', 'grammar', 'I recommend ___ early.', 'book', 'booking', 'to book', 'booked', 'booking',
             'Recommend + ing', 'Gerund', 3),
            ('B1', 'grammar', 'She resented ___ treated unfairly.', 'be', 'being', 'to be', 'been', 'being',
             'Resent + ing', 'Gerund', 3),
            ('B1', 'grammar', 'He risked ___ his job.', 'lose', 'losing', 'to lose', 'lost', 'losing', 'Risk + ing',
             'Gerund', 3),
            ('B1', 'grammar', 'I suggest ___ a break.', 'take', 'taking', 'to take', 'took', 'taking', 'Suggest + ing',
             'Gerund', 3),
        ]
        sample_questions.extend(b1_questions)

        # B2 вопросы
        b2_questions = [
            ('B2', 'grammar', 'Had I known, I ___ helped.', 'would have', 'will have', 'would', 'will', 'would have',
             'Third conditional', 'Inversion', 4),
            ('B2', 'grammar', 'The report ___ by tomorrow.', 'will finish', 'will be finished', 'finishes', 'finished',
             'will be finished', 'Future Passive', 'Passive voice', 4),
            ('B2', 'grammar', 'I object ___ treated like a child.', 'to be', 'to being', 'being', 'be', 'to being',
             'Object to + ing', 'Gerund', 4),
            ('B2', 'grammar', 'Not only ___ late, but he also forgot the documents.', 'he was', 'was he', 'did he',
             'he did', 'was he', 'Inversion', 'Sentence structure', 4),
            ('B2', 'grammar', 'Had I ___ sooner, I could have prevented it.', 'act', 'acted', 'acting', 'action',
             'acted', 'Past Perfect', 'Conditional', 4),
            ('B2', 'grammar', 'I\'d rather you ___ here.', 'stay', 'stayed', 'staying', 'to stay', 'stayed',
             'Would rather', 'Subjunctive', 4),
            ('B2', 'grammar', 'It\'s high time we ___ a decision.', 'make', 'made', 'making', 'to make', 'made',
             'It\'s high time', 'Subjunctive', 4),
            ('B2', 'grammar', 'But for your help, I ___ succeeded.', 'wouldn\'t have', 'won\'t have', 'didn\'t have',
             'haven\'t', 'wouldn\'t have', 'But for', 'Conditional', 4),
            ('B2', 'grammar', '___ I you, I\'d accept the offer.', 'Was', 'Were', 'Am', 'Be', 'Were', 'Were I you',
             'Formal conditional', 4),
            ('B2', 'grammar', 'Little ___ she know what was coming.', 'did', 'does', 'do', 'has', 'did', 'Little did',
             'Inversion', 4),
            ('B2', 'grammar', 'Hardly ___ I arrived when it started raining.', 'had', 'have', 'did', 'was', 'had',
             'Hardly had', 'Inversion', 4),
            ('B2', 'grammar', 'No sooner ___ he left than the phone rang.', 'had', 'has', 'did', 'was', 'had',
             'No sooner had', 'Inversion', 4),
            ('B2', 'grammar', 'Under no circumstances ___ allowed.', 'smoking is', 'is smoking', 'smoking', 'smoke',
             'is smoking', 'Under no circumstances', 'Inversion', 4),
            ('B2', 'grammar', 'Only by working hard ___ succeed.', 'you can', 'can you', 'you will', 'will you',
             'can you', 'Only by', 'Inversion', 4),
            ('B2', 'grammar', 'Such ___ the situation that we had to act.', 'was', 'were', 'is', 'are', 'was',
             'Such was', 'Inversion', 4),
            ('B2', 'grammar', 'Never before ___ such beauty.', 'I saw', 'saw I', 'have I seen', 'I have seen',
             'have I seen', 'Never before', 'Inversion', 4),
            ('B2', 'grammar', 'Rarely ___ so disappointed.', 'have I been', 'I have been', 'was I', 'I was',
             'have I been', 'Rarely', 'Inversion', 4),
            ('B2', 'grammar', 'Not until later ___ realize the truth.', 'did I', 'I did', 'I', 'me', 'did I',
             'Not until', 'Inversion', 4),
            ('B2', 'grammar', 'So difficult ___ that few could solve it.', 'was the problem', 'the problem was',
             'were the problem', 'the problem were', 'was the problem', 'So difficult', 'Inversion', 4),
            ('B2', 'grammar', 'Only then ___ understand.', 'did I', 'I did', 'I', 'me', 'did I', 'Only then',
             'Inversion', 4),
            ('B2', 'grammar', 'Were I ___ time, I would help.', 'have', 'had', 'has', 'having', 'had', 'Were I',
             'Formal conditional', 4),
            ('B2', 'grammar', 'Should you ___ any problems, call me.', 'have', 'had', 'has', 'having', 'have',
             'Should you', 'Formal conditional', 4),
            ('B2', 'grammar', 'Had they ___ earlier, they would have caught the train.', 'left', 'leave', 'leaving',
             'leaves', 'left', 'Had they', 'Conditional perfect', 4),
            ('B2', 'grammar', 'Not for one moment ___ I believe him.', 'did', 'do', 'does', 'have', 'did',
             'Not for one moment', 'Inversion', 4),
            ('B2', 'grammar', 'At no time ___ aware of the danger.', 'was he', 'he was', 'were he', 'he were', 'was he',
             'At no time', 'Inversion', 4),
            ('B2', 'grammar', 'In no way ___ responsible.', 'is he', 'he is', 'are he', 'he are', 'he is', 'In no way',
             'Inversion', 4),
            ('B2', 'grammar', 'On no account ___ this door.', 'open you', 'you open', 'open', 'do you open',
             'do you open', 'On no account', 'Inversion', 4),
            ('B2', 'grammar', 'By no means ___ the best solution.', 'is this', 'this is', 'are this', 'this are',
             'this is', 'By no means', 'Inversion', 4),
            ('B2', 'grammar', 'Not a word ___ during the meeting.', 'did he say', 'he said', 'said he', 'he did say',
             'he said', 'Not a word', 'Inversion', 4),
            ('B2', 'grammar', 'Scarcely ___ when the phone rang.', 'had he arrived', 'he had arrived', 'arrived he',
             'he arrived', 'he had arrived', 'Scarcely', 'Inversion', 4),
            ('B2', 'grammar', 'Barely ___ when the storm started.', 'had we left', 'we had left', 'left we', 'we left',
             'we had left', 'Barely', 'Inversion', 4),
            ('B2', 'grammar', 'No way ___ that!', 'am I doing', 'I am doing', 'do I do', 'I do', 'I am doing', 'No way',
             'Inversion', 4),
            ('B2', 'grammar', 'In vain ___ to convince him.', 'did we try', 'we tried', 'tried we', 'we did try',
             'we tried', 'In vain', 'Inversion', 4),
            ('B2', 'grammar', 'Not once ___ consider our proposal.', 'did they', 'they did', 'they', 'them', 'they did',
             'Not once', 'Inversion', 4),
            ('B2', 'grammar', 'Only after months ___ the truth.', 'did we learn', 'we learned', 'learned we',
             'we did learn', 'we learned', 'Only after', 'Inversion', 4),
            ('B2', 'grammar', 'Only when it\'s too late ___ appreciate what we had.', 'do we', 'we do', 'we', 'us',
             'we do', 'Only when', 'Inversion', 4),
            ('B2', 'grammar', 'Only by chance ___ the mistake.', 'did we discover', 'we discovered', 'discovered we',
             'we did discover', 'we discovered', 'Only by chance', 'Inversion', 4),
            ('B2', 'grammar', 'Only through hard work ___ success.', 'can you achieve', 'you can achieve',
             'achieve you', 'you achieve', 'you can achieve', 'Only through', 'Inversion', 4),
            ('B2', 'grammar', 'Not only intelligent but also ___ .', 'hardworking is he', 'he is hardworking',
             'is he hardworking', 'hardworking he is', 'he is hardworking', 'Not only... but also',
             'Parallel structure', 4),
            ('B2', 'grammar', 'Neither the manager nor the employees ___ satisfied.', 'is', 'are', 'was', 'were', 'are',
             'Neither... nor', 'Subject-verb agreement', 4),
            ('B2', 'grammar', 'Either you or I ___ mistaken.', 'am', 'are', 'is', 'were', 'am', 'Either... or',
             'Subject-verb agreement', 4),
            ('B2', 'grammar', 'Not just the students but also the teacher ___ present.', 'was', 'were', 'are', 'is',
             'was', 'Not just... but also', 'Subject-verb agreement', 4),
            ('B2', 'grammar', 'Both the book and the movie ___ interesting.', 'is', 'are', 'was', 'were', 'are',
             'Both... and', 'Subject-verb agreement', 4),
            ('B2', 'grammar', 'No sooner said than ___ .', 'done', 'did', 'do', 'doing', 'done', 'No sooner... than',
             'Fixed expression', 4),
            ('B2', 'grammar', 'The more you practice, ___ you become.', 'better', 'the better', 'good', 'the good',
             'the better', 'The more... the better', 'Comparative', 4),
            ('B2', 'grammar', 'So quickly ___ that nobody noticed.', 'did he leave', 'he left', 'left he',
             'he did leave', 'he left', 'So quickly', 'Inversion', 4),
            ('B2', 'grammar', 'To such an extent ___ that we had to stop.', 'did he complain', 'he complained',
             'complained he', 'he did complain', 'he complained', 'To such an extent', 'Inversion', 4),
            ('B2', 'grammar', 'With no difficulty ___ the test.', 'did he pass', 'he passed', 'passed he',
             'he did pass', 'he passed', 'With no difficulty', 'Inversion', 4),
            ('B2', 'grammar', 'On no occasion ___ late.', 'has he been', 'he has been', 'been he', 'he been',
             'he has been', 'On no occasion', 'Inversion', 4),
            ('B2', 'grammar', 'Under no condition ___ this information.', 'should you share', 'you should share',
             'share you', 'you share', 'you should share', 'Under no condition', 'Inversion', 4),
        ]
        sample_questions.extend(b2_questions)

        # C1 вопросы
        c1_questions = [
            ('C1', 'grammar', '___ had he arrived than the phone rang.', 'No sooner', 'Hardly', 'Scarcely', 'Barely',
             'No sooner', 'No sooner... than', 'Inversion', 5),
            ('C1', 'grammar', 'Such ___ the complexity that few understood.', 'was', 'were', 'is', 'are', 'was',
             'Such was', 'Inversion', 5),
            ('C1', 'grammar', 'Were the situation ___, we\'d act differently.', 'to arise', 'arising', 'arose',
             'arisen', 'to arise', 'Were + to', 'Formal conditional', 5),
            ('C1', 'grammar', '___ be said that honesty is the best policy.', 'It may', 'It might', 'It can',
             'It could', 'It may', 'It may be said', 'Formal expression', 5),
            ('C1', 'grammar', 'Not until later ___ the full implications.', 'did he realize', 'he realized',
             'realized he', 'he did realize', 'he realized', 'Not until', 'Inversion', 5),
            ('C1', 'grammar', 'So compelling ___ that everyone listened.', 'was the argument', 'the argument was',
             'were the argument', 'the argument were', 'the argument was', 'So compelling', 'Inversion', 5),
            ('C1', 'grammar', 'Had it not been for the warning, disaster ___.', 'would have struck', 'will strike',
             'struck', 'strikes', 'would have struck', 'Had it not been', 'Conditional', 5),
            ('C1', 'grammar', 'Rarely ___ such dedication.', 'does one encounter', 'one encounters', 'encounters one',
             'one does encounter', 'one encounters', 'Rarely', 'Inversion', 5),
            ('C1', 'grammar', 'Under no circumstances ___ the deadline.', 'can we extend', 'we can extend',
             'extend we can', 'can extend we', 'we can extend', 'Under no circumstances', 'Inversion', 5),
            ('C1', 'grammar', 'Only by working together ___ solve this.', 'can we', 'we can', 'we will', 'will we',
             'we can', 'Only by', 'Inversion', 5),
            ('C1', 'grammar', 'Little ___ he suspect the truth.', 'did', 'does', 'do', 'has', 'did', 'Little did',
             'Inversion', 5),
            ('C1', 'grammar', 'So intense ___ that it became unbearable.', 'was the pressure', 'the pressure was',
             'were the pressure', 'the pressure were', 'the pressure was', 'So intense', 'Inversion', 5),
            ('C1', 'grammar', 'Never ___ such incompetence.', 'had I witnessed', 'I had witnessed', 'witnessed I',
             'I witnessed', 'I had witnessed', 'Never had', 'Inversion', 5),
            ('C1', 'grammar', 'Not for all the money in the world ___ that.', 'would I do', 'I would do', 'I do',
             'do I', 'I would do', 'Not for', 'Inversion', 5),
            ('C1', 'grammar', 'Only when it\'s too late ___ appreciate what we had.', 'do we', 'we do', 'we', 'us',
             'we do', 'Only when', 'Inversion', 5),
            ('C1', 'grammar', 'So convincing ___ that nobody doubted him.', 'was his story', 'his story was',
             'were his story', 'his story were', 'his story was', 'So convincing', 'Inversion', 5),
            ('C1', 'grammar', 'At no time ___ aware of the danger.', 'was he', 'he was', 'were he', 'he were', 'he was',
             'At no time', 'Inversion', 5),
            ('C1', 'grammar', 'Not once ___ consider the consequences.', 'did he', 'he did', 'he', 'him', 'he did',
             'Not once', 'Inversion', 5),
            ('C1', 'grammar', 'Only after years of study ___ master the technique.', 'did he', 'he did', 'he', 'him',
             'he did', 'Only after', 'Inversion', 5),
            ('C1', 'grammar', 'Such ___ his determination that failure was impossible.', 'was', 'were', 'is', 'are',
             'was', 'Such was', 'Inversion', 5),
            ('C1', 'grammar', 'Had I ___ to, I would have objected.', 'wanted', 'want', 'wants', 'wanting', 'wanted',
             'Had I wanted', 'Conditional perfect', 5),
            ('C1', 'grammar', 'Were he ___ , he would understand.', 'to know', 'know', 'knows', 'knowing', 'to know',
             'Were he to know', 'Formal conditional', 5),
            ('C1', 'grammar', 'Should there ___ any problems, contact us.', 'be', 'is', 'are', 'were', 'be',
             'Should there be', 'Formal conditional', 5),
            ('C1', 'grammar', 'Had the weather ___ better, we would have gone.', 'been', 'be', 'was', 'were', 'been',
             'Had the weather been', 'Conditional perfect', 5),
            ('C1', 'grammar', '___ we to succeed, it would be miraculous.', 'Were', 'Was', 'Are', 'Is', 'Were',
             'Were we to', 'Formal conditional', 5),
            ('C1', 'grammar', 'Not for the life of me ___ remember.', 'can I', 'I can', 'could I', 'I could', 'I can',
             'Not for the life of me', 'Inversion', 5),
            ('C1', 'grammar', 'In no uncertain terms ___ his disapproval.', 'did he express', 'he expressed',
             'expressed he', 'he did express', 'he expressed', 'In no uncertain terms', 'Inversion', 5),
            ('C1', 'grammar', 'By no stretch of the imagination ___ acceptable.', 'is this', 'this is', 'are this',
             'this are', 'this is', 'By no stretch', 'Inversion', 5),
            ('C1', 'grammar', 'On no account whatsoever ___ disturbed.', 'should he be', 'he should be', 'be he',
             'he be', 'he should be', 'On no account', 'Inversion', 5),
            ('C1', 'grammar', 'Under no circumstances whatever ___ tolerated.', 'will this be', 'this will be',
             'be this', 'this be', 'this will be', 'Under no circumstances', 'Inversion', 5),
            ('C1', 'grammar', 'Not a single word of apology ___ .', 'did he offer', 'he offered', 'offered he',
             'he did offer', 'he offered', 'Not a single word', 'Inversion', 5),
            ('C1', 'grammar', 'Scarcely a day goes by ___ I think of it.', 'that', 'when', 'which', 'where', 'that',
             'Scarcely... that', 'Inversion', 5),
            ('C1', 'grammar', 'Hardly anyone ___ the truth.', 'knows', 'know', 'knew', 'knowing', 'knows',
             'Hardly anyone', 'Inversion', 5),
            ('C1', 'grammar', 'Barely had the words ___ his lips when he regretted them.', 'left', 'leave', 'leaving',
             'leaves', 'left', 'Barely had', 'Inversion', 5),
            ('C1', 'grammar', 'No sooner had we ___ than the trouble started.', 'arrived', 'arrive', 'arriving',
             'arrives', 'arrived', 'No sooner had', 'Inversion', 5),
            ('C1', 'grammar', 'Only by a miracle ___ survived.', 'did they', 'they did', 'they', 'them', 'they did',
             'Only by a miracle', 'Inversion', 5),
            ('C1', 'grammar', 'Only through sheer determination ___ overcome.', 'did she', 'she did', 'she', 'her',
             'she did', 'Only through', 'Inversion', 5),
            ('C1', 'grammar', 'Only with great difficulty ___ persuaded.', 'was he', 'he was', 'were he', 'he were',
             'he was', 'Only with', 'Inversion', 5),
            ('C1', 'grammar', 'Only after much deliberation ___ a decision.', 'did we reach', 'we reached',
             'reached we', 'we did reach', 'we reached', 'Only after', 'Inversion', 5),
            ('C1', 'grammar', 'Only when all else fails ___ desperate measures.', 'do we resort to', 'we resort to',
             'resort we to', 'we do resort to', 'we resort to', 'Only when', 'Inversion', 5),
            ('C1', 'grammar', 'Not only did he fail, ___ made things worse.', 'but he also', 'also he', 'he also',
             'but also he', 'but he also', 'Not only... but also', 'Parallel structure', 5),
            ('C1', 'grammar', 'Neither here nor there ___ the matter.', 'is', 'are', 'was', 'were', 'is',
             'Neither... nor', 'Subject-verb agreement', 5),
            ('C1', 'grammar', 'Either now or never ___ chance.', 'is our', 'our is', 'are our', 'our are', 'is our',
             'Either... or', 'Subject-verb agreement', 5),
            ('C1', 'grammar', 'Both then and now ___ important.', 'it was', 'was it', 'it is', 'is it', 'it is',
             'Both... and', 'Tense agreement', 5),
            ('C1', 'grammar', 'No more no less ___ required.', 'is', 'are', 'was', 'were', 'is', 'No more no less',
             'Subject-verb agreement', 5),
            ('C1', 'grammar', 'The sooner the better ___ situation.', 'is the', 'the is', 'are the', 'the are',
             'is the', 'The sooner the better', 'Fixed expression', 5),
            ('C1', 'grammar', 'So be it ___ decided.', 'is', 'are', 'was', 'were', 'is', 'So be it', 'Fixed expression',
             5),
            ('C1', 'grammar', 'To cut a long story short ___ happened.', 'what', 'that', 'which', 'who', 'what',
             'To cut a long story short', 'Fixed expression', 5),
            ('C1', 'grammar', 'When all is said and done ___ matters.', 'what', 'that', 'which', 'who', 'what',
             'When all is said and done', 'Fixed expression', 5),
            ('C1', 'grammar', 'Last but not least ___ contribution.', 'his', 'him', 'he', 'himself', 'his',
             'Last but not least', 'Fixed expression', 5),
        ]
        sample_questions.extend(c1_questions)

        # C2 вопросы
        c2_questions = [
            ('C2', 'grammar', '___ he to apologize, I might reconsider.', 'Were', 'Was', 'Be', 'Being', 'Were',
             'Were he to', 'Formal conditional', 6),
            ('C2', 'grammar', 'So intricate ___ that it took years to decipher.', 'was the code', 'the code was',
             'were the code', 'the code were', 'the code was', 'So intricate', 'Inversion', 6),
            ('C2', 'grammar', 'Never before ___ such a spectacle.', 'had I witnessed', 'I had witnessed', 'witnessed I',
             'I witnessed', 'I had witnessed', 'Never before', 'Inversion', 6),
            ('C2', 'vocabulary', '___ the consequences, he proceeded anyway.', 'Notwithstanding', 'Despite', 'Although',
             'Whereas', 'Notwithstanding', 'Notwithstanding', 'Formal preposition', 6),
            ('C2', 'grammar', 'Little did they realize what ___ them.', 'awaited', 'awaiting', 'await', 'awaits',
             'awaited', 'What awaited', 'Past simple', 6),
            ('C2', 'grammar', 'Had I but known, ___ differently.', 'would I have acted', 'I would have acted',
             'I acted', 'I would act', 'I would have acted', 'Had I but known', 'Conditional', 6),
            ('C2', 'grammar', '___ they succeed remains to be seen.', 'Whether', 'If', 'That', 'What', 'Whether',
             'Whether they succeed', 'Formal clause', 6),
            ('C2', 'grammar', 'Such ___ his determination that failure was impossible.', 'was', 'were', 'is', 'are',
             'was', 'Such was', 'Inversion', 6),
            ('C2', 'vocabulary', '___ all efforts, the project failed.', 'Notwithstanding', 'Despite', 'Although',
             'Whereas', 'Notwithstanding', 'Notwithstanding', 'Formal preposition', 6),
            ('C2', 'grammar', 'Had circumstances ___ different, the outcome would vary.', 'been', 'be', 'being', 'are',
             'been', 'Had circumstances been', 'Conditional', 6),
            ('C2', 'grammar', 'So profound ___ that it changed everything.', 'was the impact', 'the impact was',
             'were the impact', 'the impact were', 'the impact was', 'So profound', 'Inversion', 6),
            ('C2', 'grammar', 'Never in my wildest dreams ___ imagine this.', 'could I have', 'I could have', 'I could',
             'could I', 'I could have', 'Never', 'Inversion', 6),
            ('C2', 'grammar', 'Only by sheer luck ___ survive.', 'did we', 'we did', 'we', 'us', 'we did', 'Only by',
             'Inversion', 6),
            ('C2', 'grammar', 'Not for one moment ___ doubt her.', 'did I', 'I did', 'I', 'me', 'I did',
             'Not for one moment', 'Inversion', 6),
            ('C2', 'grammar', 'So elaborate ___ that it seemed impossible.', 'was the plan', 'the plan was',
             'were the plan', 'the plan were', 'the plan was', 'So elaborate', 'Inversion', 6),
            ('C2', 'grammar', 'At no point ___ consider giving up.', 'did we', 'we did', 'we', 'us', 'we did',
             'At no point', 'Inversion', 6),
            ('C2', 'grammar', 'Only through perseverance ___ overcome.', 'can one', 'one can', 'one', 'ones', 'one can',
             'Only through', 'Inversion', 6),
            ('C2', 'grammar', 'Such ___ the mystery that it captivated all.', 'was', 'were', 'is', 'are', 'was',
             'Such was', 'Inversion', 6),
            ('C2', 'grammar', 'Had I the means, ___ differently.', 'would I act', 'I would act', 'I acted', 'I act',
             'I would act', 'Had I', 'Conditional', 6),
            ('C2', 'grammar', 'Not until the very end ___ the truth.', 'did they learn', 'they learned', 'learned they',
             'they did learn', 'they learned', 'Not until', 'Inversion', 6),
            ('C2', 'grammar', 'Were the truth ___ , it would shock everyone.', 'known', 'know', 'knows', 'knowing',
             'known', 'Were the truth known', 'Passive subjunctive', 6),
            ('C2', 'grammar', 'Should evidence ___ , we\'ll reconsider.', 'emerge', 'emerges', 'emerged', 'emerging',
             'emerge', 'Should evidence emerge', 'Formal conditional', 6),
            ('C2', 'grammar', 'Had permission ___ granted, we would have proceeded.', 'been', 'be', 'was', 'were',
             'been', 'Had permission been', 'Passive conditional', 6),
            ('C2', 'grammar', '___ the authorities to intervene, things might improve.', 'Were', 'Was', 'Are', 'Is',
             'Were', 'Were the authorities to', 'Formal conditional', 6),
            ('C2', 'grammar', 'Not for want of trying ___ succeed.', 'did he', 'he did', 'he', 'him', 'he did',
             'Not for want of trying', 'Inversion', 6),
            ('C2', 'grammar', 'In no way shape or form ___ acceptable.', 'is this', 'this is', 'are this', 'this are',
             'this is', 'In no way', 'Inversion', 6),
            ('C2', 'grammar', 'By no means whatsoever ___ justified.', 'was it', 'it was', 'were it', 'it were',
             'it was', 'By no means', 'Inversion', 6),
            ('C2', 'grammar', 'On no account under any circumstances ___ repeated.', 'should this be', 'this should be',
             'be this', 'this be', 'this should be', 'On no account', 'Inversion', 6),
            ('C2', 'grammar', 'Under no condition at any time ___ permitted.', 'will it be', 'it will be', 'be it',
             'it be', 'it will be', 'Under no condition', 'Inversion', 6),
            ('C2', 'grammar', 'Not a solitary soul ___ the answer.', 'knew', 'know', 'knows', 'knowing', 'knew',
             'Not a solitary soul', 'Inversion', 6),
            ('C2', 'grammar', 'Scarcely had a moment passed ___ he spoke again.', 'before', 'when', 'than', 'that',
             'before', 'Scarcely... before', 'Inversion', 6),
            ('C2', 'grammar', 'Hardly a soul ___ untouched by the news.', 'remained', 'remain', 'remains', 'remaining',
             'remained', 'Hardly a soul', 'Inversion', 6),
            ('C2', 'grammar', 'Barely a trace ___ of the original structure.', 'remains', 'remain', 'remained',
             'remaining', 'remains', 'Barely a trace', 'Inversion', 6),
            ('C2', 'grammar', 'No sooner had the thought ___ than he acted.', 'occurred', 'occur', 'occurs',
             'occurring', 'occurred', 'No sooner had', 'Inversion', 6),
            ('C2', 'grammar', 'Only by a stroke of genius ___ solution.', 'was the', 'the was', 'were the', 'the were',
             'was the', 'Only by a stroke', 'Inversion', 6),
            ('C2', 'grammar', 'Only through divine intervention ___ saved.', 'were they', 'they were', 'was they',
             'they was', 'they were', 'Only through', 'Inversion', 6),
            ('C2', 'grammar', 'Only with tremendous effort ___ accomplished.', 'was it', 'it was', 'were it', 'it were',
             'it was', 'Only with', 'Inversion', 6),
            ('C2', 'grammar', 'Only after exhaustive research ___ conclusions.', 'did we draw', 'we drew', 'drew we',
             'we did draw', 'we drew', 'Only after', 'Inversion', 6),
            ('C2', 'grammar', 'Only when hell freezes over ___ agree.', 'will I', 'I will', 'would I', 'I would',
             'I will', 'Only when', 'Inversion', 6),
            ('C2', 'grammar', 'Not only was he brilliant, ___ unparalleled.', 'but his insight was', 'his insight was',
             'was his insight', 'but was his insight', 'but his insight was', 'Not only... but also',
             'Parallel structure', 6),
            ('C2', 'grammar', 'Neither at the beginning nor at the end ___ mentioned.', 'was it', 'it was', 'were it',
             'it were', 'it was', 'Neither... nor', 'Subject-verb agreement', 6),
            ('C2', 'grammar', 'Either now or at some future date ___ addressed.', 'must this be', 'this must be',
             'be this', 'this be', 'this must be', 'Either... or', 'Modal inversion', 6),
            ('C2', 'grammar', 'Both in theory and in practice ___ valid.', 'it is', 'is it', 'it was', 'was it',
             'it is', 'Both... and', 'Tense agreement', 6),
            ('C2', 'grammar', 'No more no less than the truth ___ demanded.', 'is', 'are', 'was', 'were', 'is',
             'No more no less', 'Subject-verb agreement', 6),
            ('C2', 'grammar', 'The more things change, ___ they stay the same.', 'the more', 'more', 'most', 'the most',
             'the more', 'The more... the more', 'Comparative', 6),
            ('C2', 'grammar', 'So it goes ___ say.', 'needless to', 'need to', 'needs to', 'needed to', 'needless to',
             'So it goes', 'Fixed expression', 6),
            ('C2', 'grammar', 'To make a long story short ___ outcome.', 'the', 'that', 'what', 'which', 'the',
             'To make a long story short', 'Fixed expression', 6),
            ('C2', 'grammar', 'When push comes to shove ___ counts.', 'what', 'that', 'which', 'who', 'what',
             'When push comes to shove', 'Fixed expression', 6),
            ('C2', 'grammar', 'Last but by no means least ___ opinion.', 'her', 'she', 'hers', 'herself', 'her',
             'Last but not least', 'Fixed expression', 6),
            ('C2', 'grammar', 'All things considered ___ reasonable.', 'it seems', 'seems it', 'it seem', 'seem it',
             'it seems', 'All things considered', 'Fixed expression', 6),
        ]
        sample_questions.extend(c2_questions)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.executemany('''
            INSERT INTO english_questions 
            (question_level, question_type, question_text, option1, option2, option3, option4, correct_option, explanation, hint, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_questions)

        conn.commit()
        conn.close()
        print(f"Загружено {len(sample_questions)} вопросов в базу данных")

    def get_questions_by_level(self, level: str, limit: int = 50) -> List[EnglishQuestion]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, question_level, question_type, question_text, 
                   option1, option2, option3, option4, correct_option, explanation, hint
            FROM english_questions 
            WHERE question_level = ?
            ORDER BY RANDOM()
            LIMIT ?
        ''', (level, limit))

        questions = []
        for row in cursor.fetchall():
            question_id, question_level, question_type, question_text, \
                option1, option2, option3, option4, correct_option, explanation, hint = row

            questions.append(EnglishQuestion(
                id=str(question_id),
                level=question_level,
                question_type=question_type,
                question=question_text,
                options=[option1, option2, option3, option4],
                correct_answer=correct_option,
                explanation=explanation,
                hint=hint
            ))

        conn.close()
        return questions

    def add_question(self, question: EnglishQuestion):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO english_questions 
            (question_level, question_type, question_text, option1, option2, option3, option4, 
             correct_option, explanation, hint, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            question.level,
            question.question_type,
            question.question,
            question.options[0] if len(question.options) > 0 else '',
            question.options[1] if len(question.options) > 1 else '',
            question.options[2] if len(question.options) > 2 else '',
            question.options[3] if len(question.options) > 3 else '',
            question.correct_answer,
            question.explanation,
            question.hint,
            1
        ))

        conn.commit()
        conn.close()

    def create_or_update_player(self, username: str, english_level: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO players 
            (username, english_level, sound_enabled) 
            VALUES (?, ?, 1)
        ''', (username, english_level))

        conn.commit()
        conn.close()

    def get_player_sound_setting(self, username: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sound_enabled FROM players WHERE username = ?
        ''', (username,))

        result = cursor.fetchone()
        conn.close()

        return bool(result[0]) if result else True

    def update_player_sound_setting(self, username: str, enabled: bool):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE players SET sound_enabled = ? WHERE username = ?
        ''', (1 if enabled else 0, username))

        conn.commit()
        conn.close()

    def update_player_progress(self, username: str, level: int, keys: int, score: int,
                               correct: int = 0, wrong: int = 0):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE players 
            SET current_level = ?,
                current_keys = ?,
                total_score = total_score + ?,
                correct_answers = correct_answers + ?,
                wrong_answers = wrong_answers + ?,
                games_played = games_played + 1
            WHERE username = ?
        ''', (level, keys, score, correct, wrong, username))

        conn.commit()
        conn.close()

    def save_high_score(self, player_name: str, score: int, level: int, english_level: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO high_scores (player_name, score, level, english_level)
            VALUES (?, ?, ?, ?)
        ''', (player_name, score, level, english_level))

        conn.commit()
        conn.close()

    def get_high_scores(self, limit: int = 10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT player_name, score, level, english_level, date_achieved
            FROM high_scores 
            ORDER BY score DESC 
            LIMIT ?
        ''', (limit,))

        scores = cursor.fetchall()
        conn.close()
        return scores

    def clear_high_scores(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM high_scores')
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="high_scores"')

        conn.commit()
        conn.close()


class EnglishQuizSystem:
    def __init__(self):
        self.all_questions = []
        self.current_question = None
        self.used_questions_per_game = set()
        self.question_pool = {}
        self.question_cycle = 0
        self.level_questions_cache = {}

    def load_questions_from_database(self, level: str):
        print(f"Загрузка вопросов для уровня {level} из базы данных...")

        db = PlayerDatabase()

        questions = db.get_questions_by_level(level, limit=50)

        if not questions:
            print(f"Предупреждение: не найдено вопросов для уровня {level}. Загружаем резервные...")
            questions = self.create_backup_questions(level)

        print(f"Загружено {len(questions)} вопросов для уровня {level}")
        return questions

    def create_backup_questions(self, level: str):
        backup_questions = []

        base_questions = [
            EnglishQuestion(
                id=f"backup_{level}_1",
                level=level,
                question_type="vocabulary",
                question=f"What is 'hello' in Russian?",
                options=["Привет", "Пока", "Спасибо", "Извините"],
                correct_answer="Привет",
                explanation="Hello = привет",
                hint="Greeting"
            ),
            EnglishQuestion(
                id=f"backup_{level}_2",
                level=level,
                question_type="grammar",
                question=f"I ___ a student.",
                options=["am", "is", "are", "be"],
                correct_answer="am",
                explanation="I am",
                hint="First person"
            ),
        ]

        return base_questions

    def create_300_questions(self):
        print("Используется база данных для хранения вопросов. Метод create_300_questions не используется.")
        return []

    def create_a1_questions(self, count):
        return []

    def create_a2_questions(self, count):
        return []

    def create_b1_questions(self, count):
        return []

    def create_b2_questions(self, count):
        return []

    def create_c1_questions(self, count):
        return []

    def create_c2_questions(self, count):
        return []

    def initialize_game_questions(self, level: str):
        level_questions = self.load_questions_from_database(level)

        if level in self.level_questions_cache:
            all_level_questions = self.level_questions_cache[level][:]
        else:
            self.level_questions_cache[level] = level_questions[:]
            all_level_questions = level_questions

        random.shuffle(all_level_questions)

        if len(all_level_questions) >= 10:
            selected = all_level_questions[:10]
        else:
            selected = all_level_questions * (10 // len(all_level_questions) + 1)
            selected = selected[:10]

        self.question_pool = {}
        for i in range(5):
            if i * 2 < len(selected):
                main_q = selected[i * 2]
                backup_q = selected[i * 2 + 1] if i * 2 + 1 < len(selected) else selected[0]
                self.question_pool[i] = {
                    'main': main_q,
                    'backup': backup_q,
                    'attempts': 0,
                    'current_cycle': 0,
                    'used': False
                }

        self.used_questions_per_game = set()
        self.question_cycle = 0
        print(f"Инициализировано {len(self.question_pool)} пар вопросов для уровня {level}")

    def get_question_for_key(self, key_index: int):
        if key_index not in self.question_pool:
            print(f"Нет доступных вопросов для ключа {key_index}")
            return None

        pool_item = self.question_pool[key_index]

        if pool_item['used'] and pool_item['backup']:
            return pool_item['backup']
        elif pool_item['used']:
            return pool_item['main']

        pool_item['used'] = True
        return pool_item['main']

    def check_answer(self, answer: str) -> Tuple[bool, str]:
        if not self.current_question:
            return False, "No question selected"

        is_correct = answer == self.current_question.correct_answer
        return is_correct, self.current_question.explanation


class Button:
    def __init__(self, center_x, center_y, width, height, text, action=None, color=None, font_size=16):
        self.center_x = center_x
        self.center_y = center_y
        self.width = width
        self.height = height
        self.text = text
        self.action = action
        self.enabled = True
        self.state = "normal"
        self.custom_color = color
        self.font_size = font_size

    def draw(self):
        if self.custom_color:
            color = self.custom_color
        elif self.state == "normal":
            color = BUTTON_NORMAL
        elif self.state == "hover":
            color = BUTTON_HOVER
        else:
            color = BUTTON_CLICKED

        left = self.center_x - self.width / 2
        right = self.center_x + self.width / 2
        bottom = self.center_y - self.height / 2
        top = self.center_y + self.height / 2

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.WHITE, 2)

        arcade.draw_text(
            self.text,
            self.center_x,
            self.center_y,
            arcade.color.WHITE,
            self.font_size,
            align="center",
            anchor_x="center",
            anchor_y="center",
            width=self.width - 20
        )

    def check_hover(self, x, y):
        left = self.center_x - self.width / 2
        right = self.center_x + self.width / 2
        bottom = self.center_y - self.height / 2
        top = self.center_y + self.height / 2

        return left <= x <= right and bottom <= y <= top

    def on_click(self):
        if self.enabled and self.action:
            self.action()


class Door:
    def __init__(self, x, y, locked=True, door_id=0):
        self.center_x = x
        self.center_y = y
        self.locked = locked
        self.color = arcade.color.RED if locked else arcade.color.GREEN
        self.width = SPRITE_SIZE - 4
        self.height = SPRITE_SIZE - 4
        self.door_id = door_id
        self.open_progress = 0

    def draw(self):
        left = self.center_x - self.width / 2
        right = self.center_x + self.width / 2
        bottom = self.center_y - self.height / 2
        top = self.center_y + self.height / 2

        if self.open_progress > 0:
            right = left + (self.width * (1 - self.open_progress))

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, self.color)

        if self.locked:
            arcade.draw_text(
                "🔒",
                self.center_x,
                self.center_y,
                arcade.color.WHITE,
                20,
                align="center",
                anchor_x="center",
                anchor_y="center"
            )
        else:
            arcade.draw_text(
                "EXIT",
                self.center_x,
                self.center_y,
                arcade.color.WHITE,
                20,
                align="center",
                anchor_x="center",
                anchor_y="center"
            )

    def update(self, delta_time):
        if not self.locked and self.open_progress < 1:
            self.open_progress += delta_time * 2
            if self.open_progress > 1:
                self.open_progress = 1

    def open(self):
        self.locked = False
        self.color = arcade.color.GREEN


class Enemy:
    def __init__(self, x, y, enemy_id=0, speed=ENEMY_SPEED, level=1):
        self.center_x = x
        self.center_y = y
        self.color = random.choice([arcade.color.PURPLE, arcade.color.RED, arcade.color.ORANGE])
        self.width = 40
        self.height = 40
        self.speed = speed
        self.enemy_id = enemy_id
        self.wave_offset = 0

        self.patrol_path = self.generate_complex_patrol_path(x, y, level)
        self.current_target = 0
        self.target_x, self.target_y = self.patrol_path[self.current_target]

        self.time_at_target = 0
        self.time_to_stay = random.uniform(0.3, 1.0)
        self.rotation_angle = 0

    def generate_complex_patrol_path(self, start_x, start_y, level):
        path = []

        if level == 1:
            points = [
                (150, 600),
                (850, 600),
                (850, 200),
                (150, 200),
                (500, 400),
            ]
        elif level == 2:
            points = [
                (200, 650),
                (800, 650),
                (800, 150),
                (200, 150),
                (500, 400),
                (300, 300),
                (700, 300),
            ]
        else:
            points = [
                (100, 650),
                (900, 650),
                (900, 100),
                (100, 100),
                (500, 500),
                (300, 200),
                (700, 200),
                (500, 300),
            ]

        for point in points:
            x, y = point
            x = max(80, min(SCREEN_WIDTH - 80, x))
            y = max(80, min(SCREEN_HEIGHT - 80, y))
            path.append((x, y))

        return path

    def draw(self):
        wave_speed = 0.1
        self.wave_offset += wave_speed

        arcade.draw_circle_filled(self.center_x, self.center_y, 20, self.color)

        points = []
        for i in range(9):
            x_offset = -20 + i * 5
            y_offset = -10 + math.sin(self.wave_offset + i * 0.5) * 5
            points.append((self.center_x + x_offset, self.center_y + y_offset))

        points.append((self.center_x + 20, self.center_y - 10))
        points.append((self.center_x - 20, self.center_y - 10))

        arcade.draw_polygon_filled(points, self.color)

        eye_offset = math.sin(self.wave_offset) * 2
        arcade.draw_circle_filled(self.center_x - 6, self.center_y + 5 + eye_offset, 5, arcade.color.WHITE)
        arcade.draw_circle_filled(self.center_x + 6, self.center_y + 5 + eye_offset, 5, arcade.color.WHITE)
        arcade.draw_circle_filled(self.center_x - 6, self.center_y + 5 + eye_offset, 2, arcade.color.BLACK)
        arcade.draw_circle_filled(self.center_x + 6, self.center_y + 5 + eye_offset, 2, arcade.color.BLACK)

        arcade.draw_arc_filled(self.center_x, self.center_y - 5, 15, 8, arcade.color.BLACK, 0, 180)

    def update(self, player_x, player_y, delta_time):
        self.time_at_target += delta_time
        self.rotation_angle += delta_time * 0.5

        dx = self.target_x - self.center_x
        dy = self.target_y - self.center_y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance < 10:
            if self.time_at_target >= self.time_to_stay:
                self.current_target = (self.current_target + 1) % len(self.patrol_path)
                self.target_x, self.target_y = self.patrol_path[self.current_target]
                self.time_at_target = 0
                self.time_to_stay = random.uniform(0.3, 1.0)
        else:
            if distance > 0:
                dx_normalized = dx / distance
                dy_normalized = dy / distance

                speed_factor = 1.0
                current_speed = self.speed * speed_factor * delta_time

                self.center_x += dx_normalized * current_speed
                self.center_y += dy_normalized * current_speed

        self.center_x = max(40, min(SCREEN_WIDTH - 40, self.center_x))
        self.center_y = max(40, min(SCREEN_HEIGHT - 40, self.center_y))


class Platform:
    def __init__(self, x, y, width=100, height=20):
        self.center_x = x
        self.center_y = y
        self.width = width
        self.height = height
        self.color = arcade.color.DARK_GREEN

    def draw(self):
        left = self.center_x - self.width // 2
        right = self.center_x + self.width // 2
        bottom = self.center_y - self.height // 2
        top = self.center_y + self.height // 2

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, self.color)
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.GREEN, 2)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def create_explosion(self, x, y, color=arcade.color.GOLD, count=20):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 5)
            particle = {
                'x': x,
                'y': y,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'color': color,
                'life': 1.0,
                'size': random.uniform(2, 6)
            }
            self.particles.append(particle)

    def update(self, delta_time):
        for particle in self.particles[:]:
            particle['x'] += particle['dx']
            particle['y'] += particle['dy']
            particle['life'] -= delta_time
            particle['dy'] -= 0.1

            if particle['life'] <= 0:
                self.particles.remove(particle)

    def draw(self):
        for particle in self.particles:
            alpha = int(255 * particle['life'])
            color_with_alpha = (
                particle['color'][0],
                particle['color'][1],
                particle['color'][2],
                alpha
            )
            arcade.draw_circle_filled(
                particle['x'], particle['y'],
                particle['size'], color_with_alpha
            )


class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.music_player = None
        self.sound_enabled = True
        self.sound_volume = 0.5
        self.music_volume = 0.3
        self._initialized = False
        self._is_music_playing = False

    def initialize(self):
        if self._initialized:
            return

        try:
            print("Инициализация звуковой системы...")

            sound_files = {
                'button_click': ":resources:sounds/click2.wav",
                'jump': ":resources:sounds/jump3.wav",
                'collect': ":resources:sounds/coin1.wav",
                'correct': ":resources:sounds/coin5.wav",
                'wrong': ":resources:sounds/error2.wav",
                'victory': ":resources:sounds/win2.wav",
                'door_open': ":resources:sounds/upgrade1.wav",
                'enemy_hit': ":resources:sounds/hurt2.wav",
                'footstep': ":resources:sounds/rockHit2.wav",
            }

            for name, path in sound_files.items():
                try:
                    self.sounds[name] = arcade.load_sound(path)
                    print(f"Звук '{name}' загружен: {path}")
                except Exception as e:
                    print(f"Не удалось загрузить звук '{name}' ({path}): {e}")
                    self.sounds[name] = None

            try:
                music_path = ":resources:music/funkyrobot.mp3"
                self.sounds['background_music'] = arcade.load_sound(music_path)
                print(f"Фоновая музыка загружена: {music_path}")
            except Exception as e:
                print(f"Не удалось загрузить фоновую музыку: {e}")
                self.sounds['background_music'] = None

            self._initialized = True
            print(f"Звуковая система инициализирована. Загружено {len([s for s in self.sounds.values() if s])} звуков")

        except Exception as e:
            print(f"Критическая ошибка инициализации звука: {e}")
            self.sounds = {}
            self._initialized = True

    def play_sound(self, sound_name, volume=None):
        if not self.sound_enabled or not self._initialized:
            return None

        if sound_name not in self.sounds or self.sounds[sound_name] is None:
            print(f"Звук '{sound_name}' не доступен")
            return None

        try:
            vol = volume if volume is not None else self.sound_volume

            if sound_name == 'button_click':
                vol = 0.3
            elif sound_name == 'footstep':
                vol = 0.2
            elif sound_name == 'correct':
                vol = 0.6

            return arcade.play_sound(self.sounds[sound_name], volume=vol)
        except Exception as e:
            print(f"Ошибка воспроизведения '{sound_name}': {e}")
            return None

    def play_button_click(self):
        return self.play_sound('button_click')

    def play_background_music(self):
        if self._is_music_playing:
            print("Музыка уже играет, не запускаем повторно")
            return

        if not self.sound_enabled:
            return

        if 'background_music' in self.sounds and self.sounds['background_music']:
            try:
                print("Запуск фоновой музыки...")
                self.music_player = arcade.play_sound(
                    self.sounds['background_music'],
                    volume=self.music_volume,
                    loop=True
                )
                self._is_music_playing = True
                print("Фоновая музыка запущена")
            except Exception as e:
                print(f"Ошибка запуска музыки: {e}")
                self.music_player = None
                self._is_music_playing = False
        else:
            print("Фоновая музыка не доступна")

    def stop_background_music(self):
        if self.music_player:
            try:
                arcade.stop_sound(self.music_player)
                print("Фоновая музыка остановлена")
            except Exception as e:
                print(f"Ошибка остановки музыки: {e}")
            self.music_player = None
            self._is_music_playing = False

    def set_sound_enabled(self, enabled):
        old_enabled = self.sound_enabled
        self.sound_enabled = enabled

        if not enabled and old_enabled:
            self.stop_background_music()
        elif enabled and not old_enabled and not self._is_music_playing:
            self.play_background_music()


class MessageView(arcade.View):
    def __init__(self, game_view, message, button_text="OK"):
        super().__init__()
        self.game_view = game_view
        self.message = message
        self.button_text = button_text
        self.ok_button = None

    def on_show_view(self):
        self.ok_button = Button(
            SCREEN_WIDTH // 2, 150, 200, 50,
            self.button_text,
            self.return_to_game,
            arcade.color.GREEN
        )

    def return_to_game(self):
        self.window.show_view(self.game_view)

    def on_draw(self):
        self.clear()

        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (0, 0, 0, 200)
        )

        panel_width = 600
        panel_height = 300
        panel_x = SCREEN_WIDTH // 2
        panel_y = SCREEN_HEIGHT // 2

        left = panel_x - panel_width // 2
        right = panel_x + panel_width // 2
        bottom = panel_y - panel_height // 2
        top = panel_y + panel_height // 2

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (40, 40, 60, 240))
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.GOLD, 3)
        arcade.draw_text(
            "MESSAGE",
            panel_x, top - 40,
            arcade.color.GOLD, 28,
            align="center", anchor_x="center", anchor_y="center",
            bold=True
        )

        arcade.draw_text(
            self.message,
            panel_x, panel_y,
            arcade.color.WHITE, 20,
            align="center", anchor_x="center", anchor_y="center",
            width=panel_width - 40
        )

        self.ok_button.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        if self.ok_button.check_hover(x, y):
            self.ok_button.state = "hover"
        else:
            self.ok_button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.ok_button.check_hover(x, y):
                self.ok_button.on_click()


class StartView(arcade.View):
    def __init__(self, sound_manager=None):
        super().__init__()
        self.player_name = ""
        self.buttons = []
        self.selected_level = "A1"
        self.start_button = None
        self.name_field_active = False
        self.sound_manager = sound_manager

    def on_show_view(self):
        arcade.set_background_color(BACKGROUND_COLOR)
        self.setup_ui()

        if self.sound_manager and not self.sound_manager._is_music_playing:
            print("Запуск фоновой музыки в меню...")
            self.sound_manager.play_background_music()
        elif self.sound_manager:
            print("Музыка уже играет, не запускаем повторно")

    def setup_ui(self):
        self.buttons = []
        self.buttons.append(Button(
            SCREEN_WIDTH - 120, 60, 180, 40,
            "HIGH SCORES",
            self.show_high_scores_view,
            arcade.color.PURPLE
        ))

        button_width = 200
        button_height = 40
        levels = list(ENGLISH_LEVELS.keys())
        column_positions = [200, 500, 800]

        for i, level in enumerate(levels):
            column = i % 3
            row = i // 3
            x = column_positions[column]
            y = 350 - (row * 60)

            font_size = 14 if len(ENGLISH_LEVELS[level]) > 12 else 16
            button_color = None
            if level == self.selected_level:
                button_color = arcade.color.GREEN

            self.buttons.append(Button(
                x, y, button_width, button_height,
                f"{level} - {ENGLISH_LEVELS[level]}",
                lambda lvl=level: self.select_level(lvl),
                color=button_color,
                font_size=font_size
            ))

        self.start_button = Button(
            SCREEN_WIDTH // 2, 100, 200, 50,
            "START GAME",
            self.start_game,
            arcade.color.GREEN
        )
        self.start_button.enabled = False

    def show_high_scores_view(self):
        if self.sound_manager:
            self.sound_manager.play_button_click()
        high_scores_view = HighScoresView(self)
        self.window.show_view(high_scores_view)

    def select_level(self, level):
        if self.sound_manager:
            self.sound_manager.play_button_click()
        self.selected_level = level
        self.update_start_button()
        for button in self.buttons:
            if button.text.startswith(f"{level} -"):
                button.custom_color = arcade.color.GREEN
            elif button.text.startswith(tuple(ENGLISH_LEVELS.keys())):
                button.custom_color = None

    def update_start_button(self):
        if not self.start_button:
            return
        self.start_button.enabled = bool(self.player_name.strip() and self.selected_level)

    def start_game(self):
        if self.start_button.enabled:
            try:
                if self.sound_manager:
                    self.sound_manager.play_button_click()
                else:
                    print("Внимание: sound_manager не установлен!")

                level_intro_view = LevelIntroView(
                    self.player_name,
                    self.selected_level,
                    self.sound_manager
                )
                self.window.show_view(level_intro_view)
            except Exception as e:
                print(f"Error starting game: {e}")
                import traceback
                traceback.print_exc()

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (20, 20, 40)
        )

        for i in range(30):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            arcade.draw_circle_filled(x, y, size, (brightness, brightness, brightness))

        self.draw_main_interface()

    def draw_main_interface(self):
        arcade.draw_text(
            "ENGLISH MAZE ADVENTURE",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 80,
            arcade.color.GOLD,
            40,
            align="center",
            anchor_x="center",
            anchor_y="center",
            bold=True
        )

        arcade.draw_text(
            "Learn English through puzzle solving",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 130,
            arcade.color.LIGHT_BLUE,
            20,
            align="center",
            anchor_x="center",
            anchor_y="center"
        )

        arcade.draw_text(
            "STEP 1: ENTER YOUR NAME",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 190,
            arcade.color.WHITE,
            22,
            align="center",
            anchor_x="center",
            anchor_y="center"
        )

        name_y = SCREEN_HEIGHT - 240
        name_rect_width = 400
        name_rect_height = 40

        left = SCREEN_WIDTH // 2 - name_rect_width // 2
        right = SCREEN_WIDTH // 2 + name_rect_width // 2
        bottom = name_y - name_rect_height // 2
        top = name_y + name_rect_height // 2

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (30, 30, 40, 255))

        border_color = arcade.color.STEEL_BLUE if self.name_field_active else arcade.color.DARK_SLATE_GRAY
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, border_color, 3)

        name_display = self.player_name if self.player_name else "Click here and type your name..."
        name_color = arcade.color.WHITE if self.player_name else arcade.color.GRAY

        arcade.draw_text(
            name_display,
            SCREEN_WIDTH // 2,
            name_y,
            name_color,
            20,
            align="center",
            anchor_x="center",
            anchor_y="center",
            width=name_rect_width - 20
        )

        arcade.draw_text(
            "STEP 2: SELECT YOUR ENGLISH LEVEL",
            SCREEN_WIDTH // 2,
            430,
            arcade.color.WHITE,
            22,
            align="center",
            anchor_x="center",
            anchor_y="center"
        )

        current_text = f"SELECTED: {self.selected_level} - {ENGLISH_LEVELS[self.selected_level]}"
        arcade.draw_text(
            current_text,
            SCREEN_WIDTH // 2,
            400,
            arcade.color.LIGHT_BLUE,
            20,
            align="center",
            anchor_x="center",
            anchor_y="center"
        )

        for button in self.buttons:
            button.draw()

        if self.start_button:
            if not self.start_button.enabled and self.player_name:
                arcade.draw_text(
                    "⚠ Please select your English level!",
                    SCREEN_WIDTH // 2,
                    180,
                    arcade.color.RED,
                    16,
                    align="center",
                    anchor_x="center",
                    anchor_y="center"
                )

            self.start_button.draw()

        arcade.draw_text(
            "Press ENTER to start | Press ESC to exit | Use mouse to select",
            SCREEN_WIDTH // 2,
            30,
            arcade.color.LIGHT_GRAY,
            14,
            align="center",
            anchor_x="center",
            anchor_y="center"
        )

    def on_mouse_motion(self, x, y, dx, dy):
        for button in self.buttons:
            if button.check_hover(x, y):
                button.state = "hover"
            else:
                button.state = "normal"

        if self.start_button:
            if self.start_button.check_hover(x, y):
                self.start_button.state = "hover"
            else:
                self.start_button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.sound_manager:
                self.sound_manager.play_button_click()

            name_rect_center_y = SCREEN_HEIGHT - 240
            name_rect_width = 400
            name_rect_height = 40

            left = SCREEN_WIDTH // 2 - name_rect_width // 2
            right = SCREEN_WIDTH // 2 + name_rect_width // 2
            bottom = name_rect_center_y - name_rect_height // 2
            top = name_rect_center_y + name_rect_height // 2

            if left <= x <= right and bottom <= y <= top:
                self.name_field_active = True
                if not self.player_name:
                    self.player_name = ""
            else:
                self.name_field_active = False

            for btn in self.buttons:
                if btn.check_hover(x, y):
                    btn.on_click()

            if self.start_button and self.start_button.check_hover(x, y):
                self.start_button.on_click()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            arcade.close_window()
        elif symbol == arcade.key.ENTER and self.start_button.enabled:
            if self.sound_manager:
                self.sound_manager.play_button_click()
            self.start_game()
        elif self.name_field_active:
            if symbol == arcade.key.BACKSPACE:
                self.player_name = self.player_name[:-1]
                self.update_start_button()
            elif symbol == arcade.key.SPACE:
                if len(self.player_name) < 20:
                    self.player_name += " "
                    self.update_start_button()
            elif symbol >= arcade.key.A and symbol <= arcade.key.Z:
                if len(self.player_name) < 20:
                    char = chr(symbol)
                    if modifiers & arcade.key.MOD_SHIFT:
                        self.player_name += char.upper()
                    else:
                        self.player_name += char.lower()
                    self.update_start_button()


class LevelIntroView(arcade.View):
    def __init__(self, player_name, english_level, sound_manager):
        super().__init__()
        self.player_name = player_name
        self.english_level = english_level
        self.start_button = None
        self.sound_manager = sound_manager

    def on_show_view(self):
        arcade.set_background_color(BACKGROUND_COLOR)
        self.start_button = Button(
            SCREEN_WIDTH // 2, 100, 200, 50,
            "START LEVEL",
            self.start_game,
            arcade.color.GREEN
        )

    def start_game(self):
        self.sound_manager.play_button_click()
        game_view = GameView()
        game_view.setup(self.player_name, self.english_level, self.sound_manager)
        self.window.show_view(game_view)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (20, 20, 40)
        )

        for i in range(30):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            arcade.draw_circle_filled(x, y, size, (brightness, brightness, brightness))

        arcade.draw_lrbt_rectangle_filled(
            100, SCREEN_WIDTH - 100,
            50, SCREEN_HEIGHT - 50,
            (30, 30, 50, 240)
        )

        arcade.draw_lrbt_rectangle_outline(
            100, SCREEN_WIDTH - 100,
            50, SCREEN_HEIGHT - 50,
            arcade.color.GOLD, 3
        )

        arcade.draw_text(
            "LEVEL 1",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 100,
            arcade.color.GOLD,
            40,
            align="center",
            anchor_x="center",
            anchor_y="center",
            bold=True
        )

        arcade.draw_text(
            f"Welcome, {self.player_name}!",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 140,
            arcade.color.LIGHT_BLUE,
            28,
            align="center",
            anchor_x="center",
            anchor_y="center"
        )

        instructions = [
            "GAME OBJECTIVES:",
            "1. Answer 5 English questions to get 5 keys",
            "2. Avoid purple ghosts - they reset the level!",
            "3. Find question stations (marked with '?')",
            "4. Use SPACE to jump on platforms",
            "5. Use 5 keys to open the final door to exit",
            "",
            "ENGLISH QUESTIONS:",
            f"• Questions will be at {self.english_level} level",
            "• Answer correctly to get a key immediately",
            "• Questions can be answered in any order",
            "",
            "CONTROLS:",
            "• WASD or Arrow Keys to move",
            "• SPACE to jump",
            "• P to pause the game",
            "• ESC to return to menu",
        ]

        start_y = SCREEN_HEIGHT - 190
        for i, instruction in enumerate(instructions):
            color = arcade.color.GOLD if instruction.startswith("GAME") or instruction.startswith(
                "ENGLISH") or instruction.startswith("CONTROLS") else arcade.color.WHITE
            size = 16 if instruction.startswith("GAME") or instruction.startswith("ENGLISH") or instruction.startswith(
                "CONTROLS") else 14

            arcade.draw_text(
                instruction,
                SCREEN_WIDTH // 2,
                start_y - i * 22,
                color,
                size,
                align="center",
                anchor_x="center",
                anchor_y="center"
            )

        self.start_button.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        if self.start_button.check_hover(x, y):
            self.start_button.state = "hover"
        else:
            self.start_button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.sound_manager.play_button_click()
            if self.start_button.check_hover(x, y):
                self.start_button.on_click()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            if self.sound_manager:
                self.sound_manager.play_button_click()
            start_view = StartView()
            self.window.show_view(start_view)
        elif symbol == arcade.key.ENTER:
            if self.sound_manager:
                self.sound_manager.play_button_click()
            self.start_game()


class HighScoresView(arcade.View):
    def __init__(self, previous_view):
        super().__init__()
        self.previous_view = previous_view
        self.back_button = None
        self.clear_button = None
        self.sound_manager = previous_view.sound_manager

    def on_show_view(self):
        arcade.set_background_color(BACKGROUND_COLOR)
        self.back_button = Button(
            SCREEN_WIDTH // 2, 80, 220, 50,
            "BACK TO MENU",
            self.go_back,
            arcade.color.RED
        )
        self.clear_button = Button(
            SCREEN_WIDTH // 2, 140, 220, 50,
            "🗑️ CLEAR SCORES",
            self.clear_scores,
            arcade.color.ORANGE
        )

    def go_back(self):
        if self.sound_manager:
            self.sound_manager.play_button_click()

        self.window.show_view(self.previous_view)

    def clear_scores(self):
        if self.sound_manager:
            self.sound_manager.play_button_click()
        try:
            db = PlayerDatabase()
            db.clear_high_scores()
        except Exception as e:
            print(f"Error clearing scores: {e}")

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (20, 20, 40)
        )

        for i in range(30):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            arcade.draw_circle_filled(x, y, size, (brightness, brightness, brightness))

        arcade.draw_lrbt_rectangle_filled(
            150, SCREEN_WIDTH - 150,
            80, SCREEN_HEIGHT - 80,
            (30, 30, 50, 240)
        )

        arcade.draw_lrbt_rectangle_outline(
            150, SCREEN_WIDTH - 150,
            80, SCREEN_HEIGHT - 80,
            arcade.color.GOLD, 3
        )

        arcade.draw_text(
            "🏆 HIGH SCORES 🏆",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 120,
            arcade.color.GOLD,
            32,
            align="center",
            anchor_x="center",
            anchor_y="center",
            bold=True
        )

        try:
            db = PlayerDatabase()
            scores = db.get_high_scores(10)
        except:
            scores = []

        if not scores:
            arcade.draw_text(
                "No scores yet! Be the first!",
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 2,
                arcade.color.WHITE,
                22,
                align="center",
                anchor_x="center",
                anchor_y="center"
            )
        else:
            headers = ["Rank", "Player", "Score", "Level", "English"]
            header_y = SCREEN_HEIGHT - 170
            column_positions = [180, 320, 460, 580, 700]

            for i, header in enumerate(headers):
                x = column_positions[i]
                arcade.draw_text(
                    header,
                    x,
                    header_y,
                    arcade.color.CYAN,
                    16,
                    align="center",
                    anchor_x="center",
                    anchor_y="center",
                    bold=True
                )

            for rank, (player_name, score, level, eng_level, date) in enumerate(scores, 1):
                y = header_y - (rank * 35)

                row_color = arcade.color.WHITE
                if rank == 1:
                    row_color = arcade.color.GOLD
                elif rank == 2:
                    row_color = arcade.color.SILVER
                elif rank == 3:
                    row_color = arcade.color.BRONZE

                if isinstance(player_name, str):
                    display_name = player_name[:10] + "..." if len(player_name) > 10 else player_name
                else:
                    display_name = str(player_name)

                display_level = eng_level[:3] if eng_level else "A1"

                arcade.draw_text(str(rank), column_positions[0], y, row_color, 14, align="center", anchor_x="center")
                arcade.draw_text(display_name, column_positions[1], y, row_color, 14, align="center", anchor_x="center")
                arcade.draw_text(str(score), column_positions[2], y, row_color, 14, align="center", anchor_x="center")
                arcade.draw_text(str(level), column_positions[3], y, row_color, 14, align="center", anchor_x="center")
                arcade.draw_text(display_level, column_positions[4], y, row_color, 14, align="center",
                                 anchor_x="center")

        self.back_button.draw()
        self.clear_button.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        if self.back_button.check_hover(x, y):
            self.back_button.state = "hover"
        else:
            self.back_button.state = "normal"

        if self.clear_button.check_hover(x, y):
            self.clear_button.state = "hover"
        else:
            self.clear_button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.sound_manager:
                self.sound_manager.play_button_click()
            if self.back_button.check_hover(x, y):
                self.back_button.on_click()
            elif self.clear_button.check_hover(x, y):
                self.clear_button.on_click()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            self.go_back()


class VictoryView(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        self.confetti_particles = []
        self.smiling_player_y = 300
        self.player_wave_offset = 0
        self.message_alpha = 0
        self.timer = 0
        self.next_level_button = None

    def on_show_view(self):
        for _ in range(200):
            self.confetti_particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'dx': random.uniform(-3, 3),
                'dy': random.uniform(-5, -1),
                'color': random.choice([
                    arcade.color.RED, arcade.color.GREEN, arcade.color.BLUE,
                    arcade.color.YELLOW, arcade.color.PURPLE, arcade.color.ORANGE,
                    arcade.color.PINK, arcade.color.CYAN, arcade.color.LIME
                ]),
                'size': random.uniform(4, 8),
                'rotation': random.uniform(0, 360),
                'rotation_speed': random.uniform(-5, 5)
            })

        arcade.schedule(self.create_buttons, 2.0)

    def create_buttons(self, delta_time):
        arcade.unschedule(self.create_buttons)

        if self.game_view.current_level < NUM_LEVELS:
            self.next_level_button = Button(
                SCREEN_WIDTH // 2, 150, 250, 50,
                "➡ NEXT LEVEL",
                self.start_next_level,
                arcade.color.GREEN
            )
        else:
            self.next_level_button = Button(
                SCREEN_WIDTH // 2, 150, 300, 50,
                "🏆 ALL LEVELS COMPLETE!",
                self.show_final_screen,
                arcade.color.GOLD
            )

    def start_next_level(self):
        if self.game_view.sound_manager:
            self.game_view.sound_manager.play_button_click()

        self.game_view.current_level += 1
        self.game_view.start_level()
        self.window.show_view(self.game_view)

    def show_final_screen(self):
        if self.game_view.sound_manager:
            self.game_view.sound_manager.play_button_click()

        game_over_view = GameOverView(self.game_view)
        self.window.show_view(game_over_view)

    def on_draw(self):
        self.clear()

        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (20, 30, 40)
        )

        for particle in self.confetti_particles:
            arcade.draw_circle_filled(
                particle['x'], particle['y'],
                particle['size'] / 2,
                particle['color']
            )

        panel_width = 700
        panel_height = 400
        panel_x = SCREEN_WIDTH // 2
        panel_y = SCREEN_HEIGHT // 2 + 50

        arcade.draw_lrbt_rectangle_filled(
            panel_x - panel_width // 2, panel_x + panel_width // 2,
            panel_y - panel_height // 2, panel_y + panel_height // 2,
            (30, 40, 50, 230)
        )

        arcade.draw_lrbt_rectangle_outline(
            panel_x - panel_width // 2, panel_x + panel_width // 2,
            panel_y - panel_height // 2, panel_y + panel_height // 2,
            arcade.color.GOLD, 4
        )

        arcade.draw_text(
            "🎉 LEVEL COMPLETED! 🎉",
            panel_x, panel_y + 120,
            arcade.color.GOLD, 36,
            align="center", anchor_x="center", anchor_y="center",
            bold=True
        )

        arcade.draw_text(
            f"Level {self.game_view.current_level} Finished!",
            panel_x, panel_y + 70,
            arcade.color.LIGHT_GREEN, 28,
            align="center", anchor_x="center", anchor_y="center"
        )

        stats = [
            f"Keys collected: {self.game_view.keys_collected}/5",
            f"Time: {self.game_view.level_time:.1f} seconds",
            f"Score: +{LEVEL_SCORES.get(self.game_view.english_level, 10) * 5} points",
            f"Total score: {self.game_view.total_score}",
            f"Next: Level {min(self.game_view.current_level + 1, NUM_LEVELS)}/{NUM_LEVELS}"
        ]

        for i, stat in enumerate(stats):
            arcade.draw_text(
                stat,
                panel_x, panel_y - i * 40,
                arcade.color.WHITE, 22,
                align="center", anchor_x="center", anchor_y="center"
            )

        self.draw_smiling_player(panel_x - 200, self.smiling_player_y)

        if self.next_level_button:
            self.next_level_button.draw()

        if self.timer < 2 and not self.next_level_button:
            alpha = int(255 * (1 - (self.timer / 2)))

            arcade.draw_text(
                "Loading next level options...",
                panel_x, 150,
                (255, 255, 0, alpha),
                24,
                align="center", anchor_x="center", anchor_y="center"
            )

    def draw_smiling_player(self, x, y):
        bounce = math.sin(self.player_wave_offset * 2) * 20

        arcade.draw_ellipse_filled(
            x, y + bounce - 10,
            30, 40, arcade.color.BLUE
        )

        arcade.draw_circle_filled(x, y + bounce + 25, 20, arcade.color.LIGHT_BLUE)

        arcade.draw_circle_filled(x - 6, y + bounce + 30, 4, arcade.color.WHITE)
        arcade.draw_circle_filled(x + 6, y + bounce + 30, 4, arcade.color.WHITE)
        arcade.draw_circle_filled(x - 6, y + bounce + 30, 2, arcade.color.BLACK)
        arcade.draw_circle_filled(x + 6, y + bounce + 30, 2, arcade.color.BLACK)

        arcade.draw_arc_outline(
            x, y + bounce + 20,
            15, 8, arcade.color.BLACK, 180, 360, 3
        )

        arm_wave = math.sin(self.player_wave_offset * 3) * 15
        arcade.draw_line(
            x - 15, y + bounce,
            x - 30, y + bounce + 40 + arm_wave,
            arcade.color.DARK_BLUE, 4
        )
        arcade.draw_line(
            x + 15, y + bounce,
            x + 30, y + bounce + 40 - arm_wave,
            arcade.color.DARK_BLUE, 4
        )

        leg_offset = math.sin(self.player_wave_offset * 4) * 15
        arcade.draw_line(
            x - 8, y + bounce - 30,
            x - 15, y + bounce - 50 + leg_offset,
            arcade.color.DARK_BLUE, 4
        )
        arcade.draw_line(
            x + 8, y + bounce - 30,
            x + 15, y + bounce - 50 - leg_offset,
            arcade.color.DARK_BLUE, 4
        )

    def update(self, delta_time):
        self.timer += delta_time
        self.player_wave_offset += delta_time * 2

        self.smiling_player_y = 300 + math.sin(self.player_wave_offset) * 20

        for particle in self.confetti_particles:
            particle['x'] += particle['dx']
            particle['y'] += particle['dy']
            particle['rotation'] += particle['rotation_speed']
            particle['dy'] += 0.1

            if particle['y'] < -10:
                particle['y'] = SCREEN_HEIGHT + 10
                particle['dy'] = random.uniform(-5, -1)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.next_level_button:
            if self.next_level_button.check_hover(x, y):
                self.next_level_button.state = "hover"
            else:
                self.next_level_button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.next_level_button and self.next_level_button.check_hover(x, y):
                self.next_level_button.on_click()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.SPACE and self.timer > 2:
            if self.game_view.current_level < NUM_LEVELS:
                self.start_next_level()
            else:
                self.show_final_screen()
        elif key == arcade.key.ESCAPE:
            if self.game_view.sound_manager:
                self.game_view.sound_manager.play_button_click()

            from main import StartView
            start_view = StartView()
            self.window.show_view(start_view)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.walls = []
        self.question_stations = []
        self.final_door = None
        self.enemies = []
        self.platforms = []
        self.particle_system = ParticleSystem()
        self.player_x = 0
        self.player_y = 0
        self.is_jumping = False
        self.jump_velocity = 0
        self.on_ground = False
        self.current_level = 1
        self.keys_collected = 0
        self.keys_required = KEYS_PER_LEVEL
        self.level_start_time = 0
        self.level_time = 0
        self.player_name = ""
        self.english_level = ""
        self.total_score = 0
        self.correct_answers = 0
        self.quiz_system = None
        self.database = None
        self.asked_questions = []
        self.current_station_index = 0
        self.key_up = False
        self.key_down = False
        self.key_left = False
        self.key_right = False
        self.game_paused = False
        self.game_active = True
        self.pause_buttons = []
        self.last_time = time.time()
        self.last_footstep_time = 0
        self.footstep_sound = None
        self.sound_manager = None
        self.is_moving = False
        self.sound_enabled = True
        self.last_key_press_time = 0
        self.key_press_delay = 0.05
        self.movement_speed = PLAYER_SPEED
        self.move_dx = 0
        self.move_dy = 0
        self.collected_stations = []
        self.level_score = 0
        self.physics_engine = PhysicsEngine()  # Добавляем физический движок
        self.door_message_time = 0  # Время показа сообщения у двери
        self.door_message_duration = 2.0  # Длительность показа сообщения
        self.show_door_message = False  # Показывать ли сообщение у двери
        self.door_message_text = ""  # Текст сообщения у двери

    def on_show_view(self):
        print("GameView показан")
        self.key_up = False
        self.key_down = False
        self.key_left = False
        self.key_right = False
        self.game_active = True
        self.last_key_press_time = time.time()
        self.move_dx = 0
        self.move_dy = 0
        self.door_message_time = 0
        self.show_door_message = False

    def on_hide_view(self):
        if self.footstep_sound:
            arcade.stop_sound(self.footstep_sound)
            self.footstep_sound = None

    def setup(self, player_name, english_level, sound_manager=None):
        print(f"GameView setup: player_name={player_name}, english_level={english_level}")
        self.player_name = player_name
        self.english_level = english_level
        self.database = PlayerDatabase()
        self.quiz_system = EnglishQuizSystem()

        if self.database:
            self.sound_enabled = self.database.get_player_sound_setting(player_name)
            if self.sound_manager:
                self.sound_manager.set_sound_enabled(self.sound_enabled)

        self.database.create_or_update_player(player_name, english_level)
        self.quiz_system.initialize_game_questions(english_level)
        self.start_level()

    def start_level(self):
        print(f"Starting level {self.current_level}")
        self.keys_collected = 0
        self.current_station_index = 0
        self.collected_stations = []
        self.level_start_time = time.time()
        self.asked_questions = []
        self.game_active = True
        self.game_paused = False
        self.pause_buttons = []
        self.key_up = False
        self.key_down = False
        self.key_left = False
        self.key_right = False
        self.is_jumping = False
        self.jump_velocity = 0
        self.on_ground = False
        self.is_moving = False
        self.last_key_press_time = time.time()
        self.move_dx = 0
        self.move_dy = 0
        self.level_score = 0
        self.door_message_time = 0
        self.show_door_message = False
        self.create_level()

    def create_level(self):
        print(f"Creating level {self.current_level}")
        self.player_x = 100
        self.player_y = 150
        self.walls = []
        self.question_stations = []
        self.enemies = []
        self.platforms = []
        self.final_door = None
        self.create_maze_level(self.current_level)
        self.particle_system = ParticleSystem()

    def create_maze_level(self, level_num):
        difficulty = LEVEL_DIFFICULTY.get(level_num, LEVEL_DIFFICULTY[1])

        base_walls = [
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30, SCREEN_WIDTH, 60),
            (30, SCREEN_HEIGHT // 2, 60, SCREEN_HEIGHT),
            (SCREEN_WIDTH - 30, SCREEN_HEIGHT // 2, 60, SCREEN_HEIGHT),
        ]

        if level_num == 1:
            internal_walls = [
                (380, 550, 30, 200),
                (700, 350, 30, 150),
                (180, 450, 200, 30),
            ]
        elif level_num == 2:
            internal_walls = [
                (500, 600, 30, 300),
                (250, 500, 200, 30),
                (700, 300, 30, 200),
                (600, 200, 150, 30),
            ]

        elif level_num == 3:
            internal_walls = [
                (350, 550, 30, 200),
                (650, 500, 30, 250),
                (250, 150, 150, 30),
                (750, 220, 150, 30),
            ]

        elif level_num == 4:
            internal_walls = [
                (200, 600, 30, 300),
                (800, 600, 30, 300),
                (300, 500, 30, 200),
                (650, 450, 30, 200),
                (250, 170, 150, 30),
                (750, 200, 150, 30),
            ]

        elif level_num == 5:
            internal_walls = [
                (250, 600, 200, 30),
                (750, 600, 200, 30),
                (500, 500, 400, 30),
                (250, 300, 30, 200),
                (900, 300, 30, 200),
                (400, 150, 300, 30),
            ]

        self.walls = base_walls + internal_walls

        self.platforms = []
        if level_num == 1:
            platform_configs = [
                (200, 250, 120, 20),
                (400, 350, 120, 20),
                (600, 300, 120, 20),
                (800, 250, 120, 20),
                (300, 200, 140, 20),
            ]
        elif level_num == 2:
            platform_configs = [
                (200, 300, 110, 20),
                (400, 350, 110, 20),
                (600, 320, 110, 20),
                (800, 290, 110, 20),
                (350, 220, 130, 20),
            ]
        else:
            platform_configs = [
                (180, 320, 100, 20),
                (420, 340, 100, 20),
                (580, 310, 100, 20),
                (820, 280, 100, 20),
                (320, 230, 120, 20),
            ]

        for x, y, width, height in platform_configs:
            self.platforms.append(Platform(x, y, width, height))

        self.question_stations = []
        if level_num == 1:
            station_positions = [
                (200, 320),
                (400, 420),
                (600, 370),
                (800, 320),
                (300, 270),
            ]
        elif level_num == 2:
            station_positions = [
                (200, 370),
                (400, 420),
                (600, 390),
                (800, 360),
                (350, 290),
            ]
        else:
            station_positions = [
                (180, 390),
                (420, 410),
                (580, 380),
                (820, 350),
                (320, 300),
            ]

        self.question_stations = station_positions

        self.final_door = Door(SCREEN_WIDTH - 100, 100, True, 0)

        self.enemies = []
        num_enemies = difficulty['enemies']
        enemy_speed = difficulty['enemy_speed']

        enemy_positions = []
        if level_num == 1:
            enemy_positions = [
                (500, 500),
                (300, 200),
            ]
        elif level_num == 2:
            enemy_positions = [
                (300, 600),
                (600, 150),
                (900, 450),
            ]
        elif level_num == 3:
            enemy_positions = [
                (200, 150),
                (500, 650),
                (800, 150),
                (950, 550),
            ]
        else:
            enemy_positions = [
                (150, 100),
                (400, 650),
                (600, 150),
                (850, 600),
                (950, 300),
            ]

        for i in range(min(num_enemies, len(enemy_positions))):
            x, y = enemy_positions[i]
            enemy = Enemy(x, y, i, enemy_speed, level_num)
            self.enemies.append(enemy)

    def on_draw(self):
        current_time = time.time()
        delta_time = current_time - self.last_time

        if delta_time > 0.05:
            delta_time = 0.05

        self.last_time = current_time

        if not self.game_paused and self.game_active:
            self.update(delta_time)

        self.clear()

        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (30, 30, 50)
        )

        grid_size = 50
        for x in range(0, SCREEN_WIDTH, grid_size):
            arcade.draw_line(x, 0, x, SCREEN_HEIGHT, (40, 40, 60, 50))
        for y in range(0, SCREEN_HEIGHT, grid_size):
            arcade.draw_line(0, y, SCREEN_WIDTH, y, (40, 40, 60, 50))

        floor_height = 40
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, floor_height,
            (45, 60, 45)
        )

        tile_size = 40
        for x in range(0, SCREEN_WIDTH, tile_size):
            for y in range(0, floor_height, tile_size):
                if (x // tile_size + y // tile_size) % 2 == 0:
                    arcade.draw_lrbt_rectangle_filled(
                        x, x + tile_size,
                        y, y + tile_size,
                        (55, 70, 55)
                    )

        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            floor_height - 5, floor_height,
            (35, 80, 35)
        )

        for wall_x, wall_y, wall_width, wall_height in self.walls:
            left = wall_x - wall_width // 2
            right = wall_x + wall_width // 2
            bottom = wall_y - wall_height // 2
            top = wall_y + wall_height // 2

            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, arcade.color.DARK_BROWN)
            arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.BROWN, 2)

            brick_size = 20
            for brick_x in range(int(left), int(right), brick_size):
                for brick_y in range(int(bottom), int(top), brick_size):
                    if (brick_x // brick_size + brick_y // brick_size) % 2 == 0:
                        arcade.draw_lrbt_rectangle_filled(
                            brick_x, brick_x + brick_size,
                            brick_y, brick_y + brick_size,
                            (101, 67, 33)
                        )

        for platform in self.platforms:
            platform.draw()

        for i, (x, y) in enumerate(self.question_stations):
            if i in self.collected_stations:
                arcade.draw_circle_filled(x, y, 25, arcade.color.GREEN)
                arcade.draw_text(
                    "✓",
                    x,
                    y,
                    arcade.color.WHITE,
                    30,
                    align="center",
                    anchor_x="center",
                    anchor_y="center"
                )
                arcade.draw_text(
                    f"Q{i + 1}",
                    x,
                    y - 45,
                    arcade.color.YELLOW,
                    12,
                    align="center",
                    anchor_x="center",
                    anchor_y="center"
                )
            else:
                pulse = math.sin(time.time() * 3) * 0.2 + 1
                arcade.draw_circle_filled(x, y, 22 * pulse, arcade.color.BLUE)
                arcade.draw_circle_outline(x, y, 22 * pulse, arcade.color.LIGHT_BLUE, 3)
                arcade.draw_text(
                    "?",
                    x,
                    y,
                    arcade.color.WHITE,
                    22,
                    align="center",
                    anchor_x="center",
                    anchor_y="center"
                )
                arcade.draw_text(
                    f"Q{i + 1}",
                    x,
                    y - 45,
                    arcade.color.YELLOW,
                    12,
                    align="center",
                    anchor_x="center",
                    anchor_y="center"
                )

                if i == 4 and len(self.collected_stations) == 4:
                    arcade.draw_text(
                        "Last question!",
                        x,
                        y + 60,
                        arcade.color.YELLOW,
                        14,
                        align="center",
                        anchor_x="center",
                        anchor_y="center"
                    )

        if self.final_door:
            self.final_door.draw()

            if self.show_door_message and self.door_message_time > 0:
                lines = self.door_message_text.split('\n')
                for i, line in enumerate(lines):
                    arcade.draw_text(
                        line,
                        self.final_door.center_x,
                        self.final_door.center_y + 60 - (i * 20),
                        arcade.color.RED,
                        12,
                        align="center",
                        anchor_x="center",
                        anchor_y="center"
                    )

        for enemy in self.enemies:
            enemy.draw()

        self.particle_system.draw()

        self.draw_player()

        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            SCREEN_HEIGHT - 70, SCREEN_HEIGHT,
            (20, 20, 30, 220)
        )

        arcade.draw_line(
            0, SCREEN_HEIGHT - 70,
            SCREEN_WIDTH, SCREEN_HEIGHT - 70,
            arcade.color.GOLD, 2
        )

        stats = [
            (f"Player: {self.player_name}", 90, SCREEN_HEIGHT - 35, TEXT_COLOR, 16),
            (f"Level: {self.current_level}/5", 90, SCREEN_HEIGHT - 55, TEXT_COLOR, 16),
            (f"Keys: {self.keys_collected}/{self.keys_required}", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30,
             arcade.color.GOLD, 22),
            (f"English: {self.english_level}", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 55, arcade.color.CYAN, 16),
            (f"Score: {self.total_score}", SCREEN_WIDTH - 120, SCREEN_HEIGHT - 35, arcade.color.GREEN, 20),
            (f"Time: {self.level_time:.1f}s", SCREEN_WIDTH - 120, SCREEN_HEIGHT - 55, TEXT_COLOR, 16),
        ]

        for text, x, y, color, size in stats:
            arcade.draw_text(
                text, x, y, color, size,
                align="center", anchor_x="center", anchor_y="center"
            )

        arcade.draw_text(
            "CONTROLS: WASD/ARROWS to move | SPACE/W/↑ = Jump | P = Pause | ESC = Menu",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80,
            arcade.color.LIGHT_YELLOW, 14,
            align="center", anchor_x="center", anchor_y="center"
        )

        if self.game_paused:
            self.draw_pause_menu()

    def draw_player(self):
        arcade.draw_ellipse_filled(
            self.player_x, self.player_y - 10,
            25, 35, arcade.color.BLUE
        )

        arcade.draw_circle_filled(self.player_x, self.player_y + 20, 18, arcade.color.LIGHT_BLUE)

        arcade.draw_circle_filled(self.player_x - 5, self.player_y + 25, 3, arcade.color.WHITE)
        arcade.draw_circle_filled(self.player_x + 5, self.player_y + 25, 3, arcade.color.WHITE)
        arcade.draw_circle_filled(self.player_x - 5, self.player_y + 25, 2, arcade.color.BLACK)
        arcade.draw_circle_filled(self.player_x + 5, self.player_y + 25, 2, arcade.color.BLACK)

        arcade.draw_arc_outline(
            self.player_x, self.player_y + 15,
            10, 5, arcade.color.BLACK, 180, 360, 2
        )

        # Анимация только при движении
        wave_offset = 0
        if self.key_left or self.key_right or self.key_up or self.key_down:
            wave_offset = math.sin(time.time() * 5) * 5

        arcade.draw_line(
            self.player_x - 12, self.player_y,
            self.player_x - 25, self.player_y + wave_offset,
            arcade.color.DARK_BLUE, 3
        )
        arcade.draw_line(
            self.player_x + 12, self.player_y,
            self.player_x + 25, self.player_y - wave_offset,
            arcade.color.DARK_BLUE, 3
        )

        leg_offset = 0
        if not self.on_ground:
            leg_offset = math.sin(time.time() * 10) * 10

        arcade.draw_line(
            self.player_x - 6, self.player_y - 25,
            self.player_x - 12, self.player_y - 45 + leg_offset,
            arcade.color.DARK_BLUE, 3
        )
        arcade.draw_line(
            self.player_x + 6, self.player_y - 25,
            self.player_x + 12, self.player_y - 45 - leg_offset,
            arcade.color.DARK_BLUE, 3
        )

    def draw_pause_menu(self):
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (0, 0, 0, 180)
        )

        arcade.draw_text(
            "GAME PAUSED",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120,
            arcade.color.GOLD, 40,
            align="center", anchor_x="center", anchor_y="center",
            bold=True
        )

        self.pause_buttons = [
            Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40, 250, 50,
                   "▶ RESUME", self.resume_game, arcade.color.GREEN),
            Button(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20, 250, 50,
                   "🔄 RESTART LEVEL", self.restart_level, arcade.color.ORANGE),
        ]

        for button in self.pause_buttons:
            button.draw()

    def resume_game(self):
        if self.sound_manager:
            self.sound_manager.play_button_click()
        self.game_paused = False
        self.pause_buttons = []

    def restart_level(self):
        if self.sound_manager:
            self.sound_manager.play_button_click()

        self.total_score -= self.level_score
        self.level_score = 0

        self.start_level()
        self.game_paused = False
        self.pause_buttons = []

    def update(self, delta_time):
        if self.game_paused:
            return

        current_time = time.time()
        self.level_time = current_time - self.level_start_time

        if self.show_door_message:
            self.door_message_time -= delta_time
            if self.door_message_time <= 0:
                self.show_door_message = False

        for enemy in self.enemies:
            enemy.update(self.player_x, self.player_y, delta_time)

        if self.final_door:
            self.final_door.update(delta_time)

        self.particle_system.update(delta_time)
        self.update_player_physics(delta_time)

        self.check_interactions()

        self.check_footstep_sounds()

    def check_footstep_sounds(self):
        if not self.sound_manager or not self.sound_enabled:
            return

        is_moving_now = self.key_up or self.key_down or self.key_left or self.key_right

        if is_moving_now and self.on_ground:
            current_time = time.time()
            if current_time - self.last_footstep_time > FOOTSTEP_INTERVAL:
                self.last_footstep_time = current_time
                self.sound_manager.play_sound('footstep', volume=0.3)

    def update_player_physics(self, delta_time):
        self.jump_velocity = self.physics_engine.apply_gravity(
            self.jump_velocity, self.on_ground, delta_time
        )

        dx = 0
        if self.key_left:
            dx -= 1
        if self.key_right:
            dx += 1

        vertical_movement = self.jump_velocity * delta_time
        dy = 0
        if vertical_movement != 0:
            dy = 1 if vertical_movement > 0 else -1

        new_x, new_y, self.on_ground = self.physics_engine.apply_movement(
            self.player_x, self.player_y,
            dx, dy,
            self.walls, self.platforms,
            delta_time
        )

        if self.jump_velocity != 0:
            jump_test_y = self.player_y + self.jump_velocity * delta_time * 40

            if not self.physics_engine.check_collision_with_walls(self.player_x, jump_test_y, self.walls):
                new_y = jump_test_y
            else:
                self.jump_velocity = 0

        self.player_x, self.player_y = new_x, new_y

        self.player_x = max(35, min(SCREEN_WIDTH - 35, self.player_x))
        self.player_y = max(70, min(SCREEN_HEIGHT - 70, self.player_y))

        if not self.on_ground:
            for platform in self.platforms:
                if (self.player_x + 25 > platform.center_x - platform.width // 2 and
                        self.player_x - 25 < platform.center_x + platform.width // 2 and
                        self.player_y - 25 <= platform.center_y + platform.height // 2 and
                        self.player_y - 25 >= platform.center_y - platform.height // 2 and
                        self.jump_velocity <= 0):
                    self.on_ground = True
                    self.jump_velocity = 0
                    self.player_y = platform.center_y + platform.height // 2 + 25
                    break

        if self.player_y < 45:
            self.player_y = 45
            self.on_ground = True
            self.jump_velocity = 0

    def jump(self):
        if self.on_ground:
            self.jump_velocity = JUMP_POWER
            self.on_ground = False
            self.is_jumping = True

            if self.sound_manager and self.sound_enabled:
                self.sound_manager.play_sound('jump', volume=0.4)

            self.particle_system.create_explosion(
                self.player_x, self.player_y - 25,
                arcade.color.LIGHT_BLUE, 8
            )

    def check_interactions(self):
        if not self.game_active:
            return

        for i, (station_x, station_y) in enumerate(self.question_stations):
            if i in self.collected_stations:
                continue

            distance = math.sqrt(
                (self.player_x - station_x) ** 2 +
                (self.player_y - station_y) ** 2
            )

            if distance < 40:
                print(f"Активирована станция вопроса {i + 1}")
                self.ask_question(i)
                return

        for enemy in self.enemies:
            distance = math.sqrt(
                (self.player_x - enemy.center_x) ** 2 +
                (self.player_y - enemy.center_y) ** 2
            )

            if distance < 35:
                self.restart_level_from_enemy()
                return

        if self.final_door:
            distance = math.sqrt(
                (self.player_x - self.final_door.center_x) ** 2 +
                (self.player_y - self.final_door.center_y) ** 2
            )

            if distance < 40:
                if self.final_door.locked:
                    if self.keys_collected < self.keys_required:
                        keys_needed = self.keys_required - self.keys_collected
                        keys_text = get_keys_text(keys_needed)
                        self.door_message_text = f"Нужно еще {keys_needed} {keys_text}!"
                        self.show_door_message = True
                        self.door_message_time = self.door_message_duration
                    else:
                        self.final_door.open()
                        if self.sound_manager:
                            self.sound_manager.play_sound('door_open', volume=0.5)
                else:
                    self.complete_level()

    def restart_level_from_enemy(self):
        print("Перезапуск уровня из-за врага!")

        self.total_score -= self.level_score
        self.level_score = 0

        if hasattr(self, 'sound_manager') and self.sound_manager and self.sound_enabled:
            self.sound_manager.play_sound('enemy_hit', volume=0.5)
        else:
            print("Sound not available for enemy hit")

        self.particle_system.create_explosion(
            self.player_x, self.player_y,
            arcade.color.RED, 25
        )
        self.start_level()

    def ask_question(self, station_index):
        self.game_active = False
        question = self.quiz_system.get_question_for_key(station_index)

        if question:
            self.quiz_system.current_question = question
            quiz_view = QuizView(self, question, station_index)
            self.window.show_view(quiz_view)
        else:
            backup_question = EnglishQuestion(
                id="backup",
                level=self.english_level,
                question_type="vocabulary",
                question="What is 'game' in Russian?",
                options=["Игра", "Фильм", "Книга", "Музыка"],
                correct_answer="Игра",
                explanation="Game = игра",
                hint="Entertainment activity"
            )
            self.quiz_system.current_question = backup_question
            quiz_view = QuizView(self, backup_question, station_index)
            self.window.show_view(quiz_view)

    def complete_level(self):
        time_bonus = max(0, 100 - int(self.level_time))
        perfect_bonus = 50 if self.keys_collected == self.keys_required else 0
        level_completion_bonus = 100

        self.level_score = level_completion_bonus + time_bonus + perfect_bonus
        self.total_score += self.level_score

        self.database.update_player_progress(
            self.player_name,
            self.current_level,
            self.keys_collected,
            self.level_score,
            correct=self.correct_answers
        )

        self.database.save_high_score(
            self.player_name,
            self.total_score,
            self.current_level,
            self.english_level
        )

        if self.sound_manager and self.sound_enabled:
            self.sound_manager.play_sound('victory', volume=0.6)

        victory_view = VictoryView(self)
        self.window.show_view(victory_view)

    def on_key_press(self, key, modifiers):
        current_time = time.time()

        if key == arcade.key.UP or key == arcade.key.W or key == arcade.key.SPACE:
            self.jump()
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.key_down = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.key_left = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.key_right = True
        elif key == arcade.key.P:
            self.game_paused = not self.game_paused
            if self.game_paused and self.sound_manager:
                self.sound_manager.play_button_click()
        elif key == arcade.key.ESCAPE:
            if self.sound_manager:
                self.sound_manager.play_button_click()

            from main import StartView
            start_view = StartView()
            self.window.show_view(start_view)

    def on_key_release(self, key, modifiers):
        if key == arcade.key.DOWN or key == arcade.key.S:
            self.key_down = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.key_left = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.key_right = False

    def on_mouse_motion(self, x, y, dx, dy):
        if self.game_paused:
            for button in self.pause_buttons:
                if button.check_hover(x, y):
                    button.state = "hover"
                else:
                    button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and self.game_paused:
            if self.sound_manager:
                self.sound_manager.play_button_click()
            for btn in self.pause_buttons:
                if btn.check_hover(x, y):
                    btn.on_click()
                    return


class QuizView(arcade.View):
    def __init__(self, game_view, question, station_index, sound_manager=None):
        super().__init__()
        self.game_view = game_view
        self.question = question
        self.station_index = station_index
        self.answer_buttons = []
        self.selected_answer = None
        self.show_result = False
        self.result_text = ""
        self.result_color = arcade.color.WHITE
        self.hint_button = None
        self.attempts = 0
        self.show_hint_text = False
        self.sound_manager = sound_manager
        self.answered = False
        self.locked = False

    def on_show_view(self):
        center_x = SCREEN_WIDTH // 2
        start_y = SCREEN_HEIGHT // 2 + 40

        self.answer_buttons = []
        for i, option in enumerate(self.question.options):
            y = start_y - i * 60
            btn = Button(
                center_x, y, 500, 45,
                option,
                lambda opt=option: self.select_answer(opt)
            )
            self.answer_buttons.append(btn)

        self.hint_button = Button(
            SCREEN_WIDTH // 2, 100, 180, 35,
            "💡 Show Hint",
            self.show_hint,
            arcade.color.ORANGE
        )

    def select_answer(self, answer):
        if self.locked or self.answered:
            return

        if self.sound_manager:
            self.sound_manager.play_button_click()

        self.selected_answer = answer
        self.attempts += 1
        self.locked = True

        arcade.schedule(lambda dt: self.check_answer(), 0.1)

    def show_hint(self):
        if self.locked or self.answered:
            return

        if self.sound_manager:
            self.sound_manager.play_button_click()
        self.result_text = f"Hint: {self.question.hint}"
        self.result_color = arcade.color.YELLOW
        self.show_result = True
        self.show_hint_text = True

    def check_answer(self):
        if not self.selected_answer or self.answered:
            return

        is_correct, explanation = self.game_view.quiz_system.check_answer(self.selected_answer)

        if self.sound_manager:
            if is_correct:
                self.sound_manager.play_sound('correct', volume=0.5)
            else:
                self.sound_manager.play_sound('wrong', volume=0.5)

        if is_correct:
            if self.attempts == 1:
                if self.show_hint_text:
                    score_earned = 7
                    self.result_text = f"✅ Правильно с подсказкой! +7 очков! {explanation}"
                else:
                    score_earned = 10
                    self.result_text = f"✅ Идеально! +10 очков! {explanation}"
            else:
                score_earned = 5
                self.result_text = f"✅ Правильно! +5 очков! {explanation}"

            self.result_color = arcade.color.GREEN

            if not self.answered:
                self.answered = True
                self.game_view.keys_collected += 1
                self.game_view.correct_answers += 1

                self.game_view.level_score += score_earned
                self.game_view.total_score += score_earned

                self.game_view.collected_stations.append(self.station_index)

                if self.sound_manager:
                    self.sound_manager.play_sound('collect', volume=0.4)

                self.game_view.database.update_player_progress(
                    self.game_view.player_name,
                    self.game_view.current_level,
                    1,
                    score_earned,
                    correct=1
                )

            self.game_view.game_active = True
            arcade.schedule(self.return_to_game, 2.0)
        else:
            self.result_text = f"❌ Неправильно! {explanation}"
            self.result_color = arcade.color.RED

            self.game_view.database.update_player_progress(
                self.game_view.player_name,
                self.game_view.current_level,
                0,
                0,
                wrong=1
            )

            self.locked = False
            self.selected_answer = None

        self.show_result = True

    def return_to_game(self, delta_time):
        arcade.unschedule(self.return_to_game)
        if (self.game_view.final_door and
                self.game_view.final_door.locked and
                self.game_view.keys_collected >= self.game_view.keys_required):
            self.game_view.final_door.open()
            if self.sound_manager:
                self.sound_manager.play_sound('door_open', volume=0.5)
        self.window.show_view(self.game_view)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (0, 0, 0, 200)
        )

        panel_width = 750
        panel_height = 500
        panel_x = SCREEN_WIDTH // 2
        panel_y = SCREEN_HEIGHT // 2

        left = panel_x - panel_width // 2
        right = panel_x + panel_width // 2
        bottom = panel_y - panel_height // 2
        top = panel_y + panel_height // 2

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (40, 40, 60, 240))
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.GOLD, 3)

        arcade.draw_text(
            "ENGLISH QUESTION",
            panel_x, top - 40,
            arcade.color.GOLD, 28,
            align="center", anchor_x="center", anchor_y="center",
            bold=True
        )

        arcade.draw_text(
            f"Level: {self.question.level} - {ENGLISH_LEVELS[self.question.level]}",
            panel_x, top - 75,
            arcade.color.LIGHT_BLUE, 20,
            align="center", anchor_x="center", anchor_y="center"
        )

        arcade.draw_text(
            f"Question {self.station_index + 1} of 5",
            panel_x, top - 105,
            arcade.color.YELLOW, 16,
            align="center", anchor_x="center", anchor_y="center"
        )

        arcade.draw_text(
            self.question.question,
            panel_x, panel_y + 120,
            TEXT_COLOR, 20,
            align="center", anchor_x="center", anchor_y="center",
            width=panel_width - 40
        )

        for button in self.answer_buttons:
            button.enabled = not (self.locked or self.answered)
            button.draw()

        if self.show_result:
            arcade.draw_text(
                self.result_text,
                panel_x, 150,
                self.result_color, 18,
                align="center", anchor_x="center", anchor_y="center",
                width=panel_width - 40
            )

        if not self.show_result and self.hint_button and not self.answered:
            self.hint_button.draw()

        if not self.selected_answer and not self.answered:
            arcade.draw_text(
                "Choose the correct answer",
                panel_x, 70,
                arcade.color.LIGHT_GRAY, 16,
                align="center", anchor_x="center", anchor_y="center"
            )

    def on_mouse_motion(self, x, y, dx, dy):
        for button in self.answer_buttons:
            if button.check_hover(x, y) and button.enabled:
                button.state = "hover"
            else:
                button.state = "normal"

        if self.hint_button and self.hint_button.check_hover(x, y):
            self.hint_button.state = "hover"
        elif self.hint_button:
            self.hint_button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.sound_manager:
                self.sound_manager.play_button_click()

            if self.locked or self.answered:
                return

            for btn in self.answer_buttons:
                if btn.check_hover(x, y) and btn.enabled:
                    btn.on_click()
                    return

            if not self.show_result and self.hint_button and self.hint_button.check_hover(x, y):
                self.hint_button.on_click()


class GameOverView(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        self.buttons = []

    def on_show_view(self):
        self.buttons = [
            Button(SCREEN_WIDTH // 2, 130, 220, 50,
                   "MAIN MENU", self.return_to_menu,
                   arcade.color.STEEL_BLUE),
            Button(SCREEN_WIDTH // 2, 70, 220, 50,
                   "HIGH SCORES", self.show_high_scores,
                   arcade.color.PURPLE),
        ]

    def return_to_menu(self):
        if self.game_view.sound_manager:
            self.game_view.sound_manager.play_button_click()
        start_view = StartView()
        self.window.show_view(start_view)

    def show_high_scores(self):
        if self.game_view.sound_manager:
            self.game_view.sound_manager.play_button_click()
        high_scores_view = HighScoresView(self)
        self.window.show_view(high_scores_view)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH,
            0, SCREEN_HEIGHT,
            (20, 20, 40)
        )

        for i in range(80):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            color = random.choice([
                arcade.color.RED, arcade.color.GREEN, arcade.color.BLUE,
                arcade.color.YELLOW, arcade.color.PURPLE, arcade.color.ORANGE
            ])
            arcade.draw_circle_filled(x, y, 3, color)

        panel_width = 600
        panel_height = 500
        panel_x = SCREEN_WIDTH // 2
        panel_y = SCREEN_HEIGHT // 2

        left = panel_x - panel_width // 2
        right = panel_x + panel_width // 2
        bottom = panel_y - panel_height // 2
        top = panel_y + panel_height // 2

        arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (30, 30, 50, 240))
        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.GOLD, 3)

        arcade.draw_text(
            "🎉 CONGRATULATIONS! 🎉",
            panel_x, top - 50,
            arcade.color.GOLD, 36,
            align="center", anchor_x="center", anchor_y="center",
            bold=True
        )

        arcade.draw_text(
            "You completed all 5 levels!",
            panel_x, top - 90,
            arcade.color.LIGHT_GREEN, 24,
            align="center", anchor_x="center", anchor_y="center"
        )

        stats_y = panel_y + 80
        stats = [
            (f"Player: {self.game_view.player_name}", arcade.color.WHITE, 22),
            (f"Final Score: {self.game_view.total_score}", arcade.color.GOLD, 28),
            (f"English Level: {self.game_view.english_level}", arcade.color.CYAN, 20),
            (f"Correct Answers: {self.game_view.correct_answers}", arcade.color.GREEN, 20),
            (f"Levels Completed: 5/5", arcade.color.LIGHT_BLUE, 20),
        ]

        for i, (text, color, size) in enumerate(stats):
            arcade.draw_text(
                text, panel_x, stats_y - i * 45,
                color, size,
                align="center", anchor_x="center", anchor_y="center"
            )

        for button in self.buttons:
            button.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        for button in self.buttons:
            if button.check_hover(x, y):
                button.state = "hover"
            else:
                button.state = "normal"

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            for btn in self.buttons:
                if btn.check_hover(x, y):
                    btn.on_click()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            self.return_to_menu()


def create_and_setup_sound_manager():
    sound_manager = SoundManager()
    sound_manager.initialize()
    return sound_manager


def main():
    print("=" * 60)
    print("ENGLISH MAZE ADVENTURE - FINAL FIXED VERSION 3.0")
    print("=" * 60)

    os.makedirs("data", exist_ok=True)

    sound_manager = create_and_setup_sound_manager()

    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    start_view = StartView(sound_manager)
    window.show_view(start_view)

    arcade.run()


if __name__ == "__main__":
    main()
