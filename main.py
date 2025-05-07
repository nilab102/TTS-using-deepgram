import os
import uuid
import hashlib
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from deepgram import DeepgramClient, SpeakOptions
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI()

# Create and mount a static folder to serve saved audio files
audio_folder = "static"
os.makedirs(audio_folder, exist_ok=True)
app.mount("/static", StaticFiles(directory=audio_folder), name="static")

# Define the request body model
class TTSRequest(BaseModel):
    text: str
    model: str = "aura-2-thalia-en"  # default voice model

# Load Deepgram API key from environment variable
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise RuntimeError("DEEPGRAM_API_KEY environment variable is not set.")
deepgram = DeepgramClient(DEEPGRAM_API_KEY)

def compute_cache_filename(text: str, model: str) -> str:
    """Compute a SHA256 hash from text and model, and return a filename for caching."""
    hash_object = hashlib.sha256(f"{model}:{text}".encode())
    return hash_object.hexdigest() + ".mp3"

def generate_and_save_tts(text: str, model: str, file_path: str):
    """
    Generate TTS audio from text using Deepgram and save it to file_path.
    This function uses the .save() method to write the audio to disk.
    """
    options = SpeakOptions(model=model)
    speak_options = {"text": text}
    # Using the save method to write the file directly to disk.
    response = deepgram.speak.rest.v("1").save(file_path, speak_options, options)
    return response

@app.post("/tts", response_class=JSONResponse)
async def text_to_speech(req: TTSRequest, request: Request):
    """
    Accepts a JSON payload with:
      - "text": The text to convert to speech.
      - "model": (Optional) The voice model to use (default: "aura-2-thalia-en").
      
    Implements a caching mechanism:
      - A unique filename is generated based on the hash of text+model.
      - If the file already exists, the cached version is returned.
      - Otherwise, the service generates the TTS audio, saves it, and returns the link.
    """
    try:
        # Compute cache filename based on text and model
        filename = compute_cache_filename(req.text, req.model)
        file_path = os.path.join(audio_folder, filename)

        # Build the absolute URL for the static file
        # Using url_for to respect mount settings and host
        file_url = request.url_for('static', path=filename)

        # Check if the file already exists (cache hit)
        if os.path.exists(file_path):
            return {"link": str(file_url), "cached": True}

        # Run the blocking TTS operation in a threadpool (cache miss)
        await run_in_threadpool(generate_and_save_tts, req.text, req.model, file_path)

        # Return the link to the newly saved audio file
        return {"link": str(file_url), "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
