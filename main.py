import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo,
    InputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# FSM
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# -----------------------------
# НАСТРОЙКИ
BOT_TOKEN   = ""
CHANNEL_ID  = ""
REF_LINK    = ""
SUPPORT_URL = ""
PARTNER_URL = ""
POLICY_URL  = ""
ADMIN_ID    =    # 🔥 замени на свой реальный user_id, если не он
# -----------------------------

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher(storage=MemoryStorage())

# Храним пользователей
user_ids: set[int] = set()          # для рассылки
usernames: set[str] = set()         # для выгрузки в txt

# ---------- utils ----------
async def is_subscribed(user_id: int) -> bool:
    try:
        cm = await bot.get_chat_member(CHANNEL_ID, user_id)
        return cm.status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
    except Exception:
        return False

def kb_subscribe() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подписаться на канал", url="https://t.me/TGRunn")
    kb.button(text="🔄 Проверить подписку", callback_data="check_sub")
    return kb.as_markup()

def kb_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎮 Играть / Казино", url=REF_LINK))
    kb.row(InlineKeyboardButton(text="🛟 Поддержка", url=SUPPORT_URL))
    kb.row(InlineKeyboardButton(text="🤝 Сотрудничество", url=PARTNER_URL))
    kb.row(InlineKeyboardButton(
        text="📜 Политика",
        web_app=WebAppInfo(url=POLICY_URL)   # Политика открывается как WebApp
    ))
    return kb.as_markup()

def kb_admin() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    kb.row(InlineKeyboardButton(text="📂 Выгрузка пользователей", callback_data="admin_export"))
    return kb.as_markup()

# ---------- ТЕКСТЫ ----------
WELCOME_NEED_SUB = (
    "👋 <b>ПРИВЕТ!</b>\n\n"
    "Ты попал в ОФИЦИАЛЬНЫЙ ПАРТНЁРСКИЙ БОТ TGRun 🎰\n\n"
    "⚡️ ЗДЕСЬ ТЕБЯ ЖДУТ:\n"
    "— Еженедельные ПРОМО 🎁\n"
    "— Спец-предложения 💎\n"
    "— Партнёрка до 50% 🤝\n\n"
    "НО! Чтобы открыть доступ 👉 сначала подпишись на наш канал.\n"
    "После этого жми «Проверить подписку» 👇"
)

WELCOME_OK = (
    "🥳 <b>ПОДПИСКА ПОДТВЕРЖДЕНА!</b>\n\n"
    "Теперь ты в игре 💎\n"
    "Здесь всё работает и всё крутится:\n\n"
    "🎮 Играть и забирать подарки\n"
    "🛟 Получать поддержку\n"
    "🤝 Работать по партнёрке\n"
    "📜 Читать правила\n\n"
    "⚡️ Не тормози — начинай прямо сейчас!"
)

# ---------- START / MENU ----------
@dp.message(CommandStart())
async def on_start(m: types.Message):
    # сохраняем юзера
    user_ids.add(m.from_user.id)
    if m.from_user.username:
        usernames.add(m.from_user.username)

    if await is_subscribed(m.from_user.id):
        await m.answer(WELCOME_OK, reply_markup=kb_main())
    else:
        await m.answer(WELCOME_NEED_SUB, reply_markup=kb_subscribe())

