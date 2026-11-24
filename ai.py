"""
LAAG 2 EN 3 - DE AI (Google Gemini)
===================================

Laag 2: de AI beoordeelt de tekst op 6 punten (hoofdstuk 6 van de methode).
        - vaste ankers per cijfer (wat is een 1, 3 en 5)
        - bewijs verplicht: de AI citeert de pagina en de tool controleert dat citaat
        - meerdere rondes, we nemen het middelste cijfer (mediaan)
        - temperature 0 en altijd hetzelfde model
Laag 3: de AI schrijft advies over de inhoud. De tool zet erbij dat het door AI is geschreven.
"""

import json
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from analyse import normaliseer_tekst
from methode import CRITERIA, ONZEKER_VANAF

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
STANDAARD_MODEL = "gemini-flash-lite-latest"
RESERVE_MODELLEN = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
PROMPT_VERSIE = "2.2"


class AIFout(Exception):
    pass


def vraag_gemini(prompt: str, sleutel: str, model: str, json_antwoord=False):
    """Stuurt een vraag naar Gemini. Geeft (tekst, gebruikt_model, modelversie) terug.
    Bij drukte wacht de tool even; lukt het dan nog niet, dan probeert hij een reservemodel."""
    config = {"temperature": 0}
    if json_antwoord:
        config["responseMimeType"] = "application/json"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}

    laatste = ""
    for m in [model] + [x for x in RESERVE_MODELLEN if x != model]:
        for poging in range(3):
            try:
                r = requests.post(API_URL.format(model=m), headers={"x-goog-api-key": sleutel}, json=body, timeout=90)
                if r.status_code in (400, 401, 403):
                    r2 = requests.post(API_URL.format(model=m), params={"key": sleutel}, json=body, timeout=90)
                    if r2.status_code not in (400, 401, 403):
                        r = r2
            except requests.Timeout:
                laatste = f"{m} reageerde te traag"
                break
            except requests.RequestException as e:
                raise AIFout(f"Geen verbinding met Gemini ({e.__class__.__name__}). Controleer de internetverbinding.")

            if r.status_code == 200:
                data = r.json()
                try:
                    tekst = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
                except (KeyError, IndexError):
                    raise AIFout("Gemini gaf een leeg antwoord (mogelijk tegengehouden door een filter).")
                return tekst, m, data.get("modelVersion", m)
            try:
                melding = r.json().get("error", {}).get("message", "")[:220]
            except ValueError:
                melding = r.text[:220]
            if r.status_code in (429, 500, 502, 503, 504):
                laatste = f"{m} is druk of de limiet is bereikt ({melding})"
                time.sleep(4 + 6 * poging)
                continue
            if r.status_code == 404:
                laatste = f"model {m} bestaat niet (meer)"
                break
            if r.status_code in (400, 401, 403):
                raise AIFout(f"Google accepteert de AI-sleutel niet. Controleer sleutel.txt. (Melding van Google: {melding})")
            raise AIFout(f"Gemini gaf foutcode {r.status_code}: {melding}")
        # volgend model proberen
    raise AIFout(f"Gemini is nu niet bereikbaar: {laatste}. Wacht een paar minuten en probeer opnieuw.")


def _lees_json(tekst: str):
    m = re.search(r"\{.*\}", tekst, re.S)
    kandidaat = m.group(0) if m else tekst
    gerepareerd = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", re.sub(r"\\u(?![0-9a-fA-F]{4})", r"\\\\u", kandidaat))
    for t in (tekst, kandidaat, gerepareerd):
        try:
            return json.loads(t, strict=False)
        except json.JSONDecodeError:
            continue
    raise AIFout("Het antwoord van de AI kon niet worden gelezen.")


# --------------------------------------------------------------------------
# Laag 2: beoordelen
# --------------------------------------------------------------------------

