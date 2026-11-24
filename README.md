# Bronwaardig – SEO- en GEO-analysetool

Studentenproject (minor Datadriven & AI Solutions, Hogeschool Rotterdam), opdracht "Van SEO naar GEO".

De tool analyseert een webpagina op SEO, GEO-techniek en GEO-inhoud (met Google Gemini) en geeft verbeteradvies.

## Online zetten (Render)
Deze map bevat `render.yaml`. Kies in Render **New → Blueprint** en selecteer deze repository.
Vul daarna in:
- `GEMINI_API_KEY`: je Gemini API-sleutel (aistudio.google.com/apikey)
- `WACHTWOORD`: optioneel; leeg = iedereen met de link kan de tool gebruiken

## Lokaal draaien
    pip install -r requirements.txt
    GEMINI_API_KEY=... python app.py
