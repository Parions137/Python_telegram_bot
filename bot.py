import time
import logging
import requests
import datetime

from config import BOT_TOKEN, WEATHER_TOKEN # Берем нужные токены из файла

from sql import db_start, create_profile, edit_profile # подключение бд

#Импортирование из библеотеки aiogram
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import BotBlocked
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

#Глобальные переменные
storage = MemoryStorage()
number = 0
TOKEN = BOT_TOKEN
HELP_COMMAND = """
/give - стикер от бота
/definition - описание бота
/photo - фото от бота
/contact - клавиатура
/vote - голосование
/remind - напоминание
/weathere - прогноз погоды
"""

# Запуск работы с бд
async def on_start_up(_):
    await db_start()
    


# Клавиатура Меню
menu = ReplyKeyboardMarkup(resize_keyboard=True)
#mb7 = KeyboardButton('/definition')#
mb1 = KeyboardButton('Погода🌡️')
#mb2 = KeyboardButton('/give')
#mb3 = KeyboardButton('/photo')
mb4 = KeyboardButton('Где меня найти👨‍💻')
#mb5 = KeyboardButton('/vote')
mb6 = KeyboardButton('Напоминание🕓')

menu.add(mb1,mb4,mb6)



# Клавиатура для новых пользователей 
kb = ReplyKeyboardMarkup(resize_keyboard=True,
                         one_time_keyboard=True) #default = false 
b1 = KeyboardButton('✨Создать профиль✨')
kb.add(b1)

# Токен API и инициализация диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage = storage)


# Приветсвие и удаление сообщение пользователя
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await bot.send_message(chat_id=message.from_user.id,
                           text='Добро пожаловать к нам! Для того чтобы начать пользоваться ботом необходимо произвести регистрацию!',
                           reply_markup=kb)
    await message.delete()
    await create_profile(user_id=message.from_user.id)

# Класс в котором описаны состояния создания профиля
class ProfileStatesGroup(StatesGroup):
    photo = State()
    name = State()
    age = State()
    description = State()

class ProfileWeather(StatesGroup):
    city = State()
    
# Клавиатура отмены в create 
def get_cancel_kb() -> ReplyKeyboardMarkup:
    ckb =ReplyKeyboardMarkup(resize_keyboard=True)
    ckb.add(KeyboardButton('/cancel'))
    return ckb

# Отмена создания анкеты
@dp.message_handler(commands=['cancel'], state='*')
async def cancel_command(message: types.Message, state: FSMContext):
    if state is None:
        return
    await state.finish()
    await message.answer('Создание прервано',
                         reply_markup=kb)

# обработка ошибки если отправлена не фотография
@dp.message_handler(lambda message: not message.photo, state=ProfileStatesGroup.photo)
async def check_photo(message: types.Message):
    await message.reply('Это не фотография!')

# Переходим в создание анкеты
@dp.message_handler(lambda message: message.text == "✨Создать профиль✨")
async def create_command(message: types.Message) -> None:
    await message.answer("Давай начнем! Для начала пришли мне фото профиля",
                         reply_markup=get_cancel_kb())
    await ProfileStatesGroup.photo.set()

# Обработка фотографии в анкете и переход в следующее состояние
@dp.message_handler(content_types=['photo'], state=ProfileStatesGroup.photo)
async def load_photo(message: types.Message, state: FSMContext)-> None:
    async with state.proxy() as data:
        data['photo'] = message.photo[0].file_id
    await message.reply('Как тебя зовут?')
    await ProfileStatesGroup.next()

# Обработка имени в анкете и переход в следующее состояние
@dp.message_handler(state=ProfileStatesGroup.name)
async def load_name(message: types.Message, state: FSMContext)-> None:
    async with state.proxy() as data:
        data['name'] = message.text
    await message.reply('Сколько тебе лет?')
    await ProfileStatesGroup.next()

# Обработка ошибки при неправильном вводе данных о возрасте
@dp.message_handler(lambda message: not message.text.isdigit() or float(message.text) > 50, state=ProfileStatesGroup.age)
async def check_age(message: types.Message):
    await message.reply('Проверь указанный возраст!')

