import os
import datetime
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from keep_alive import keep_alive
from mongo_db import add_point, get_house_scores

# Tokens here
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

user_states = {}

# Function to speak like Dumbledore
async def speak_like_dumbledore(user_message):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = (
            "Responde como si fueras Albus Dumbledore, con un tono sabio, gracioso, "
            "a veces enigmático, pero siempre amable. Estás interactuando en un juego de puntos entre casas de Hogwarts."
            "Tus respuestas deben contener maximo 300 caracteres. \n\n"
            f"Usuario: {user_message}\nDumbledore:"
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres Albus Dumbledore, el director de Hogwarts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.8
        )
        content = response.choices[0].message.content
        return content.strip() if content else "Lamento decir que incluso la magia más poderosa puede fallar a veces. Intenta de nuevo."
    except Exception as e:
        print(f"Error en speak_like_dumbledore: {e}")
        return "Lamento decir que incluso la magia más poderosa puede fallar a veces. Intenta de nuevo."


# /help command
async def help_command(update: Update, context):
    help_text = """
✨ **Saludos, jóvenes mentes brillantes, y bienvenidos a la noble labor de la Academia Hogwarts.** ✨

Como su humilde servidor, Albus Dumbledore, es mi placer guiarlos a través del delicado equilibrio que mantiene nuestra sana competencia. Este sistema ha sido cuidadosamente diseñado para reconocer el mérito y el espíritu indomable de cada Casa.

Aquí, en el entramado de nuestra magia digital, encontrarán las herramientas para honrar la valentía de Gryffindor, la lealtad de Hufflepuff, la astucia de Slytherin y la sabiduría de Ravenclaw.

Permítanme presentarles las sendas que pueden transitar.

📋 **Encantamientos disponibles:**

/help - Muestra este mensaje de ayuda

/point - Agregar o quitar puntos a una casa

/status - Ver el estado actual de puntos de todas las casas

/profesor [mensaje] - Habla directamente con el Profesor Dumbledore

✨ *"La felicidad se puede encontrar hasta en los momentos más oscuros, si uno recuerda encender la luz."* - Dumbledore
    """
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

# /point command
async def point_command(update: Update, context):
    keyboard = [
        [
            InlineKeyboardButton("🦁 Gryffindor", callback_data="gryffindor"),
            InlineKeyboardButton("🦡 Hufflepuff", callback_data="hufflepuff")
        ],
        [
            InlineKeyboardButton("🦅 Ravenclaw", callback_data="ravenclaw"),
            InlineKeyboardButton("🐍 Slytherin", callback_data="slytherin")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🏰 Selecciona la casa:", reply_markup=reply_markup)

# Button handler
async def handle_buttons(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data in ['gryffindor', 'hufflepuff', 'ravenclaw', 'slytherin']:
        user_states[user_id] = {'house': data.title()}
        keyboard = [
            [
                InlineKeyboardButton("+1 Punto!", callback_data='point_one'),
                InlineKeyboardButton("+2 Puntos!!", callback_data='point_two')
            ],
            [
                InlineKeyboardButton("-1 Punto :c", callback_data='point_mone'),
                InlineKeyboardButton("-2 Puntos :(", callback_data='point_mtwo')
            ],
            [InlineKeyboardButton("⬅️ Volver", callback_data='comeback')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        emojis = {'gryffindor': '🦁', 'hufflepuff': '🦡', 'ravenclaw': '🦅', 'slytherin': '🐍'}
        await query.edit_message_text(
            f"Casa seleccionada: {emojis[data]} {data.title()}\n\n¿Cuántos puntos?",
            reply_markup=reply_markup
        )
    elif data in ['point_one', 'point_two', 'point_mone', 'point_mtwo']:
        if user_id not in user_states:
            await query.edit_message_text("❌ Error: Selecciona una casa primero con /point")
            return
        points_map = {
            'point_one': 1, 'point_two': 2,
            'point_mone': -1, 'point_mtwo': -2
        }
        points = points_map[data]
        user_states[user_id]['points'] = points
        user_states[user_id]['waiting_for_reason'] = True
        house = user_states[user_id]['house']
        sign = "+" if points > 0 else ""
        await query.edit_message_text(
            f"✅ {house}: {sign}{points} puntos\n\n📝 Ahora escribe la razón:"
        )
    elif data == 'comeback':
        keyboard = [
            [
                InlineKeyboardButton("🦁 Gryffindor", callback_data="gryffindor"),
                InlineKeyboardButton("🦡 Hufflepuff", callback_data="hufflepuff")
            ],
            [
                InlineKeyboardButton("🦅 Ravenclaw", callback_data="ravenclaw"),
                InlineKeyboardButton("🐍 Slytherin", callback_data="slytherin")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🏰 Selecciona una casa:", reply_markup=reply_markup)

# Handle text input (reason)
async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_states and user_states[user_id].get('waiting_for_reason'):
        reason = update.message.text
        house = user_states[user_id]['house']
        points = user_states[user_id]['points']
        person = update.effective_user.first_name or "Usuario"
        
        # Save to MongoDB
        success = add_point(person, house, points, reason)
        
        del user_states[user_id]
        
        if success:
            emojis = {'Gryffindor': '🦁', 'Hufflepuff': '🦡', 'Ravenclaw': '🦅', 'Slytherin': '🐍'}
            sign = "+" if points > 0 else ""            
            await update.message.reply_text(
                f"🎉 ¡Puntos agregados!\n\n"
                f"{emojis[house]} *{house}*: {sign}{points} puntos\n"
                f"📝 Razón: {reason}\n"
                f"👤 Por: {person}",
                parse_mode="Markdown"
            )
            dumbledore_context = (
                f"Se han agregado {sign}{points} puntos a {house} por la siguiente razón: {reason}."
            )
            dumbledore_quote = await speak_like_dumbledore(dumbledore_context)            
            await update.message.reply_text(dumbledore_quote)
        else:
            await update.message.reply_text("❌ Error al guardar los puntos. Intenta de nuevo.")

# /estado command
async def status_command(update: Update, context):
    scores = get_house_scores()
    emojis = {'Gryffindor': '🦁', 'Hufflepuff': '🦡', 'Ravenclaw': '🦅', 'Slytherin': '🐍'}
    message = "🏆 *Estado de Puntos:*\n\n"
    for house, total in scores.items():
        message += f"{emojis[house]} {house}: {total} puntos\n"
    await update.message.reply_text(message, parse_mode="Markdown")
    dumbledore_quote = await speak_like_dumbledore(f"Dime algo sabio sobre los puntos actuales:\n {message}")
    await update.message.reply_text(dumbledore_quote)

# /profesor command
async def profesor_command(update: Update, context):
    # Obtén el texto después del comando
    user_message = " ".join(context.args)
    if not user_message:
        await update.message.reply_text("Por favor, escribe tu pregunta o mensaje después de /profesor.")
        return
    dumbledore_reply = await speak_like_dumbledore(user_message)
    await update.message.reply_text(dumbledore_reply)

# Main
def main():
    keep_alive()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("point", point_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CommandHandler("profesor", profesor_command))
    print("🤖 Hogwarts Bot with Dumbledore personality is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
