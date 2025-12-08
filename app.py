# app.py (KRIITISESTI KORJATTU VERSIO)
import os
from flask import Flask, request, jsonify
from google import genai
from google.genai.errors import APIError
from google.auth.exceptions import DefaultCredentialsError

# Uudet tuonnit Secret Managerille (HUOM: Suora tuonti)
from google.cloud.secretmanager import SecretManagerServiceClient 

# Uudet tuonnit Firestorelle (firebase-admin)
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime

app = Flask(__name__)

# Oletusprojektin ID (käytetään Secret Managerissa ja Firebase Alustuksessa)
# GCP_PROJECT on Cloud Runin automaattisesti asettama ympäristömuuttuja.
# Tämä täytyy hakea heti alussa.
PROJECT_ID = os.environ.get('GCP_PROJECT') 

# --- Firebase & Firestore Alustus ---
db = None # Oletetaan, että Firestore ei ole käytössä

try:
    if not PROJECT_ID:
        # TÄMÄ KAATAA GUNICORNIN, JOS KUTSUTAAN ENNEN KUIN GCP_PROJECT ON ASETETTU
        # Mutta Cloud Runissa sen pitäisi olla OK. Jos ei, tämä tulostuu lokiin.
        raise Exception("GCP_PROJECT puuttuu. Ei voida alustaa Firebasea.")
        
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        
        # Alustetaan Firebase nimenomaisesti projektin ID:llä
        firebase_admin.initialize_app(cred, {
            'projectId': PROJECT_ID 
        })
    db = firestore.client()
    print("FIREBASE ALUSTUS ONNISTUI!") # TARKISTUSLOKI, näkyy Cloud Loggingissa
    
except Exception as e:
    # JOS ALUSTUS EPÄONNISTUU (esim. puuttuva IAM-rooli), emme kaada koko Gunicornia
    print(f"CRITICAL ERROR: FIREBASE ALUSTUS EPÄONNISTUI: {e}")
    db = None 
# ...


# --- Funktio salaisuuden lukemiseen Secret Managerista ---
def get_gemini_api_key():
    """Hakee Gemini API-avaimen turvallisesti Secret Managerista."""
    
    if not PROJECT_ID:
        # Tämä virhe palautuu, jos GCP_PROJECT ei ole asetettu, mikä on virheellinen tila Cloud Runissa.
        return "Virhe: GCP-projektin ID (GCP_PROJECT) puuttuu. Palvelu on virheellisesti konfiguroitu."
        
    secret_name = "gemini-api-key"
    resource_name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"

    try:
        client = SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": resource_name})
        return response.payload.data.decode("UTF-8")

    except DefaultCredentialsError:
        return "Virhe: GCP-oikeuksia (DefaultCredentialsError) puuttuu. Tarkista IAM-rooli."
    except Exception as e:
        # Palauttaa virheen, jos esim. salaisuutta ei löydy (Secret not found)
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
                db.collection('gemini_logs').add({
                    'timestamp': datetime.now(),
                    'user_prompt': prompt,
                    'model_response_snippet': response.text[:100] + "...", 
                    'status': 'SUCCESS'
                })
            except Exception as e:
                print(f"LOKITUSVIRHE: {e}") # Näkyy Cloud Loggingissa
        
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