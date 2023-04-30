import sqlite3
import os
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InputFile
from typing import Union
from typing import List

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

# Задаем API токен для бота
bot = Bot(token='5838405583:AAFWTbm4tDF0y9r4XV5pnJ5POkJrN-leP1I')

# Создаем объект Dispatcher для обработки событий бота
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Создаем класс, который будет хранить состояние пользователя
class Order(StatesGroup):
    item_name = State()
    quantity = State()
    confirmation = State()


# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    # Создаем кнопки меню и о нас
    keyboard_markup = InlineKeyboardMarkup(row_width=2)
    menu_button = InlineKeyboardButton('Меню', callback_data='menu')
    about_button = InlineKeyboardButton('О нас', callback_data='about')
    keyboard_markup.add(menu_button, about_button)

    # Отправляем сообщение приветствия и кнопки
    # await message.reply("Добро пожаловать в наш ресторан!", reply_markup=keyboard_markup)
    tx_1 = "Добро пожаловать!\nЗабирай любимые вкусняшки 🍉 по ВЫГОДНОЙ цене и в Отличном качестве!"
    photo = open('photos/Эмблема КФХ.jpg', 'rb')
    await bot.send_photo(message.chat.id, photo=photo, caption=tx_1, reply_markup=keyboard_markup)



# @dp.callback_query_handler(text='menu')
# async def process_menu_callback(callback_query: types.CallbackQuery):
#     # Удаляем кнопки
#     await bot.answer_callback_query(callback_query.id)
#     await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
#
#     # Получаем список товаров из базы данных
#     with sqlite3.connect('menu.db') as conn:
#         cursor = conn.cursor()
#
#     # Вычисляем значения offset и limit на основе номера страницы и размера страницы
#     page_size = 1
#     page_number = 0
#     if 'page_number' in callback_query.data:
#         page_number = int(callback_query.data.split('_')[2]) + 1
#     elif 'prev' in callback_query.data:
#         page_number = int(callback_query.data.split('_')[2]) - 1
#     elif 'next' in callback_query.data:
#         page_number = int(callback_query.data.split('_')[2]) + 1
#     offset = page_size * page_number
#     limit = page_size
#
#     cursor.execute(f'SELECT * FROM menu LIMIT {limit} OFFSET {offset}')
#     item = cursor.fetchone()
#     conn.close()
#
#     # Создаем сообщение с товаром и кнопками
#     message_text = f'{item[1]}\n{item[2]}\n{item[3]} руб.\n\n'
#     keyboard_markup = InlineKeyboardMarkup()
#     add_to_cart_button = InlineKeyboardButton('В корзину', callback_data=f'add_to_cart_{item[0]}')
#     prev_button = InlineKeyboardButton('⮨', callback_data=f'menu_prev_{page_number}')
#     next_button = InlineKeyboardButton('⮩', callback_data=f'menu_next_{page_number}')
#     keyboard_markup.row(prev_button, add_to_cart_button, next_button)
#     await bot.send_photo(callback_query.message.chat.id, photo=InputFile(item[4]), caption=message_text,
#                          reply_markup=keyboard_markup)
#
#     # Создаем кнопки "назад" и "вперед"
#     keyboard_markup = InlineKeyboardMarkup()
#     if page_number > 0:
#         prev_button = InlineKeyboardButton('⮨', callback_data=f'menu_prev_{page_number}')
#         keyboard_markup.add(prev_button)
#     if cursor.fetchone() is not None:
#         next_button = InlineKeyboardButton('⮩', callback_data=f'menu_next_{page_number}')
#         keyboard_markup.add(next_button)
#
#     await bot.send_message(callback_query.message.chat.id, 'Выберите товар', reply_markup=keyboard_markup)

