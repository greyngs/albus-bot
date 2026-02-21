import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv

from app.dumbledore import speak_like_dumbledore, react_to_points
from app.database import get_user, register_user, update_house_points, get_scoreboard, get_all_students

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_PASSWORD = os.getenv("SECRET_PASSWORD") 
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
✨ **Saludos, jóvenes mentes brillantes.** ✨

Soy Albus Dumbledore. El Gran Comedor está listo para recibir sus méritos.

📋 **Encantamientos disponibles:**
/help - Muestra este mensaje
/registro - Inscribirte en los pergaminos de Hogwarts
/point - Agregar o quitar puntos a una casa
/status - Ver el estado actual de puntos
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
    
    response = await speak_like_dumbledore(user_text, telegram_id, name, house, profession)
    await update.message.reply_text(response, reply_to_message_id=update.message.message_id)

CHOOSING_STUDENT, TYPING_POINTS, TYPING_REASON = range(3)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = await get_scoreboard()
    board_text = "🏆 **Copa de las Casas - Marcador Actual** 🏆\n\n"
    
    house_emojis = {"Gryffindor": "🦁", "Hufflepuff": "🦡", "Ravenclaw": "🦅", "Slytherin": "🐍"}
    
    for house, points in scores.items():
        emoji = house_emojis.get(house, "✨")
        board_text += f"{emoji} {house}: {points} puntos\n"
        
    await update.message.reply_text(board_text, parse_mode="Markdown")

async def point_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    students = await get_all_students()
    
    if not students:
        await update.message.reply_text("Aún no hay estudiantes registrados en Hogwarts.")
        return ConversationHandler.END

    keyboard = []
    # Crear filas de botones con 2 estudiantes por fila si es posible
    for i in range(0, len(students), 2):
        row = []
        for student in students[i:i+2]:
            house_emoji = {"Gryffindor": "🦁", "Hufflepuff": "🦡", "Ravenclaw": "🦅", "Slytherin": "🐍"}.get(student['house'], "✨")
            button_text = f"{house_emoji} {student['name']}"
            # Convertir id a string para callback_data
            row.append(InlineKeyboardButton(button_text, callback_data=str(student['telegram_id'])))
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🪄 ¿A qué estudiante deseas otorgar (o quitar) puntos?\n\n"
        "Selecciona un nombre de la lista, o escribe /cancel para anular el hechizo.",
        reply_markup=reply_markup
    )
    return CHOOSING_STUDENT

async def point_student_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Necesario para q el boton deje de cargar en UI
    
    student_id = int(query.data)
    context.user_data["student_id"] = student_id
    
    # Buscamos el nombre para mostrarlo amistosamente
    students = await get_all_students()
    student_name = next((s["name"] for s in students if s["telegram_id"] == student_id), "Estudiante Desconocido")
    
    await query.edit_message_text(
        f"Has elegido a {student_name}. ¿Cuántos puntos? (Escribe un número, por ejemplo: 10 o -5)"
    )
    return TYPING_POINTS

async def point_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        points_to_add = int(update.message.text)
        context.user_data["points"] = points_to_add
        
        await update.message.reply_text(
            f"Entendido, {points_to_add} puntos.\n"
            "¿Cuál es el motivo de esta hazaña o travesura? (Ej: Por un encantamiento bien ejecutado)"
        )
        return TYPING_REASON
    except ValueError:
        await update.message.reply_text("Por favor, escribe solo un número entero válido. Intenta de nuevo.")
        return TYPING_POINTS

async def point_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text
    student_id = context.user_data["student_id"]
    points = context.user_data["points"]
    
    teacher_id = update.message.from_user.id
    student = await get_user(teacher_id)
    teacher_name = student["name"] if student else "Profesor Desconocido"

    result = await update_house_points(student_id, points, reason, teacher_name)

    if result:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        dumbledore_reaction = await react_to_points(
            student_name=result['student_name'], 
            house=result['house'], 
            points=points, 
            reason=reason, 
            teacher_name=teacher_name
        )
        
        await update.message.reply_text(
            f"{dumbledore_reaction}\n\n"
            f"📊 Nuevo balance de {result['house']}: {result['new_total']} puntos."
        )
    else:
        await update.message.reply_text("Hubo un error al otorgar los puntos. Estudiante no encontrado.")
    
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
        CHOOSING_STUDENT: [CallbackQueryHandler(point_student_callback)],
        TYPING_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, point_amount)],
        TYPING_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, point_reason)],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
)

telegram_app.add_handler(point_conv_handler) 
telegram_app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & (filters.ChatType.PRIVATE | filters.Entity("mention")), 
    handle_message
))

async def init_bot():
    await telegram_app.initialize()
    await telegram_app.start()
    
    if WEBHOOK_URL:
        print(f"🔗 Configurando Webhook en: {WEBHOOK_URL}")
        await telegram_app.bot.set_webhook(url=WEBHOOK_URL)
    else:
        print("🔄 Iniciando bot en modo Polling (Local)...")
        await telegram_app.updater.start_polling()

async def stop_bot():
    if telegram_app.updater and telegram_app.updater.running:
        await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()