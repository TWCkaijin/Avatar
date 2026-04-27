import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv(".env")
from app.main import process_tts_chunks_sync

res = process_tts_chunks_sync("<neutral> Hello")
print(res)
