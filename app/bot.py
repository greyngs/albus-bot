import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
✨ **Saludos, jóvenes mentes brillantes.** ✨

Soy Albus Dumbledore. El Gran Comedor está listo para recibir sus méritos.

📋 **Encantamientos disponibles:**
/help - Muestra este mensaje
/point - Agregar o quitar puntos a una casa (Próximamente)
/status - Ver el estado actual de puntos (Próximamente)
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("start", help_command))

async def init_bot():
    await telegram_app.initialize()
    await telegram_app.start()

async def stop_bot():
    await telegram_app.stop()
    await telegram_app.shutdown()
