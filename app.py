# app.py (Karsittu versio API-avaimen kelpoisuustestiin)
import os
from flask import Flask, request, jsonify
from google import genai
from google.genai.errors import APIError

# TÄRKEÄÄ: Poistettu kaikki Secret Manager- ja Firebase-tuonnit, jotta nähdään API-avaimen toimivuus

app = Flask(__name__)

# --- Funktio salaisuuden lukemiseen ympäristöstä ---
def get_gemini_api_key():
    """Hakee API-avaimen suoraan Cloud Runin ympäristömuuttujasta."""
    # Nimi on GEMINI_API_KEY_TEST, jonka asetit gcloud-komennossa
    api_key = os.environ.get("GEMINI_API_KEY_TEST")
    if not api_key:
        return "Virhe: GEMINI_API_KEY_TEST ei ole asetettu Cloud Runiin."
    return api_key

# --- Web-reitti ---
@app.route('/ask-gemini', methods=['POST'])
def ask_gemini():
    # 1. HAE SALAISUUS TURVALLISESTI
    api_key_or_error = get_gemini_api_key()
    
    if "Virhe:" in api_key_or_error:
        # Palauttaa virheen, jos muuttujaa ei löydy Cloud Runista
        return jsonify({"error": api_key_or_error}), 500
    
    # Koodin suoritus
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'Kirjoita lyhyt yhteenveto karsitusta sovelluksesta.')
        
        # 2. KUTSU GEMINI API:A
        client = genai.Client(api_key=api_key_or_error) 
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # LOKITUS POISTETTU TÄSTÄ VERSIOSTA
        
        # 3. PALAUTA VASTAUS
        return jsonify({
            "status": "success",
            "source": "Environment Variable Test",
            "response": response.text
        })

    except APIError as e:
        return jsonify({"error": f"Gemini API-virhe: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Tuntematon virhe tapahtui: {e}"}), 500

if __name__ == '__main__':
    # ...
    app.run(debug=True, host='127.0.0.1', port=8080)