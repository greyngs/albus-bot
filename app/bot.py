import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv

from app.dumbledore import speak_like_dumbledore
from app.database import get_user, register_user, update_house_points, get_scoreboard # <-- Nuevas importaciones

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
    
    response = await speak_like_dumbledore(user_text, name, house, profession)
    await update.message.reply_text(response)

HOOSING_HOUSE, TYPING_POINTS, TYPING_REASON = range(3)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = await get_scoreboard()
    board_text = "🏆 **Copa de las Casas - Marcador Actual** 🏆\n\n"
    
    house_emojis = {"Gryffindor": "🦁", "Hufflepuff": "🦡", "Ravenclaw": "🦅", "Slytherin": "🐍"}
    
    for house, points in scores.items():
        emoji = house_emojis.get(house, "✨")
        board_text += f"{emoji} {house}: {points} puntos\n"
        
    await update.message.reply_text(board_text, parse_mode="Markdown")

async def point_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Gryffindor", "Hufflepuff"], ["Ravenclaw", "Slytherin"]]
    
    await update.message.reply_text(
        "🪄 ¿A qué casa deseas otorgar (o quitar) puntos?\n\n"
        "Elige una opción del teclado o escribe /cancel para anular el hechizo.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSING_HOUSE

async def point_house(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chosen_house = update.message.text
    context.user_data["house"] = chosen_house
    
    await update.message.reply_text(
        f"Has elegido {chosen_house}. ¿Cuántos puntos? (Escribe un número, por ejemplo: 10 o -5)",
        reply_markup=ReplyKeyboardRemove(), 
    )
    return TYPING_POINTS

async def point_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        points_to_add = int(update.message.text)
        context.user_data["points"] = points_to_add
        
        await update.message.reply_text(
            f"Entendido, {points_to_add} puntos para {context.user_data['house']}.\n"
            "¿Cuál es el motivo de esta acción? (Ej: Por un excelente despliegue de código en Rust, o por salvar una vida en el hospital)"
        )
        return TYPING_REASON
    except ValueError:
        await update.message.reply_text("Por favor, escribe solo un número entero válido. Intenta de nuevo.")
        return TYPING_POINTS

async def point_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text
    house = context.user_data["house"]
    points = context.user_data["points"]
    telegram_id = update.message.from_user.id
    
    student = await get_user(telegram_id)
    teacher_name = student["name"] if student else "Profesor Desconocido"

    new_total = await update_house_points(house, points, reason, teacher_name)

    await update.message.reply_text(
        f"✨ ¡Hecho! {points} puntos para {house}.\n"
        f"📜 Motivo: {reason}\n\n"
        f"📊 Nuevo total de {house}: {new_total} puntos."
    )
    
    context.user_data.clear() 
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Encantamiento cancelado. Los relojes de arena permanecen intactos.", 
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("start", help_command))
telegram_app.add_handler(CommandHandler("registro", register_command))
telegram_app.add_handler(CommandHandler("status", status_command)) 

point_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("point", point_start)],
    states={
        CHOOSING_HOUSE: [MessageHandler(filters.Regex("^(Gryffindor|Hufflepuff|Ravenclaw|Slytherin)$"), point_house)],
        TYPING_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, point_amount)],
        TYPING_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, point_reason)],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
)

telegram_app.add_handler(point_conv_handler) 
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def init_bot():
    await telegram_app.initialize()
    await telegram_app.start()

async def stop_bot():
    await telegram_app.stop()
    await telegram_app.shutdown()