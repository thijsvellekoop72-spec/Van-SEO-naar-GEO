"""
DE METHODE IN CODE
==================

Dit bestand is de "vertaling" van ons methode-document naar code.
Per check staat hier:
  - naam, groep (SEO of GEO) en of hij meetelt of een tip is
  - bewijsniveau (sterk / vuistregel / zwak), bepaald met de vier vragen uit hoofdstuk 4
  - wat we meten en waarom (met bron), zoals in hoofdstuk 5
  - het vaste advies als de check niet goed is

Wil je iets aanpassen aan de methode? Dan hoef je alleen dit bestand te veranderen.
"""

# Verdeling van de totaalscore (hoofdstuk 7)
WEGING = {"seo": 0.4, "geo_techniek": 0.2, "geo_inhoud": 0.4}

# --------------------------------------------------------------------------
# Stap 1: de basis (poorten)
# --------------------------------------------------------------------------
POORTEN = {
    "p_werkt": {
        "naam": "De pagina werkt",
        "wat": "Laadt de pagina zonder foutmelding?",
        "bron": "Google Search Central, z.d.-b",
        "advies": "Zorg dat de pagina laadt zonder foutmelding (statuscode 200). Vraag dit na bij de beheerder van de website.",
    },
    "p_index": {
        "naam": "De pagina mag in Google komen",
        "wat": "Staat er geen \"noindex\"-code op de pagina?",
        "bron": "Google Search Central, 2026a",
        "advies": "Haal de \"noindex\"-code van de pagina. Zolang die erop staat, laat Google de pagina nergens zien, ook niet in AI-antwoorden.",
    },
    "p_robots": {
        "naam": "Zoekmachines mogen de pagina lezen",
        "wat": "Mogen Googlebot en Bingbot de pagina lezen volgens robots.txt?",
        "bron": "Google Search Central, z.d.-b; Koster et al., 2022",
        "advies": "Pas robots.txt aan zodat Googlebot en Bingbot deze pagina mogen lezen.",
    },
}