# Обработка возраста в анкете и переход в следующее состояние
@dp.message_handler(state=ProfileStatesGroup.age)
async def load_age(message: types.Message, state: FSMContext)-> None:
    async with state.proxy() as data:
        data['age'] = message.text
    await message.reply('А теперь расскажи о себе')
    await ProfileStatesGroup.next()

# Обработка информации о себе в анкете и переход в следующее состояние
@dp.message_handler(state=ProfileStatesGroup.description)
async def load_description(message: types.Message, state: FSMContext)-> None:
    async with state.proxy() as data:
        data['description'] = message.text
        await bot.send_photo(chat_id=message.from_user.id,
                             photo=data['photo'],
                             caption=f"{data['name']}, {data['age']}\n{data['description']}",
                             reply_markup=menu)
    await edit_profile(state, user_id=message.from_user.id)
    await message.reply('Ваша анкета успешно создана')
    await state.finish()

@dp.message_handler(lambda message: message.text == "Погода🌡️") # Найти способ как использовать этот вариант и использовать commands=['weather'] !!!!
async def weather_command(message: types.Message):
    await message.answer("Давай узнаем погоду! Введи название города")
    await ProfileWeather.city.set()
   
   
@dp.message_handler(state=ProfileWeather.city)
async def load_description(message: types.Message, state: FSMContext)-> None:
    code_to_smile = {
        "Clear": "Ясно \U00002600",
        "Clouds": "Облачно \U00002601",
        "Rain": "Дождь \U00002614",
        "Drizzle": "Дождь \U00002614",
        "Thunderstorm": "Гроза \U000026A1",
        "Snow": "Снег \U0001F328",
        "Mist": "Туман \U0001F32B"
    }
    try:
        request = requests.get(
           f"https://api.openweathermap.org/data/2.5/weather?q={message.text}&appid={WEATHER_TOKEN}&units=metric"
        )
        data = request.json()
        city = data["name"]
        tempreture = data["main"]["temp"]
        description = data["weather"][0]["main"]
        if description in code_to_smile:
            wd=code_to_smile[description]
        else:
            wd = "Посмотри в окно, не пойму что за погода!"
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        wind = data["wind"]["speed"]
        sunrise_time = datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
        sunset_time = datetime.datetime.fromtimestamp(data["sys"]["sunset"])
        lenth_of_the_day = datetime.datetime.fromtimestamp(data["sys"]["sunset"]) - datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
        await message.answer(f"***{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}***\n"
              f"Погода в городе: {city} \nТемпература: {tempreture}С° {wd} \n"
              f"Влажность: {humidity}%\nВетер: {wind} м/с \n"
              f"Восход солнца: {sunrise_time}\nЗакат солнца: {sunset_time}\nПродолжительность дня: {lenth_of_the_day}\n"
              f"***Хорошего дня!***",
              reply_markup=menu)
        await state.finish() 
    except:
        await message.reply("Проверьте написание города")
        
#@dp.message_handler()
#async def bot_message(message: types.Message):
 #   if message.text == 'Погода':
        weather_command()
        #await message.answer("Давай узнаем погоду! Введи название города")
        #await ProfileWeather.city.set()    

# Голосование с фото и описанием к нему, выбор из чего голосовать в виде инлайн клавиатуры 
@dp.message_handler(commands=['vote'])
async def vote_command(message: types.Message):
    ikb1 = InlineKeyboardMarkup(row_width=2)
    ibb1 = InlineKeyboardButton(text='❤️', 
                                 callback_data="like_yes")
    ibb2 = InlineKeyboardButton(text='👎',
                                 callback_data="like_no")
    ikb1.add(ibb1,ibb2)
    await bot.send_photo(chat_id=message.from_user.id,
                         photo='https://vsegda-pomnim.com/uploads/posts/2022-04/1651245136_45-vsegda-pomnim-com-p-mandarin-frukt-foto-68.jpg',
                         caption='Нравится ли тебе данная фотография?',
                         reply_markup=ikb1)

