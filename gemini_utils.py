import os
import json
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash')

LEGAL_ADVISOR_PROMPT = """
You are Nyay Sahayak, an AI legal advisor for Indian law. Your role is to provide general guidance and explain legal concepts in a simple and understandable way.

**Your Instructions:**
1.  Analyze the user's query and identify the key legal issues.
2.  Provide a clear, step-by-step explanation of the relevant legal provisions or procedures.
3.  Do not use complex legal jargon. If you must use a legal term, explain it immediately.
4.  You can ask clarifying questions if the user's query is vague.
5.  **Crucially, you must end EVERY response with the following disclaimer:**
    ---
    **Disclaimer:** I am an AI assistant and not a qualified lawyer. This information is for educational purposes only and should not be considered as legal advice. Please consult with a professional lawyer for any legal action or decision."

User's query is: "{user_query}"
"""

FIR_FILLER_PROMPT_START = """
You are an assistant helping a user fill out a demonstration First Information Report (FIR).
Your task is to ask the user for information for each field, one at a time. After asking for a piece of information, explain its legal significance in one or two simple sentences.
Start by asking for the first field: "Complainant's Name".
"""

FIR_FILLER_PROMPT_CONTINUE = """
You are an assistant helping a user fill out a demonstration First Information Report (FIR).
You have already collected the following information:
{collected_data}

The user just provided the answer for the last question. Now, you must ask for the next field: **'{next_field}'**.
After asking the question, briefly explain its legal importance in simple terms.
"""

FIR_FILLER_PROMPT_FINALIZE = """
You have collected all the necessary information for the demonstration FIR.
Your final task is to generate a JSON object containing the summary.

**Instructions:**
1.  First, write a brief introductory sentence in English.
2.  Then, on a new line, provide a JSON object enclosed in ```json ... ```.
3.  The JSON object must have a key called "fir_data" which is an array of objects.
4.  Each object in the array represents a field and must have two keys: "label" (the field name) and "value" (the user's answer).
5.  After the JSON object, on a new line, add the mandatory disclaimer.
6.  Do not add any other text, formatting, or explanations outside this structure.

Here is the collected data:
{form_data}

Example of the required output format:
Here is the summary of your demonstration FIR.
```json
{{
  "fir_data": [
    {{"label": "Complainant's Name", "value": "Rishik Ashili"}},
    {{"label": "Father's/Husband's Name", "value": "Shankar Ashili"}}
  ]
}}
Disclaimer: I am an AI assistant...
"""

def get_legal_guidance(user_query):
    try:
        prompt = LEGAL_ADVISOR_PROMPT.format(user_query=user_query)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error getting response from Gemini: {e}")
        return "Sorry, I encountered an error trying to process your request."

def translate_to_hindi(text):
    try:
        json_fence = "```json"
        if json_fence in text:
            parts = text.split(json_fence)
            intro_text = parts[0].strip()
            translated_intro = model.generate_content(
                f"Translate the following English text into Hindi: '{intro_text}'"
            ).text.strip()

            json_and_rest = parts[1].split("```")
            json_part = json_and_rest[0].strip()

            disclaimer_part_hindi = ""
            if "---" in text:
                disclaimer_original = text.split("---", 1)[1]
                disclaimer_hindi_prompt = f"Translate the following disclaimer into Hindi: '---{disclaimer_original}'"
                disclaimer_part_hindi = model.generate_content(disclaimer_hindi_prompt).text.strip()

            return f"{translated_intro}\n```json\n{json_part}\n```\n{disclaimer_part_hindi}"
        else:
            prompt = (
                f"Translate the following English text into Hindi. Do not translate markdown like `**` or `---`.\n\n{text}"
            )
            response = model.generate_content(prompt)
            return response.text.strip()
    except Exception as e:
        print(f"Error during translation with Gemini: {e}")
        return "अनुवाद में त्रुटि हुई।"

def get_form_filler_response(next_field=None, collected_data=None, finalize_data=None):
    try:
        if finalize_data:
            form_data_str = "\n".join([f"- {key}: {value}" for key, value in finalize_data.items()])
            prompt = FIR_FILLER_PROMPT_FINALIZE.format(form_data=form_data_str)
        elif next_field:
            collected_data_str = "\n".join([f"- {key}: {value}" for key, value in collected_data.items()])
            prompt = FIR_FILLER_PROMPT_CONTINUE.format(
                collected_data=collected_data_str, next_field=next_field
            )
        else:
            prompt = FIR_FILLER_PROMPT_START

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error in form filler response from Gemini: {e}")
        return "Sorry, I encountered an error. Let's try again."