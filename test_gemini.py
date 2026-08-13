import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(".env")
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

config = types.GenerateContentConfig(
    tools=[{"google_search": {}}],
    temperature=0.2,
    response_mime_type="application/json",
    system_instruction="Kembalikan JSON format: {'artist':'', 'title':''}."
)

resp = client.models.generate_content(
    model='gemini-2.5-flash',
    contents="Cari tahu lagu asli dari nama file ini: 'dongker - di bandung'",
    config=config
)
print(resp.text)