# Ответные сообщения на кнопки инлайн клавиатуры в функции /vote
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('like'))
async def vote_callback(callback: types.CallbackQuery):
    if callback.data == 'like_yes':
        await callback.answer(text="Тебе понравилась данная фотография")
    elif callback.data == 'like_no':
        await callback.answer("Тебе не нравится эта фотография")

# Кнопки клавиатуры на сообщении в функции keyboard 
ikb = InlineKeyboardMarkup(row_width=2)
ib1 = InlineKeyboardButton(text = 'Вк',
                            url = "https://vk.com/parions")
ib2 = InlineKeyboardButton(text = 'GitHub',
                            url = "https://github.com/Parions137")
ikb.add(ib1, ib2)

# Функция открывает сообщение с интерактивными кнопками, которые перенаправляют на различные сайты
@dp.message_handler(lambda message: message.text == "Где меня найти👨‍💻")
async def contact_handler(message: types.Message):
    await bot.send_message(chat_id=message.from_user.id,
                           text='Соцсети',
                           reply_markup=ikb)
    await message.delete()
    
# Функция выводит список команд бота (HELP_COMMAND)
@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await bot.send_message(chat_id=message.from_user.id,
                           text=HELP_COMMAND)
    await message.delete()

# Функция отправляет стикер по команде give
@dp.message_handler(commands=['give'])
async def sticker_command(message: types.Message):
    await bot.send_sticker(message.from_user.id,
                           sticker="CAACAgIAAxkBAAEHE0BjrxcW33ElfEB4fj_f2lqb6QQFPwACHAEAAhUiIB3RpiCH2_XQFy0E")
    await message.delete()

# Функция выводит текст с описание функционала бота
@dp.message_handler(commands=['definition'])
async def dsc_command(message: types.Message):
    await bot.send_message(сhat_id=message.from_user.id,
                           text="Бот умеет многое")
    await message.delete()

# Функция выводит фото по команде photo
@dp.message_handler(commands=['photo'])
async def photo_command(message: types.Message):
    await bot.send_photo(message.from_user.id, 
                         photo="https://kartiny-po-nomeram.ru/assets/images/catalog/59412/ds582.jpg")
    await message.delete()

# Автоматическое сообщение с повторяющимся текстом
@dp.message_handler(lambda message: message.text == "Напоминание🕓")
async def remind_command(message: types.Message) -> None:
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    logging.info(f'{user_id=} {user_name} {time.asctime()}')
    for i in range(5):
        time.sleep(5)
        await bot.send_message(user_id,
                               text='Напоминание')
    
# Создание экземпляра клавиатуры для счетчика
def get_inline_keyboard() -> InlineKeyboardMarkup:
    iikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton('Increase', callback_data="btn_increase"), InlineKeyboardButton('Decrease', callback_data="btn_decrease")],
        ])
    return iikb

# Функция выводит сообщение с счетчиком. один счетчик для всех, найти как исправить
@dp.message_handler(commands=['count'])
async def count_command(message: types.Message) -> None:
    await message.answer(f'The current number is {number}',
                         reply_markup=get_inline_keyboard())

# Обработка callback для счетчика. Функционал счетчика
@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('btn'))
async def count_kb_callback(callback: types.CallbackQuery) -> None:
    global number
    if callback.data == 'btn_increase': 
        number +=1
        await callback.message.edit_text(f'The current number is {number}',
                                         reply_markup=get_inline_keyboard())
    elif callback.data == 'btn_decrease':
        number -=1
        await callback.message.edit_text(f'The current number is {number}',
                                         reply_markup=get_inline_keyboard())
    else:
        1/0

# Обработка исключения если бот заблокирован
@dp.errors_handler(exception=BotBlocked)
async def error_bot_blocked(update: types.Update, exeption: BotBlocked) -> bool:
    print('Cant send message')
    return True

# Запуск программы
if __name__ == '__main__':
    executor.start_polling(dispatcher=dp,
                           skip_updates=True,
                           on_startup=on_start_up)