import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import Database
from monitor import PriceMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
monitor = PriceMonitor(bot, db)


class AddTrack(StatesGroup):
    waiting_for_url = State()
    waiting_for_price = State()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот мониторинга цен.\n\n"
        "Добавь товар, и я уведомлю тебя, когда цена упадёт до нужного уровня.\n\n"
        "📌 Команды:\n"
        "/add — добавить товар\n"
        "/list — мои отслеживания\n"
        "/help — помощь"
    )


@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer("🔗 Отправь ссылку на товар (Wildberries, Ozon, AliExpress):")
    await state.set_state(AddTrack.waiting_for_url)


@dp.message(AddTrack.waiting_for_url)
async def process_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("❌ Некорректная ссылка. Попробуй ещё раз:")
        return

    await state.update_data(url=url)
    msg = await message.answer("⏳ Получаю текущую цену...")

    price = await monitor.fetch_price(url)
    if price is None:
        await msg.edit_text("❌ Не удалось получить цену. Проверь ссылку и попробуй снова.")
        await state.clear()
        return

    await msg.edit_text(
        f"✅ Текущая цена: <b>{price} ₽</b>\n\n"
        f"💰 Укажи целевую цену (при достижении которой я пришлю уведомление):",
        parse_mode="HTML"
    )
    await state.update_data(current_price=price)
    await state.set_state(AddTrack.waiting_for_price)


@dp.message(AddTrack.waiting_for_price)
async def process_target_price(message: types.Message, state: FSMContext):
    try:
        target = float(message.text.replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer("❌ Введи число. Например: 1500 или 1500.50")
        return

    data = await state.get_data()
    url = data["url"]
    current = data["current_price"]

    db.add_track(
        user_id=message.from_user.id,
        url=url,
        current_price=current,
        target_price=target
    )

    await message.answer(
        f"✅ Товар добавлен!\n\n"
        f"🔗 <a href='{url}'>Открыть товар</a>\n"
        f"💵 Текущая цена: <b>{current} ₽</b>\n"
        f"🎯 Целевая цена: <b>{target} ₽</b>\n\n"
        f"Уведомлю тебя, когда цена снизится!",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await state.clear()


@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    tracks = db.get_tracks(message.from_user.id)
    if not tracks:
        await message.answer("📭 У тебя нет активных отслеживаний.\n\nДобавь товар командой /add")
        return

    text = "📋 <b>Твои отслеживания:</b>\n\n"
    for i, t in enumerate(tracks, 1):
        text += (
            f"{i}. <a href='{t['url']}'>Товар</a>\n"
            f"   💵 Сейчас: <b>{t['current_price']} ₽</b>\n"
            f"   🎯 Цель: <b>{t['target_price']} ₽</b>\n\n"
        )

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "1. /add — добавить товар для отслеживания\n"
        "2. Отправь ссылку на товар\n"
        "3. Укажи цену, при которой хочешь получить уведомление\n"
        "4. Бот проверяет цены каждые 30 минут\n\n"
        "🛒 Поддерживаемые магазины:\n"
        "• Wildberries\n• Ozon\n• AliExpress",
        parse_mode="HTML"
    )


async def main():
    await db.init()
    asyncio.create_task(monitor.run_periodic(interval=1800))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
