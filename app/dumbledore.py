import os
import json
from google import genai
from google.genai import types

client = genai.Client()

# Diccionario en memoria para guardar las sesiones de chat por usuario
user_chats = {}

async def speak_like_dumbledore(user_message: str, telegram_id: int, name: str, house: str, profession: str) -> str:
    system_instruction = (
        f"Eres Albus Dumbledore, el sabio y benévolo director de Hogwarts. "
        f"Estás hablando con {name}, un estudiante de la casa {house}. "
        f"Además, en el mundo muggle, este estudiante se dedica a lo siguiente: {profession}. "
        f"Usa un tono amable, misterioso y lleno de sabiduría. "
        f"Si es natural en la conversación, haz metáforas sutiles que conecten la magia de Hogwarts "
        f"con su profesión (por ejemplo, relacionando la medicina con pociones y artes curativas, "
        f"o la ingeniería/programación con la precisión de los encantamientos y la Aritmancia). "        
        f"Tus respuestas deben ser cortas (máximo 300 caracteres). Llenas de magia, sabiduría y un toque de humor."
        f"Nunca rompas el personaje. Sé conciso y conversacional."
    )

    try:
        if telegram_id not in user_chats:
            user_chats[telegram_id] = client.chats.create(
                model='gemini-2.5-flash',
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            
        chat = user_chats[telegram_id]
                
        if len(chat.get_history()) > 14:
            history = chat.get_history()
            chat.history = history[-14:]
            
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        print(f"❌ Error conectando a Gemini: {e}")
        return "Parece que los duendecillos de Cornualles han interferido con mi red flu. Intenta de nuevo más tarde."

async def evaluate_and_react(student_name: str, house: str, scale: str, reason: str, teacher_name: str) -> dict:
    scale_rules = {
        "buena_normal": "Otorga entre 5 y 10 puntos a su favor.",
        "buena_extraordinaria": "Otorga entre 11 y 30 puntos a su favor.",
        "buena_epica": "Otorga entre 31 y 50 puntos a su favor.",
        "mala_normal": "Quita entre 1 y 10 puntos (escribiendo el número en negativo, ej. -5).",
        "mala_extraordinaria": "Quita entre 11 y 30 puntos (escribiendo el número en negativo, ej. -20).",
        "mala_epica": "Quita entre 31 y 50 puntos (escribiendo el número en negativo, ej. -40)."
    }
    
    rule = scale_rules.get(scale, "Otorga 0 puntos.")
    
    system_instruction = (
        f"Eres Albus Dumbledore. El profesor o alumno '{teacher_name}' está reportando una acción "
        f"del estudiante '{student_name}' de la casa '{house}'. El motivo es: '{reason}'. "
        f"Instrucción para los puntos: {rule} "
        f"Primero, decide la cantidad EXACTA de puntos a otorgar (o quitar) respetando estrictamente el rango de la regla según qué tan bien (o mal) haya sonado el motivo. "
        f"Segundo, reacciona a esta situación como el sabio director de Hogwarts. "
        f"IMPORTANTE: Tu respuesta debe ser EXCLUSIVAMENTE un objeto JSON válido con este formato exacto: "
        f'{{"points": 10, "reaction": "tu respuesta aquí"}}'
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="Por favor, evalúa la acción basándote en el motivo, y dime cuántos puntos le corresponden y tu reacción como director, usa JSON.",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"❌ Error conectando a Gemini (Evaluador JSON): {e}")
        fallback_points = 5 if "buena" in scale else -5
        return {"points": fallback_points, "reaction": f"Parece que los duendecillos interfirieron, pero he sumado {fallback_points} puntos."}