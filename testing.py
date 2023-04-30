# Обработчик кнопки "Получить скидку"
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'get_discount', state='*')
async def process_get_discount_callback(callback_query: types.CallbackQuery):
    # Генерируем уникальный идентификатор для ссылки
    referral_link = f'https://t.me/kobrin_bot?start=ref={shortuuid.uuid()}'
    # Отправляем пользователю ссылку
    await bot.send_message(callback_query.message.chat.id, f'Ваша реферальная ссылка:\n{referral_link}')


@dp.message_handler(regexp=r'/start ref=.+')
async def process_referral_link(message: types.Message, state: FSMContext):
    # Извлекаем идентификатор приглашающего пользователя из ссылки
    referrer_id = message.text.split('=')[1]

    # Получаем объект User приглашающего пользователя
    referrer = await message.chat.get_member(referrer_id)

    # Сохраняем полноценный идентификатор приглашающего пользователя в базе данных
    conn = sqlite3.connect('check.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                   (referrer.id, message.from_user.id))
    conn.commit()
    conn.close()

    # Сохраняем идентификатор приглашающего пользователя в состоянии
    await state.update_data(referrer_id=referrer.id)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'confirm', state=OrderInfo)
async def process_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем информацию о товарах из состояния пользователя
    data = await state.get_data()
    item_name = data['item_name']
    quantity = data['quantity']
    price = data['price']

    # Получаем информацию о пользователе из состояния
    data = await state.get_data()
    name = data['name']
    phone = data['phone']
    address = data['address']
    referrer_id = data.get('referrer_id', None)

    # Вычисляем стоимость заказа с учетом скидки
    discount = 0
    if referrer_id:
        # Получаем количество пользователей, которые перешли по ссылке приглашающего пользователя
        conn = sqlite3.connect('check.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM referrals WHERE referrer_id='{referrer_id}'")
        num_referrals = cursor.fetchone()[0]
        conn.close()

        # Вычисляем размер скидки
        if num_referrals >= 10:
            discount = 0.2
        elif num_referrals >= 5:
            discount = 0.1

    total_price = price * quantity * (1 - discount)

    # Отправляем подтверждение заказа пользователю
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id,
                           f"Спасибо за заказ! Вы заказали {quantity} шт. товара '{item_name}' по адресу {address}."
                           f"С вас {total_price} руб.")
    await state.finish()



5838405583:AAFWTbm4tDF0y9r4XV5pnJ5POkJrN-leP1I