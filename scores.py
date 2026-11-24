"""
DE SCORES (hoofdstuk 4 en 7 van de methode) + DE VARIANTEN VOOR HOOFDSTUK 8
"""

from methode import BLOKKEREND, WEGING


def onderdeel_score(checks, groep, gewicht=lambda c: 1.0, met_tips=False, tip_gewicht=None):
    """Score = goede checks / aantal checks x 100. Checks die 'nvt' zijn tellen niet mee."""
    teller = noemer = 0.0
    for c in checks:
        if c["groep"] != groep or c["waarde"] is None:
            continue
        if not c["telt"] and not met_tips:
            continue
        g = gewicht(c) if c["telt"] else (tip_gewicht(c) if tip_gewicht else 1.0)
        teller += g * c["waarde"]
        noemer += g
    return round(100 * teller / noemer) if noemer else None


def totaal(seo, geo_t, geo_i, weging=WEGING):
    if None in (seo, geo_t, geo_i):
        return None
    return round(weging["seo"] * seo + weging["geo_techniek"] * geo_t + weging["geo_inhoud"] * geo_i)


def bereken(checks, geo_inhoud):
    seo = onderdeel_score(checks, "seo")
    geo_t = onderdeel_score(checks, "geo")
    return {"seo": seo, "geo_techniek": geo_t, "geo_inhoud": geo_inhoud,
            "totaal": totaal(seo, geo_t, geo_inhoud)}


def varianten(checks, geo_inhoud):
    """De drie andere manieren van rekenen uit hoofdstuk 8, stap 4."""
    # A: checks die een pagina onvindbaar of onleesbaar maken tellen dubbel
    dubbel = lambda c: 2.0 if c["id"] in BLOKKEREND else 1.0
    a = totaal(onderdeel_score(checks, "seo", dubbel), onderdeel_score(checks, "geo", dubbel), geo_inhoud)
    # B: de oude manier: sterk 3, vuistregel 2, zwak (tips) 1 punt
    punten = {"sterk": 3.0, "vuistregel": 2.0, "zwak": 1.0}
    pg = lambda c: punten[c["bewijs"]]
    b = totaal(onderdeel_score(checks, "seo", pg, met_tips=True, tip_gewicht=pg),
               onderdeel_score(checks, "geo", pg, met_tips=True, tip_gewicht=pg), geo_inhoud)
    # C: totaalscore met 33/33/33
    seo, geo_t = onderdeel_score(checks, "seo"), onderdeel_score(checks, "geo")
    c = totaal(seo, geo_t, geo_inhoud, {"seo": 1 / 3, "geo_techniek": 1 / 3, "geo_inhoud": 1 / 3})
    return {"a_blokkerend_dubbel": a, "b_oude_punten": b, "c_gelijk_verdeeld": c}


def _rangen(waarden):
    """Rangnummers, met gemiddelde rang bij gelijke waarden."""
    volgorde = sorted(range(len(waarden)), key=lambda i: waarden[i])
    rang = [0.0] * len(waarden)
    i = 0
    while i < len(volgorde):
        j = i
        while j + 1 < len(volgorde) and waarden[volgorde[j + 1]] == waarden[volgorde[i]]:
            j += 1
        for k in range(i, j + 1):
            rang[volgorde[k]] = (i + j) / 2 + 1
        i = j + 1
    return rang


def spearman(x, y):
    """Spearman-rangcorrelatie (-1 tot 1). Geeft None bij te weinig data."""
    paren = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(paren) < 3:
        return None
    rx, ry = _rangen([p[0] for p in paren]), _rangen([p[1] for p in paren])
    n = len(paren)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    if vx == 0 or vy == 0:
        return None
    return round(cov / (vx * vy), 2)
