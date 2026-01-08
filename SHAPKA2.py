import logging
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.error import RetryAfter, TelegramError

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "8546278129:AAHvs6GTOMcn3ayeSkG8XoZ4UOuLzskfQT4"

# 🔑 ТЫ (кому приходят уведомления)
ADMIN_CHATS = {999745128}

# 💖 ОНА (кому приходят напоминания)
GIRL_CHAT_ID = 1063089931

# антиспам для /test: user_id -> datetime последнего теста
last_test_time = {}


def yes_no_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Да", callback_data="pill_yes"),
        InlineKeyboardButton("❌ Нет", callback_data="pill_no"),
    ]])


async def start(update, _):
    await update.message.reply_text("✅ Я буду напоминать каждый день в 21:00 по МСК!")


async def notify_admins(context, text: str):
    for admin_id in ADMIN_CHATS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text)
        except RetryAfter as e:
            logging.warning(f"Flood limit notifying admin {admin_id}, retry_after={e.retry_after}s")
        except TelegramError as e:
            logging.error(f"TelegramError notifying admin {admin_id}: {e}")


# ✅ Напоминание ТОЛЬКО ей
async def send_daily_reminder(context):
    try:
        await context.bot.send_message(
            chat_id=GIRL_CHAT_ID,
            text="Солнышко, ты выпила таблеточку? 💊",
            reply_markup=yes_no_keyboard()
        )
        logging.info("✅ Daily reminder sent to girl")
    except RetryAfter as e:
        logging.warning(f"Flood limit (daily), retry_after={e.retry_after}s")
    except TelegramError as e:
        logging.error(f"TelegramError sending daily reminder: {e}")


async def button_handler(update, context):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    # кто нажал
    who = f"{user.first_name or 'Без имени'} (id: {user.id})"

    if query.data == "pill_yes":
        await query.edit_message_text("Умница 💛")
        await notify_admins(context, f"✅ Таблетка ВЫПИТА\n👤 {who}\n🕒 {now}")

    elif query.data == "pill_no":
        await query.edit_message_text("уууууууу ну всё тогда, я всё расскажу Никите и тебе пизда")
        await notify_admins(context, f"❌ Таблетка НЕ выпита\n👤 {who}\n🕒 {now}")


# 🧪 /test — тестовое сообщение ТОЛЬКО ей (с кнопками), тебе придёт уведомление о том, что тест отправлен
async def test_notification(update, context):
    user_id = update.effective_user.id
    now = datetime.datetime.now()

    # только ты можешь запускать тест (чтобы она случайно не спамила)
    if update.effective_chat.id not in ADMIN_CHATS:
        await update.message.reply_text("⛔ Эта команда не для тебя")
        return

    # антиспам: раз в 10 секунд
    if user_id in last_test_time and (now - last_test_time[user_id]).total_seconds() < 10:
        await update.message.reply_text("🧪 Подожди 10 секунд 🙂")
        return
    last_test_time[user_id] = now

    try:
        await context.bot.send_message(
            chat_id=GIRL_CHAT_ID,
            text="🧪 ТЕСТ\nСолнышко, ты выпила таблеточку? 💊",
            reply_markup=yes_no_keyboard()
        )
        await update.message.reply_text("✅ Тест отправлен ей")
        await notify_admins(context, f"🧪 Тест отправлен (инициатор id: {user_id})")
    except RetryAfter as e:
        await update.message.reply_text(f"⏳ Лимит Telegram, подожди {e.retry_after} сек")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка Telegram: {e}")


# 💬 /say — только ты → только ей
async def say(update, context):
    if update.effective_chat.id not in ADMIN_CHATS:
        await update.message.reply_text("⛔ Эта команда не для тебя")
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Используй:\n/say Текст сообщения")
        return

    try:
        await context.bot.send_message(
            chat_id=GIRL_CHAT_ID,
            text=f"💌 Сообщение от Никиты:\n{text}"
        )
        await update.message.reply_text("✅ Сообщение отправлено ей")
    except RetryAfter as e:
        await update.message.reply_text(f"⏳ Лимит Telegram, подожди {e.retry_after} сек")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка Telegram: {e}")


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_notification))
    application.add_handler(CommandHandler("say", say))
    application.add_handler(CallbackQueryHandler(button_handler))

    # каждый день в 21:00 МСК (как у тебя раньше: 18:00 UTC)
    application.job_queue.run_daily(
        send_daily_reminder,
        time=datetime.time(hour=18, minute=0)
    )

    print("🤖 Бот запущен")
    print("⏰ Напоминание каждый день в 21:00 по МСК (18:00 UTC)")
    application.run_polling()


if __name__ == '__main__':
    main()