def _beoordeel_prompt(tekst_voor_ai: str) -> str:
    regels = []
    for c in CRITERIA:
        a = c["ankers"]
        regels.append(f"- {c['id']}: {c['vraag']}\n    1 = {a[1]}\n    3 = {a[3]}\n    5 = {a[5]}\n    (2 en 4 liggen ertussen)")
    return f"""Je beoordeelt een webpagina voor een onderzoek naar Generative Engine Optimization (GEO):
hoe geschikt is deze pagina als bron voor AI-zoekmachines zoals ChatGPT, Perplexity en Google AI Overviews?

Werk per criterium in deze volgorde:
1. Zoek eerst bewijs: een letterlijk citaat uit de pagina van maximaal 25 woorden.
   Kopieer het precies zoals het op de pagina staat. Verzin nooit tekst.
   Bij cijfer 1 mag het citaat leeg zijn ("") als er niets te citeren valt.
2. Leg in één korte zin in eenvoudig Nederlands uit wat je ziet.
3. Geef dan pas een cijfer van 1 tot 5 volgens de ankers.

Belangrijk:
- De lengte van de tekst is GEEN kwaliteitscriterium. Een korte tekst kan een 5 krijgen.
- Beoordeel alleen wat er op de pagina staat, niet wat de organisatie misschien elders heeft.
- Informatie in het menu, de koptekst of de voettekst (zoals adres, telefoon of openingstijden) staat ook op de pagina en telt mee.
- Staat iets alleen als link naar een andere pagina (bijvoorbeeld "Openingstijden"), dan staat de informatie zelf NIET op deze pagina.
- Wees streng en consequent.

CRITERIA:
{chr(10).join(regels)}

Antwoord UITSLUITEND met JSON in dit formaat:
{{"onderwerp": "<waar gaat de pagina over, max 8 woorden>",
  "criteria": [{{"id": "<criterium-id>", "citaat": "<letterlijk citaat>", "uitleg": "<één zin>", "score": <1-5>}}]}}

WEBPAGINA:
\"\"\"
{tekst_voor_ai}
\"\"\"
"""


def _citaat_klopt(citaat: str, pagina_norm: str) -> bool:
    c = normaliseer_tekst(citaat).strip(" .\"'…")
    if not c:
        return False
    if c in pagina_norm:
        return True
    # Sta weglatingstekens toe: elk stuk moet op de pagina staan
    stukken = [s.strip(" .\"'") for s in re.split(r"\.\.\.|…", c) if len(s.strip()) >= 8]
    return bool(stukken) and all(s in pagina_norm for s in stukken)


def beoordeel(tekst_voor_ai: str, pagina_norm: str, sleutel: str, model: str, rondes: int = 5) -> dict:
    prompt = _beoordeel_prompt(tekst_voor_ai)

    def een_ronde(_):
        try:
            t, m, versie = vraag_gemini(prompt, sleutel, model, json_antwoord=True)
            return _lees_json(t), m, versie, None
        except AIFout as e:
            return None, None, None, str(e)

    with ThreadPoolExecutor(max_workers=rondes) as pool:
        alle = list(pool.map(een_ronde, range(rondes)))
    gelukt = [u for u in alle if u[0] is not None]
    if not gelukt:
        raise AIFout(alle[0][3])

    citaten_totaal = citaten_fout = 0
    resultaten = []
    for c in CRITERIA:
        geldige, rondes_info, uitleg, citaat = [], [], "", ""
        for data, *_ in gelukt:
            item = next((i for i in data.get("criteria", []) if i.get("id") == c["id"]), None)
            if not item:
                continue
            try:
                score = max(1, min(5, int(round(float(item.get("score"))))))
            except (TypeError, ValueError):
                continue
            cit = (item.get("citaat") or "").strip()
            if score == 1 and not cit:
                geldig = True  # niets te citeren bij de laagste score
            else:
                citaten_totaal += 1
                geldig = _citaat_klopt(cit, pagina_norm)
                if not geldig:
                    citaten_fout += 1
            rondes_info.append({"score": score, "geldig": geldig})
            if geldig:
                geldige.append(score)
                if not uitleg:
                    uitleg, citaat = item.get("uitleg", ""), cit
        if geldige:
            mediaan = statistics.median(geldige)
            spreiding = max(geldige) - min(geldige)
        else:
            mediaan, spreiding = None, None
        resultaten.append({
            "id": c["id"], "naam": c["naam"], "vraag": c["vraag"], "bron": c["bron"],
            "cijfer": mediaan, "rondes": rondes_info, "spreiding": spreiding,
            "onzeker": spreiding is not None and spreiding >= ONZEKER_VANAF,
            "uitleg": uitleg, "citaat": citaat,
        })

    bruikbaar = [r["cijfer"] for r in resultaten if r["cijfer"] is not None]
    if not bruikbaar:
        raise AIFout("De AI kon geen enkele beoordeling met geldig bewijs geven. Probeer het opnieuw.")
    gemiddeld = statistics.mean(bruikbaar)
    modellen = sorted({u[1] for u in gelukt})
    versies = sorted({u[2] for u in gelukt})
    return {
        "onderwerp": gelukt[0][0].get("onderwerp", ""),
        "criteria": resultaten,
        "gemiddelde": round(gemiddeld, 2),
        "score": round((gemiddeld - 1) / 4 * 100),
        "rondes_gevraagd": rondes,
        "rondes_gelukt": len(gelukt),
        "verzonnen_citaten": citaten_fout,
        "citaten_totaal": citaten_totaal,
        "model": ", ".join(modellen),
        "modelversie": ", ".join(versies),
        "ander_model": modellen != [model],
        "promptversie": PROMPT_VERSIE,
    }


