import sys
import random
import itertools
import sqlite3
import threading
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup, \
    QComboBox, QMessageBox, QLineEdit, QInputDialog

# Список погодных факторов
names = [
    "прогулка гномов",
    "кружка кофе",
    "голубая трава",
    "песчаная буря",
    "туман",
    "обед в столовой",
    "закрытый мост",
    "sin(60)",
    "сходка зайцев",
    "снег",
    "снег с дождем",
    "пикник в лесу",
    "радужное небо",
    "северное сияние",
    "засуха",
    "тропический дождь",
    "ветреная погода",
    "горячий ливень",
    "холодный ветер"
]

numbers = [0, 1, 2]

# Диапазоны температур для разных типов погоды
temperature_ranges = {
    "солнечно": [+25, +37, +29],
    "дождливо": [+4, +3, +1],
    "снегопад": [-23, -17, -32],
    "штормит": [+9, +11, +15],
    "облачно": [-4, -7, 0],
    "ветренно": [+15, +20, +5],
    "горячий дождь": [+30, +35, +28],
    "холодный ветер": [-5, -10, -15]
}

# Функция для генерации действительных комбинаций чисел
def generate_combinations():
    all_combinations = []
    for combination in itertools.product(numbers, repeat=3):
        if sum(x == 0 for x in combination) == 1 and len(set(combination)) > 1:
            all_combinations.append(combination)
    return all_combinations

# Функция для выбора элемента на основе заданных правил
def choose_element(output_elements):
    # обработка исключений
    try:
        values = [int(element.split('-')[1].strip()) for element in output_elements]
        unique_values = set(values)
        if len(unique_values) == len(values):
            if random.random() < 0.6:
                choices = [el for el in output_elements if int(el.split('-')[1].strip()) == 2]
                return random.choice(choices) if choices else None
            else:
                choices = [el for el in output_elements if int(el.split('-')[1].strip()) == 1]
                return random.choice(choices) if choices else None
        else:
            same_elements = [el for el in output_elements if values.count(int(el.split('-')[1].strip())) > 1]
            other_elements = [el for el in output_elements if el not in same_elements]
            if same_elements and other_elements:
                return random.choice(same_elements) if int(same_elements[0].split('-')[1].strip()) > int(other_elements[0].split('-')[1].strip()) else random.choice(other_elements)
            else:
                return random.choice(same_elements) if same_elements else None
    except Exception as e:
        return None

# Функция для определения погоды на основе фактора
def determine_weather(factor):
    weather_conditions = {
        "дождливо": ["прогулка гномов", "кружка кофе", "голубая трава", "песчаная буря"],
        "снегопад": ["песчаная буря", "туман", "обед в столовой", "закрытый мост"],
        "солнечно": ["sin(60)", "сходка зайцев"],
        "штормит": ["пикник в лесу"],
        "облачно": ["снег", "снег с дождем", "радужное небо", "северное сияние"],
        "ветренно": ["ветреная погода"],
        "горячий дождь": ["горячий ливень"],
        "холодный ветер": ["холодный ветер"]
    }
    for weather, factors in weather_conditions.items():
        if factor in factors:
            return weather
    return None

