/* Bronwaardig – werking van de webpagina */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const api = async (pad, opties = {}) => {
  const r = await fetch(pad, { headers: { "Content-Type": "application/json" }, ...opties });
  const data = await r.json().catch(() => ({}));
  if (!r.ok && !data.fout) data.fout = `Fout ${r.status}`;
  return data;
};

let METHODE = null;
let STATUS = null;
const bronLinks = (tekst) => {
  if (!METHODE) return esc(tekst);
  // Zet bekende bronnen om in links
  return String(tekst).split(";").map((deel) => {
    const d = deel.trim();
    const sleutel = Object.keys(METHODE.bronnen).find((k) => k === d || (d.startsWith("z.d.") || d.startsWith("20")) && k.endsWith(d));
    const url = METHODE.bronnen[d] || (sleutel && METHODE.bronnen[sleutel]);
    return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(d)}</a>` : esc(d);
  }).join("; ");
};

/* ============ navigatie ============ */
function toonPagina() {
  const naam = (location.hash || "#analyse").slice(1).split("/")[0];
  const bestaat = ["analyse", "resultaten", "methode"].includes(naam) ? naam : "analyse";
  document.querySelectorAll(".pagina").forEach((p) => (p.hidden = p.id !== `pagina-${bestaat}`));
  document.querySelectorAll(".menu a").forEach((a) => a.toggleAttribute("aria-current", a.dataset.pagina === bestaat));
  if (a11yFocusNa) document.querySelector(`#pagina-${bestaat} h1`)?.focus?.();
  if (bestaat === "resultaten") laadResultaten();
  if (bestaat === "methode") toonMethode();
  const bestand = (location.hash.split("/")[1] || "");
  if (bestaat === "analyse" && bestand) openOpgeslagen(decodeURIComponent(bestand));
}
let a11yFocusNa = false;
window.addEventListener("hashchange", toonPagina);

/* ============ de ring ============ */
const DELEN = [
  { id: "seo", naam: "SEO", kleur: "var(--seo)", zacht: "var(--seo-zacht)", aandeel: 40, uitleg: "Gevonden door Google" },
  { id: "geo_techniek", naam: "GEO-techniek", kleur: "var(--tech)", zacht: "var(--tech-zacht)", aandeel: 20, uitleg: "Leesbaar voor AI-robots" },
  { id: "geo_inhoud", naam: "GEO-inhoud", kleur: "var(--inh)", zacht: "var(--inh-zacht)", aandeel: 40, uitleg: "Bruikbaar als bron" },
];
function ringSVG(scores, { dik = 13, r = 52, gat = 1.6 } = {}) {
  let start = 0, delen = "";
  for (const d of DELEN) {
    const lengte = d.aandeel - gat;
    const s = scores ? scores[d.id] : 100;
    const vul = s == null ? 0 : (lengte * s) / 100;
    delen += `<circle cx="60" cy="60" r="${r}" pathLength="100" fill="none" stroke="${d.zacht}" stroke-width="${dik}"
        stroke-dasharray="${lengte} ${100 - lengte}" stroke-dashoffset="${-start}" stroke-linecap="butt"/>
      <circle class="ring-boog" cx="60" cy="60" r="${r}" pathLength="100" fill="none" stroke="${d.kleur}" stroke-width="${dik}"
        stroke-dasharray="0 100" data-vul="${vul}" stroke-dashoffset="${-start}" stroke-linecap="butt"/>`;
    start += d.aandeel;
  }
  return delen;
}
function vulRing(svg) {
  requestAnimationFrame(() => requestAnimationFrame(() => {
    svg.querySelectorAll(".ring-boog").forEach((c) => c.setAttribute("stroke-dasharray", `${c.dataset.vul} 100`));
  }));
}

/* ============ status & instellingen ============ */
async function laadStatus() {
  STATUS = await api("/api/status");
  const stip = $("#sleutelStip");
  stip.className = "sleutel-stip " + (STATUS.sleutel ? "aan" : "uit");
  $("#sleutelTekst").textContent = STATUS.sleutel ? "AI-sleutel actief" : "Geen AI-sleutel";
}
$("#instellingenKnop").addEventListener("click", async () => {
  await laadStatus();
  const s = $("#sleutelStatus");
  s.className = "sleutel-status " + (STATUS.sleutel ? "aan" : "uit");
  s.innerHTML = STATUS.sleutel
    ? "<b>De AI-sleutel is gevonden</b> in sleutel.txt. De AI-beoordeling en het advies werken."
    : "<b>Geen AI-sleutel gevonden.</b> Zet je Gemini-sleutel in het bestand sleutel.txt in de map GEO-TOOL en herstart de tool. Zonder sleutel werken alleen de technische checks.";
  $("#modelKeuze").innerHTML = STATUS.modellen.map((m) => `<option ${m === STATUS.model ? "selected" : ""}>${esc(m)}</option>`).join("");
  $("#rondeKeuze").value = String(STATUS.rondes);
  $("#instellingen").showModal();
});
$("#instellingen").addEventListener("close", async () => {
  if ($("#instellingen").returnValue !== "opslaan") return;
  await api("/api/instellingen", { method: "POST", body: JSON.stringify({ model: $("#modelKeuze").value, rondes: $("#rondeKeuze").value }) });
  laadStatus();
});

/* ============ analyse starten en volgen ============ */
$("#zoekForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = $("#urlVeld").value.trim();
  if (!url) return;
  $("#zoekFout").hidden = true;
  $("#startKnop").disabled = true;
  $("#uitslag").hidden = true;
  $("#intro").hidden = true;
  $("#voortgang").hidden = false;
  $("#voortgangAdres").textContent = url;
  $("#stappen").innerHTML = "";
  const { id } = await api("/api/analyse", { method: "POST", body: JSON.stringify({ url }) });
  volg(id);
});

