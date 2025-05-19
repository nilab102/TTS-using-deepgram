import os
import hashlib
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from deepgram import DeepgramClient, SpeakOptions
from dotenv import load_dotenv
from google import genai
from google.genai import types
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
load_dotenv(override=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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


# Load API key from environment variable
api_key = os.getenv("google_api_key_gemini")

# Initialize Gemini client
client = genai.Client(api_key=api_key)

def transcribe_audio_directly(
    audio_bytes: bytes,
    mime_type: str,
    model: str = "gemini-2.0-flash-lite"
) -> str:
    """
    Transcribe an audio file using Google Gemini API.
    """
    try:
        # Wrap bytes in a Part object with correct MIME type
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        
        system_prompt = '''
Please transcribe this audio accurately. If any email addresses, phone numbers, physical addresses, or similar details are detected, transcribe them carefully and standardize them to the correct format.

For example:

If an email is spoken with spaces or capital letters (e.g. ‘N I L A B 102 @ GMAIL dot COM’ or ‘Nilab 102 @ Gmail.com’), convert it to lowercase without spaces (e.g. nilab102@gmail.com).

If a phone number is spoken digit by digit or with pauses, reconstruct it into a continuous, correctly formatted number (e.g. ‘zero one six one six seven six six six six’ → 0161676666).

The speaker's English accent is primarily Arabic and Indian, so please pay extra attention to accent-related nuances and common pronunciation patterns when transcribing and normalizing details.Remove time stamps and speaker labels from the transcription.'''

        # Call Gemini API
        response = client.models.generate_content(
            model=model,
            contents=[
                audio_part,
                system_prompt
            ],
            config={
                "temperature": 0
            }
        )

        return response.text

    except Exception as e:
        raise RuntimeError(f"Transcription failed: {str(e)}")
import time
@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        # Validate file type
        if file.content_type not in ["audio/wav", "audio/x-wav", "audio/mpeg"]:
            raise HTTPException(status_code=400, detail="Only .wav and .mp3 files are supported.")

        # Read the file contents into bytes
        audio_bytes = await file.read()
        start_time = time.time()
        # Call transcription function with correct mime type
        transcription = transcribe_audio_directly(audio_bytes, file.content_type)
        end_time = time.time()
        return JSONResponse(content={"transcription": transcription, "time_taken": end_time - start_time})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=6500, reload=True)