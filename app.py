"""
DE WEBSERVER VAN DE TOOL
========================
Start de tool met start.command. Daarna opent de tool in je browser op http://127.0.0.1:8765

Dit bestand verbindt de onderdelen:
  analyse.py  -> technische checks (laag 1)
  ai.py       -> AI-beoordeling en advies (laag 2 en 3)
  scores.py   -> de scores en de varianten voor hoofdstuk 8
  static/     -> de webpagina die je ziet
"""

import csv
import io
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, send_from_directory, session

import ai
import analyse
import methode
import scores

MAP = Path(__file__).resolve().parent
RESULTATEN = MAP / "resultaten-v2"
INSTELLINGEN = MAP / "instellingen.json"
SLEUTEL = MAP / "sleutel.txt"
TOOLVERSIE = "2.0"

app = Flask(__name__, static_folder=str(MAP / "static"), static_url_path="/static")
app.json.sort_keys = False  # volgorde van de checks behouden
app.secret_key = os.urandom(24)  # nieuw bij elke start: na een herstart moet je opnieuw inloggen
WACHTWOORD = MAP / "wachtwoord.txt"
banen = {}  # lopende analyses
teksten = {}  # paginatekst per analyse, alleen in het geheugen (niet opgeslagen, privacy)


# ---------------- hulpfuncties ----------------

def lees_sleutel():
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    if SLEUTEL.exists():
        for regel in SLEUTEL.read_text(encoding="utf-8").splitlines():
            regel = regel.strip()
            if regel and not regel.startswith("#") and "PLAK" not in regel.upper():
                return regel
    return ""


