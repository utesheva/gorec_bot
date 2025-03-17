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
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
ADMIN = config.admin.get_secret_value()

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
        await callback.message.answer_photo(user[2], f"Вы уже зарегестрированы со следующими данными.\n\nФИО: {user[1]}\n\nФото: \n\nХотите изменить?",
                                      reply_markup = check.as_markup())
        return
    await callback.message.answer('Введите ФИО')
    await state.set_state(Registration.name)


@dp.callback_query(F.data == 'fix')
async def fix_registration(callback: CallbackQuery, state: FSMContext):
    await db.delete_user(str(callback.from_user.id))
    await callback.message.answer('Введите ФИО')
    await state.set_state(Registration.name)


@dp.message(F.text, Registration.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Отправьте фото:')
    await state.set_state(Registration.photo)


@dp.message(Registration.photo)
async def process_photo(message: Message, state: FSMContext):
    try:
        photo_link = message.photo[-1].file_id
    except Exception as e:
        await message.answer('Ошибка в регистрации, пройдите её заново')
        await state.clear()
        await callback.message.answer('Введите ФИО')
        await state.set_state(Registration.name)
        return
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

    await message.answer_photo(photo_link, caption=f"Ваши данные:\n\nФИО: {data['name']}\n\nФото: ",
                         reply_markup = check.as_markup())

@dp.callback_query(F.data == 'finish_registration')
async def finish_registration(callback: CallbackQuery, state: FSMContext):
    global bot
    data = await state.get_data()
    await db.register_user(callback.from_user.id, data['name'], data['photo'])
    await callback.message.answer('Вы успешно прошли регистрацию! Ждите дальнейших указаний')
    await bot.send_photo(chat_id=ADMIN, photo=data['photo'], caption=f"Новый участник: {data['name']}")
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

    users = await db.get_tg_ids()
    for user_id in users:
        victim = await db.get_victim(str(user_id[0]))
        victim_data = await db.get_user_by_id(victim)
        try:
            await message.bot.send_photo(chat_id=user_id[0], photo=victim_data[2], caption=f"Твоя жерва: {victim_data[1]}")
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {user_id[0]}: {e}")
    await message.answer('Рассылка завершена.')
    await state.clear()
    
@dp.message(F.text, Command("rating"))
async def get_rating(message: Message, state: FSMContext):
    rating = await db.get_rating()
    for i in range(len(rating)):
        await message.answer(f"{i+1} место: {rating[i]}")
    await state.clear()


@dp.message(F.text, Command("kill"))
async def register_kill(message: Message, state: FSMContext):
    if await db.is_dead(str(message.from_user.id)):
        await message.answer('К сожалению, вы уже выбыли из игры.')
        return
    users = await db.get_data()
    check = InlineKeyboardBuilder()
    check.add(InlineKeyboardButton(
        text="Подтверждаю",
        callback_data="agree")
    )
    check.add(InlineKeyboardButton(
        text = 'Он(а) врет',
        callback_data='refuse'
    ))
    user = await db.get_user(str(message.from_user.id))
    if user[3]:
        victim = await db.get_victim(str(message.from_user.id))
        victim_data = await db.get_user_by_id(victim)
        await message.bot.send_message(victim[4], "Подтвердите, что вы были убиты", reply_markup=check.as_markup)
    else:
        await message.answer('Игра ещё не началась.')


@dp.callback_query(F.data == 'agree')
async def confirm_kill(message: Message, state: FSMContext):
    await db.make_dead(str(message.from_user.id))
    killer = await db.get_killer(str(message.from_user.id))
    killer_data = await db.get_user_by_id(killer)
    new_victim = await db.get_victim(str(message.from_user.id))
    await db.set_victim(str(killer), new_victim)
    victim_data = await db.get_user_by_id(new_victim)
    await message.bot.send_photo(killer_data[4], victim_data[2], f"Подтверждение получено, вы получили свои баллы. Ваша новая жертва: {victim_data[1]}")


@dp.callback_query(F.data == 'refuse')
async def reject_kill(message: Message, state: FSMContext):
    killer = await db.get_killer(str(message.from_user.id))
    await message.bot.send_message(int(killer), f"Ваша жертва отказывается признавать свою смерть. Ожидайте решения администраторов")
    

async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
