# app.py
import os
import json
from flask import Flask, request, jsonify
from google import genai
from google.genai.errors import APIError
from google.cloud import secretmanager
from google.auth.exceptions import DefaultCredentialsError

app = Flask(__name__)

# Oletusprojektin ID
# HUOM: Cloud Run asettaa GCP_PROJECT-ympäristömuuttujan automaattisesti.
# Käytetään sitä ensisijaisesti.
PROJECT_ID = os.environ.get('GCP_PROJECT') 

# --- Funktio salaisuuden lukemiseen Secret Managerista ---
def get_gemini_api_key():
    """Hakee Gemini API-avaimen turvallisesti Secret Managerista."""

    # TARKISTUS: Jos emme ole Cloud Runissa/GCP:ssä, emme voi jatkaa.
    if not PROJECT_ID:
        return "Virhe: GCP-projektin ID (GCP_PROJECT) puuttuu. Tämä sovellus täytyy ajaa GCP:ssä."
    
    secret_name = "gemini-api-key"
    # Muodostetaan täydellinen resurssinimi
    resource_name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"

    try:
        # 1. Alustetaan Secret Manager -asiakas
        client = secretmanager.SecretManagerServiceClient()
        
        # 2. Pyydetään salaisuuden uusin versio
        response = client.access_secret_version(request={"name": resource_name})
        
        # Palauta salaisuus dekoodattuna
        return response.payload.data.decode("UTF-8")

    except DefaultCredentialsError:
        # Tämä virhe tapahtuu, jos palvelutilillä ei ole oikeuksia (IAM)
        return "Virhe: GCP-oikeuksia (DefaultCredentialsError) puuttuu. Tarkista IAM-rooli."
    except Exception as e:
        return f"Virhe Secret Managerissa: {e}"

# --- Web-reitti ---
@app.route('/ask-gemini', methods=['POST'])
def ask_gemini():
    # 1. HAE SALAISUUS TURVALLISESTI
    api_key_or_error = get_gemini_api_key()
    
    if "Virhe:" in api_key_or_error:
        # Palauta virhe, jos salaisuutta ei saatu (tietoturvapuutos)
        return jsonify({"error": api_key_or_error}), 500
    
    # Koodin suoritus
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'Kirjoita lyhyt, tekninen yhteenveto Secret Managerista.')
        
        # 2. ALUSTA GEMINI-ASIAKAS TURVALLISELLA SALAISUUDELLA
        client = genai.Client(api_key=api_key_or_error) 

        # 3. KUTSU API:A
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )

        # 4. PALAUTA VASTAUS
        return jsonify({
            "status": "success",
            "source": "Secret Manager",
            "model": "gemini-2.5-flash",
            "response": response.text
        })

    except APIError as e:
        return jsonify({"error": f"Gemini API-virhe: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Tuntematon virhe tapahtui: {e}"}), 500

if __name__ == '__main__':
    # Paikallinen ajo ei toimi ilman erillisiä GCP-oikeuksia, joten emme suorita testiä täällä
    print("Huom: Tämä sovellus on suunniteltu ajettavaksi vain Google Cloud Runissa.")
    app.run(debug=True, host='127.0.0.1', port=8080)