# --------------------------------------------------------------------------
# Stap 2 en hoofdstuk 5: alle checks
# telt=True  -> telt mee voor de score (sterk of vuistregel)
# telt=False -> tip (zwak bewijs), kost geen punten
# --------------------------------------------------------------------------
CHECKS = {
    # ---------------- SEO, telt mee ----------------
    "mobiel": {
        "groep": "seo", "telt": True, "bewijs": "sterk", "naam": "Mobiel",
        "wat": "Is de pagina goed te lezen op een telefoon? (viewport-code)",
        "waarom": "Google gebruikt de mobiele versie van een website om pagina's op te nemen en te rangschikken.",
        "bron": "Google Search Central, z.d.-g",
        "advies": "Zet de viewport-code in de pagina: <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">. Dan past de pagina zich aan op een telefoon.",
    },
    "titel": {
        "groep": "seo", "telt": True, "bewijs": "sterk", "naam": "Titel",
        "wat": "Heeft de pagina een titel? (de tekst in het tabblad en de blauwe tekst in Google)",
        "waarom": "Google maakt de titel in de zoekresultaten vooral van deze titel. Elke pagina hoort een eigen titel te hebben.",
        "bron": "Google Search Central, z.d.-f",
        "advies": "Geef de pagina een eigen titel die zegt waar de pagina over gaat, bijvoorbeeld \"[Dienst] in [plaats] | [Naam organisatie]\".",
    },
    "alt": {
        "groep": "seo", "telt": True, "bewijs": "sterk", "naam": "Alt-tekst",
        "wat": "Heeft minstens 90% van de afbeeldingen een beschrijving (alt-tekst)?",
        "waarom": "Google noemt de alt-tekst het belangrijkste kenmerk om te begrijpen wat er op een afbeelding staat. Ook nodig voor blinde en slechtziende bezoekers.",
        "bron": "Google Search Central, z.d.-e; W3C, 2023",
        "advies": "Geef elke inhoudelijke afbeelding een korte beschrijving in de alt-tekst, bijvoorbeeld \"Medewerker helpt klant aan de balie\". Versiering mag een lege alt-tekst (alt=\"\") hebben.",
    },
    "links": {
        "groep": "seo", "telt": True, "bewijs": "sterk", "naam": "Interne links",
        "wat": "Is er minstens één gewone link naar een andere pagina van dezelfde website?",
        "waarom": "Google vindt pagina's via links. Elke belangrijke pagina moet vanaf minstens één andere pagina gelinkt zijn, met gewone link-code.",
        "bron": "Google Search Central, z.d.-h",
        "advies": "Zet gewone links (<a href=\"...\">) naar andere pagina's van de website, bijvoorbeeld in het menu of in de tekst.",
    },
    "https": {
        "groep": "seo", "telt": True, "bewijs": "vuistregel", "naam": "HTTPS",
        "wat": "Heeft de website een veilige verbinding? (het slotje in de adresbalk)",
        "waarom": "HTTPS hoort bij een goede ervaring voor bezoekers (page experience). Google raadt het aan, maar het is geen voorwaarde.",
        "bron": "Google Search Central, 2023b",
        "advies": "Zet een SSL-certificaat op de website en stuur http:// automatisch door naar https://. De hostingpartij kan dit meestal gratis regelen.",
    },
    "meta": {
        "groep": "seo", "telt": True, "bewijs": "vuistregel", "naam": "Meta-description",
        "wat": "Is er een korte omschrijving die Google onder de titel kan laten zien?",
        "waarom": "Google gebruikt deze omschrijving soms in de zoekresultaten, maar maakt ook vaak zelf een omschrijving.",
        "bron": "Google Search Central, z.d.-d",
        "advies": "Schrijf een korte omschrijving van 1 à 2 zinnen die zegt wat de bezoeker op deze pagina vindt.",
    },
    "canonical": {
        "groep": "seo", "telt": True, "bewijs": "vuistregel", "naam": "Canonical",
        "wat": "Staat er een code die zegt welke versie van de pagina de \"echte\" is?",
        "waarom": "Google noemt dit een sterk signaal, maar het is niet verplicht. Zonder deze code kiest Google zelf.",
        "bron": "Google Search Central, z.d.-c",
        "advies": "Zet een canonical-code in de pagina die naar het eigen adres van de pagina wijst: <link rel=\"canonical\" href=\"[adres van deze pagina]\">.",
    },
    "sitemap": {
        "groep": "seo", "telt": True, "bewijs": "vuistregel", "naam": "Sitemap",
        "wat": "Heeft de website een lijst met alle pagina's voor zoekmachines?",
        "waarom": "Een sitemap helpt Google om pagina's te vinden. Google kan pagina's ook via links vinden, dus het is een hulpmiddel.",
        "bron": "Google Search Central, z.d.-j",
        "advies": "Maak een sitemap (sitemap.xml) en zet de regel \"Sitemap: [adres]/sitemap.xml\" in robots.txt. De meeste websitebouwers kunnen dit automatisch.",
    },
    "snelheid": {
        "groep": "seo", "telt": True, "bewijs": "vuistregel", "naam": "Snelheid",
        "wat": "Haalt de pagina de drie snelheidsnormen van Google (Core Web Vitals)?",
        "waarom": "De Core Web Vitals horen bij page experience. Google raadt ze aan, maar ze zijn geen voorwaarde.",
        "bron": "web.dev, z.d.; Google Search Central, 2023b",
        "advies": "Maak de pagina sneller: verklein grote afbeeldingen, laad minder scripts en zorg dat de opmaak niet verspringt tijdens het laden. Bekijk details op pagespeed.web.dev.",
    },
    "h1": {
        "groep": "seo", "telt": True, "bewijs": "vuistregel", "naam": "Hoofdkop",
        "wat": "Heeft de pagina minstens één hoofdkop (H1)?",
        "waarom": "Google raadt aan om het onderwerp van de pagina in de eerste zichtbare hoofdkop te zetten. Er is geen ideaal aantal koppen.",
        "bron": "Google Search Central, z.d.-f; z.d.-i",
        "advies": "Zet bovenaan de pagina één duidelijke hoofdkop (H1) die zegt waar de pagina over gaat.",
    },
    "schema": {
        "groep": "seo", "telt": True, "bewijs": "vuistregel", "naam": "Gestructureerde data",
        "wat": "Staat er foutloze code die vertelt wat iets is, zoals een organisatie of evenement?",
        "waarom": "Google raadt het aan voor extra functies in de zoekresultaten. Het is niet nodig voor AI-antwoorden.",
        "bron": "Google Search Central, z.d.-i; 2026b",
        "advies": "Voeg gestructureerde data (JSON-LD) toe, bijvoorbeeld van het type Organization met naam, logo en contactgegevens. Controleer het met de Rich Results Test van Google.",
    },
    # ---------------- SEO, tips ----------------
    "h2": {
        "groep": "seo", "telt": False, "bewijs": "zwak", "naam": "Tussenkoppen",
        "wat": "Heeft een tekst van meer dan 300 woorden minstens één tussenkop (H2)?",
        "waarom": "Koppen maken een tekst leesbaarder, maar volgens Google maakt het aantal koppen voor Google zelf niet uit.",
        "bron": "Google Search Central, z.d.-i",
        "advies": "Deel lange tekst op in stukken met tussenkoppen (H2).",
    },
    "titel_h1": {
        "groep": "seo", "telt": False, "bewijs": "zwak", "naam": "Titel en hoofdkop",
        "wat": "Gaan de titel en de hoofdkop over hetzelfde onderwerp?",
        "waarom": "Google gebruikt de hoofdkop soms als titel. Dat ze hetzelfde onderwerp moeten hebben, is een logisch vermoeden.",
        "bron": "Google Search Central, z.d.-f",
        "advies": "Laat de titel en de hoofdkop hetzelfde belangrijkste woord bevatten.",
    },
    "taal": {
        "groep": "seo", "telt": False, "bewijs": "zwak", "naam": "Taal",
        "wat": "Is de taal van de pagina ingesteld (bijvoorbeeld lang=\"nl\")?",
        "waarom": "Richtlijn voor toegankelijke websites. Google noemt het niet als regel voor de zoekresultaten.",
        "bron": "W3C, 2023",
        "advies": "Zet de taal in de code: <html lang=\"nl\">.",
    },
    # ---------------- GEO, telt mee ----------------
    "ai_robots": {
        "groep": "geo", "telt": True, "bewijs": "sterk", "naam": "AI-zoekrobots",
        "wat": "Mogen de zoekrobots van ChatGPT, Claude en Perplexity de website lezen volgens robots.txt?",
        "waarom": "De AI-bedrijven zeggen zelf dat een website die hun zoekrobot blokkeert, niet of minder in hun antwoorden komt.",
        "bron": "Anthropic, z.d.; OpenAI, 2026; Perplexity, 2026",
        "advies": "Sta de zoekrobots OAI-SearchBot, Claude-SearchBot en PerplexityBot toe in robots.txt. De trainingsrobots (zoals GPTBot) mag u blokkeren als u dat wilt.",
    },
    "js": {
        "groep": "geo", "telt": True, "bewijs": "sterk", "naam": "Tekst direct leesbaar",
        "wat": "Staat de tekst direct in de pagina, zonder dat JavaScript nodig is?",
        "waarom": "Uit een meting van ruim 900 miljoen bezoeken bleek dat de grote AI-robots geen JavaScript uitvoeren.",
        "bron": "Vercel, 2024",
        "advies": "Zorg dat de belangrijkste tekst direct in de HTML staat (server-side rendering of statische pagina's), en niet pas via JavaScript verschijnt.",
    },
    "bot_toegang": {
        "groep": "geo", "telt": True, "bewijs": "sterk", "naam": "Robots niet geblokkeerd",
        "wat": "Laat de website AI-robots echt door, zonder beveiligingspagina?",
        "waarom": "Een AI-zoekrobot moet de pagina kunnen lezen om hem te tonen. Een beveiligingspagina houdt de robot net zo goed tegen als robots.txt.",
        "bron": "Anthropic, z.d.; OpenAI, 2026; Koster et al., 2022",
        "advies": "Stel de beveiliging (bijvoorbeeld de firewall of CDN) zo in dat bekende AI-zoekrobots worden doorgelaten.",
    },
    "afzender": {
        "groep": "geo", "telt": True, "bewijs": "vuistregel", "naam": "Afzender duidelijk",
        "wat": "Zie je wie de organisatie is en hoe je contact opneemt?",
        "waarom": "Google raadt sterk aan om te laten zien wie een tekst maakt: wie, hoe en waarom.",
        "bron": "Google Search Central, z.d.-a",
        "advies": "Zet op de pagina duidelijk wie u bent en hoe men contact opneemt: een link naar \"Over ons\" en \"Contact\", met adres, telefoon of e-mail.",
    },
    # ---------------- GEO, tips ----------------
    "datum": {
        "groep": "geo", "telt": False, "bewijs": "zwak", "naam": "Actueel",
        "wat": "Staat er een datum op de pagina?",
        "waarom": "Enkele kleine of voorlopige onderzoeken vinden dat AI let op hoe nieuw informatie is.",
        "bron": "Chen et al., 2025; Kumar & Palkhouski, 2025",
        "advies": "Zet op de pagina wanneer de informatie voor het laatst is bijgewerkt, bijvoorbeeld \"Bijgewerkt op [datum]\".",
    },
    "lijsten": {
        "groep": "geo", "telt": False, "bewijs": "zwak", "naam": "Lijsten of tabellen",
        "wat": "Staat informatie in een lijst of tabel?",
        "waarom": "Logisch vermoeden uit de praktijk. Geen officiële bron of goed onderzoek gevonden.",
        "bron": "geen bron (vermoeden)",
        "advies": "Zet opsommingen, zoals prijzen of openingstijden, in een lijst of tabel.",
    },
    "vraagkoppen": {
        "groep": "geo", "telt": False, "bewijs": "zwak", "naam": "Koppen als vraag",
        "wat": "Is minstens één kop geschreven als vraag?",
        "waarom": "Mensen stellen AI vaak een vraag. Logisch vermoeden, nog geen bewijs.",
        "bron": "geen bron (vermoeden)",
        "advies": "Schrijf een paar koppen als vraag die bezoekers stellen, bijvoorbeeld \"Wat kost een abonnement?\", met het antwoord er direct onder.",
    },
}