@dp.callback_query(F.data == "check_sub")
async def on_check(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.edit_text(WELCOME_OK, reply_markup=kb_main())
    else:
        await call.answer("Ещё не подписан 🔔", show_alert=True)

@dp.message(Command("menu"))
async def on_menu(m: types.Message):
    if await is_subscribed(m.from_user.id):
        await m.answer("Главное меню:", reply_markup=kb_main())
    else:
        await m.answer("Сначала подпишись на канал 👇", reply_markup=kb_subscribe())

# ---------- АДМИНКА ----------
@dp.message(Command("admin"))
async def on_admin(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.answer("⛔️ У тебя нет доступа.")
    await m.answer("⚙️ Админ-панель", reply_markup=kb_admin())

# ====== FSM для пошаговой рассылки ======
class Broadcast(StatesGroup):
    waiting_text = State()
    waiting_photo = State()
    waiting_buttons = State()
    confirm = State()

def kb_next() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➡️ Дальше", callback_data="skip")
    return kb.as_markup()

def kb_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить", callback_data="do_broadcast")
    kb.button(text="❌ Отмена", callback_data="cancel_broadcast")
    return kb.as_markup()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return
    await state.clear()
    await call.message.answer("✍️ Отправь <b>текст</b> для рассылки:")
    await state.set_state(Broadcast.waiting_text)

@dp.message(Broadcast.waiting_text)
async def bc_text(m: types.Message, state: FSMContext):
    await state.update_data(text=m.text or "")
    await m.answer("📸 Отправь <b>фото</b> для рассылки\nили нажми «Дальше», если без фото.", reply_markup=kb_next())
    await state.set_state(Broadcast.waiting_photo)

@dp.callback_query(F.data == "skip", Broadcast.waiting_photo)
async def bc_skip_photo(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(photo=None)
    await call.message.answer(
        "🔘 Добавь <b>кнопки</b> (каждая с новой строки в формате: <code>Текст - URL</code>)\n"
        "или нажми «Дальше», если без кнопок.",
        reply_markup=kb_next()
    )
    await state.set_state(Broadcast.waiting_buttons)

@dp.message(Broadcast.waiting_photo)
async def bc_photo(m: types.Message, state: FSMContext):
    if not m.photo:
        return await m.answer("Пришли фото или нажми «Дальше».")
    await state.update_data(photo=m.photo[-1].file_id)
    await m.answer(
        "🔘 Добавь <b>кнопки</b> (каждая с новой строки в формате: <code>Текст - URL</code>)\n"
        "или нажми «Дальше», если без кнопок.",
        reply_markup=kb_next()
    )
    await state.set_state(Broadcast.waiting_buttons)

def parse_buttons(text: str) -> InlineKeyboardMarkup | None:
    if not text:
        return None
    kb = InlineKeyboardBuilder()
    any_btn = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if " - " not in line:
            # допускаем разделитель как " - " или " — " или "-" (без пробелов)
            if " — " in line:
                parts = line.split(" — ", 1)
            elif "-" in line:
                parts = line.split("-", 1)
            else:
                continue
        else:
            parts = line.split(" - ", 1)
        text_btn, url = parts[0].strip(), parts[1].strip()
        if not text_btn or not url:
            continue
        kb.row(InlineKeyboardButton(text=text_btn, url=url))
        any_btn = True
    return kb.as_markup() if any_btn else None

async def show_preview(chat_id: int, data: dict):
    text = data.get("text") or ""
    photo = data.get("photo")
    buttons = data.get("buttons")

    if photo:
        await bot.send_photo(chat_id, photo, caption=text, reply_markup=buttons or None)
    else:
        await bot.send_message(chat_id, text, reply_markup=buttons or None)
    await bot.send_message(chat_id, "Предпросмотр 👆\nПодтвердить отправку?", reply_markup=kb_confirm())

@dp.callback_query(F.data == "skip", Broadcast.waiting_buttons)
async def bc_skip_buttons(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(buttons=None)
    data = await state.get_data()
    await show_preview(call.message.chat.id, data)
    await state.set_state(Broadcast.confirm)

@dp.message(Broadcast.waiting_buttons)
async def bc_buttons(m: types.Message, state: FSMContext):
    kb = parse_buttons(m.text or "")
    await state.update_data(buttons=kb)
    data = await state.get_data()
    await show_preview(m.chat.id, data)
    await state.set_state(Broadcast.confirm)

@dp.callback_query(F.data == "do_broadcast", Broadcast.confirm)
async def bc_do(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text") or ""
    photo = data.get("photo")
    buttons = data.get("buttons")

    sent = 0
    for uid in list(user_ids):
        try:
            if photo:
                await bot.send_photo(uid, photo, caption=text, reply_markup=buttons or None)
            else:
                await bot.send_message(uid, text, reply_markup=buttons or None)
            sent += 1
        except Exception:
            continue

    await call.message.answer(f"✅ Рассылка завершена ({sent} пользователям).")
    await state.clear()

@dp.callback_query(F.data == "cancel_broadcast", Broadcast.confirm)
async def bc_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("❌ Рассылка отменена.")
    await state.clear()

# ====== ВЫГРУЗКА ПОЛЬЗОВАТЕЛЕЙ ======
@dp.callback_query(F.data == "admin_export")
async def on_admin_export(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    filename = "users.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for name in sorted(usernames):
            f.write(f"@{name}\n")
        f.write("\n# users without username (ids)\n")
        for uid in sorted(user_ids):
            # если у юзера нет username — пишем id
            if not any(name for name in usernames if name == str(uid)):
                f.write(f"{uid}\n")

    await call.message.answer_document(types.FSInputFile(filename))


# ---------- run ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
