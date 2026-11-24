"""
LAAG 1 - DE TECHNISCHE CHECKS (zonder AI)
=========================================

Dit bestand haalt een webpagina op en voert de vaste checks uit:
  - stap 1: de basis (poorten)
  - de 15 checks die meetellen en de 6 tips (zie methode.py)
  - extra informatie die niet meetelt (geen bewijs)

Elke check geeft een vaste uitkomst volgens een vaste regel.
Daardoor geeft dezelfde pagina altijd dezelfde uitkomst (reproduceerbaar).
"""

import json
import re
import time
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from methode import CHECKS, POORTEN

# De tool stelt zich voor als gewone browser, met een herkenbare naam erbij.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 GEO-analysetool/2.0 (studentenproject)"
)
EIGEN_ROBOTNAAM = "GEO-analysetool"

# De user-agent van de zoekrobot van ChatGPT. Hiermee testen we met één verzoek
# of de website AI-robots echt doorlaat (check "Robots niet geblokkeerd").
AI_TEST_UA = (
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; OAI-SearchBot/1.3; "
    "+https://openai.com/searchbot)"
)

AI_ZOEKROBOTS = {
    "OAI-SearchBot": "ChatGPT",
    "Claude-SearchBot": "Claude",
    "PerplexityBot": "Perplexity",
}
AI_TRAININGSROBOTS = {
    "GPTBot": "ChatGPT (training)",
    "ClaudeBot": "Claude (training)",
    "Google-Extended": "Gemini (training en Gemini-app)",
    "CCBot": "Common Crawl (training)",
}

TIMEOUT = 20

BLOKKADE_TEKENS = (
    "just a moment", "attention required", "verifying you are human", "access denied",
    "een momentje", "even geduld", "checking your browser", "ddos protection",
    "please enable cookies", "captcha",
)

STOPWOORDEN = set("""
de het een en van voor met op in aan bij naar over uit door als ook maar dan dat die dit deze
zijn is wij we jij je uw onze ons the and for with your our you home welkom homepage official
officiele website site pagina www nl com
""".split())


class AnalyseFout(Exception):
    """Begrijpelijke foutmelding voor de gebruiker."""


