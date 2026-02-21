import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from app.dumbledore import speak_like_dumbledore
from app.database import get_user, register_user 

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_PASSWORD = os.getenv("SECRET_PASSWORD") 

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
✨ **Saludos, jóvenes mentes brillantes.** ✨

Soy Albus Dumbledore. El Gran Comedor está listo para recibir sus méritos.

📋 **Encantamientos disponibles:**
/help - Muestra este mensaje
/registro - Inscribirte en los pergaminos de Hogwarts
/point - Agregar o quitar puntos a una casa (Próximamente)
/status - Ver el estado actual de puntos (Próximamente)
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    
    if len(args) < 4:
        await update.message.reply_text(
            "📜 *Formato incorrecto.* Usa:\n`/registro [Contraseña] [Nombre] [Casa] [Profesión o descripción]`", 
            parse_mode="Markdown"
        )
        return

    password = args[0]
    name = args[1]
    house = args[2]
    # Join the rest of the words for the profession (in case it has spaces)
    profession = " ".join(args[3:])
    telegram_id = update.message.from_user.id

    if password != SECRET_PASSWORD:
        await update.message.reply_text("🛡️ Contraseña incorrecta. El retrato de la Señora Gorda no te dejará pasar.")
        return

    success = await register_user(telegram_id, name, house, profession)
    
    if success:
        await update.message.reply_text(f"✨ ¡El Sombrero Seleccionador ha hablado! Bienvenido a {house}, {name}. He tomado nota de tus habilidades como {profession}.")
    else:
        await update.message.reply_text("Ya estás registrado en los pergaminos de Hogwarts.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.from_user.id
    user_text = update.message.text
    
    student = await get_user(telegram_id)
    
    if not student:
        await update.message.reply_text(
            "Alto ahí. No te encuentro en los registros del colegio. "
            "Usa el comando `/registro` junto con la contraseña para entrar al Gran Comedor."
        )
        return

    name = student["name"]
    house = student["house"]
    profession = student["profession"]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    enriched_context = f"(Soy {name}, de {house}. Mi profesión es {profession}). {user_text}"
    
    response = await speak_like_dumbledore(enriched_context, name, house)
    await update.message.reply_text(response)


telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("start", help_command))
telegram_app.add_handler(CommandHandler("registro", register_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def init_bot():
    await telegram_app.initialize()
    await telegram_app.start()

async def stop_bot():
    await telegram_app.stop()
    await telegram_app.shutdown()