# Checks die een pagina onvindbaar of onleesbaar maken als ze misgaan.
# Alleen gebruikt voor variant A in hoofdstuk 8 ("blokkerend telt dubbel").
BLOKKEREND = {"links", "ai_robots", "js", "bot_toegang"}

# --------------------------------------------------------------------------
# Hoofdstuk 6: de AI-beoordeling (6 punten, cijfer 1-5, met ankers)
# --------------------------------------------------------------------------
CRITERIA = [
    {
        "id": "antwoorden", "naam": "Directe antwoorden",
        "vraag": "Sluiten de titel en de tekst aan bij de vragen die bezoekers stellen, en staan de antwoorden bovenaan?",
        "bron": "Chen & Koudas, 2026; Martinez, 2026",
        "ankers": {
            1: "De pagina beantwoordt geen duidelijke vraag; de belangrijkste informatie is niet te vinden.",
            3: "De pagina beantwoordt een paar vragen, maar de antwoorden staan verstopt of pas laat in de tekst.",
            5: "De titel en koppen sluiten aan bij echte vragen, en de antwoorden staan direct en vooraan.",
        },
    },
    {
        "id": "feiten", "naam": "Feiten en cijfers",
        "vraag": "Staan er concrete gegevens in, zoals prijzen, tijden, adressen en aantallen?",
        "bron": "Aggarwal et al., 2024",
        "ankers": {
            1: "Geen concrete gegevens, alleen algemene zinnen (\"wij bieden goede service\").",
            3: "Enkele concrete gegevens, maar belangrijke ontbreken (wel een dag, geen tijd of prijs).",
            5: "De gegevens die de bezoeker zoekt staan er compleet en precies (\"ma-vr 8:00-17:00, consult €45, Coolsingel 10\").",
        },
    },
    {
        "id": "bronnen", "naam": "Bronnen",
        "vraag": "Verwijst de tekst naar bronnen, experts of citaten die de beweringen ondersteunen?",
        "bron": "Aggarwal et al., 2024",
        "ankers": {
            1: "Geen enkele bron, verwijzing of citaat.",
            3: "Een paar verwijzingen of een citaat, maar de meeste beweringen zijn niet onderbouwd.",
            5: "Belangrijke beweringen worden onderbouwd met bronnen, cijfers van anderen of citaten van experts.",
        },
    },
    {
        "id": "duidelijkheid", "naam": "Duidelijkheid",
        "vraag": "Is de tekst makkelijk te lezen en logisch opgebouwd?",
        "bron": "Aggarwal et al., 2024",
        "ankers": {
            1: "Moeilijk te volgen: lange zinnen, vaktaal, geen opbouw.",
            3: "Redelijk leesbaar, maar soms rommelig of met onnodig moeilijke woorden.",
            5: "Korte, heldere zinnen, logische volgorde en duidelijke stukken met koppen.",
        },
    },
    {
        "id": "betrouwbaarheid", "naam": "Betrouwbaarheid",
        "vraag": "Is duidelijk wie de afzender is en waarom je die kunt vertrouwen?",
        "bron": "Google Search Central, z.d.-a",
        "ankers": {
            1: "Onduidelijk wie de tekst schrijft of wie erachter zit.",
            3: "De organisatie wordt genoemd, maar er staat weinig over ervaring, deskundigheid of contact.",
            5: "Duidelijk wie de afzender is, met ervaring of deskundigheid en contactgegevens.",
        },
    },
    {
        "id": "eigen_info", "naam": "Eigen informatie",
        "vraag": "Staat er informatie in die je nergens anders vindt, zoals eigen ervaring, eigen cijfers of unieke details?",
        "bron": "Google Search Central, 2026b",
        "ankers": {
            1: "Alleen algemene informatie die op elke andere website ook staat.",
            3: "Een beetje eigen informatie, maar vooral algemene tekst.",
            5: "Veel unieke informatie: eigen gegevens, ervaringen, voorbeelden of details over deze organisatie.",
        },
    },
]