def normaliseer_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise AnalyseFout("Vul een webadres in.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    if not p.netloc or "." not in p.netloc:
        raise AnalyseFout("Dit lijkt geen geldig webadres. Probeer bijvoorbeeld: www.voorbeeld.nl")
    return url


def normaliseer_tekst(t: str) -> str:
    """Voor het controleren van citaten: kleine letters, gewone aanhalingstekens, enkele spaties."""
    t = (t or "").lower()
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace(" ", " ").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", t).strip()


def _get(url, ua=BROWSER_UA, timeout=TIMEOUT):
    return requests.get(url, headers={"User-Agent": ua, "Accept-Language": "nl,en;q=0.8"},
                        timeout=timeout, allow_redirects=True)


def _tekstbestand(url):
    try:
        r = _get(url, timeout=10)
        begin = r.text[:400].lower()
        if r.status_code == 200 and "<html" not in begin and "<!doctype" not in begin:
            return r.text
    except requests.RequestException:
        pass
    return None


def _is_blokkadepagina(status, html):
    kop = (html or "")[:6000].lower()
    titel = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", kop, re.S)
    if m:
        titel = m.group(1)
    if status in (401, 403, 429, 503) and (any(t in kop for t in BLOKKADE_TEKENS) or "cf-chl" in kop):
        return True
    return any(t in titel for t in BLOKKADE_TEKENS) or "cf-chl-" in kop


def _schema_types(data, gevonden):
    if isinstance(data, dict):
        t = data.get("@type")
        if isinstance(t, str):
            gevonden.add(t)
        elif isinstance(t, list):
            gevonden.update(x for x in t if isinstance(x, str))
        for v in data.values():
            _schema_types(v, gevonden)
    elif isinstance(data, list):
        for v in data:
            _schema_types(v, gevonden)


def _woorden(t):
    return {w for w in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", (t or "").lower())
            if len(w) > 3 and w not in STOPWOORDEN}


def _check(cid, status, gevonden, waarde=None):
    """Maakt één check-uitkomst. status: goed / fout / deels / nvt."""
    if waarde is None:
        waarde = {"goed": 1.0, "fout": 0.0, "nvt": None}.get(status)
    info = CHECKS[cid]
    return {
        "id": cid, "naam": info["naam"], "groep": info["groep"], "telt": info["telt"],
        "bewijs": info["bewijs"], "status": status, "waarde": waarde, "gevonden": gevonden,
        "wat": info["wat"], "waarom": info["waarom"], "bron": info["bron"],
        "advies": info["advies"] if status in ("fout", "deels") else "",
    }


def _poort(pid, ok, gevonden):
    p = POORTEN[pid]
    return {"id": pid, "naam": p["naam"], "wat": p["wat"], "bron": p["bron"],
            "ok": ok, "gevonden": gevonden, "advies": "" if ok else p["advies"]}


# --------------------------------------------------------------------------
# Hoofdfunctie
# --------------------------------------------------------------------------

def analyseer(url: str) -> dict:
    url = normaliseer_url(url)
    p0 = urlparse(url)
    basis0 = f"{p0.scheme}://{p0.netloc}"

    # robots.txt eerst: de tool volgt zelf ook de regels (ethiek, hoofdstuk 9)
    robots_txt = _tekstbestand(basis0 + "/robots.txt")
    rp = robotparser.RobotFileParser()
    rp.parse((robots_txt or "").splitlines())
    if robots_txt and not rp.can_fetch(EIGEN_ROBOTNAAM, url):
        raise AnalyseFout("Deze website vraagt in robots.txt om deze pagina niet automatisch te bezoeken. "
                          "Onze tool houdt zich daaraan en analyseert de pagina daarom niet.")

    # Pagina ophalen
    try:
        start = time.time()
        r = _get(url)
        duur = time.time() - start
    except requests.exceptions.SSLError:
        raise AnalyseFout("De beveiligde verbinding (HTTPS) van deze website werkt niet goed. Probeer het adres met http://.")
    except requests.RequestException:
        raise AnalyseFout("De pagina kon niet worden geladen. Klopt het adres, en werkt de website in je browser?")

    # Juiste tekenset gebruiken (anders worden bijvoorbeeld streepjes en é verkeerd gelezen)
    if "charset" not in r.headers.get("Content-Type", "").lower():
        m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', r.content[:3000], re.I)
        r.encoding = m.group(1).decode() if m else (r.apparent_encoding or "utf-8")

    eind_url = r.url
    pe = urlparse(eind_url)
    basis = f"{pe.scheme}://{pe.netloc}"
    domein = pe.netloc.lower().removeprefix("www.")
    if basis != basis0:  # doorgestuurd naar ander domein: robots.txt opnieuw ophalen
        robots_txt = _tekstbestand(basis + "/robots.txt")
        rp = robotparser.RobotFileParser()
        rp.parse((robots_txt or "").splitlines())

    html = r.text
    geblokkeerd = _is_blokkadepagina(r.status_code, html)
    soup = BeautifulSoup(html, "html.parser")

    # ---------------- Gegevens uit de pagina ----------------
    titel = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta = (meta_tag.get("content") or "").strip() if meta_tag else ""
    robots_meta = " ".join((t.get("content") or "").lower() for t in soup.find_all(
        "meta", attrs={"name": re.compile(r"^(robots|googlebot)$", re.I)}))
    x_robots = r.headers.get("X-Robots-Tag", "").lower()
    viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    viewport_inhoud = (viewport.get("content") or "").lower() if viewport else ""
    canonical = soup.find("link", rel=lambda v: v and "canonical" in [x.lower() for x in (v if isinstance(v, list) else [v])])
    html_tag = soup.find("html")
    taal = (html_tag.get("lang") or "").strip() if html_tag else ""

    koppen = []
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        t = tag.get_text(" ", strip=True)
        if t:
            koppen.append((int(tag.name[1]), t))
    h1s = [t for n, t in koppen if n == 1]
    h2s = [t for n, t in koppen if n == 2]

    # Gestructureerde data
    schema_types, schema_fouten, schema_blokken = set(), 0, 0
    for s in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        schema_blokken += 1
        try:
            _schema_types(json.loads(s.string or s.get_text() or ""), schema_types)
        except (json.JSONDecodeError, TypeError):
            schema_fouten += 1
    for item in soup.find_all(attrs={"itemtype": True}):
        schema_types.add(str(item["itemtype"]).rstrip("/").split("/")[-1])

    # Afbeeldingen en links
    imgs = soup.find_all("img")
    imgs_met_alt = [i for i in imgs if i.has_attr("alt")]
    interne, externe = set(), set()
    contact_link = over_link = False
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        tekst = (a.get_text(" ", strip=True) + " " + href).lower()
        if re.search(r"contact", tekst):
            contact_link = True
        if re.search(r"over[- ]?ons|about|wie[- ]?zijn[- ]?wij|organisatie|over[- ]?mij", tekst):
            over_link = True
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        volledig = urljoin(eind_url, href).split("#")[0]
        host = urlparse(volledig).netloc.lower().removeprefix("www.")
        if host == domein and volledig.rstrip("/") != eind_url.rstrip("/"):
            interne.add(volledig)
        elif host and host != domein:
            externe.add(volledig)

    # Leesbare hoofdtekst (zonder scripts, menu en footer)
    tsoup = BeautifulSoup(html, "html.parser")
    for tag in tsoup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form", "iframe", "template"]):
        tag.decompose()
    body = tsoup.body or tsoup
    pagina_tekst = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
    # Menu, kop en voettekst apart bewaren: daar staan vaak adres, telefoon en openingstijden.
    # De AI krijgt deze tekst ook te zien, als apart stuk.
    rsoup = BeautifulSoup(html, "html.parser")
    for tag in rsoup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    rand_delen = []
    for tag in rsoup.find_all(["header", "nav", "footer"]):
        if tag.find_parent(["header", "nav", "footer"]):
            continue  # niet dubbel tellen
        t = re.sub(r"\s+", " ", tag.get_text(" ", strip=True))
        if t and t not in rand_delen:
            rand_delen.append(t)
    rand_tekst = " | ".join(rand_delen)
    woorden = len(pagina_tekst.split())
    volledige_tekst = re.sub(r"\s+", " ", (soup.body or soup).get_text(" ", strip=True))

    telefoon_of_mail = bool(soup.find("a", href=re.compile(r"^(tel:|mailto:)", re.I))
                            or re.search(r"\b\d{4}\s?[A-Z]{2}\b", volledige_tekst)
                            or re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", volledige_tekst))
    org_types = {"Organization", "LocalBusiness", "Corporation", "NGO", "GovernmentOrganization",
                 "EducationalOrganization", "SportsOrganization", "SportsClub", "Store", "MedicalOrganization",
                 "Restaurant", "ProfessionalService", "Person", "OnlineStore", "NewsMediaOrganization"}
    org_schema = bool(schema_types & org_types)

    datum = bool(soup.find("time") or soup.find("meta", property=re.compile(r"(modified|published)_time"))
                 or re.search(r'"date(Modified|Published)"', html)
                 or re.search(r"(bijgewerkt|gewijzigd|gepubliceerd|updated)\s*(op)?\s*:?\s*\d", volledige_tekst, re.I))
    lijsten = [l for l in soup.find_all(["ul", "ol"]) if len(l.find_all("li")) >= 3 and not l.find_parent("nav")]
    tabellen = soup.find_all("table")
    vraag_koppen = [t for _, t in koppen if t.strip().endswith("?")]

    # ---------------- Stap 1: de basis (poorten) ----------------
    noindex = "noindex" in robots_meta or "noindex" in x_robots
    googlebot_ok = rp.can_fetch("Googlebot", eind_url)
    bingbot_ok = rp.can_fetch("Bingbot", eind_url)
    poorten = [
        _poort("p_werkt", r.status_code == 200 and not geblokkeerd,
               f"Statuscode {r.status_code}" + (" (beveiligingspagina)" if geblokkeerd else "")),
        _poort("p_index", not noindex, "\"noindex\" gevonden" if noindex else "Geen noindex-code"),
        _poort("p_robots", googlebot_ok and bingbot_ok,
               "Beide toegestaan" if googlebot_ok and bingbot_ok else
               "Geblokkeerd voor " + " en ".join(n for n, ok in (("Googlebot", googlebot_ok), ("Bingbot", bingbot_ok)) if not ok)),
    ]

    # ---------------- Checks ----------------
    checks = []
    # SEO
    vp_ok = "width=device-width" in viewport_inhoud
    checks.append(_check("mobiel", "goed" if vp_ok else "fout",
                         "Viewport-code aanwezig" if vp_ok else ("Viewport-code zonder width=device-width" if viewport else "Geen viewport-code")))
    checks.append(_check("titel", "goed" if titel else "fout",
                         f"“{titel[:90]}” ({len(titel)} tekens)" if titel else "Geen titel gevonden"))
    if imgs:
        ratio = len(imgs_met_alt) / len(imgs)
        checks.append(_check("alt", "goed" if ratio >= 0.9 else "fout",
                             f"{len(imgs_met_alt)} van {len(imgs)} afbeeldingen ({ratio:.0%})"))
    else:
        checks.append(_check("alt", "goed", "Geen afbeeldingen op de pagina"))
    checks.append(_check("links", "goed" if interne else "fout",
                         f"{len(interne)} interne links" if interne else "Geen gewone links naar andere eigen pagina's"))
    checks.append(_check("https", "goed" if eind_url.startswith("https://") else "fout",
                         "Beveiligde verbinding" if eind_url.startswith("https://") else "Geen HTTPS"))
    checks.append(_check("meta", "goed" if meta else "fout",
                         f"{len(meta)} tekens" if meta else "Geen omschrijving gevonden"))
    if canonical and canonical.get("href"):
        c_url = urljoin(eind_url, canonical["href"].strip())
        c_host = urlparse(c_url).netloc.lower().removeprefix("www.")
        ok = c_host == domein
        checks.append(_check("canonical", "goed" if ok else "fout",
                             ("Wijst naar " + c_url[:90]) if ok else f"Wijst naar ander domein ({c_host})"))
    else:
        checks.append(_check("canonical", "fout", "Geen canonical-code"))
    sitemap_bron = ""
    if robots_txt and re.search(r"(?im)^\s*sitemap\s*:", robots_txt):
        sitemap_bron = "Genoemd in robots.txt"
    else:
        for pad in ("/sitemap.xml", "/sitemap_index.xml"):
            inhoud = _tekstbestand(basis + pad)
            if inhoud and ("<urlset" in inhoud or "<sitemapindex" in inhoud):
                sitemap_bron = f"Gevonden op {pad}"
                break
    checks.append(_check("sitemap", "goed" if sitemap_bron else "fout", sitemap_bron or "Geen sitemap gevonden"))
    # Snelheid wordt apart gemeten (PageSpeed) en later ingevuld
    checks.append(_check("snelheid", "nvt", "Wordt gemeten..."))
    checks.append(_check("h1", "goed" if h1s else "fout",
                         f"“{h1s[0][:80]}”" + (f" (+{len(h1s)-1} meer)" if len(h1s) > 1 else "") if h1s else "Geen hoofdkop (H1)"))
    if schema_blokken or schema_types:
        ok = bool(schema_types) and schema_fouten == 0
        tekst = ", ".join(sorted(schema_types)[:6]) or "geen types"
        if schema_fouten:
            tekst += f" – {schema_fouten} blok(ken) met fouten"
        checks.append(_check("schema", "goed" if ok else "fout", tekst))
    else:
        checks.append(_check("schema", "fout", "Geen gestructureerde data"))
    # SEO-tips
    if woorden > 300:
        checks.append(_check("h2", "goed" if h2s else "fout", f"{len(h2s)} tussenkoppen bij {woorden} woorden"))
    else:
        checks.append(_check("h2", "goed", f"Korte tekst ({woorden} woorden), tussenkop niet nodig"))
    gedeeld = _woorden(titel) & _woorden(" ".join(h1s))
    checks.append(_check("titel_h1", "goed" if gedeeld else "fout",
                         "Gedeeld woord: " + ", ".join(sorted(gedeeld)[:3]) if gedeeld else "Geen gedeeld belangrijk woord"))
    checks.append(_check("taal", "goed" if taal else "fout", f"lang=\"{taal}\"" if taal else "Taal niet ingesteld"))

    # GEO
    toegestaan = {bot: rp.can_fetch(bot, eind_url) for bot in AI_ZOEKROBOTS}
    n_ok = sum(toegestaan.values())
    geblokkeerde = [f"{AI_ZOEKROBOTS[b]}" for b, ok in toegestaan.items() if not ok]
    checks.append(_check("ai_robots", "goed" if n_ok == 3 else ("deels" if n_ok else "fout"),
                         f"{n_ok} van 3 toegestaan" + (f" (geblokkeerd: {', '.join(geblokkeerde)})" if geblokkeerde else ""),
                         waarde=n_ok / 3))
    # Een "lege schil": de pagina bestaat vooral uit een leeg vak dat JavaScript later vult
    schil = soup.find(id=re.compile(r"^(root|app|__next|__nuxt|svelte)$"))
    lege_schil = bool(schil) and len(schil.get_text(" ", strip=True).split()) < 20 and woorden < 150
    js_ok = woorden >= 50 and not lege_schil
    checks.append(_check("js", "goed" if js_ok else "fout",
                         f"{woorden} woorden direct leesbaar zonder JavaScript"
                         + (" (de pagina lijkt pas via JavaScript gevuld te worden)" if lege_schil else "")))
    try:
        rb = _get(eind_url, ua=AI_TEST_UA, timeout=15)
        bot_blok = rb.status_code != 200 or _is_blokkadepagina(rb.status_code, rb.text)
        checks.append(_check("bot_toegang", "fout" if bot_blok else "goed",
                             f"AI-robot kreeg statuscode {rb.status_code}" + (" (beveiligingspagina)" if _is_blokkadepagina(rb.status_code, rb.text) else "")
                             if bot_blok else "AI-robot kon de pagina lezen"))
    except requests.RequestException:
        checks.append(_check("bot_toegang", "fout", "AI-robot kreeg geen antwoord van de website"))
    signalen = []
    if org_schema:
        signalen.append("organisatie in gestructureerde data")
    if over_link:
        signalen.append("link naar over ons")
    if contact_link:
        signalen.append("link naar contact")
    if telefoon_of_mail:
        signalen.append("adres, telefoon of e-mail")
    afzender_ok = org_schema or (contact_link and (over_link or telefoon_of_mail))
    checks.append(_check("afzender", "goed" if afzender_ok else "fout",
                         ("Gevonden: " + ", ".join(signalen)) if signalen else "Geen afzender- of contactgegevens gevonden"))
    # GEO-tips
    checks.append(_check("datum", "goed" if datum else "fout", "Datum gevonden" if datum else "Geen datum gevonden"))
    checks.append(_check("lijsten", "goed" if (lijsten or tabellen) else "fout",
                         f"{len(lijsten)} lijsten, {len(tabellen)} tabellen"))
    checks.append(_check("vraagkoppen", "goed" if vraag_koppen else "fout",
                         f"“{vraag_koppen[0][:70]}”" if vraag_koppen else "Geen kop als vraag"))

    # ---------------- Extra informatie (geen bewijs, telt niet mee) ----------------
    og = bool(soup.find("meta", property="og:title"))
    llms = _tekstbestand(basis + "/llms.txt") is not None
    training = {naam: rp.can_fetch(bot, eind_url) for bot, naam in AI_TRAININGSROBOTS.items()}
    info = [
        {"naam": "Aantal woorden", "waarde": f"{woorden}",
         "uitleg": "Google zegt dat er geen ideale lengte is (Google Search Central, z.d.-i)."},
        {"naam": "FAQ-code (FAQPage)", "waarde": "Ja" if "FAQPage" in schema_types else "Nee",
         "uitleg": "Google toont FAQ's bijna nergens meer (Google Search Central, 2023a)."},
        {"naam": "llms.txt", "waarde": "Gevonden" if llms else "Niet gevonden",
         "uitleg": "Google gebruikt zulke bestanden niet (Google Search Central, 2026b)."},
        {"naam": "Social-mediacode (Open Graph)", "waarde": "Ja" if og else "Nee",
         "uitleg": "Bedoeld voor social media, niet voor zoekmachines."},
        {"naam": "Trainingsrobots", "waarde": "\n".join(f"{n}: {'toegestaan' if ok else 'geblokkeerd'}" for n, ok in training.items()),
         "uitleg": "Blokkeren is een eigen keuze en kost geen punten (OpenAI, 2026; Anthropic, z.d.). Let op: Google-Extended regelt ook de Gemini-app."},
        {"naam": "Laadtijd van de HTML", "waarde": f"{duur:.1f} seconden".replace(".", ","), "uitleg": "Alleen ter informatie; de snelheidscheck gebruikt de normen van Google."},
    ]

    waarschuwingen = []
    if titel and not 30 <= len(titel) <= 65:
        waarschuwingen.append(f"De titel is {len(titel)} tekens. Google kort lange titels in; erg korte titels zeggen weinig. Dit kost geen punten.")
    if meta and not 70 <= len(meta) <= 160:
        waarschuwingen.append(f"De omschrijving is {len(meta)} tekens. Google kort lange omschrijvingen in. Dit kost geen punten.")

    koppen_tekst = "\n".join(f"{'  ' * (n - 1)}H{n}: {t}" for n, t in koppen[:60])
    tekst_voor_ai = (f"URL: {eind_url}\nTitel: {titel}\nOmschrijving: {meta}\n\nKOPPEN:\n{koppen_tekst}\n\n"
                     f"TEKST VAN DE PAGINA:\n{pagina_tekst[:24000]}\n\n"
                     f"MENU, KOPTEKST EN VOETTEKST (staan meestal op elke pagina van de website):\n{rand_tekst[:6000]}")

    return {
        "url": eind_url,
        "gevraagde_url": url,
        "domein": domein,
        "statuscode": r.status_code,
        "titel": titel,
        "omschrijving": meta,
        "woorden": woorden,
        "geblokkeerd": geblokkeerd,
        "poorten": poorten,
        "checks": checks,
        "info": info,
        "waarschuwingen": waarschuwingen,
        # Niet opslaan (privacy): alleen nodig tijdens de analyse
        "_tekst_voor_ai": tekst_voor_ai,
        "_tekst_genormaliseerd": normaliseer_tekst(titel + " " + meta + " " + " ".join(t for _, t in koppen) + " " + volledige_tekst),
    }


# --------------------------------------------------------------------------
# Snelheid: Core Web Vitals via de PageSpeed Insights API van Google
# --------------------------------------------------------------------------

PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
VELD = {
    "LARGEST_CONTENTFUL_PAINT_MS": ("Laden (LCP)", 2500, "ms"),
    "INTERACTION_TO_NEXT_PAINT": ("Reageren (INP)", 200, "ms"),
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": ("Stabiliteit (CLS)", 10, "cls"),  # percentiel x100
}


def _komma(t):
    """Nederlandse notatie: 2.1 s wordt 2,1 s."""
    return re.sub(r"(\d)\.(\d)", r"\1,\2", t)


def meet_snelheid(url: str, sleutel: str = "") -> dict:
    """Geeft de check 'snelheid' terug. Gebruikt echte gebruikersdata van Google als die er is,
    anders een labmeting. Lukt meten niet, dan telt de check niet mee (nvt)."""
    data, reden = None, "geen antwoord"
    for poging in range(3):
        params = {"url": url, "strategy": "mobile", "category": "performance"}
        if poging == 2 and sleutel:
            params["key"] = sleutel
        try:
            r = requests.get(PSI_URL, params=params, timeout=120)
            if r.status_code == 200:
                data = r.json()
                break
            try:
                melding = r.json().get("error", {}).get("message", "")
            except ValueError:
                melding = ""
            reden = ("dagelijkse limiet van Google bereikt" if r.status_code == 429 else
                     f"foutcode {r.status_code}" + (f": {melding[:120]}" if melding else ""))
            if r.status_code == 429:
                time.sleep(5)
        except requests.Timeout:
            reden = "Google deed er te lang over"
        except requests.RequestException:
            reden = "geen verbinding met Google PageSpeed"
    if not data:
        return _check("snelheid", "nvt", f"Kon niet gemeten worden ({reden}). Telt nu niet mee.")

    for sleutelnaam, bron_tekst in (("loadingExperience", "gegevens van echte bezoekers"),
                                    ("originLoadingExperience", "gegevens van de hele website")):
        metrics = (data.get(sleutelnaam) or {}).get("metrics") or {}
        if all(k in metrics for k in VELD):
            delen, alles_ok = [], True
            for k, (naam, grens, soort) in VELD.items():
                m = metrics[k]
                ok = m.get("category") == "FAST"
                alles_ok &= ok
                p = m.get("percentile", 0)
                waarde = f"{p/100:.2f}" if soort == "cls" else f"{p/1000:.1f} s" if p >= 1000 else f"{p} ms"
                delen.append(f"{naam} {waarde} {'✓' if ok else '✗'}")
            return _check("snelheid", "goed" if alles_ok else "fout", _komma("; ".join(delen) + f" ({bron_tekst})"))

    audits = (data.get("lighthouseResult") or {}).get("audits") or {}
    try:
        lcp = audits["largest-contentful-paint"]["numericValue"]
        cls = audits["cumulative-layout-shift"]["numericValue"]
        tbt = audits["total-blocking-time"]["numericValue"]
    except (KeyError, TypeError):
        return _check("snelheid", "nvt", "Kon niet gemeten worden. Telt nu niet mee.")
    ok = lcp <= 2500 and cls <= 0.1 and tbt <= 200
    return _check("snelheid", "goed" if ok else "fout", _komma(
                  f"Laden {lcp/1000:.1f} s {'✓' if lcp <= 2500 else '✗'}; Stabiliteit {cls:.2f} {'✓' if cls <= 0.1 else '✗'}; "
                  f"Blokkeertijd {tbt:.0f} ms {'✓' if tbt <= 200 else '✗'} (labmeting, geen bezoekersdata beschikbaar)"))
