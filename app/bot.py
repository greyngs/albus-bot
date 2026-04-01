import os
from datetime import datetime, timezone, timedelta, time
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv

from app.dumbledore import speak_like_dumbledore, evaluate_and_react, generate_monthly_speech
from app.database import get_user, register_user, update_house_points, get_scoreboard, get_all_students, add_cat_points, get_cat_scoreboard, set_announcement_group, get_announcement_group, get_previous_month_winners

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SECRET_PASSWORD = os.getenv("SECRET_PASSWORD") 
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

BOT_TZ = timezone(timedelta(hours=-5))

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
/cat - Registrar el avistamiento de un Gato 🐈
/catstatus - Ver la liga de Cazadores de Gatos 🐱
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

async def setgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or args[0] != SECRET_PASSWORD:
        await update.message.reply_text("🛡️ Contraseña incorrecta o faltante. Sólo el Director puede fijar el Gran Comedor.")
        return
        
    chat_id = update.effective_chat.id
    await set_announcement_group(chat_id)
    await update.message.reply_text(f"✨ ¡Hecho! Este chat (ID: {chat_id}) ha sido designado como el Gran Comedor. Albus vendrá aquí a dar sus discursos a fin de mes.")

async def start_ceremony_check(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(BOT_TZ)
    if now.day == 1:
        chat_id = await get_announcement_group()
        if not chat_id:
            print("❌ No hay Gran Comedor (grupo) configurado para la ceremonia mensual.")
            return

        meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        prev_month_date = now - timedelta(days=2)
        prev_month_name = meses_es[prev_month_date.month]
        
        winners = await get_previous_month_winners()
        w_house = winners["house"]["name"]
        w_h_points = winners["house"]["points"]
        w_cat = winners["cat_hunter"]["name"]
        w_c_points = winners["cat_hunter"]["points"]
        
        speech = await generate_monthly_speech(
            winner_house=w_house, 
            house_pts=w_h_points, 
            winner_cat=w_cat, 
            cat_pts=w_c_points, 
            month_name=prev_month_name
        )
        
        await context.bot.send_message(chat_id=chat_id, text=speech)

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

CHOOSING_STUDENT, CHOOSING_SCALE, TYPING_REASON = range(3)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = await get_scoreboard()
    meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = meses_es[datetime.now(BOT_TZ).month]
    
    board_text = f"🏆 **Copa de las Casas - {mes_actual}** 🏆\n\n"
    
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
    await query.answer() 
    
    student_id = int(query.data)
    context.user_data["student_id"] = student_id
    
    students = await get_all_students()
    student_name = next((s["name"] for s in students if s["telegram_id"] == student_id), "Estudiante Desconocido")
    
    keyboard = [
        [InlineKeyboardButton("🟢 Buena - Normal (5 a 10)", callback_data="buena_normal")],
        [InlineKeyboardButton("🌟 Buena - Extraordinaria (11 a 30)", callback_data="buena_extraordinaria")],
        [InlineKeyboardButton("🔥 Buena - Épica (31+)", callback_data="buena_epica")],
        [InlineKeyboardButton("🔴 Mala - Normal (-1 a -10)", callback_data="mala_normal")],
        [InlineKeyboardButton("⚠️ Mala - Extraordinaria (-11 a -30)", callback_data="mala_extraordinaria")],
        [InlineKeyboardButton("💥 Mala - Épica (-31+)", callback_data="mala_epica")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Has elegido a {student_name}.\n¿De qué magnitud fue su acción?",
        reply_markup=reply_markup
    )
    return CHOOSING_SCALE

async def point_scale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    scale = query.data
    context.user_data["scale"] = scale
    
    scale_names = {
        "buena_normal": "Buena (Normal)",
        "buena_extraordinaria": "Buena (Extraordinaria)",
        "buena_epica": "Buena (Épica)",
        "mala_normal": "Mala (Normal)",
        "mala_extraordinaria": "Mala (Extraordinaria)",
        "mala_epica": "Mala (Épica)"
    }
    
    await query.edit_message_text(
        f"Magnitud elegida: {scale_names.get(scale, 'Desconocida')}.\n"
        "¿Cuál es el motivo de esta hazaña o travesura? Albus Dumbledore decidirá los puntos exactos..."
    )
    return TYPING_REASON

async def point_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text
    student_id = context.user_data["student_id"]
    scale = context.user_data["scale"]
    
    teacher_id = update.message.from_user.id
    student = await get_user(teacher_id)
    teacher_name = student["name"] if student else "Profesor Desconocido"

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    students = await get_all_students()
    target_student = next((s for s in students if s["telegram_id"] == student_id), None)
    
    if not target_student:
        await update.message.reply_text("Hubo un error al otorgar los puntos. Estudiante no encontrado.")
        context.user_data.clear() 
        return ConversationHandler.END

    evaluation = await evaluate_and_react(
        student_name=target_student['name'], 
        house=target_student['house'], 
        scale=scale, 
        reason=reason, 
        teacher_name=teacher_name
    )
    
    points = evaluation.get("points", 0)
    reaction = evaluation.get("reaction", "Puntos contabilizados majestuosamente.")

    result = await update_house_points(student_id, points, reason, teacher_name)

    if result:
        await update.message.reply_text(
            f"{reaction}\n\n"
            f"🏅 Puntos otorgados: {points}\n"
            f"📊 Nuevo balance de {result['house']}: {result['new_total']} puntos."
        )
    else:
        await update.message.reply_text("Hubo un error al guardar los puntos en los archivos del colegio.")
    
    context.user_data.clear() 
    return ConversationHandler.END

async def catstatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scores = await get_cat_scoreboard()
    if not scores:
        await update.message.reply_text("Aún no se ha avistado ningún gato merodeando por el castillo 🐾")
        return
        
    meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = meses_es[datetime.now(BOT_TZ).month]
        
    board_text = f"🐱 **Liga de Cazadores de Gatos - {mes_actual}** 🐱\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, score in enumerate(scores):
        medal = medals[i] if i < len(medals) else "🐈"
        board_text += f"{medal} {score['name']}: {score['points']} pts\n"
        
    await update.message.reply_text(board_text, parse_mode="Markdown")

async def cat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🐈 Normal (2 pts)", callback_data="cat_normal")],
        [InlineKeyboardButton("😼 Especial/Peculiar (4 pts)", callback_data="cat_especial")],
        [InlineKeyboardButton("🔭 Remoto (1 pt)", callback_data="cat_remoto")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🐾 ¡Avistamiento gatuno!\n¿Qué tipo de gato encontraste?",
        reply_markup=reply_markup
    )

async def cat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    cat_type = query.data
    
    points_map = {
        "cat_normal": {"pts": 2, "label": "Gato Normal"},
        "cat_especial": {"pts": 4, "label": "Gato Especial"},
        "cat_remoto": {"pts": 1, "label": "Gato Remoto"}
    }
    
    details = points_map.get(cat_type)
    if not details:
        return
        
    result = await add_cat_points(telegram_id, details["pts"], details["label"])
    
    if result:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        student = await get_user(telegram_id)
        name = student["name"] if student else "Alguien"
        
        prompt = f"El estudiante {name} acaba de encontrar un {details['label']} y ha ganado {details['pts']} puntos en el juego de avistamiento de gatos. Di una frase muy corta y mágica felicitándolo por su habilidad de observación de criaturas mágicas. Reacciona alegre u orgulloso."
        
        dumbledore_reaction = await speak_like_dumbledore(prompt, telegram_id, name, "Hogwarts", "Cazador de Gatos")
        
        await query.edit_message_text(
            f"{dumbledore_reaction}\n\n"
            f"🐈 **{details['label']} registrado (+{details['pts']} pts)**\n"
            f"📊 Puntos gatunos actuales: {result['new_total']}"
        )
    else:
        await query.edit_message_text("No estás registrado en Hogwarts para sumar puntos de gato.")


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
telegram_app.add_handler(CommandHandler("cat", cat_start)) 
telegram_app.add_handler(CommandHandler("catstatus", catstatus_command))
telegram_app.add_handler(CommandHandler("setgroup", setgroup_command))

point_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("point", point_start)],
    states={
        CHOOSING_STUDENT: [CallbackQueryHandler(point_student_callback)],
        CHOOSING_SCALE: [CallbackQueryHandler(point_scale_callback)],
        TYPING_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, point_reason)],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
)

telegram_app.add_handler(point_conv_handler) 
telegram_app.add_handler(CallbackQueryHandler(cat_callback, pattern='^cat_'))
telegram_app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & (filters.ChatType.PRIVATE | filters.Entity("mention")), 
    handle_message
))

async def init_bot():
    t = time(hour=0, minute=0, second=1, tzinfo=BOT_TZ)
    telegram_app.job_queue.run_daily(start_ceremony_check, time=t)
    
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