# Основной класс для окна игры
class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.difficulty_level = "Легкий"
        self.time_limit = self.random_time_limit()
        self.facts_count = 3
        self.user_name = ""
        self.players = {}
        self.current_player = None
        self.bonus_count = 0
        self.penalty_count = 0
        self.initUI()
        self.start_timer()
        self.init_database()
        self.hints_used = 0
        self.max_hints = 3
        self.previous_guesses = []
        self.leaderboard = []

    # Функция для генерации случайного времени от 10 до 55 секунд
    def random_time_limit(self):
        return random.randint(10, 55)

    # Инициализация пользовательского интерфейса
    def initUI(self):
        self.setWindowTitle("Предсказание погоды")
        self.layout = QVBoxLayout()

        self.name_label = QLabel("Введите ваше имя:")
        self.layout.addWidget(self.name_label)
        self.name_input = QLineEdit(self)
        self.layout.addWidget(self.name_input)

        self.confirm_name_button = QPushButton("Подтвердить имя")
        self.confirm_name_button.clicked.connect(self.confirm_name)
        self.layout.addWidget(self.confirm_name_button)

        self.player_name_display = QLabel("Имя игрока: Не указано")
        self.layout.addWidget(self.player_name_display)

        self.fact_label = QLabel("Факты о погоде:")
        self.layout.addWidget(self.fact_label)

        self.difficulty_label = QLabel("Выберите уровень сложности:")
        self.layout.addWidget(self.difficulty_label)
        self.difficulty_combo = QComboBox(self)
        self.difficulty_combo.addItems(["Легкий", "Средний", "Сложный"])
        self.difficulty_combo.currentTextChanged.connect(self.update_difficulty)
        self.layout.addWidget(self.difficulty_combo)

        self.mode_label = QLabel("Выберите режим игры:")
        self.layout.addWidget(self.mode_label)
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(["Одиночный", "Многопользовательский"])
        self.mode_combo.currentTextChanged.connect(self.update_game_mode)
        self.layout.addWidget(self.mode_combo)

        self.instructions_button = QPushButton("Инструкции по игре")
        self.instructions_button.clicked.connect(self.show_instructions)
        self.layout.addWidget(self.instructions_button)

        # Группа для выбора погодных условий
        self.weather_group = QButtonGroup(self)
        self.weather_options = ["дождливо", "снегопад", "солнечно", "штормит", "облачно", "ветренно", "горячий дождь", "холодный ветер"]
        for option in self.weather_options:
            radio_button = QRadioButton(option, self)
            self.weather_group.addButton(radio_button)
            self.layout.addWidget(radio_button)

        # Кнопки управления игрой
        self.check_button = QPushButton("Предсказать погоду")
        self.check_button.clicked.connect(self.check_weather)
        self.layout.addWidget(self.check_button)

        self.restart_button = QPushButton("Играть снова")
        self.restart_button.clicked.connect(self.restart_game)
        self.layout.addWidget(self.restart_button)

        self.hint_button = QPushButton("Получить подсказку")
        self.hint_button.clicked.connect(self.give_hint)
        self.layout.addWidget(self.hint_button)

        self.history_button = QPushButton("Посмотреть историю игр")
        self.history_button.clicked.connect(self.show_game_history)
        self.layout.addWidget(self.history_button)

        self.clear_history_button = QPushButton("Очистить историю игр")
        self.clear_history_button.clicked.connect(self.clear_game_history)
        self.layout.addWidget(self.clear_history_button)

        self.save_stats_button = QPushButton("Сохранить статистику")
        self.save_stats_button.clicked.connect(self.save_statistics)
        self.layout.addWidget(self.save_stats_button)

        self.show_leaderboard_button = QPushButton("Показать лидерборд")
        self.show_leaderboard_button.clicked.connect(self.show_leaderboard)
        self.layout.addWidget(self.show_leaderboard_button)

        self.exit_button = QPushButton("Выйти из игры")
        self.exit_button.clicked.connect(self.exit_game)
        self.layout.addWidget(self.exit_button)

        # Дисплей таймера
        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-size: 48px;")
        self.layout.addWidget(self.timer_label)

        # Индикаторы счета и бонусов/штрафов
        self.score_label = QLabel("Правильные ответы: 0")
        self.layout.addWidget(self.score_label)

        self.bonus_penalty_label = QLabel("Бонусы: 0, Штрафы: 0")
        self.layout.addWidget(self.bonus_penalty_label)

        self.setLayout(self.layout)
        self.time_left = self.time_limit
        self.running = False
        self.guesses_count = 0
        self.output_elements = []
        self.display_weather_facts()

    # Подтверждение имени пользователя и отображение его
    def confirm_name(self):
        self.user_name = self.name_input.text().strip() or "Игрок"
        self.player_name_display.setText(f"Имя игрока: {self.user_name}")
        if self.current_player is None:
            self.current_player = self.user_name
            self.players[self.current_player] = {"correct_guesses": 0, "history": []}

    # Показать инструкции по игре
    def show_instructions(self):
        instructions = (
            "Инструкции по игре:\n"
            "1. Выберите режим игры: Одиночный или Многопользовательский.\n"
            "2. Введите ваше имя.\n"
            "3. Выберите уровень сложности: Легкий, Средний или Сложный.\n"
            "4. После этого вы сможете предсказать погоду, основываясь на предоставленных фактах.\n"
            "5. Получайте бонусы за правильные ответы и штрафы за неправильные.\n"
            "6. Воспользуйтесь подсказками, если хотите.\n"
            "7. Удачи!"
        )
        QMessageBox.information(self, "Инструкции", instructions)

    # Обновление уровня сложности
    def update_difficulty(self, difficulty):
        self.difficulty_level = difficulty
        if difficulty == "Легкий":
            self.facts_count = 3
        elif difficulty == "Средний":
            self.facts_count = 3
        elif difficulty == "Сложный":
            self.facts_count = 2
        self.display_weather_facts()

    # Обновление режима игры
    def update_game_mode(self, mode):
        if mode == "Многопользовательский":
            self.players.clear()
            self.current_player = None
            self.fact_label.setText("Добавьте игроков и начните игру.")
        else:
            self.current_player = self.user_name
            if self.current_player not in self.players:
                self.players[self.current_player] = {"correct_guesses": 0, "history": []}
            self.fact_label.setText(f"Вы в одиночном режиме под именем: {self.current_player}")

    # Инициализация базы данных
    def init_database(self):
        # обработка исключений
        try:
            self.conn = sqlite3.connect('weather_game.db')
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                correct_guesses INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Не удалось подключиться к базе данных: {e}")

    # Сохранение результата игры в базе данных
    def save_game_result(self, correct_guesses):
        if self.current_player:
            # обработка исключений
            try:
                self.cursor.execute('''
                INSERT INTO game_results (user_name, correct_guesses)
                VALUES (?, ?)
                ''', (self.current_player, correct_guesses))
                self.conn.commit()
            except sqlite3.Error as e:
                QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить результат: {e}")

    # Показать историю игр
    def show_game_history(self):
        # обработка исключений
        try:
            if not self.current_player:
                QMessageBox.warning(self, "Ошибка", "Вы не выбрали игрока!")
                return
            self.cursor.execute('SELECT * FROM game_results WHERE user_name = ? ORDER BY timestamp DESC', (self.current_player,))
            rows = self.cursor.fetchall()
            if not rows:
                QMessageBox.information(self, "История игр", "История игр пуста.")
                return
            history = "История игр:\n"
            for row in rows:
                history += f"Игра {row[0]} - Правильные ответы: {row[2]} - Время: {row[3]}\n"
            QMessageBox.information(self, "История игр", history)
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Ошибка истории", f"Не удалось загрузить историю игр: {e}")

    # Очистка истории игр
    def clear_game_history(self):
        # обработка исключений
        try:
            self.cursor.execute('DELETE FROM game_results WHERE user_name = ?', (self.current_player,))
            self.conn.commit()
            QMessageBox.information(self, "Очистка истории", "История игр успешно очищена.")
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Ошибка очистки", f"Не удалось очистить историю игр: {e}")

    # Сохранение статистики в текстовый файл
    def save_statistics(self):
        # обработка исключений
        try:
            with open("game_statistics.txt", "a") as file:
                file.write(f"{self.current_player} - Правильные ответы: {self.guesses_count} - Время: {self.time_limit - self.time_left}s\n")
            QMessageBox.information(self, "Сохранение статистики", "Статистика успешно сохранена.")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить статистику: {e}")

    # Отображение фактов о погоде
    def display_weather_facts(self):
        valid_combinations = generate_combinations()
        if len(valid_combinations) == 0:
            self.fact_label.setText("Нет доступных комбинаций.")
            return
        chosen_numbers = random.choice(valid_combinations)
        random_names = random.sample(names, self.facts_count)
        self.output_elements = []
        for name, number in zip(random_names, chosen_numbers):
            self.output_elements.append(f"{name} - {number}")
        weather = random.choice(self.weather_options)
        temperature_facts_weather = self.get_temperature_facts(weather)
        self.fact_label.setText(
            "\n".join(self.output_elements) +
            f"\nТемпература для {weather}: {temperature_facts_weather}"
        )

    # Получение температурных фактов по типу погоды
    def get_temperature_facts(self, weather):
        return f"{random.choice(temperature_ranges[weather])}°C."

    # Проверка выбранного типа погоды
    def check_weather(self):
        if self.check_button.isEnabled():
            if self.output_elements:
                chosen_element = choose_element(self.output_elements)
                if chosen_element:
                    factor = chosen_element.split('-')[0].strip()
                    weather = determine_weather(factor)

                    selected_weather = self.weather_group.checkedButton()
                    if selected_weather:
                        user_guess = selected_weather.text()
                        is_correct = user_guess == weather
                        if is_correct:
                            self.guesses_count += 1
                            self.score_label.setText(f"Правильные ответы: {self.guesses_count}")
                            self.fact_label.setText(f"Вы угадали! Cейчас действительно: {weather}.")
                            self.save_game_result(self.guesses_count)
                            if self.current_player:
                                self.players[self.current_player]["correct_guesses"] += 1
                            self.calculate_bonus()
                            self.bonus_penalty_label.setText(f"Бонусы: {self.bonus_count}, Штрафы: {self.penalty_count}")
                            self.time_limit = self.adjust_time_limit(increase=True)
                        else:
                            self.fact_label.setText(f"Увы! Вы не угадали! Cейчас: {weather}.")
                            self.save_game_result(0)
                            self.calculate_penalty()
                            self.bonus_penalty_label.setText(f"Бонусы: {self.bonus_count}, Штрафы: {self.penalty_count}")
                            self.time_limit = self.adjust_time_limit(increase=False)
                    else:
                        self.fact_label.setText("Выберите тип погоды.")
                else:
                    self.fact_label.setText("Нет доступных элементов для выбора.")

    # Рассчитываем бонусы в зависимости от уровня сложности
    def calculate_bonus(self):
        if self.difficulty_level in ["Средний", "Сложный"]:
            self.bonus_count += 1
        elif self.difficulty_level == "Легкий" and len(self.previous_guesses) >= 2:
            if self.previous_guesses[-1]:
                self.bonus_count += 1
        self.previous_guesses.append(True)

    # Рассчитываем штрафы
    def calculate_penalty(self):
        if self.difficulty_level == "Легкий":
            self.penalty_count += 1
        self.previous_guesses.append(False)

    # Регулировка времени таймера в зависимости от угадываний и подсказок
    def adjust_time_limit(self, increase):
        # обработка исключений
        try:
            if increase:
                new_time = min(self.time_limit + 5, 55)
            else:
                new_time = max(self.time_limit - 10, 10)
            return new_time
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось изменить лимит времени: {e}")
            return self.time_limit

    # Получение подсказки
    def give_hint(self):
        if self.hints_used < self.max_hints:
            hint_weather = random.choice(self.weather_options)
            self.fact_label.setText(f"Подсказка: Погода может быть {hint_weather}.")
            self.hints_used += 1
            self.time_limit = self.adjust_time_limit(increase=False)
        else:
            self.fact_label.setText("Подсказки исчерпаны.")

    # Запуск таймера
    def start_timer(self):
        self.running = True
        self.timer_thread = threading.Thread(target=self.update_timer)
        self.timer_thread.start()

    # Остановка таймера
    def stop_timer(self):
        self.running = False
        self.check_button.setEnabled(False)
        self.display_weather_facts()

    # Обновление таймера
    def update_timer(self):
        self.time_left = self.time_limit
        while self.running and self.time_left > 0:
            time.sleep(1)
            self.time_left -= 1
            self.update_timer_display()
        if self.time_left == 0:
            self.stop_timer()

    # Обновление отображения таймера
    def update_timer_display(self):
        minutes, seconds = divmod(self.time_left, 60)
        self.timer_label.setText(f"{minutes:02}:{seconds:02}")

    # Перезапуск игры
    def restart_game(self):
        # Сброс всех значений для новой игры
        self.guesses_count = 0
        self.bonus_count = 0
        self.penalty_count = 0
        self.hints_used = 0
        self.previous_guesses.clear()
        self.user_name = self.name_input.text().strip() or "Игрок"
        self.time_limit = self.random_time_limit()
        self.display_weather_facts()
        self.check_button.setEnabled(True)
        self.start_timer()

    # Выход из игры
    def exit_game(self):
        # обработка исключений
        try:
            reply = QMessageBox.question(self, 'Выход из игры', 'Вы уверены, что хотите выйти из игры?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                QApplication.quit()  # Выход из приложения
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось выйти из игры: {e}")

    # Показать лидерборд
    def show_leaderboard(self):
        leaderboard_text = self.get_leaderboard()
        QMessageBox.information(self, "Лидерборд", leaderboard_text)

    # Получение строки лидерборда
    def get_leaderboard(self):
        # обработка исключений
        try:
            self.cursor.execute('SELECT user_name, SUM(correct_guesses) as total_guesses FROM game_results GROUP BY user_name ORDER BY total_guesses DESC LIMIT 10')
            leaderboard = "Топ 10 игроков:\n"
            rows = self.cursor.fetchall()
            for i, row in enumerate(rows):
                leaderboard += f"{i + 1}. {row[0]} - Правильные ответы: {row[1]}\n"
            return leaderboard if leaderboard.strip() else "Лидерборд пуст."
        except sqlite3.Error as e:
            return f"Ошибка при получении лидерборда: {e}"

# Основная структура приложения
if __name__ == "__main__":
    # обработка исключений
    try:
        app = QApplication(sys.argv)
        my_notes = WeatherApp()
        my_notes.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Произошла ошибка: {e}")