# --------------------------------------------------------------------------
# Laag 3: advies over de inhoud
# --------------------------------------------------------------------------

def schrijf_advies(tekst_voor_ai: str, inhoud: dict, sleutel: str, model: str):
    """Geeft (samenvatting, adviezen) terug."""
    criteria = "\n".join(
        f"- {c['naam']} ({c['id']}): cijfer {c['cijfer'] if c['cijfer'] is not None else 'onbekend'}. {c['uitleg']}"
        for c in inhoud["criteria"])
    prompt = f"""Je bent een ervaren adviseur voor Generative Engine Optimization (GEO). Een organisatie wil dat AI-zoekmachines
(ChatGPT, Perplexity, Google AI Overviews) deze pagina vaker als bron gebruiken.

Hieronder staat hoe de inhoud van de pagina is beoordeeld (cijfer 1-5):
{criteria}

Schrijf:
1. Een samenvatting van 2 tot 3 zinnen: wat gaat goed en wat is het belangrijkste verbeterpunt voor de inhoud?
2. 4 tot 6 concrete adviezen om de INHOUD van deze pagina te verbeteren. Begin bij wat het meeste oplevert.

Per advies:
- titel: kort en concreet
- criterium: het id van het criterium waar het bij hoort
- prioriteit: Hoog, Middel of Laag
- inspanning: Klein (minder dan een uur), Middel (een dagdeel) of Groot (meer dan een dag)
- nu: wat er NU op de pagina staat of ontbreekt (feitelijk, één of twee zinnen)
- waarom: waarom dit helpt om door AI als bron gebruikt te worden (twee of drie zinnen)
- stappen: 2 tot 4 korte stappen om het uit te voeren
- voorbeeld: een concreet voorbeeld dat past bij deze pagina (voorbeeldtekst, voorbeeldkop of voorbeeldvraag met antwoord)

Regels:
- Schrijf in eenvoudig Nederlands, voor een marketeer zonder technische kennis. Spreek de lezer aan met "u".
- Het menu en de voettekst horen ook bij de pagina. Adviseer niets toe te voegen wat daar al staat.
- Staat informatie alleen op een andere pagina (er is een link in het menu, bijvoorbeeld "Openingstijden"), zeg dat dan.
  Adviseer dan bijvoorbeeld een korte samenvatting op deze pagina met een link naar de pagina met alle details.
- Verzin GEEN feiten over de organisatie. Ken je een gegeven niet (prijs, tijd, aantal, naam), schrijf dan een invulplek
  tussen blokhaken, bijvoorbeeld [vul uw openingstijden in].
- Geen technische adviezen (zoals code, snelheid of robots); die geeft de tool al apart.

Antwoord UITSLUITEND met JSON:
{{"samenvatting": "<2-3 zinnen>",
  "adviezen": [{{"titel": "", "criterium": "", "prioriteit": "Hoog", "inspanning": "Klein", "nu": "", "waarom": "",
                 "stappen": ["", ""], "voorbeeld": ""}}]}}

PAGINA:
\"\"\"
{tekst_voor_ai[:16000]}
\"\"\"
"""
    t, _, _ = vraag_gemini(prompt, sleutel, model, json_antwoord=True)
    data = _lees_json(t)
    keuze = lambda v, opties, std: v if v in opties else std
    adviezen = []
    for a in data.get("adviezen", [])[:6]:
        stappen = a.get("stappen") if isinstance(a.get("stappen"), list) else []
        adviezen.append({
            "titel": str(a.get("titel", "")).strip(),
            "criterium": str(a.get("criterium", "")).strip(),
            "prioriteit": keuze(a.get("prioriteit"), ("Hoog", "Middel", "Laag"), "Middel"),
            "inspanning": keuze(a.get("inspanning"), ("Klein", "Middel", "Groot"), ""),
            "nu": str(a.get("nu", "")).strip(),
            "waarom": str(a.get("waarom", "")).strip(),
            "stappen": [str(s).strip() for s in stappen if str(s).strip()][:4],
            "voorbeeld": str(a.get("voorbeeld", "")).strip(),
        })
    return str(data.get("samenvatting", "")).strip(), adviezen


