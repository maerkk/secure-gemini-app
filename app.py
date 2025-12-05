# app.py (PÄIVITETTY)
import os
from flask import Flask, request, jsonify
from google import genai
from google.genai.errors import APIError
from google.cloud import secretmanager
from google.auth.exceptions import DefaultCredentialsError

# Uudet tuonnit Firestorelle (firebase-admin)
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime

app = Flask(__name__)

# --- Firebase & Firestore Alustus ---
# Alustaa Firebase Admin SDK:n. Cloud Runissa tämä käyttää automaattisesti 
# Cloud Runin palvelutiliä (jonka IAM-roolit juuri asetimme).
try:
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"FIREBASE VIRHE ALUSTUKSESSA: {e}")
    db = None # Jos alustus epäonnistuu, db-muuttuja on None.

# Oletusprojektin ID (käytetään Secret Managerissa)
PROJECT_ID = os.environ.get('GCP_PROJECT') 

# --- Funktio salaisuuden lukemiseen Secret Managerista ---
def get_gemini_api_key():
    """Hakee Gemini API-avaimen turvallisesti Secret Managerista."""
    if not PROJECT_ID:
        return "Virhe: GCP-projektin ID (GCP_PROJECT) puuttuu."
    
    secret_name = "gemini-api-key"
    resource_name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"

    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": resource_name})
        return response.payload.data.decode("UTF-8")

    except DefaultCredentialsError:
        return "Virhe: GCP-oikeuksia (DefaultCredentialsError) puuttuu. Tarkista IAM-rooli."
    except Exception as e:
        return f"Virhe Secret Managerissa: {e}"


# --- Web-reitti ---
@app.route('/ask-gemini', methods=['POST'])
def ask_gemini():
    # 1. HAE SALAISUUS TURVALLISESTI
    api_key_or_error = get_gemini_api_key()
    
    if "Virhe:" in api_key_or_error:
        return jsonify({"error": api_key_or_error}), 500
    
    # Koodin suoritus
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'Kirjoita lyhyt, tekninen yhteenveto Firestoresta ja lokituksesta.')
        
        client = genai.Client(api_key=api_key_or_error) 
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # 2. LOKITUS FIRESTOREEN (Lokittaa onnistuneen API-kutsun)
        if db:
            try:
                # Tallennetaan uusi dokumentti 'gemini_logs' -kokoelmaan
                db.collection('gemini_logs').add({
                    'timestamp': datetime.now(),
                    'user_prompt': prompt,
                    'model_response_snippet': response.text[:100] + "...", 
                    'status': 'SUCCESS'
                })
            except Exception as e:
                # Jos lokitus epäonnistuu, tulostetaan virhe Cloud Loggingiin
                print(f"LOKITUSVIRHE: {e}")

        # 3. PALAUTA VASTAUS
        return jsonify({
            "status": "success",
            "source": "Secret Manager & Firestore Lokitus",
            "response": response.text
        })

    except APIError as e:
        return jsonify({"error": f"Gemini API-virhe: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Tuntematon virhe tapahtui: {e}"}), 500

if __name__ == '__main__':
    print("Huom: Tämä sovellus on suunniteltu ajettavaksi vain Google Cloud Runissa.")
    app.run(debug=True, host='127.0.0.1', port=8080)