# Hoeveel cijfers mogen maximaal uit elkaar liggen voordat we "onzeker" zeggen
ONZEKER_VANAF = 2

# Bronnenlijst (kort), voor de methodepagina in de tool
BRONNEN = {
    "Aggarwal et al., 2024": "https://doi.org/10.1145/3637528.3671900",
    "Anthropic, z.d.": "https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler",
    "Chen & Koudas, 2026": "https://arxiv.org/abs/2610.15033",
    "Chen et al., 2025": "https://arxiv.org/abs/2509.08919",
    "Dawes, 1979": "https://doi.org/10.1037/0003-066X.34.7.571",
    "Google Search Central, z.d.-a": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    "Google Search Central, z.d.-b": "https://developers.google.com/search/docs/essentials",
    "Google Search Central, z.d.-c": "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls",
    "Google Search Central, z.d.-d": "https://developers.google.com/search/docs/appearance/snippet",
    "Google Search Central, z.d.-e": "https://developers.google.com/search/docs/appearance/google-images",
    "Google Search Central, z.d.-f": "https://developers.google.com/search/docs/appearance/title-link",
    "Google Search Central, z.d.-g": "https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing",
    "Google Search Central, z.d.-h": "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    "Google Search Central, z.d.-i": "https://developers.google.com/search/docs/fundamentals/seo-starter-guide",
    "Google Search Central, z.d.-j": "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
    "Google Search Central, 2023b": "https://developers.google.com/search/blog/2023/04/page-experience-in-search",
    "Google Search Central, 2026a": "https://developers.google.com/search/docs/appearance/ai-features",
    "Google Search Central, 2026b": "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide",
    "Koster et al., 2022": "https://www.rfc-editor.org/rfc/rfc9309",
    "Kumar & Palkhouski, 2025": "https://arxiv.org/abs/2509.10762",
    "Martinez, 2026": "https://arxiv.org/abs/2607.14035",
    "OpenAI, 2026": "https://developers.openai.com/api/docs/bots",
    "Perplexity, 2026": "https://docs.perplexity.ai/docs/resources/perplexity-crawlers",
    "Vercel, 2024": "https://vercel.com/blog/the-rise-of-the-ai-crawler",
    "W3C, 2023": "https://www.w3.org/TR/WCAG22/",
    "web.dev, z.d.": "https://web.dev/articles/vitals",
    "Zheng et al., 2023": "https://arxiv.org/abs/2306.05685",
}
