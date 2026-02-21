import os
from google import genai
from google.genai import types

client = genai.Client()

async def speak_like_dumbledore(user_message: str, name: str, house: str, profession: str) -> str:
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
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        return response.text
    except Exception as e:
        print(f"❌ Error conectando a Gemini: {e}")
        return "Parece que los duendecillos de Cornualles han interferido con mi red flu. Intenta de nuevo más tarde."

async def react_to_points(student_name: str, house: str, points: int, reason: str, teacher_name: str) -> str:
    action = "otorgado" if points > 0 else "quitado"
    abs_points = abs(points)
    
    system_instruction = (
        f"Eres Albus Dumbledore. El profesor o alumno '{teacher_name}' acaba de {action} {abs_points} puntos "
        f"al estudiante '{student_name}' de la casa '{house}'. El motivo ha sido: '{reason}'. "
        f"Reacciona a esta situación como el sabio director de Hogwarts. "
        f"Si es una pérdida de puntos, muéstrate decepcionado, comprensivo o da una lección moral. "
        f"Si es una ganancia, muéstrate orgulloso, alegre o intrigado. "
        f"Sé conciso (máximo 300 caracteres). Nunca rompas tu personaje ni hables como un bot."
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="¿Qué opinas sobre estos puntos que se acaban de dar en Hogwarts, Director?",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.8,
            )
        )
        return response.text
    except Exception as e:
        print(f"❌ Error conectando a Gemini (Puntos): {e}")
        return f"✨ ¡Hecho! {points} puntos contabilizados para {student_name} ({house})."