async function volg(id) {
  const d = await api(`/api/analyse/${id}`);
  if (d.stappen) {
    $("#stappen").innerHTML = d.stappen.map((s) =>
      `<li class="${esc(s.status)}">${esc(s.status === "bezig" && s.tekst ? s.tekst : s.naam)}${
        s.status !== "bezig" && s.tekst ? `<small>${esc(s.tekst)}</small>` : ""}</li>`).join("");
  }
  if (!d.klaar) return setTimeout(() => volg(id), 900);
  $("#startKnop").disabled = false;
  if (d.fout) {
    $("#voortgang").hidden = true;
    $("#intro").hidden = false;
    const f = $("#zoekFout");
    f.textContent = d.fout;
    f.hidden = false;
    return;
  }
  history.replaceState(null, "", `#analyse/${encodeURIComponent(d.resultaat.bestand)}`);
  toonUitslag(d.resultaat);
}

async function openOpgeslagen(bestand) {
  if ($("#uitslag").dataset.bestand === bestand) return;
  const d = await api(`/api/resultaat/${encodeURIComponent(bestand)}`);
  if (d.fout) return;
  toonUitslag(d);
}

/* ============ de uitslag ============ */
function statusTeken(s) {
  return { goed: "✓", fout: "✕", deels: "½", nvt: "–" }[s] || "";
}
function bewijsTekst(b) {
  return { sterk: "sterk bewijs", vuistregel: "vuistregel", zwak: "zwak bewijs" }[b] || b;
}
function uitlegKnop(soort, id) {
  return `<div class="uitleg"><button type="button" class="uitleg-knop" data-soort="${esc(soort)}" data-id="${esc(id)}">Leg beter uit</button><div class="uitleg-vak" hidden></div></div>`;
}
function checkHTML(c) {
  return `<details class="check">
    <summary>
      <span class="st st-${esc(c.status)}" aria-label="${esc(c.status)}">${statusTeken(c.status)}</span>
      <span><span class="check-naam">${esc(c.naam)}</span><span class="check-gevonden">${esc(c.gevonden)}</span></span>
      <span class="bewijs">${bewijsTekst(c.bewijs)}</span>
    </summary>
    <div class="check-meer">
      <p><b>Wat meten we?</b> ${esc(c.wat)}</p>
      <p><b>${c.telt ? "Waarom telt dit mee?" : "Waarom alleen een tip?"}</b> ${esc(c.waarom)} <span class="bronlink">(${bronLinks(c.bron)})</span></p>
      ${c.advies ? `<p><b>Wat kunt u doen?</b> ${esc(c.advies)}</p>` : ""}
      ${uitlegKnop("check", c.id)}
    </div>
  </details>`;
}