# --------------------------------------------------------------------------
# "Leg beter uit": een langere uitleg over één advies, check of AI-punt
# --------------------------------------------------------------------------

def leg_uit(onderwerp: str, tekst_voor_ai: str, sleutel: str, model: str) -> list:
    """Geeft een lijst met onderdelen terug: [{"kop": ..., "tekst": ..., "lijst": [...]}]."""
    prompt = f"""Je bent een geduldige adviseur voor SEO en Generative Engine Optimization (GEO). Je legt uit aan een
marketeer zonder technische kennis. De gebruiker heeft op "Leg beter uit" geklikt bij dit onderdeel van een analyse:

{onderwerp}

Schrijf een uitgebreide, maar makkelijke uitleg in het Nederlands, specifiek voor de pagina hieronder.
Gebruik deze onderdelen (laat een onderdeel weg als het niet past):
1. "Wat betekent dit?" - leg het begrip of de bevinding uit in gewone woorden, met een vergelijking uit het dagelijks leven.
2. "Wat zien we op deze pagina?" - wat er nu concreet op deze pagina staat of ontbreekt.
3. "Waarom is dit belangrijk?" - voor Google en voor AI-zoekmachines zoals ChatGPT.
4. "Zo pakt u het aan" - een stappenplan (3 tot 6 stappen) dat past bij deze pagina.
5. "Voorbeeld" - een concreet voorbeeld (tekst, kop of code) voor deze pagina.
6. "Zo controleert u of het gelukt is" - hoe de gebruiker kan zien dat het goed is gegaan.
7. "Veelgemaakte fouten" - 2 of 3 dingen om op te letten.

Regels:
- Spreek de lezer aan met "u". Korte zinnen. Leg vaktermen meteen uit.
- Verzin GEEN feiten over de organisatie. Gebruik invulplekken tussen blokhaken, bijvoorbeeld [vul uw adres in].
- Het menu en de voettekst horen ook bij de pagina.
- Noem geen bronnen of onderzoeken die je niet zeker weet.

Antwoord UITSLUITEND met JSON:
{{"onderdelen": [{{"kop": "<kop>", "tekst": "<1-4 zinnen of leeg>", "lijst": ["<stap of punt>", "..."]}}]}}

PAGINA:
\"\"\"
{tekst_voor_ai[:14000]}
\"\"\"
"""
    t, _, _ = vraag_gemini(prompt, sleutel, model, json_antwoord=True)
    data = _lees_json(t)
    uit = []
    for o in data.get("onderdelen", [])[:8]:
        lijst = o.get("lijst") if isinstance(o.get("lijst"), list) else []
        uit.append({"kop": str(o.get("kop", "")).strip(), "tekst": str(o.get("tekst", "")).strip(),
                    "lijst": [str(x).strip() for x in lijst if str(x).strip()][:8]})
    if not uit:
        raise AIFout("De AI gaf geen bruikbare uitleg. Probeer het nog een keer.")
    return uit
