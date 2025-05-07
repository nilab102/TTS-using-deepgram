import os
import uuid
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from deepgram import DeepgramClient, SpeakOptions
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI()

# Create and mount a static folder to serve saved audio files
AUDIO_FOLDER = "static"
os.makedirs(AUDIO_FOLDER, exist_ok=True)
app.mount("/static", StaticFiles(directory=AUDIO_FOLDER), name="static")

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
    filename = hash_object.hexdigest() + ".mp3"
    return filename

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
async def text_to_speech(req: TTSRequest):
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
        file_path = os.path.join(AUDIO_FOLDER, filename)

        # Check if the file already exists (cache hit)
        if os.path.exists(file_path):
            file_link = f"/static/{filename}"
            return {"link": file_link, "cached": True}

        # Run the blocking TTS operation in a threadpool (cache miss)
        await run_in_threadpool(generate_and_save_tts, req.text, req.model, file_path)

        # Return the link to the newly saved audio file
        file_link = f"/static/{filename}"
        return {"link": file_link, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