def lees_instellingen():
    standaard = {"model": ai.STANDAARD_MODEL, "rondes": 5}
    try:
        standaard.update(json.loads(INSTELLINGEN.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return standaard


def opgeslagen():
    RESULTATEN.mkdir(exist_ok=True)
    uit = []
    for f in sorted(RESULTATEN.glob("*.json")):
        if f.name == "zichtbaarheid.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            d["bestand"] = f.name
            uit.append(d)
        except (OSError, ValueError):
            continue
    return uit


def lees_zichtbaarheid():
    try:
        return json.loads((RESULTATEN / "zichtbaarheid.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def regel_adviezen(poorten, checks):
    """Vaste adviezen voor alles wat niet goed ging (geen AI). Belangrijkste eerst."""
    uit = []
    for p in poorten:
        if not p["ok"]:
            uit.append({"soort": "basis", "titel": p["naam"], "tekst": p["advies"], "bron": p["bron"], "gevonden": p["gevonden"]})
    volgorde = {"sterk": 0, "vuistregel": 1, "zwak": 2}
    for c in sorted(checks, key=lambda c: (not c["telt"], volgorde[c["bewijs"]])):
        if c["status"] in ("fout", "deels"):
            uit.append({"soort": "check" if c["telt"] else "tip", "titel": c["naam"], "tekst": c["advies"],
                        "bron": c["bron"], "gevonden": c["gevonden"], "bewijs": c["bewijs"], "groep": c["groep"]})
    return uit


# ---------------- de analyse (draait op de achtergrond) ----------------

STAPPEN = [
    ("ophalen", "Pagina ophalen en technische checks uitvoeren"),
    ("snelheid", "Snelheid laten meten door Google"),
    ("ai", "Tekst laten beoordelen door de AI"),
    ("advies", "Advies over de inhoud laten schrijven"),
]


def voer_uit(baan_id, url):
    baan = banen[baan_id]
    zet = lambda stap, status, tekst=None: baan["stappen"][stap].update({"status": status, **({"tekst": tekst} if tekst else {})})
    inst = lees_instellingen()
    sleutel = lees_sleutel()
    try:
        zet("ophalen", "bezig")
        a = analyse.analyseer(url)
        zet("ophalen", "klaar")

        ai_mag = bool(sleutel) and not a["geblokkeerd"] and a["woorden"] >= 30
        inhoud, advies, ai_fout, samenvatting = None, [], None, ""

        def doe_snelheid():
            zet("snelheid", "bezig")
            c = analyse.meet_snelheid(a["url"], sleutel)
            zet("snelheid", "klaar" if c["status"] != "nvt" else "overgeslagen", None if c["status"] != "nvt" else "Niet gemeten")
            return c

        def doe_ai():
            if not ai_mag:
                reden = ("Geen AI-sleutel gevonden" if not sleutel else
                         "De website blokkeert automatische bezoekers" if a["geblokkeerd"] else "Te weinig tekst op de pagina")
                zet("ai", "overgeslagen", reden)
                zet("advies", "overgeslagen", reden)
                return None, ("", []), reden
            try:
                zet("ai", "bezig", f"Tekst laten beoordelen door de AI ({inst['rondes']}×)")
                ih = ai.beoordeel(a["_tekst_voor_ai"], a["_tekst_genormaliseerd"], sleutel, inst["model"], int(inst["rondes"]))
                zet("ai", "klaar")
            except ai.AIFout as e:
                zet("ai", "fout", str(e))
                zet("advies", "overgeslagen", "AI-beoordeling mislukt")
                return None, ("", []), str(e)
            try:
                zet("advies", "bezig")
                adv = ai.schrijf_advies(a["_tekst_voor_ai"], ih, sleutel, inst["model"])
                zet("advies", "klaar")
            except ai.AIFout as e:
                zet("advies", "fout", str(e))
                adv = ("", [])
            return ih, adv, None

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_snel = pool.submit(doe_snelheid)
            f_ai = pool.submit(doe_ai)
            snel = f_snel.result()
            inhoud, (samenvatting, advies), ai_fout = f_ai.result()

        checks = [snel if c["id"] == "snelheid" else c for c in a["checks"]]
        geo_i = inhoud["score"] if inhoud else None
        resultaat = {
            "toolversie": TOOLVERSIE,
            "datum": datetime.now().isoformat(timespec="seconds"),
            "url": a["url"], "gevraagde_url": a["gevraagde_url"], "domein": a["domein"],
            "titel": a["titel"], "omschrijving": a["omschrijving"], "woorden": a["woorden"],
            "geblokkeerd": a["geblokkeerd"],
            "poorten": a["poorten"],
            "basis_ok": all(p["ok"] for p in a["poorten"]),
            "checks": checks,
            "info": a["info"],
            "waarschuwingen": a["waarschuwingen"],
            "scores": scores.bereken(checks, geo_i),
            "varianten": scores.varianten(checks, geo_i),
            "inhoud": inhoud,
            "ai_samenvatting": samenvatting,
            "ai_advies": advies,
            "ai_fout": ai_fout,
            "regel_advies": regel_adviezen(a["poorten"], checks),
            "instellingen": {"model": inst["model"], "rondes": int(inst["rondes"])},
        }
        RESULTATEN.mkdir(exist_ok=True)
        naam = f"{datetime.now():%Y-%m-%d_%H-%M-%S}_{a['domein'].replace(':', '_')}.json"
        (RESULTATEN / naam).write_text(json.dumps(resultaat, ensure_ascii=False, indent=2), encoding="utf-8")
        resultaat["bestand"] = naam
        teksten[naam] = a["_tekst_voor_ai"]
        baan["resultaat"] = resultaat
        baan["klaar"] = True
    except analyse.AnalyseFout as e:
        baan["fout"] = str(e)
        baan["klaar"] = True
    except Exception as e:  # onverwachte fout: toon hem, zodat je hem kunt doorgeven
        baan["fout"] = f"Onverwachte fout: {e.__class__.__name__}: {e}"
        baan["klaar"] = True


# ---------------- wachtwoord voor de gedeelde link ----------------
# Alleen bezoekers die via de gedeelde link (Cloudflare) binnenkomen moeten een wachtwoord invullen.
# Op je eigen laptop (127.0.0.1) hoeft dat niet.

INLOG_HTML = """<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bronwaardig – inloggen</title><link rel="stylesheet" href="/static/style.css"></head>
<body><main><section class="intro" style="max-width:520px">
<h1 style="font-size:2.4rem">Bronwaardig</h1>
<p class="intro-tekst">Dit is een prototype van een SEO- en GEO-analysetool (studentenproject). Vul het wachtwoord in dat u heeft gekregen.</p>
<form class="zoek" method="post" action="/inloggen"><label class="vh" for="w">Wachtwoord</label>
<input id="w" name="wachtwoord" type="password" placeholder="Wachtwoord" required autofocus><button type="submit">Inloggen</button></form>
{fout}</section></main></body></html>"""


ONLINE = bool(os.environ.get("RENDER"))  # true als de tool op Render draait


def gedeeld_wachtwoord():
    if os.environ.get("WACHTWOORD", "").strip():
        return os.environ["WACHTWOORD"].strip()
    try:
        return WACHTWOORD.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


@app.before_request
def controleer_toegang():
    via_link = bool(request.headers.get("Cf-Connecting-Ip") or request.headers.get("X-Forwarded-For"))
    if not via_link or request.path in ("/inloggen",) or request.path.startswith("/static/"):
        return None
    w = gedeeld_wachtwoord()
    if not w and ONLINE:
        return None  # online zonder wachtwoord: open voor iedereen
    if not w:
        return Response("De gedeelde link is nog niet beveiligd met een wachtwoord. Start het delen opnieuw met deel.command.", 403)
    if session.get("ingelogd") == w:
        return None
    if request.path.startswith("/api/"):
        return jsonify({"fout": "Log eerst in."}), 401
    return Response(INLOG_HTML.replace("{fout}", ""), mimetype="text/html")


@app.post("/inloggen")
def inloggen():
    w = gedeeld_wachtwoord()
    if w and request.form.get("wachtwoord", "") == w:
        session["ingelogd"] = w
        return redirect("/")
    return Response(INLOG_HTML.replace("{fout}", '<p class="zoek-fout">Dat wachtwoord klopt niet.</p>'), mimetype="text/html", status=401)


# ---------------- routes ----------------

@app.get("/")
def index():
    return send_from_directory(MAP / "static", "index.html")


@app.get("/api/status")
def status():
    inst = lees_instellingen()
    return jsonify({
        "sleutel": bool(lees_sleutel()),
        "model": inst["model"], "rondes": int(inst["rondes"]),
        "modellen": [ai.STANDAARD_MODEL] + ai.RESERVE_MODELLEN,
        "toolversie": TOOLVERSIE,
        "aantal_analyses": len(opgeslagen()),
        "online": ONLINE,
    })


@app.post("/api/instellingen")
def instellingen():
    data = request.get_json(force=True) or {}
    inst = lees_instellingen()
    if data.get("model") in [ai.STANDAARD_MODEL] + ai.RESERVE_MODELLEN:
        inst["model"] = data["model"]
    if str(data.get("rondes")) in ("1", "3", "5"):
        inst["rondes"] = int(data["rondes"])
    INSTELLINGEN.write_text(json.dumps(inst, indent=2), encoding="utf-8")
    return jsonify(inst)


@app.post("/api/analyse")
def start_analyse():
    url = (request.get_json(force=True) or {}).get("url", "")
    baan_id = uuid.uuid4().hex[:10]
    banen[baan_id] = {"klaar": False, "fout": None, "resultaat": None,
                      "stappen": {k: {"id": k, "naam": n, "status": "wacht"} for k, n in STAPPEN}}
    threading.Thread(target=voer_uit, args=(baan_id, url), daemon=True).start()
    return jsonify({"id": baan_id})


@app.get("/api/analyse/<baan_id>")
def volg_analyse(baan_id):
    b = banen.get(baan_id)
    if not b:
        return jsonify({"fout": "Deze analyse bestaat niet (meer). Start een nieuwe.", "klaar": True}), 404
    return jsonify({"klaar": b["klaar"], "fout": b["fout"], "resultaat": b["resultaat"],
                    "stappen": [b["stappen"][k] for k, _ in STAPPEN]})


@app.get("/api/resultaat/<naam>")
def toon_resultaat(naam):
    f = RESULTATEN / Path(naam).name
    if not f.exists():
        return jsonify({"fout": "Niet gevonden"}), 404
    d = json.loads(f.read_text(encoding="utf-8"))
    d["bestand"] = f.name
    return jsonify(d)


@app.get("/api/resultaten")
def resultaten():
    """Overzicht van alle analyses (nieuwste per adres) + rangcorrelaties voor hoofdstuk 8."""
    alle = opgeslagen()
    laatste = {}
    for d in alle:  # bestanden zijn op datum gesorteerd, dus de laatste wint
        laatste[d["url"]] = d
    zicht = lees_zichtbaarheid()
    rijen = []
    for d in laatste.values():
        s, v = d["scores"], d["varianten"]
        rijen.append({
            "bestand": d["bestand"], "url": d["url"], "domein": d["domein"], "titel": d["titel"], "datum": d["datum"],
            "basis_ok": d["basis_ok"], "seo": s["seo"], "geo_techniek": s["geo_techniek"], "geo_inhoud": s["geo_inhoud"],
            "totaal": s["totaal"], **v, "zichtbaarheid": zicht.get(d["url"]),
            "model": (d.get("inhoud") or {}).get("modelversie", ""),
        })
    rijen.sort(key=lambda r: (r["totaal"] is None, -(r["totaal"] or 0)))
    tot = [r["totaal"] for r in rijen]
    correlaties = {
        "a_blokkerend_dubbel": scores.spearman(tot, [r["a_blokkerend_dubbel"] for r in rijen]),
        "b_oude_punten": scores.spearman(tot, [r["b_oude_punten"] for r in rijen]),
        "c_gelijk_verdeeld": scores.spearman(tot, [r["c_gelijk_verdeeld"] for r in rijen]),
        "zichtbaarheid": scores.spearman(tot, [r["zichtbaarheid"] for r in rijen]),
        "zichtbaarheid_n": sum(1 for r in rijen if r["zichtbaarheid"] is not None and r["totaal"] is not None),
    }
    return jsonify({"rijen": rijen, "correlaties": correlaties, "totaal_analyses": len(alle)})


@app.post("/api/zichtbaarheid")
def zet_zichtbaarheid():
    data = request.get_json(force=True) or {}
    zicht = lees_zichtbaarheid()
    url, waarde = data.get("url"), data.get("waarde")
    if waarde in ("", None):
        zicht.pop(url, None)
    else:
        try:
            zicht[url] = max(0.0, min(100.0, float(str(waarde).replace(",", "."))))
        except ValueError:
            return jsonify({"fout": "Vul een getal tussen 0 en 100 in."}), 400
    RESULTATEN.mkdir(exist_ok=True)
    (RESULTATEN / "zichtbaarheid.json").write_text(json.dumps(zicht, indent=2), encoding="utf-8")
    return jsonify({"ok": True})


@app.get("/api/export.csv")
def export():
    """Alle analyses als Excel-bestand (CSV met puntkomma)."""
    zicht = lees_zichtbaarheid()
    uit = io.StringIO()
    w = csv.writer(uit, delimiter=";")
    check_ids = list(methode.CHECKS)
    crit_ids = [c["id"] for c in methode.CRITERIA]
    w.writerow(["datum", "url", "basis_ok", "seo", "geo_techniek", "geo_inhoud", "totaal",
                "var_a_blokkerend_dubbel", "var_b_oude_punten", "var_c_gelijk_verdeeld", "ai_zichtbaarheid_procent",
                "model", "rondes_gelukt", "verzonnen_citaten", "citaten_totaal"]
               + [f"check_{c}" for c in check_ids] + [f"ai_{c}" for c in crit_ids])
    for d in opgeslagen():
        s, v, ih = d["scores"], d["varianten"], d.get("inhoud") or {}
        per_check = {c["id"]: c["waarde"] for c in d["checks"]}
        per_crit = {c["id"]: c["cijfer"] for c in ih.get("criteria", [])}
        getal = lambda x: "" if x is None else str(x).replace(".", ",")
        w.writerow([d["datum"], d["url"], "ja" if d["basis_ok"] else "nee", getal(s["seo"]), getal(s["geo_techniek"]),
                    getal(s["geo_inhoud"]), getal(s["totaal"]), getal(v["a_blokkerend_dubbel"]), getal(v["b_oude_punten"]),
                    getal(v["c_gelijk_verdeeld"]), getal(zicht.get(d["url"])), ih.get("modelversie", ""),
                    getal(ih.get("rondes_gelukt")), getal(ih.get("verzonnen_citaten")), getal(ih.get("citaten_totaal"))]
                   + [getal(per_check.get(c)) for c in check_ids] + [getal(per_crit.get(c)) for c in crit_ids])
    return Response("﻿" + uit.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=geo-analyses.csv"})


def _onderwerp(d, soort, sleutel_id):
    """Beschrijft het onderdeel waar de gebruiker uitleg over wil."""
    if soort == "advies":
        lijst = (d.get("ai_advies") or [])
        i = int(sleutel_id)
        a = lijst[i]
        return (f"AI-advies over de inhoud: \"{a['titel']}\". Nu: {a.get('nu', '')} Waarom: {a.get('waarom', '')} "
                f"Stappen: {'; '.join(a.get('stappen', []))}. Voorbeeld: {a.get('voorbeeld', '')}")
    if soort == "check":
        c = next(c for c in d["checks"] if c["id"] == sleutel_id)
        status = {"goed": "goed", "fout": "niet goed", "deels": "deels goed", "nvt": "niet gemeten"}[c["status"]]
        return (f"Technische check \"{c['naam']}\" ({'telt mee' if c['telt'] else 'tip'}, {c['bewijs']}). "
                f"Wat we meten: {c['wat']} Uitkomst: {status}. Gevonden: {c['gevonden']}. "
                f"Waarom deze check: {c['waarom']} (bron: {c['bron']}). Vast advies: {c['advies'] or 'geen, de check is goed'}")
    if soort == "basis":
        p = next(p for p in d["poorten"] if p["id"] == sleutel_id)
        return f"Basischeck \"{p['naam']}\": {p['wat']} Uitkomst: {'in orde' if p['ok'] else 'NIET in orde'} ({p['gevonden']}). {p['advies']}"
    if soort == "criterium":
        c = next(c for c in d["inhoud"]["criteria"] if c["id"] == sleutel_id)
        return (f"AI-beoordeling van de tekst op het punt \"{c['naam']}\": {c['vraag']} Cijfer: {c['cijfer']} van 5. "
                f"Uitleg van de beoordelaar: {c['uitleg']} Citaat: \"{c['citaat']}\"")
    raise ValueError("onbekend onderdeel")


@app.post("/api/uitleg")
def uitleg():
    data = request.get_json(force=True) or {}
    naam = Path(str(data.get("bestand", ""))).name
    soort, sid = data.get("soort"), str(data.get("id", ""))
    f = RESULTATEN / naam
    if not f.exists():
        return jsonify({"fout": "Deze analyse is niet gevonden."}), 404
    d = json.loads(f.read_text(encoding="utf-8"))
    sleutel_uitleg = f"{soort}:{sid}"
    if (d.get("uitleg") or {}).get(sleutel_uitleg):
        return jsonify({"onderdelen": d["uitleg"][sleutel_uitleg]})
    sleutel = lees_sleutel()
    if not sleutel:
        return jsonify({"fout": "Geen AI-sleutel gevonden. Zet je sleutel in sleutel.txt."}), 400
    try:
        onderwerp = _onderwerp(d, soort, sid)
    except (StopIteration, ValueError, IndexError, KeyError, TypeError):
        return jsonify({"fout": "Dit onderdeel is niet gevonden."}), 400
    tekst = teksten.get(naam)
    if not tekst:  # na een herstart: pagina opnieuw ophalen
        try:
            tekst = analyse.analyseer(d["url"])["_tekst_voor_ai"]
            teksten[naam] = tekst
        except (analyse.AnalyseFout, Exception):
            tekst = f"(De pagina kon niet opnieuw worden opgehaald.) Titel: {d.get('titel', '')}. Omschrijving: {d.get('omschrijving', '')}"
    try:
        onderdelen = ai.leg_uit(onderwerp, tekst, sleutel, lees_instellingen()["model"])
    except ai.AIFout as e:
        return jsonify({"fout": str(e)}), 502
    d.setdefault("uitleg", {})[sleutel_uitleg] = onderdelen  # bewaren, zodat je het later terugziet
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"onderdelen": onderdelen})


@app.get("/api/methode")
def methode_data():
    return jsonify({"checks": methode.CHECKS, "poorten": methode.POORTEN, "criteria": methode.CRITERIA,
                    "weging": methode.WEGING, "bronnen": methode.BRONNEN})


if __name__ == "__main__":
    print("\n  De tool draait op: http://127.0.0.1:8765\n  Stoppen: druk op Ctrl+C\n")
    app.run(host="127.0.0.1", port=int(os.environ.get("POORT", 8765)), debug=False, threaded=True)
