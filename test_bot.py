from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8505982304:AAGg9zZyT0_dnqg9GIv4kEsEwbwXOQViBT8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    print(f"TEST: /start dari {user_name} (ID: {user_id})")
    await update.message.reply_text(f"Halo {user_name}! Bot test berjalan.")

def main():
    print("🤖 Test bot starting...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Test bot ready!")
    app.run_polling()

if __name__ == "__main__":
    main()