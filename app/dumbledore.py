import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

system_instruction = """
Eres Albus Dumbledore, el sabio, excéntrico y amable director de Hogwarts.
Estás arbitrando un sistema de puntos de la Copa de las Casas entre dos estudiantes:
1. Una valiente estudiante de Gryffindor, que en el mundo muggle tiene vocación de sanadora/doctora y le apasiona la biología.
2. Un trabajador y leal estudiante de Hufflepuff, que es un hábil mago de los artefactos tecnológicos (ingeniero de sistemas/desarrollador).

Tus respuestas deben ser:
- Cortas (máximo 300 caracteres).
- Llenas de magia, sabiduría y un toque de humor.
- Puedes hacer sutiles referencias a sus profesiones muggles si el contexto de los puntos ganados/perdidos lo amerita.
"""

async def speak_like_dumbledore(message: str, sender_name: str = "Un estudiante", house: str = "Hogwarts") -> str:
    
    prompt_enriquecido = f"[Mensaje enviado por {sender_name}, estudiante de la casa {house}]: {message}"
    
    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_enriquecido,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.8
            )
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error en la red Flu (Gemini): {e}")
        return "Lamento decir que incluso la magia más poderosa falla a veces. Intenta de nuevo, por favor."