function toonUitslag(r) {
  $("#intro").hidden = true;
  $("#voortgang").hidden = true;
  const u = $("#uitslag");
  u.dataset.bestand = r.bestand || "";
  const s = r.scores;
  const datum = new Date(r.datum).toLocaleString("nl-NL", { dateStyle: "long", timeStyle: "short" });
  const ih = r.inhoud;

  const basisFout = r.poorten.filter((p) => !p.ok);
  const meldingen = [];
  if (basisFout.length) {
    meldingen.push(`<div class="melding rood" role="alert"><h3>Deze pagina kan niet goed gevonden worden door Google. Los dit eerst op.</h3>
      <ul>${basisFout.map((p) => `<li><b>${esc(p.naam)}:</b> ${esc(p.gevonden)}. ${esc(p.advies)}</li>`).join("")}</ul>
      <p class="hulp">De andere scores zijn wel berekend, zodat u ziet wat er verder beter kan.</p></div>`);
  }
  if (r.ai_fout) {
    const overgeslagen = /^(Geen AI-sleutel|Te weinig tekst|De website blokkeert)/.test(r.ai_fout);
    meldingen.push(`<div class="melding geel"><h3>${overgeslagen ? "De AI-beoordeling is overgeslagen" : "De AI-beoordeling is niet gelukt"}</h3><p>${esc(r.ai_fout)}</p>
      <p class="hulp">Zonder AI-beoordeling is er geen GEO-inhoudscore en geen totaalscore. De technische checks zijn wel compleet.</p></div>`);
  }
  if (r.waarschuwingen?.length) {
    meldingen.push(`<div class="melding geel"><h3>Let op</h3><ul>${r.waarschuwingen.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>`);
  }

  // Adviezen: eerst de basis en de checks (vaste regels), dan de AI, dan de tips
  const regel = r.regel_advies || [];
  const hoofd = regel.filter((a) => a.soort !== "tip");
  const tips = regel.filter((a) => a.soort === "tip");
  const adviesItems = [
    ...hoofd.map((a, i) => `<li class="advies"><details ${i === 0 ? "open" : ""}><summary>
        <span class="adv-labels"><span class="advies-label ${a.soort === "basis" ? "lbl-basis" : a.groep === "geo" ? "lbl-geo" : "lbl-seo"}">${
          a.soort === "basis" ? "Basis" : a.groep === "geo" ? "GEO-techniek" : "SEO"}</span></span>
        <h3>${esc(a.titel)}</h3><span class="adv-kort">${esc(a.gevonden)}</span></summary>
        <div class="adv-body"><p>${esc(a.tekst)}</p>
        <p class="gevonden">Gevonden: ${esc(a.gevonden)} <span class="bronlink">(${bronLinks(a.bron)})</span></p>
        ${uitlegKnop(a.soort === "basis" ? "basis" : "check", r.poorten.find((p) => p.naam === a.titel)?.id || r.checks.find((c) => c.naam === a.titel)?.id || "")}</div></details></li>`),
    ...(r.ai_advies || []).map((a, i) => `<li class="advies"><details ${hoofd.length === 0 && i === 0 ? "open" : ""}><summary>
        <span class="adv-labels"><span class="advies-label lbl-ai">GEO-inhoud, prioriteit ${esc((a.prioriteit || "").toLowerCase())}</span>
        ${a.inspanning ? `<span class="advies-label lbl-tip">Inspanning: ${esc(a.inspanning.toLowerCase())}</span>` : ""}</span>
        <h3>${esc(a.titel)}</h3>${a.nu ? `<span class="adv-kort">${esc(a.nu)}</span>` : ""}</summary>
        <div class="adv-body">
        <p><b>Waarom dit helpt:</b> ${esc(a.waarom)}</p>
        ${a.stappen?.length ? `<div class="adv-stappen"><b>Zo pakt u het aan:</b><ol>${a.stappen.map((s) => `<li>${esc(s)}</li>`).join("")}</ol></div>` : ""}
        ${a.voorbeeld ? `<div class="voorbeeld"><b>Voorbeeld:</b> ${esc(a.voorbeeld)}</div>` : ""}
        <p class="ai-noot">Geschreven door AI, controleer dit voordat u het uitvoert.</p>
        ${uitlegKnop("advies", String(i))}</div></details></li>`),
  ];

  const seoChecks = r.checks.filter((c) => c.groep === "seo" && c.telt);
  const geoChecks = r.checks.filter((c) => c.groep === "geo" && c.telt);
  const tipChecks = r.checks.filter((c) => !c.telt);
  const aantalGoed = (lijst) => lijst.filter((c) => c.status === "goed").length;
  const telbaar = (lijst) => lijst.filter((c) => c.status !== "nvt").length;

  const delen = DELEN.map((d) => {
    const w = s[d.id];
    return `<div class="deel">
      <span class="deel-naam">${d.naam}<small>${d.uitleg}, telt ${d.aandeel}%</small></span>
      <span class="deel-balk"><span data-breed="${w ?? 0}" style="background:${d.kleur}"></span></span>
      <span class="deel-getal ${w == null ? "leeg" : ""}">${w ?? "–"}</span></div>`;
  }).join("");

  const criteriaHTML = ih ? ih.criteria.map((c) => `<details class="crit"><summary>
      <div class="crit-kop"><h3>${esc(c.naam)}</h3>
        <span class="schaal" aria-label="cijfer ${c.cijfer ?? "onbekend"} van 5">${[1, 2, 3, 4, 5].map((i) => `<i class="${c.cijfer != null && i <= Math.round(c.cijfer) ? "vol" : ""}"></i>`).join("")}
        <span class="crit-cijfer">${c.cijfer ?? "–"}</span></span></div>
      <p class="crit-uitleg">${esc(c.uitleg || "Geen geldige beoordeling.")}</p></summary>
      <div class="crit-meer">
      <p class="hulp"><b>Vraag aan de AI:</b> ${esc(c.vraag)} <span class="bronlink">(${bronLinks(c.bron)})</span></p>
      ${c.citaat ? `<p class="citaat">\u201c${esc(c.citaat)}\u201d</p>` : ""}
      <div class="rondes">Rondes: ${c.rondes.map((x) => `<span class="${x.geldig ? "" : "ongeldig"}" title="${x.geldig ? "geldig" : "citaat niet gevonden op de pagina"}">${x.score}</span>`).join("")}
        ${c.onzeker ? `<span class="onzeker">onzeker</span>` : ""}</div>
      ${uitlegKnop("criterium", c.id)}</div>
    </details>`).join("") : `<p class="hulp">Geen AI-beoordeling beschikbaar.</p>`;

  u.innerHTML = `
    <div class="uitslag-kop">
      <div class="ring-wrap">
        <svg viewBox="0 0 120 120" role="img" aria-label="Totaalscore ${s.totaal ?? "onbekend"} van 100">${ringSVG(s)}</svg>
        <div class="ring-midden"><span class="ring-getal">${s.totaal ?? "–"}</span><span class="ring-label">${s.totaal == null ? "geen totaal" : "van 100"}</span></div>
      </div>
      <div class="bronkaart">
        <div class="bron-domein"><img alt="" src="https://www.google.com/s2/favicons?domain=${encodeURIComponent(r.domein)}&sz=64" onerror="this.remove()"><span>${esc(r.domein)}</span></div>
        <div><p class="bron-titel">${esc(r.titel || "Pagina zonder titel")}</p>
          <p class="bron-oms ${r.omschrijving ? "" : "leeg"}">${esc(r.omschrijving || "Deze pagina heeft geen omschrijving.")}</p></div>
        <div class="delen">${delen}</div>
        <div class="meta-regel"><span>${esc(datum)}</span><span>${r.woorden} woorden</span>${ih ? `<span>AI: ${esc(ih.modelversie)}, ${ih.rondes_gelukt} rondes</span>` : ""}
          <a href="${esc(r.url)}" target="_blank" rel="noopener">Pagina openen</a></div>
      </div>
    </div>
    ${meldingen.join("")}

    <section class="sectie">
      <div class="sectie-kop"><h2>Wat kunt u het beste eerst doen?</h2>
        <p>Eerst de basis en de technische punten (vaste regels), daarna de adviezen over de tekst (geschreven door AI). Klik op een advies voor meer.</p>
        <button type="button" class="klap-knop">Alles uitklappen</button></div>
      ${r.ai_samenvatting ? `<div class="samenvatting"><p>${esc(r.ai_samenvatting)}</p><p class="ai-noot">Samenvatting geschreven door AI.</p></div>` : ""}
      ${adviesItems.length ? `<ol class="adviezen">${adviesItems.join("")}</ol>` : `<p class="hulp">Geen verbeterpunten gevonden. Bekijk de tips hieronder.</p>`}
    </section>

    <section class="sectie twee">
      <div>
        <div class="sectie-kop"><h2>SEO</h2><p>${aantalGoed(seoChecks)} van ${telbaar(seoChecks)} checks goed. Klik op een check voor uitleg en bron.</p><button type="button" class="klap-knop">Alles uitklappen</button></div>
        <div class="checklijst">${seoChecks.map(checkHTML).join("")}</div>
        <div class="sectie-kop" style="margin-top:32px"><h2>GEO-techniek</h2><p>${aantalGoed(geoChecks)} van ${telbaar(geoChecks)} checks goed.</p></div>
        <div class="checklijst">${geoChecks.map(checkHTML).join("")}</div>
      </div>
      <div>
        <div class="sectie-kop"><h2>GEO-inhoud</h2><p>Een AI geeft de tekst op 6 punten een cijfer van 1 tot 5. Bij elk cijfer moet de AI een citaat van de pagina geven; de tool controleert of dat citaat echt op de pagina staat. Klik op een punt voor meer.</p><button type="button" class="klap-knop">Alles uitklappen</button></div>
        ${ih ? `<div class="ai-samenvatting"><span>Onderwerp: ${esc(ih.onderwerp)}</span><span>Gemiddeld ${String(ih.gemiddelde).replace(".", ",")} van 5</span>
          <span>${ih.verzonnen_citaten} van ${ih.citaten_totaal} citaten niet gevonden</span>${ih.ander_model ? "<span>Let op: reservemodel gebruikt</span>" : ""}</div>` : ""}
        <div class="criteria">${criteriaHTML}</div>
      </div>
    </section>

    <section class="sectie">
      <div class="sectie-kop"><h2>Tips</h2><p>Voor deze punten is het bewijs te zwak. Ze kosten geen punten, maar kunnen wel helpen.</p></div>
      <div class="checklijst">${tipChecks.map(checkHTML).join("")}</div>
    </section>

    <section class="sectie">
      <div class="sectie-kop"><h2>Ter informatie</h2><p>Hiervoor is geen bewijs. Dit telt niet mee.</p></div>
      <div class="info-lijst">${r.info.map((i) => `<div class="info"><b>${esc(i.naam)}</b><div class="w ${i.waarde.includes("\n") ? "lijst" : ""}">${esc(i.waarde).replace(/\n/g, "<br>")}</div><p>${esc(i.uitleg)}</p></div>`).join("")}</div>
    </section>

    <section class="sectie">
      <div class="knoppen-rij">
        <button class="knop-licht" type="button" id="nieuweKnop">Nieuwe pagina analyseren</button>
        <a class="knop-licht" href="/api/resultaat/${encodeURIComponent(r.bestand || "")}" download="${esc(r.bestand || "resultaat.json")}">Download deze analyse</a>
        <a class="knop-licht" href="#resultaten">Alle resultaten</a>
      </div>
    </section>`;
  u.hidden = false;
  vulRing(u.querySelector(".ring-wrap svg"));
  requestAnimationFrame(() => requestAnimationFrame(() => u.querySelectorAll(".deel-balk span").forEach((b) => (b.style.width = b.dataset.breed + "%"))));
  $("#nieuweKnop").addEventListener("click", () => {
    u.hidden = true; u.dataset.bestand = "";
    $("#intro").hidden = false;
    history.replaceState(null, "", "#analyse");
    $("#urlVeld").select();
    window.scrollTo({ top: 0 });
  });
  window.scrollTo({ top: 0 });
}