@dp.callback_query_handler(text='menu')
async def process_menu_callback(callback_query: types.CallbackQuery):
    # Удаляем кнопки
    await bot.answer_callback_query(callback_query.id)
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await bot.send_message(callback_query.message.chat.id, 'Выберите товар')

    # Получаем список товаров из базы данных
    with sqlite3.connect('menu.db') as conn:
        cursor = conn.cursor()

        logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

        def button_click_handler():
            # Выполнение запроса к базе данных
            cursor.execute('SELECT * FROM menu')
            items = cursor.fetchall()

            # Вывод товаров на экран
            for item in items:
                print(item)

            # Запись запроса в лог-файл
            logging.debug('Executed query: SELECT * FROM menu')


        # Вычисляем значения offset и limit на основе номера страницы и размера страницы
        page_size = 1
        page_number = 0
        if 'page_number' in callback_query.data:
            page_number = int(callback_query.data.split('_')[2])
        elif 'prev' in callback_query.data:
            page_number = int(callback_query.data.split('_')[2]) - 1
        elif 'next' in callback_query.data:
            page_number = int(callback_query.data.split('_')[2]) + 1
        offset = page_size * page_number
        limit = page_size

        cursor.execute(f'SELECT * FROM menu ORDER BY id LIMIT {limit} OFFSET {offset}')
        items = cursor.fetchall()

        for item in items:
            print(item)

    conn.close()

    # Создаем сообщение с товаром и кнопками
    item = items[0]
    message_text = f'{item[1]}\n{item[2]}\n{item[3]} руб.\n\n'
    keyboard_markup = InlineKeyboardMarkup()
    add_to_cart_button = InlineKeyboardButton('В корзину', callback_data=f'add_to_cart_{item[0]}')
    prev_button = InlineKeyboardButton('⮨', callback_data=f'menu_prev_{page_number}')
    next_button = InlineKeyboardButton('⮩', callback_data=f'menu_next_{page_number}')
    keyboard_markup.row(prev_button, add_to_cart_button, next_button)
    await bot.send_photo(callback_query.message.chat.id, photo=InputFile(item[4]), caption=message_text,
                         reply_markup=keyboard_markup)

    # Создаем кнопки "назад" и "вперед"
    keyboard_markup = InlineKeyboardMarkup()
    if page_number > 0:
        prev_button = InlineKeyboardButton('⮨', callback_data=f'menu_prev_{page_number - 1}')
        keyboard_markup.add(prev_button)
    if len(items) > 1:
        next_button = InlineKeyboardButton('⮩', callback_data=f'menu_next_{page_number + 1}')
        keyboard_markup.add(next_button)
    await bot.send_message(callback_query.message.chat.id, 'Выберите товар', reply_markup=keyboard_markup)

    # await bot.send_message(callback_query.message.chat.id, 'Выберите товар', reply_markup=keyboard_markup)


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
    await Order.quantity.set()
# Обработчик сообщения с количеством товара
@dp.message_handler(state=Order.quantity)
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
    confirm_button = InlineKeyboardButton('Подтвердить', callback_data='confirm')
    cancel_button = InlineKeyboardButton('Отменить', callback_data='cancel')
    keyboard_markup.add(confirm_button, cancel_button)
    await message.reply(message_text, reply_markup=keyboard_markup, parse_mode=ParseMode.HTML)

    # Переходим в состояние подтверждения заказа
    await Order.confirmation.set()
# Обработчик кнопок "Подтвердить" и "Отменить"
@dp.callback_query_handler(lambda callback_query: callback_query.data in ['confirm', 'cancel'], state=Order.confirmation)
async def process_confirmation_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем информацию о товаре и его стоимости из состояния пользователя
    data = await state.get_data()
    item_name = data['item_name']
    quantity = data['quantity']
    price = data['price']

    # Если пользователь подтверждает заказ
    if callback_query.data == 'confirm':
        try:
            # Сохраняем заказ в базе данных
            conn = sqlite3.connect('orders.db')
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO orders VALUES (NULL, '{item_name}', {quantity}, {price})")
            conn.commit()
            conn.close()

            # Отправляем сообщение с подтверждением заказа
            message_text = f'Ваш заказ на <b>{item_name}</b> в количестве {quantity} шт. на сумму {price} руб. принят!'
            await bot.send_message(callback_query.message.chat.id, message_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            # Обрабатываем ошибку и отправляем сообщение об ошибке
            error_message = f'Произошла ошибка при сохранении заказа: {e}'
            await bot.send_message(callback_query.message.chat.id, error_message)
    # Если пользователь отменяет заказ
    else:
        # Отправляем сообщение с отменой заказа
        message_text = 'Заказ отменен!'
        await bot.send_message(callback_query.message.chat.id, message_text)

        # Очищаем состояние пользователя
        await state.finish()

# Обработчик команды /menu
@dp.message_handler(commands=['menu'])
async def process_menu_command(message: types.Message):
    # Получаем список товаров из базы данных
    # conn = sqlite3.connect('menu.db')
    # cursor = conn.cursor()
    # cursor.execute('SELECT * FROM menu')
    # items = cursor.fetchall()
    # conn.close()

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
        add_to_cart_button = InlineKeyboardButton('В корзину', callback_data=f'add_to_cart_{item[0]}')
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

# Обработчик ошибок
# @dp.errors_handler()
# async def process_errors(update: types.Update, exception: Exception):
#     # Логируем ошибку
#     logger.error(f'Update {update} caused error {exception}')
#     # Отправляем сообщение об ошибке пользователю
#     message_text = 'Произошла ошибка. Пожалуйста, попробуйте еще раз.'
#     await update.message.answer(message_text)

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