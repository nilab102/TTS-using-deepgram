# Deepgram TTS FastAPI Service

This is a FastAPI service that converts text to speech (TTS) using Deepgram's Text-to-Speech API. The service generates audio files from provided text, caches the results by computing a hash over the input, saves the audio in a local static directory, and returns a URL link for the generated audio file.

## Features

- **Text-to-Speech Conversion**: Converts given text into speech using Deepgram TTS.
- **Caching Mechanism**: Uses a SHA256 hash of the text and model to cache results. If the same text is requested again, it serves the cached audio file.
- **Static File Serving**: The generated audio is saved locally in the `static` folder and served as a static file via FastAPI.
- **Environment Configuration**: Loads the Deepgram API key from an environment variable (using a `.env` file if available).

## Prerequisites

- **Python 3.7+**: Ensure that you have a compatible Python version installed.
- **Deepgram API Key**: You must have a valid Deepgram API key. Set it in your environment as `DEEPGRAM_API_KEY` (e.g., in a `.env` file).

## Installation

1. **Clone the repository** (if hosted in a VCS) or copy the source code into your project directory.
2. **Install dependencies** using `pip`:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory (if not already done) and add your Deepgram API key:

   ```env
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   ```

## Running the Service

Start the FastAPI server using uvicorn. For example:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

This command will start the server on `http://0.0.0.0:8001/`.

## Usage

### Endpoint

* **POST /tts**

  **Request Body (JSON):**

  ```json
  {
    "text": "Hello, world!",
    "model": "aura-2-thalia-en"
  }
  ```

  * **text**: The text you want to convert to speech.
  * **model**: *(Optional)* The voice model to use. Default is `aura-2-thalia-en`.

  **Response (JSON):**

  ```json
  {
    "link": "/static/your_generated_audio_file.mp3",
    "cached": false
  }
  ```

  The response includes a link to the generated audio file and an indicator (`cached`) that tells whether the file was served from cache or newly generated.

### Static File Access

The audio files are served from the `/static` endpoint. For example, if your response returns:

```
/static/12345abcdef.mp3
```

You can access the audio file at `http://<your_server_address>:8001/static/12345abcdef.mp3`.

## Contributing

Feel free to open issues or submit pull requests for any improvements or bug fixes.

## License

This project is provided under the MIT License.
