import json
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "models/gemini-2.0-flash"
CHUNK_FILE = "chunks.json"


def load_chunks():
    with open(CHUNK_FILE, "r") as f:
        return json.load(f)


def find_relevant_chunks(query, chunks):
    return [chunk["content"] for chunk in chunks if query.lower() in chunk["content"].lower()]


def query_model(error_code):
    if not GOOGLE_API_KEY:
        return "⚠️ Missing Google API key."

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)

    chunks = load_chunks()
    matched_chunks = find_relevant_chunks(error_code, chunks)

    if not matched_chunks:
        return "Sorry, I couldn’t find anything about that error code."

    context = "\n\n".join(matched_chunks)
    prompt = f"""
    Return ONLY a valid JSON object. 
    Do not include explanations, backticks, or markdown syntax.
    ...
    You are an AI assistant that explains car OBD-II error codes clearly for non-mechanics.

    Given the OBD error code "{error_code}" and the related context below:
    {context}

    Return your answer STRICTLY as a JSON object with the following keys:
    "title": (short title of the issue),
    "severity": (low/medium/high risk),
    "description": (2-3 sentence explanation of what this code means),
    "causes": (list of possible causes as short strings),
    "fixes": (list of possible fixes as short strings)

    Example format:
    {{
    "title": "Random/Multiple Cylinder Misfire Detected",
    "severity": "Medium",
    "description": "This means the engine control unit detected random misfires across multiple cylinders...",
    "causes": ["Faulty spark plugs", "Vacuum leaks"],
    "fixes": ["Replace spark plugs", "Check ignition coils"]
    }}
    """

    response = model.generate_content(prompt)
    
    try:
        return response.text.strip()
    except:
        # fallback if not valid JSON
        return {"title": "AI Report", "description": response.text, "causes": [], "fixes": []}