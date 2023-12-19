import base64
import logging
import os
import sqlite3

import requests
from cryptography.fernet import Fernet

logging.basicConfig(filename='bank_system.log', level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s')


class BankManagementSystem:
    def __init__(self):
        try:
            self.conn = sqlite3.connect('bank_system.db')
            self.create_tables()
            self.key = self.load_or_generate_key()
            self.api_key = '603b05e22e866bc0d33cb4f0'
        except sqlite3.Error as e:
            logging.error(f"Ошибка при подключении к базе данных: {e}")
            print(f"Ошибка при подключении к базе данных: {e}")

    def load_or_generate_key(self):
        key_file = 'encryption_key.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as key_file:
                key = key_file.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as key_file:
                key_file.write(key)
        return key

    def encrypt_password(self, password):
        cipher_suite = Fernet(self.key)
        encrypted_password = cipher_suite.encrypt(password.encode())
        return base64.b64encode(encrypted_password).decode()

    def decrypt_password(self, encrypted_password):
        cipher_suite = Fernet(self.key)
        decoded_password = base64.b64decode(encrypted_password.encode())
        decrypted_password = cipher_suite.decrypt(decoded_password)
        return decrypted_password.decode()

    def create_tables(self):
        try:
            with self.conn:
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        balance REAL NOT NULL DEFAULT 0
                    )
                ''')
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании таблицы: {e}")
            print(f"Ошибка при создании таблицы: {e}")

    def create_user(self, username, password):
        try:
            with self.conn:
                cursor = self.conn.execute("SELECT * FROM users WHERE username=?", (username,))
                if cursor.fetchone():
                    print("Пользователь с таким именем уже существует.")
                else:
                    encrypted_password = self.encrypt_password(password)
                    self.conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                                      (username, encrypted_password))
                    self.conn.commit()
                    print(f"Пользователь {username} успешно создан.")
                    logging.info(f"Создан новый пользователь: {username}")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при создании пользователя: {e}")
            print(f"Ошибка при создании пользователя: {e}")

    def login(self, username, password):
        try:
            with self.conn:
                cursor = self.conn.execute("SELECT * FROM users WHERE username=?", (username,))
                user = cursor.fetchone()
                if user:
                    decrypted_password = self.decrypt_password(user[2])
                    if decrypted_password == password:
                        user_dict = {'id': user[0], 'username': user[1], 'password': user[2], 'balance': user[3]}
                        print(f"Добро пожаловать, {username}!")
                        self.user_menu(user_dict)
                        logging.info(f"Пользователь вошел в систему: {username}")
                    else:
                        print("Неверное имя пользователя или пароль.")
                else:
                    print("Неверное имя пользователя или пароль.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при входе в систему: {e}")
            print(f"Ошибка при входе в систему: {e}")

    def user_menu(self, user):
        while True:
            try:
                print("\nВыберите действие:")
                print("a. Внести сумму на счет")
                print("b. Снять со счета")
                print("c. Просмотреть баланс счета")
                print("d. Конвертировать валюту")
                print("e. Выйти в главное меню")
                print("f. Выйти")

                choice = input("Ваш выбор: ").lower()

                if choice == 'a':
                    amount = float(input("Введите сумму для внесения на счет: "))
                    self.deposit(user, amount)
                elif choice == 'b':
                    amount = float(input("Введите сумму для снятия со счета: "))
                    self.withdraw(user, amount)
                elif choice == 'c':
                    self.check_balance(user)
                elif choice == 'd':
                    self.currency_converter(user)
                elif choice == 'e':
                    break  # Выйти в главное меню
                elif choice == 'f':
                    exit()  # Выйти из программы
                else:
                    print("Неверный выбор. Попробуйте еще раз.")
            except ValueError:
                print("Ошибка ввода. Пожалуйста, введите корректное значение.")

    def deposit(self, user, amount):
        try:
            with self.conn:
                new_balance = user['balance'] + amount
                self.conn.execute("UPDATE users SET balance=? WHERE id=?", (new_balance, user['id']))
                self.conn.commit()
                print(f"Сумма {amount} успешно внесена на счет. Новый баланс: {new_balance}")
                logging.info(f"Пользователь {user['username']} внес на счет {amount}. Новый баланс: {new_balance}")
                self.log_transaction(user['username'], 'Внесение', amount)

                # Update user_dict with the new balance
                user['balance'] = new_balance

        except sqlite3.Error as e:
            logging.error(f"Ошибка при внесении средств: {e}")
            print(f"Ошибка при внесении средств: {e}")

    def withdraw(self, user, amount):
        try:
            if user['balance'] >= amount:
                with self.conn:
                    new_balance = user['balance'] - amount
                    self.conn.execute("UPDATE users SET balance=? WHERE id=?", (new_balance, user['id']))
                    self.conn.commit()
                    print(f"Сумма {amount} успешно снята со счета. Новый баланс: {new_balance}")
                    logging.info(f"Пользователь {user['username']} снял со счета {amount}. Новый баланс: {new_balance}")
                    self.log_transaction(user['username'], 'Снятие', amount)

                    # Update user_dict with the new balance
                    user['balance'] = new_balance
            else:
                print("Недостаточно средств на счете.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при снятии средств: {e}")
            print(f"Ошибка при снятии средств: {e}")

    def check_balance(self, user):
        print(f"Текущий баланс счета пользователя {user['username']}: {user['balance']}")

    def get_exchange_rates(self):
        try:
            url = f'https://open.er-api.com/v6/latest?apikey={self.api_key}'
            params = {'base': 'KZT'}
            response = requests.get(url, params=params)
            response.raise_for_status()  # Проверяем наличие ошибок в ответе

            exchange_rates = response.json()['rates']
            return exchange_rates
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении данных о курсах валют: {e}")
            logging.error(f"Ошибка при получении данных о курсах валют: {e}")

    def currency_converter(self, user):
        try:
            print("\nВыберите валюту, в которую хотите конвертировать счет:")
            print("a. Доллары США (USD)")
            print("b. Евро (EUR)")
            print("c. Российские рубли (RUB)")
            print("d. Выйти в главное меню")

            choice = input("Ваш выбор: ")

            if choice == 'a':
                self.convert_currency(user, 'USD')
            elif choice == 'b':
                self.convert_currency(user, 'EUR')
            elif choice == 'c':
                self.convert_currency(user, 'RUB')
            elif choice == 'd':
                return  # Выход в главное меню
            else:
                print("Неверный выбор. Пожалуйста, введите корректное значение.")
        except ValueError:
            print("Ошибка ввода. Пожалуйста, введите корректное значение.")

    def convert_currency(self, user, target_currency):
        try:
            amount = float(input("Введите сумму для конвертации: "))
            base_currency = 'KZT'

            exchange_rates = self.get_exchange_rates()
            conversion_rate = exchange_rates.get(target_currency)

            if conversion_rate is not None:
                converted_amount = amount * conversion_rate
                print(f"{amount} {base_currency} равны {converted_amount:.2f} {target_currency}")
                logging.info(
                    f"Пользователь {user['username']} сконвертировал {amount} {base_currency} в {converted_amount:.2f} {target_currency}")
                self.log_transaction(user['username'], 'Конвертация валюты', amount, target_currency)
            else:
                print(f"Ошибка при получении курса конвертации для валюты: {target_currency}")
                logging.error(f"Ошибка при получении курса конвертации для валюты: {target_currency}")
        except (ValueError, requests.exceptions.RequestException) as e:
            print(f"Ошибка при конвертации валюты: {e}")
            logging.error(f"Ошибка при конвертации валюты: {e}")

    def log_transaction(self, username, action, amount=None, target_currency=None):
        log_entry = f"{username}: {action}"
        if amount is not None:
            log_entry += f", Amount: {amount}"
        if target_currency is not None:
            log_entry += f", Target Currency: {target_currency}"

        try:
            with open('transaction_log.txt', 'a') as log_file:
                log_file.write(log_entry + '\n')
        except IOError as e:
            logging.error(f"Ошибка записи в журнал транзакций: {e}")

    def __del__(self):
        try:
            self.conn.close()
        except sqlite3.Error as e:
            logging.error(f"Ошибка при закрытии соединения с базой данных: {e}")
            print(f"Ошибка при закрытии соединения с базой данных: {e}")


def main():
    bank_system = BankManagementSystem()

    while True:
        try:
            print("\nГлавное меню:")
            print("a. Создать пользователя")
            print("b. Войти")
            print("c. Выйти")

            choice = input("Ваш выбор: ").lower()

            if choice == 'a':
                username = input("Введите имя пользователя: ")
                password = input("Введите пароль: ")
                bank_system.create_user(username, password)
            elif choice == 'b':
                username = input("Введите имя пользователя: ")
                password = input("Введите пароль: ")
                bank_system.login(username, password)
            elif choice == 'c':
                break
            else:
                print("Неверный выбор. Попробуйте еще раз.")
        except Exception as e:
            print(f"Произошла ошибка: {e}")
        finally:
            bank_system.log_transaction('Система', 'Выход из программы')


if __name__ == "__main__":
    main()
