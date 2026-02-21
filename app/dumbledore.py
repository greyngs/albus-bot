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