function toonUitleg(vak, onderdelen) {
  vak.innerHTML = `<p class="uitleg-label">Uitgebreide uitleg, geschreven door AI. Controleer dit voordat u het uitvoert.</p>` +
    onderdelen.map((o) => `<div class="uitleg-deel">${o.kop ? `<h4>${esc(o.kop)}</h4>` : ""}${o.tekst ? `<p>${esc(o.tekst)}</p>` : ""}${
      o.lijst?.length ? `<ul>${o.lijst.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</div>`).join("");
}
$("#uitslag").addEventListener("click", async (e) => {
  const klap = e.target.closest(".klap-knop");
  if (klap) {
    const sectie = klap.closest(".sectie-kop").parentElement;
    const lijst = [...sectie.querySelectorAll("details")];
    const open = klap.textContent.startsWith("Alles uit");
    lijst.forEach((d) => (d.open = open));
    sectie.querySelectorAll(".klap-knop").forEach((k) => (k.textContent = open ? "Alles inklappen" : "Alles uitklappen"));
    return;
  }
  const knop = e.target.closest(".uitleg-knop");
  if (!knop) return;
  const vak = knop.nextElementSibling;
  if (!vak.hidden && vak.dataset.klaar) { vak.hidden = true; knop.textContent = "Leg beter uit"; return; }
  if (vak.dataset.klaar) { vak.hidden = false; knop.textContent = "Uitleg verbergen"; return; }
  knop.disabled = true;
  knop.textContent = "AI schrijft een uitleg...";
  vak.hidden = false;
  vak.innerHTML = `<p class="hulp">Even geduld, dit duurt meestal 5 tot 20 seconden.</p>`;
  const d = await api("/api/uitleg", { method: "POST", body: JSON.stringify({ bestand: $("#uitslag").dataset.bestand, soort: knop.dataset.soort, id: knop.dataset.id }) });
  knop.disabled = false;
  if (d.fout) {
    vak.innerHTML = `<p class="uitleg-fout">${esc(d.fout)}</p>`;
    knop.textContent = "Probeer opnieuw";
    return;
  }
  toonUitleg(vak, d.onderdelen);
  vak.dataset.klaar = "1";
  knop.textContent = "Uitleg verbergen";
});

/* ============ resultaten ============ */
function corrUitleg(rho) {
  if (rho == null) return "Nog te weinig analyses (minimaal 3).";
  if (rho >= 0.8) return "Bijna dezelfde volgorde. De keuze maakt weinig uit.";
  if (rho >= 0.5) return "Redelijk dezelfde volgorde, met verschuivingen.";
  return "Duidelijk andere volgorde. Noem dit bij de beperkingen.";
}
async function laadResultaten() {
  const d = await api("/api/resultaten");
  const noot = $("#onlineNoot");
  if (noot) noot.hidden = !(STATUS && STATUS.online);
  const c = d.correlaties || {};
  const fmt = (x) => (x == null ? "–" : String(x).replace(".", ","));
  $("#correlaties").innerHTML = `
    <div class="corr hoofd"><div class="naam">Score tegenover AI-zichtbaarheid</div><div class="getal">${fmt(c.zichtbaarheid)}</div>
      <p>${c.zichtbaarheid == null ? `Vul bij minstens 3 pagina's de gemeten AI-zichtbaarheid in (hoofdstuk 8, stap 2). Nu: ${c.zichtbaarheid_n || 0}.` :
        c.zichtbaarheid >= 0.5 ? "Pagina's met een hoge score worden vaker genoemd door AI." : c.zichtbaarheid > 0 ? "Een zwak verband tussen score en AI-zichtbaarheid." : "Geen positief verband gevonden."} Spearman, ${c.zichtbaarheid_n || 0} pagina's.</p></div>
    <div class="corr"><div class="naam">Variant A: blokkerend telt dubbel</div><div class="getal">${fmt(c.a_blokkerend_dubbel)}</div><p>${corrUitleg(c.a_blokkerend_dubbel)}</p></div>
    <div class="corr"><div class="naam">Variant B: oude 3-2-1-punten</div><div class="getal">${fmt(c.b_oude_punten)}</div><p>${corrUitleg(c.b_oude_punten)}</p></div>
    <div class="corr"><div class="naam">Variant C: 33/33/33</div><div class="getal">${fmt(c.c_gelijk_verdeeld)}</div><p>${corrUitleg(c.c_gelijk_verdeeld)}</p></div>`;
  const rijen = d.rijen || [];
  if (!rijen.length) {
    $("#resTabel").innerHTML = `<tbody><tr><td class="leeg-staat" colspan="9">Nog geen analyses. Analyseer eerst een pagina; die verschijnt dan hier.</td></tr></tbody>`;
    return;
  }
  $("#resTabel").innerHTML = `<thead><tr><th>Pagina</th><th>SEO</th><th>GEO-techniek</th><th>GEO-inhoud</th><th>Totaal</th>
      <th>Var. A</th><th>Var. B</th><th>Var. C</th><th>AI-zichtbaarheid (%)</th></tr></thead>
    <tbody>${rijen.map((r) => `<tr>
      <td><a href="#analyse/${encodeURIComponent(r.bestand)}">${esc(r.titel || r.domein)}</a><small>${esc(r.url)}${r.basis_ok ? "" : " – basis niet in orde"}</small></td>
      <td>${r.seo ?? "–"}</td><td>${r.geo_techniek ?? "–"}</td><td>${r.geo_inhoud ?? "–"}</td><td class="tot">${r.totaal ?? "–"}</td>
      <td>${r.a_blokkerend_dubbel ?? "–"}</td><td>${r.b_oude_punten ?? "–"}</td><td>${r.c_gelijk_verdeeld ?? "–"}</td>
      <td><label class="vh" for="z-${esc(r.bestand)}">AI-zichtbaarheid voor ${esc(r.domein)}</label>
        <input id="z-${esc(r.bestand)}" data-url="${esc(r.url)}" inputmode="decimal" value="${r.zichtbaarheid ?? ""}" placeholder="0–100"></td></tr>`).join("")}</tbody>`;
  $("#resTabel").querySelectorAll("input").forEach((inp) => inp.addEventListener("change", async () => {
    const res = await api("/api/zichtbaarheid", { method: "POST", body: JSON.stringify({ url: inp.dataset.url, waarde: inp.value }) });
    if (res.fout) { inp.setCustomValidity(res.fout); inp.reportValidity(); return; }
    inp.setCustomValidity("");
    laadResultaten();
  }));
}

/* ============ methode ============ */
async function toonMethode() {
  if (!METHODE) METHODE = await api("/api/methode");
  const m = METHODE;
  const rij = ([id, c]) => `<tr><td><b>${esc(c.naam)}</b></td><td>${esc(c.wat)}</td><td>${bewijsTekst(c.bewijs)}</td><td>${c.telt ? "Telt mee" : "Tip"}</td><td>${bronLinks(c.bron)}</td></tr>`;
  const tabel = (groep) => `<table class="m-tabel"><thead><tr><th>Check</th><th>Wat meten we?</th><th>Bewijs</th><th>Telt mee?</th><th>Bron</th></tr></thead>
      <tbody>${Object.entries(m.checks).filter(([, c]) => c.groep === groep).map(rij).join("")}</tbody></table>`;
  $("#methodeInhoud").innerHTML = `<div class="methode">
    <div><h1>Hoe werkt de score?</h1>
      <p class="lead">De tool volgt de methode uit ons onderzoeksdocument. Elke score is na te rekenen, en bij elke check staat de bron.</p></div>
    <ol class="stap-lijst">
      <li><h3>Eerst de basis</h3><p>Werkt de pagina, mag hij in Google komen en mogen zoekmachines hem lezen? Zo niet, dan toont de tool een rode melding.</p></li>
      <li><h3>Alleen bewezen checks tellen</h3><p>Vier vaste vragen bepalen per check hoe sterk het bewijs is. Sterk bewijs en vuistregels tellen mee; zwak bewijs wordt een tip.</p></li>
      <li><h3>Alles telt even zwaar</h3><p>Niemand weet hoeveel zwaarder de ene check is dan de andere. Gelijke gewichten zijn dan het eerlijkst (Dawes, 1979).</p></li>
      <li><h3>Van checks naar een cijfer</h3><p>Score = goede checks ÷ aantal checks × 100. Totaal = 40% SEO + 20% GEO-techniek + 40% GEO-inhoud.</p></li>
    </ol>
    <div><h2>SEO-checks</h2><div class="tabel-wrap" style="margin-top:14px">${tabel("seo")}</div></div>
    <div><h2>GEO-checks</h2><div class="tabel-wrap" style="margin-top:14px">${tabel("geo")}</div></div>
    <div><h2>De AI-beoordeling</h2><p class="lead">Zes punten, elk een cijfer van 1 tot 5. Temperature 0, vaste instructies, meerdere rondes en het middelste cijfer. Bij elk cijfer moet de AI een citaat geven dat de tool controleert.</p>
      <div class="tabel-wrap" style="margin-top:14px"><table class="m-tabel"><thead><tr><th>Punt</th><th>Een 1 is...</th><th>Een 3 is...</th><th>Een 5 is...</th><th>Bron</th></tr></thead>
      <tbody>${m.criteria.map((c) => `<tr><td><b>${esc(c.naam)}</b><br><span class="hulp">${esc(c.vraag)}</span></td><td>${esc(c.ankers[1])}</td><td>${esc(c.ankers[3])}</td><td>${esc(c.ankers[5])}</td><td>${bronLinks(c.bron)}</td></tr>`).join("")}</tbody></table></div></div>
    <div><h2>Bronnen</h2><ul class="bronnen-lijst">${Object.entries(m.bronnen).map(([k, v]) => `<li><a href="${esc(v)}" target="_blank" rel="noopener">${esc(k)}</a></li>`).join("")}</ul></div>
  </div>`;
}

/* ============ start ============ */
(async function start() {
  const mini = $(".mini-ring");
  mini.innerHTML = ringSVG({ seo: 100, geo_techniek: 100, geo_inhoud: 100 }, { dik: 16, r: 48 });
  mini.style.transform = "rotate(-90deg)";
  vulRing(mini);
  METHODE = await api("/api/methode");
  await laadStatus();
  toonPagina();
  a11yFocusNa = true;
})();
