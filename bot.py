
from datetime import datetime
import io
import sqlite3
import os
from venv import logger
from PIL import Image
from aiogram import types
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, callback_query, Update
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from telegram.ext import CallbackContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InputFile
from typing import Union
from typing import List
import shortuuid

# Создаем базу данных и таблицы
from aiogram.utils import executor

conn = sqlite3.connect('menu.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY,
        item_name TEXT,
        description TEXT,
        price INTEGER,
        photo TEXT
    )
''')
conn.commit()

# Добавляем товары в базу данных
cursor.execute('''INSERT OR IGNORE INTO menu (id, item_name, description, price, photo) 
                VALUES (1, 'Романза','Сорт "Романза" - идеальное сочетание сладости и свежести. Попробуйте его сегодня и наслаждайтесь незабываемым вкусом лета!', 10, 'photos/romanza.jpg')''')
cursor.execute('''INSERT OR IGNORE INTO menu (id, item_name, description, price, photo) 
                VALUES (2, 'Топ Ган', 'Сорт "Топ Ган" - арбуз, который заставит вас влюбиться в него с первого кусочка. Это идеальный выбор для тех, кто ищет качественный и вкусный продукт.', 5, 'photos/top_gan.jpg')''')
cursor.execute('''INSERT OR IGNORE INTO menu (id, item_name, description, price, photo)
                VALUES (3, 'Семена f2', 'Кратко описать', 3, 'photos/Поле.jpg')''')
conn.commit()
conn.close()

# # удаляем базу
# if os.path.exists('check.db'):
#     os.remove('check.db')

# Подключение к базе данных
conn = sqlite3.connect('check.db')
cursor = conn.cursor()

# Создание таблицы orders
cursor.execute('''CREATE TABLE IF NOT EXISTS orders
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 user_name TEXT,
                 item_name TEXT,
                 quantity INTEGER,
                 price INTEGER,
                 name TEXT,
                 phone TEXT,
                 address TEXT,
                 date TEXT,
                 time TEXT)''')

# Создаем столбец item_id в таблице orders
# cursor.execute("ALTER TABLE orders ADD COLUMN item_id INTEGER;")

# Удаляем столбец в таблице orders
# cursor.execute("ALTER TABLE orders DROP COLUMN referral_id;")
# cursor.execute("ALTER TABLE orders DROP COLUMN referral_source;")


# Создание таблицы users
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                (user_id INTEGER PRIMARY KEY)''')

conn.commit()

conn = sqlite3.connect('check.db')
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER NOT NULL,
        order_placed INTEGER DEFAULT 0
    )
