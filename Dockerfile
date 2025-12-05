Dockerfile

Rakennusohje Cloud Runiin julkaisua varten

1. Käytä kevyttä Python-imagea pohjana (Alpine on kevyt Linux-jakelu)

FROM python:3.9-slim

2. Aseta työkansio Docker-kontin sisällä

WORKDIR /app

3. Kopioi riippuvuudet ja asenna ne

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

4. Kopioi sovelluskoodi

COPY app.py .

5. Määritä, mitä porttia sovellus kuuntelee

Ympäristömuuttuja $PORT asetetaan automaattisesti Cloud Runissa

ENV PORT 8080

6. Komento, joka käynnistää palvelimen

Käytetään gunicornia Flaskin sijaan tuotantoajoon

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app