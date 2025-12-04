import os

import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("GEMINI_API_KEY")
default_model = "gemini-2.0-flash"
client = genai.Client(api_key=KEY)


def ask_gemini(prompt: str):
    response = client.models.generate_content(model=default_model, contents=prompt)
    return response.text


def text_cleanup(extracted: str):
    prompt = f"""
    Analyze the extracted text below and carefully fix any technical / font error. Ensure that the meaning and the context of the extracted remain intact as the origin intended.  Remove any \n \t or anything alike as well if possible and replace it with actual new line or tab. Also make sure to not add any new message just response purely the cleanup.
    Extracted:

    {extracted}

    """
    response = client.models.generate_content(model=default_model, contents=prompt)
    return response.text
