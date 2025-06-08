from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os

load_dotenv()

import bhashini_utils
import gemini_utils

app = Flask(__name__)

fir_form_state = {}
FIR_FIELDS = [
    "Complainant's Name",
    "Father's/Husband's Name",
    "Complainant's Address",
    "Place of Occurrence",
    "Date and Time of Occurrence",
    "Details of the Incident (in brief)",
    "Name(s) of the accused (if known)"
]

def get_or_create_session(session_id):
    """Initializes or retrieves the form state for a session."""
    if session_id not in fir_form_state:
        fir_form_state[session_id] = {
            "active": False,
            "current_field_index": 0,
            "form_data": {},
        }
    return fir_form_state[session_id]


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    session_id = request.remote_addr
    state = get_or_create_session(session_id)

    user_input = ""
    is_audio_input = 'audio_data' in request.files

    if is_audio_input:
        audio_file = request.files['audio_data']
        audio_bytes = audio_file.read()
        
        user_input = bhashini_utils.run_bhashini_transcription(audio_bytes, source_lang="en")
        if "Error" in user_input or user_input == "(No speech detected)":
            error_message = user_input if "Error" in user_input else "I couldn't hear anything. Please try speaking again."
            return jsonify({"english_response": error_message, "hindi_response": "मैं कुछ सुन नहीं पाया। कृपया दोबारा प्रयास करें।", "audio_response": None})
    else:
        user_input = request.form.get('text_input')

    if user_input.strip().lower() == "fill fir form":
        state["active"] = True
        state["current_field_index"] = 0
        state["form_data"] = {}
        
        bot_response_en = gemini_utils.get_form_filler_response()

    elif state.get("active"):
        previous_field_index = state["current_field_index"]
        if previous_field_index < len(FIR_FIELDS):
            field_to_save = FIR_FIELDS[previous_field_index]
            state["form_data"][field_to_save] = user_input
        
        state["current_field_index"] += 1
        
        if state["current_field_index"] < len(FIR_FIELDS):
            next_field_to_ask = FIR_FIELDS[state["current_field_index"]]
            bot_response_en = gemini_utils.get_form_filler_response(
                next_field=next_field_to_ask,
                collected_data=state["form_data"]
            )
        else:
            bot_response_en = gemini_utils.get_form_filler_response(
                finalize_data=state["form_data"]
            )
            state["active"] = False
    
    else:
        bot_response_en = gemini_utils.get_legal_guidance(user_input)

    bot_response_hi = gemini_utils.translate_to_hindi(bot_response_en)
    
    audio_response_b64 = None
    if is_audio_input or state.get("active") or user_input.strip().lower() == "fill fir form":
        audio_response_b64 = bhashini_utils.run_bhashini_tts(bot_response_hi, target_lang="hi")

    return jsonify({
        "english_response": bot_response_en,
        "hindi_response": bot_response_hi,
        "audio_response": audio_response_b64
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)