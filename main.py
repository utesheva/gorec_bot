import asyncio
import logging
import sys

from config_reader import config
import db
import texts
from admin import Admin, Access

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.client.default import DefaultBotProperties
from aiogram.types.inline_keyboard_button import InlineKeyboardButton 
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = config.bot_token.get_secret_value()
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_link():
    return 'no photo support yet'

class Registration(StatesGroup):
    name = State()
    photo = State()


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    registr = InlineKeyboardBuilder()
    registr.add(InlineKeyboardButton(
        text="Регистрация",
        callback_data="registration")
    )
    await message.answer(texts.greeting, 
                         reply_markup = registr.as_markup())


@dp.callback_query(F.data == 'registration')
async def registration(callback: CallbackQuery, state: FSMContext):
    users = await db.get_tg_ids()
    print(callback.from_user.id, users)
    if (str(callback.from_user.id),) in users:
        user = await db.get_user(str(callback.from_user.id))
        check = InlineKeyboardBuilder()
        check.add(InlineKeyboardButton(
             text="Всё верно",
             callback_data='wait'
        ))
        check.add(InlineKeyboardButton(
             text = 'Исправить',
             callback_data='fix'
        ))
        await callback.message.answer(f"Вы уже зарегестрированы со следующими данными.\n\nФИО: {user[1]}\n\nФото: {user[2]}\n\nХотите изменить?",
                                      reply_markup = check.as_markup())
        return
    await callback.message.answer('Введите ФИО')
    await state.set_state(Registration.name)


@dp.callback_query(F.data == 'fix')
async def registration(callback: CallbackQuery, state: FSMContext):
    await db.delete_user(str(callback.from_user.id))
    await callback.message.answer('Введите ФИО')
    await state.set_state(Registration.name)


@dp.message(F.text, Registration.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Введите группу')
    await state.set_state(Registration.photo)


@dp.message(F.text, Registration.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_link = get_link()
    await state.update_data(photo=photo_link)
    data = await state.get_data()
    check = InlineKeyboardBuilder()
    check.add(InlineKeyboardButton(
        text="Всё верно",
        callback_data="finish_registration")
    )
    check.add(InlineKeyboardButton(
        text = 'Исправить',
        callback_data='registration'
    ))
    await message.answer(f"Ваши данные:\n\nФИО: {data['name']}\n\nФото: {data['photo']}",
                         reply_markup = check.as_markup())


@dp.callback_query(F.data == 'finish_registration')
async def finish_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await db.register_user(callback.from_user.id, data['name'], data['photo'])
    await callback.message.answer('Вы успешно прошли регистрацию! Ждите дальнейших указаний')
    await state.clear()


@dp.callback_query(F.data == 'wait')
async def wait(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer('Отлично! Отдыхайте и готовьтесь к следующему этапу.')
    await state.clear()


@dp.message(F.text, Command('admin'))
async def admin_mode(message: Message, state: FSMContext):
    if await db.is_admin(str(message.from_user.id)):
        await message.answer('У вас уже есть права администратора.')
        return
    await message.answer('Введите пароль:')
    await state.set_state(Access.password)


@dp.message(Access.password)
async def get_access(message: Message, state: FSMContext):
    if message.text == config.admin_password.get_secret_value():
        await db.make_admin(str(message.from_user.id))
        await message.answer('Верификация пройдена')
    else:
        await message.answer('Пароль неверный')
    await state.clear()



@dp.message(F.text, Command('send_message'))
async def broadcast_command(message: Message, state: FSMContext):
    if not await db.is_admin(str(message.from_user.id)):
        await message.answer('У вас нет прав администратора.')
        return
    await message.answer('Введите сообщение для рассылки:')
    await state.set_state(Admin.message)


@dp.message(Admin.message)
async def process_message(message: Message, state: FSMContext):
    users = await db.get_tg_ids()
    for user_id in users:
        try:
            await message.bot.send_message(user_id[0], message.text)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {user_id[0]}: {e}")
    await message.answer('Рассылка завершена.')
    await state.clear()
    
@dp.message(F.text, Command("shuffle_players"))
async def send_victims(message: Message, state: FSMContext):
    if not await db.is_admin(str(message.from_user.id)):
        await message.answer('У вас нет прав администратора.')
        return
    shuffled_players = await db.shuffle_players()
    if len(shuffled_players) == 0:
        await message.answer('Для старта игры недостаточно игроков')
        return
    users = await db.get_data()
    for user in users:
        try:
            await message.bot.send_message(user[4], f"Your victim is {users[user[3]][4]}")
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {user[0]}: {e}")
    await message.answer('Рассылка завершена.')
    await state.clear()


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