""")
conn.commit()
conn.close()

# Задаем API токен для бота
bot = Bot(token='')

# Создаем объект Dispatcher для обработки событий бота
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Создаем класс, который будет хранить состояние пользователя
class OrderInfo(StatesGroup):
    item_name = State()
    quantity = State()
    confirmation = State()
    name = State()
    phone = State()
    address = State()


class OrderState(StatesGroup):
    choosing = State()  # начальное состояние
    waiting_next_item = State()


# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message, state: FSMContext):
    # Создаем кнопки меню и о нас
    keyboard_markup = InlineKeyboardMarkup(row_width=2)
    menu_button = InlineKeyboardButton('Меню', callback_data='menu')
    about_button = InlineKeyboardButton('О нас', callback_data='about')
    keyboard_markup.add(menu_button, about_button)

    # Отправляем сообщение приветствия и кнопки
    tx_1 = "Добро пожаловать!\nЗабирай любимые вкусняшки 🍉 по ВЫГОДНОЙ цене и в Отличном качестве!"
    photo = open('photos/Эмблема КФХ.jpg', 'rb')
    # Очищаем состояние пользователя
    await state.finish()

    await bot.send_photo(message.chat.id, photo, caption=tx_1, reply_markup=keyboard_markup)


@dp.callback_query_handler(lambda c: c.data.startswith('menu'))
async def process_menu_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    page_number = 0
    if 'page_number' in callback_query.data:
        page_number = int(callback_query.data.split('_')[2])
    elif 'prev' in callback_query.data:
        page_number = int(callback_query.data.split('_')[2]) - 1
    elif 'next' in callback_query.data:
        page_number = int(callback_query.data.split('_')[2]) + 1

    await send_menu_page(callback_query.message.chat.id, page_number)


async def send_menu_page(chat_id, page_number):
    items, total_pages = get_items_from_db(page_number)

    if items:
        item = items[0]

        # Открываем изображение
        with open(item[4], 'rb') as photo_file:
            image = Image.open(photo_file)

            # Меняем размер изображения до нужных значений, сохраняя соотношение сторон
            new_size = (800, 600)  # задаем новый размер
            image.thumbnail(new_size, resample=Image.LANCZOS)

            # Конвертируем изображение в байтовую строку
            image_byte_array = io.BytesIO()
            image.save(image_byte_array, format='JPEG')
            image_data = image_byte_array.getvalue()

        message_text = f'{item[1]}\n{item[2]}\n{item[3]} руб.\n\n'
        keyboard_markup = InlineKeyboardMarkup(resize_keyboard=True)  # Добавляем параметр resize_keyboard=True
        add_to_cart_button = InlineKeyboardButton('🛒', callback_data=f'add_to_cart_{item[0]}')
        prev_button = InlineKeyboardButton('◄', callback_data=f'menu_prev_{page_number}')
        next_button = InlineKeyboardButton('►', callback_data=f'menu_next_{page_number}')
        keyboard_markup.row(prev_button, add_to_cart_button, next_button)

        # Отправляем измененное изображение вместе с текстом и кнопками
        await bot.send_photo(chat_id, photo=image_data, caption=message_text, reply_markup=keyboard_markup)

        # Получаем выбранный товар и его информацию из callback-данных
        item_id, quantity, price, total_price = callback_query.data.split('_')[1:]
        item = menu[int(item_id)]

        # Сохраняем информацию о выбранном товаре в состоянии пользователя
        await state.update_data(item_id=item_id, item_name=item[1], quantity=quantity, price=price,
                                total_price=total_price)


def get_items_from_db(page_number):
    with sqlite3.connect('menu.db') as conn:
        cursor = conn.cursor()
        page_size = 1
        offset = page_size * page_number
        limit = page_size

        cursor.execute(f'SELECT * FROM menu LIMIT {limit} OFFSET {offset}')
        items = cursor.fetchall()

        cursor.execute('SELECT COUNT(*) FROM menu')
        items_count = cursor.fetchone()[0]
        total_pages = items_count // page_size + (1 if items_count % page_size > 0 else 0)

        return items, total_pages


# Обработчик кнопки "О нас"
@dp.callback_query_handler(text='about')
async def process_about_callback(callback_query: types.CallbackQuery):
    # Удаляем кнопки
    await bot.answer_callback_query(callback_query.id)
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

    # Отправляем фотографию и текст о нас из папки photos
    photo_path = os.path.join(os.getcwd(), 'photos', 'КФХ_семья.jpg')
    message_text = 'КФХ "Красный Борок" было основано в 2017 году и специализируется на выращивании арбуза. Мы гордимся тем, что предлагаем одни из лучших продуктов в Беларуси благодаря тщательному отбору сортов и строгому контролю качества. Наша команда всегда готова помочь и ответить на любые вопросы, связанные с нашей продукцией, чтобы обеспечить нашим клиентам превосходный сервис.'
    await bot.send_photo(callback_query.message.chat.id, photo=InputFile(photo_path), caption=message_text)


# Обработчик кнопки "В корзину"
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('add_to_cart_'))
async def process_add_to_cart_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем ID товара из callback_data
    item_id = int(callback_query.data.split('_')[-1])

    # Сохраняем ID товара в состоянии пользователя
    await state.update_data(item_id=item_id)

    # Спрашиваем количество товара
    message_text = 'Введите количество товара:'
    await bot.send_message(callback_query.message.chat.id, message_text)
    await OrderInfo.quantity.set()


# Обработчик сообщения с количеством товара
@dp.message_handler(state=OrderInfo.quantity)
async def process_quantity_command(message: types.Message, state: FSMContext):
    # Получаем ID товара и количество товара из состояния пользователя
    data = await state.get_data()
    item_id = data['item_id']
    quantity = int(message.text)

    # Получаем информацию о товаре из базы данных
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM menu WHERE id={item_id}')
    item = cursor.fetchone()
    conn.close()

    # Считаем стоимость товара
    price = item[3] * quantity

    # Сохраняем информацию о товаре и его стоимости в состоянии пользователя
    await state.update_data(item_name=item[1], quantity=quantity, price=price)

    # Отправляем сообщение с информацией о товаре и кнопками
    message_text = f'Вы выбрали <b>{item[1]}</b> в количестве {quantity} шт.\nСтоимость: {price} руб.'
    keyboard_markup = InlineKeyboardMarkup()
    continue_button = InlineKeyboardButton('Продолжить', callback_data='continue')
    confirm_button = InlineKeyboardButton('Заказать', callback_data='confirm')
    # cancel_button = InlineKeyboardButton('Отменить', callback_data='cancel')
    keyboard_markup.add(continue_button, confirm_button)  # cancel_button)
    await message.reply(message_text, reply_markup=keyboard_markup, parse_mode=ParseMode.HTML)

    # Переходим в состояние ожидания действия пользователя
    await OrderInfo.next()

    def get_menu_keyboard():
        # Получаем информацию о товарах из базы данных
        conn = sqlite3.connect('menu.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM menu')
        items = cursor.fetchall()
        conn.close()

        keyboard_markup = InlineKeyboardMarkup()
        for item in items:
            item_button = InlineKeyboardButton(f'{item[1]} ({item[3]} руб.)', callback_data=f'item_{item[0]}')
            keyboard_markup.add(item_button)

        return keyboard_markup


# Обработчик выбора товара
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('item_'), state=OrderInfo)
async def process_item_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем ID товара из callback_data
    item_id = int(callback_query.data.split('_')[-1])

    # Получаем информацию о товаре из базы данных
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM menu WHERE id={item_id}')
    item = cursor.fetchone()
    # conn.close()

    # Считаем стоимость товара и общую стоимость
    quantity = 1
    price = item[3] * quantity
    data = await state.get_data()
    total_price = data.get('total_price', 0)
    total_price += price

    # Сохраняем информацию о товаре и его стоимости в базе данных
    cursor.execute(
        f"INSERT INTO orders (item_id, item_name, quantity, price) VALUES ({item_id}, '{item[1]}', {quantity}, {price})")
    conn.commit()
    conn.close()

    # Сохраняем информацию о товаре и его стоимости в состоянии пользователя
    await state.update_data(item_id=item_id, item_name=item[1], quantity=quantity, price=price, total_price=total_price)

    # Отправляем сообщение с информацией о товаре и кнопками
    message_text = f'Вы выбрали <b>{item[1]}</b> в количестве {quantity} шт.\nОбщая стоимость: {total_price} руб.'
    keyboard_markup = InlineKeyboardMarkup()
    continue_button = InlineKeyboardButton('Продолжить', callback_data='menu')
    confirm_button = InlineKeyboardButton('Заказать', callback_data='confirm')
    keyboard_markup.add(continue_button, confirm_button)
    await bot.send_message(callback_query.message.chat.id, message_text, reply_markup=keyboard_markup, parse_mode=ParseMode.HTML)

    # Переходим в состояние ожидания действия пользователя
    await OrderInfo.next()


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('add_to_cart'), state=OrderState.choosing)
async def process_add_to_cart_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем информацию о товарах из базы данных
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders')
    rows = cursor.fetchall()

    # Формируем список товаров и общую стоимость
    items = []
    total_price = 0
    for row in rows:
        item = f"{row[1]} - {row[2]} шт. - {row[4]} руб."
        items.append(item)
        total_price += row[4]

    # Отправляем сообщение с информацией о товарах и общей стоимости
    text = "Ваша корзина:\n" + "\n".join(items) + f"\n\nИтого: {total_price} руб."
    await bot.send_message(chat_id=callback_query.from_user.id, text=text)

    # Закрываем соединение с базой данных
    conn.close()


async def remove_item_callback(update: Update, context: CallbackContext):
    callback_query = update.callback_query
    item_id = callback_query.data.split("_")[1]

    # Удаляем информацию о товаре из базы данных
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM orders WHERE item_id={item_id}")
    conn.commit()

    # Получаем информацию о товарах из базы данных
    cursor.execute('SELECT * FROM orders')
    rows = cursor.fetchall()

    # Формируем список товаров и общую стоимость
    items = []
    total_price = 0
    for row in rows:
        item = f"{row[1]} - {row[2]} шт. - {row[4]} руб."
        items.append(item)
        total_price += row[4]

    # Сохраняем информацию о товарах и их стоимости в состоянии пользователя
    await context.bot.send_message(chat_id=callback_query.from_user.id, text=text)

    # Отправляем сообщение с информацией о товарах и общей стоимости
    text = "Ваша корзина:\n" + "\n".join(items)
    if not items:
        text = "Ваша корзина пуста"
    else:
        text += f"\n\nИтого: {total_price} руб."
    await context.bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                text=text)

    # Закрываем соединение с базой данных
    conn.close()


async def checkout_callback(update: Update, context: CallbackContext):
    callback_query = update.callback_query

    # Получаем информацию о товарах из базы данных
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders')
    rows = cursor.fetchall()

    # Формируем список товаров и общую стоимость
    items = []
    total_price = 0
    for row in rows:
        item = f"{row[1]} - {row[2]} шт. - {row[4]} руб."
        items.append(item)
        total_price += row[4]

    # Отправляем сообщение с информацией о заказе
    text = "Новый заказ:\n" + "\n".join(items) + f"\n\nИтого: {total_price} руб."
    await bot.send_message(chat_id=CHAT_ID, text=text)

    # Очищаем состояние пользователя и базу данных
    await state.reset_data()
    cursor.execute('DELETE FROM orders')
    conn.commit()

    # Отправляем сообщение об успешном оформлении заказа
    text = "Ваш заказ успешно оформлен. Ожидайте звонка оператора для подтверждения заказа."
    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                text=text)

    # Закрываем соединение с базой данных
    conn.close()

# Обработчик кнопки "Заказать"
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'confirm', state=OrderInfo)
async def process_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем информацию о товарах из состояния пользователя
    data = await state.get_data()
    item_name = data['item_name']
    quantity = data['quantity']
    price = data['price']

    # Переходим к состоянию получения информации о пользователе
    await OrderInfo.name.set()
    await bot.send_message(callback_query.message.chat.id, 'Введите свое имя:')


# Обработчик состояния получения имени пользователя
@dp.message_handler(state=OrderInfo.name)
async def process_name(message: types.Message, state: FSMContext):
    # Сохраняем имя пользователя в состоянии
    await state.update_data(name=message.text)

    # Переходим к состоянию получения номера телефона
    await OrderInfo.phone.set()
    await bot.send_message(message.chat.id, 'Введите свой номер телефона:')


# Обработчик состояния получения номера телефона пользователя
@dp.message_handler(state=OrderInfo.phone)
async def process_phone(message: types.Message, state: FSMContext):
    # Сохраняем номер телефона пользователя в состоянии
    await state.update_data(phone=message.text)

    # Переходим к состоянию получения адреса пользователя
    await OrderInfo.address.set()
    await bot.send_message(message.chat.id, 'Введите свой адрес:')


# Обработчик состояния получения адреса пользователя
@dp.message_handler(state=OrderInfo.address)
async def process_address(message: types.Message, state: FSMContext):
    # Сохраняем адрес пользователя в состоянии
    await state.update_data(address=message.text)

    # Получаем информацию о товарах и пользователе из состояния
    data = await state.get_data()
    item_name = data['item_name']
    quantity = data['quantity']
    price = data['price']
    name = data['name']
    phone = data['phone']
    address = data['address']

    try:
        # Получение текущей даты и времени
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        # Сохраняем заказ в базе данных
        conn = sqlite3.connect('check.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO orders (user_id, user_name, item_name, quantity, price, name, phone, address, date, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (message.from_user.id, message.from_user.username, data.get('item_name'), data.get('quantity'),
             data.get('price'), data.get('name'), data.get('phone'), data.get('address'), date, time))
        conn.commit()
        conn.close()

        # Отправляем сообщение с подтверждением заказа
        message_text = f'Заказ подтвержден:\nВы заказали <b>{item_name}</b> в количестве {quantity} шт.\nСтоимость: {price} руб.\n\nДанные для доставки:\nИмя: {name}\nНомер телефона: {phone}\nАдрес: {address}'
        keyboard_markup1 = InlineKeyboardMarkup()
        discount_button = InlineKeyboardButton('СКИДКА', callback_data='get_discount')
        keyboard_markup1.add(discount_button)
        await bot.send_message(message.chat.id, message_text, reply_markup=keyboard_markup1, parse_mode=ParseMode.HTML)

        # Возвращаемся к состоянию ожидания выбора товара
        await state.finish()
    except Exception as e:
        await bot.send_message(message.chat.id, f'Произошла ошибка при сохранении заказа: {e}')
        print('Ошибка сохранения заказа в базу данных:', e)




# Обработчик команды /menu
@dp.message_handler(commands=['menu'])
async def process_menu_command(message: types.Message):
    # Получаем список товаров из базы данных
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM my_table')
    row = cursor.fetchone()
    # Обработка результата
    cursor.close()
    conn.close()

    # Создаем список кнопок товаров
    keyboard_markup = InlineKeyboardMarkup(row_width=2)
    for item in items:
        item_button = InlineKeyboardButton(item[1], callback_data=f'show_item_{item[0]}')
        add_to_cart_button = InlineKeyboardButton('🛒', callback_data=f'add_to_cart_{item[0]}')
        keyboard_markup.add(item_button, add_to_cart_button)

    # Отправляем сообщение с кнопками товаров
    message_text = 'Меню ресторана:'
    await message.reply(message_text, reply_markup=keyboard_markup)


@dp.message_handler(commands=['orders'])
async def process_orders_command(message: types.Message):
    # Получаем список заказов из базы данных
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders')
    orders = cursor.fetchall()
    conn.close()

    # Создаем сообщение со списком заказов
    if orders:
        message_text = 'Список заказов:\n\n'
        for order in orders:
            message_text += f'- {order[1]} в количестве {order[2]} шт. на сумму {order[3]} руб.\n'
    else:
        message_text = 'Список заказов пуст.'

    # Отправляем сообщение со списком заказов
    await message.reply(message_text)


# Обработчик неизвестной команды
@dp.message_handler()
async def process_unknown_command(message: types.Message):
    # Отправляем сообщение с подсказкой по командам
    message_text = 'Я не знаю такой команды. Вот список доступных команд:\n\n/menu - посмотреть меню ресторана\n/orders - посмотреть список заказов\n/about - информация о нас'
    await message.reply(message_text)


@dp.errors_handler()
async def process_errors(update: types.Update, exception: Exception):
    # Логируем ошибку
    logger.error(f'Update {update} caused error {exception}')
    # Отправляем сообщение об ошибке пользователю
    if update.message is not None:
        message_text = 'Произошла ошибка. Пожалуйста, попробуйте еще раз.'
        await update.message.answer(message_text)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
