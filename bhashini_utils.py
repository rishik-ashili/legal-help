
import requests
import base64
import json
import os
import subprocess
from io import BytesIO

BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID")
BHASHINI_ULCA_API_KEY = os.getenv("BHASHINI_ULCA_API_KEY")
PIPELINE_ID = os.getenv("BHASHINI_PIPELINE_ID")

PIPELINE_CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"


def get_asr_config(source_lang):
    """Fetches the pipeline configuration for ASR."""
    headers = {"userID": BHASHINI_USER_ID, "ulcaApiKey": BHASHINI_ULCA_API_KEY}
    payload = {
        "pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": source_lang}}}],
        "pipelineRequestConfig": {"pipelineId": PIPELINE_ID}
    }
    try:
        response = requests.post(PIPELINE_CONFIG_URL, json=payload, headers=headers)
        response.raise_for_status()
        config_data = response.json()

        service_id = config_data["pipelineResponseConfig"][0]["config"][0]["serviceId"]
        callback_url = config_data["pipelineInferenceAPIEndPoint"]["callbackUrl"]
        auth_name = config_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"]
        auth_value = config_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]

        return service_id, callback_url, auth_name, auth_value
    except requests.exceptions.RequestException as e:
        print(f"Error in ASR Pipeline Config Call: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return None, None, None, None
    except (KeyError, IndexError) as e:
        print(f"Error parsing ASR config response: {e}")
        return None, None, None, None

def convert_audio_to_wav_ffmpeg(audio_bytes):
    """
    Converts audio data from any format to WAV using FFmpeg.
    Returns the converted audio bytes.
    """
    command = [
        'ffmpeg',
        '-i', 'pipe:0',      # Input from stdin
        '-f', 'wav',         # Output format is WAV
        '-ac', '1',          # Mono channel
        '-ar', '16000',      # Sample rate 16000 Hz (standard for ASR)
        'pipe:1'             # Output to stdout
    ]
    try:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        wav_bytes, stderr = proc.communicate(input=audio_bytes)
        
        if proc.returncode != 0:
            print("FFmpeg Error:", stderr.decode())
            return None
            
        print("FFmpeg conversion successful.")
        return wav_bytes
    except FileNotFoundError:
        print("\n--- FFmpeg not found! ---")
        print("This program requires FFmpeg to convert audio. Please install it.")
        print("On Windows (with Chocolatey): choco install ffmpeg")
        print("On Linux (Debian/Ubuntu): sudo apt-get install ffmpeg")
        print("On macOS (with Homebrew): brew install ffmpeg")
        print("--------------------------\n")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during FFmpeg conversion: {e}")
        return None

def run_bhashini_transcription(audio_bytes, source_lang="en"):
    """
    Takes audio bytes, gets config, and returns the transcribed text.
    Uses FFmpeg for robust audio conversion and VAD pre-processor.
    """
    print(f"Starting transcription for language: {source_lang}")
    asr_config = get_asr_config(source_lang)
    if not all(asr_config):
        return "Error: Could not get ASR configuration."

    service_id, callback_url, auth_name, auth_value = asr_config
    
    wav_bytes = convert_audio_to_wav_ffmpeg(audio_bytes)
    if not wav_bytes:
        return "Error: Audio conversion failed. Is FFmpeg installed on your system?"
    
    encoded_audio = base64.b64encode(wav_bytes).decode('utf-8')

    headers = {auth_name: auth_value, "Content-Type": "application/json"}
    payload = {
        "pipelineTasks": [
            {"taskType": "asr", "config": {
                "language": {"sourceLanguage": source_lang},
                "serviceId": service_id,
                "audioFormat": "wav",
                "samplingRate": 16000,
                "preProcessors": ["vad"]
            }}
        ],
        "inputData": {"audio": [{"audioContent": encoded_audio}]}
    }

    try:
        print("Sending audio for transcription...")
        response = requests.post(callback_url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("pipelineResponse") or not result["pipelineResponse"][0].get("output"):
             print(f"Transcription returned empty or invalid response: {result}")
             return "(No speech detected)"
             
        transcribed_text = result["pipelineResponse"][0]["output"][0]["source"]
        
        if not transcribed_text.strip():
            print("Transcription result was empty.")
            return "(No speech detected)"

        print(f"Transcription successful: {transcribed_text}")
        return transcribed_text
    except requests.exceptions.RequestException as e:
        print(f"Error in Transcription Compute Call: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return f"Error during transcription: {e}"
    except (KeyError, IndexError) as e:
        print(f"Error parsing transcription response: {e}")
        print(f"Full Bhashini Response: {response.json()}")
        return "Error parsing transcription response."


# --- TTS (Text-to-Speech) Functions (No changes needed here) ---

def get_tts_config(target_lang):
    """Fetches the pipeline configuration for TTS."""
    headers = {"userID": BHASHINI_USER_ID, "ulcaApiKey": BHASHINI_ULCA_API_KEY}
    payload = {
        "pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": target_lang}}}],
        "pipelineRequestConfig": {"pipelineId": PIPELINE_ID}
    }
    try:
        response = requests.post(PIPELINE_CONFIG_URL, json=payload, headers=headers)
        response.raise_for_status()
        config_data = response.json()

        service_id = config_data["pipelineResponseConfig"][0]["config"][0]["serviceId"]
        callback_url = config_data["pipelineInferenceAPIEndPoint"]["callbackUrl"]
        auth_name = config_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"]
        auth_value = config_data["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]
        
        return service_id, callback_url, auth_name, auth_value
    except requests.exceptions.RequestException as e:
        print(f"Error in TTS Pipeline Config Call: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return None, None, None, None
    except (KeyError, IndexError) as e:
        print(f"Error parsing TTS config response: {e}")
        return None, None, None, None

def run_bhashini_tts(text, target_lang="hi"):
    """
    Takes text, gets TTS config, and returns base64 encoded audio string.
    """
    print(f"Starting TTS for text: '{text}' in language: {target_lang}")
    tts_config = get_tts_config(target_lang)
    if not all(tts_config):
        return "Error: Could not get TTS configuration."

    service_id, callback_url, auth_name, auth_value = tts_config
    
    headers = {auth_name: auth_value, "Content-Type": "application/json"}
    payload = {
        "pipelineTasks": [
            {"taskType": "tts", "config": {
                "language": {"sourceLanguage": target_lang},
                "serviceId": service_id,
                "gender": "female",
                "samplingRate": 22050,
                "audioFormat": "wav"
            }}
        ],
        "inputData": {"input": [{"source": text}]}
    }

    try:
        print("Sending text for speech synthesis...")
        response = requests.post(callback_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        audio_b64 = result["pipelineResponse"][0]["audio"][0]["audioContent"]
        print("TTS successful.")
        return audio_b64
    except requests.exceptions.RequestException as e:
        print(f"Error in TTS Compute Call: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return f"Error during TTS: {e}"
    except (KeyError, IndexError) as e:
        print(f"Error parsing TTS response: {e}")
        return "Error parsing TTS response."