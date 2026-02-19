"""
TWICE — Generateur rapport HTML
Val d'Isere : carte Leaflet + graphiques + module simulation JS
Langues : Français, English, Luxembourgeois, Allemand
"""

import json
from pathlib import Path
import os


def fmt_eur(v):
    return f"{int(v):,} EUR".replace(",", "\u202f")


def fmt_date(iso):
    if len(iso) >= 16:
        return f"{iso[8:10]}/{iso[5:7]} {iso[11:16]}"
    return iso


def badge_statut(s):
    c = {"ouvert":("#d1fae5","#065f46"),"reduit":("#fef3c7","#92400e"),"ferme":("#fee2e2","#991b1b")}
    bg, fg = c.get(s, ("#f3f4f6","#374151"))
    return f'<span style="background:{bg};color:{fg};padding:1px 7px;border-radius:3px;font-size:11px;font-weight:600">{s}</span>'


def generate(data):
    times     = data["meteo"]["times"]
    vent      = data["meteo"]["vent"]
    neige     = data["meteo"]["neige"]
    temp      = data["meteo"]["temp"]
    indices   = data["indices_alea"]
    now_idx   = data["now_index"]
    gen_at    = data["generated_at"][:16].replace("T"," ")
    remontees = data["remontees"]
    resultats = data["resultats"]
    hyps      = data["hypotheses"]
    perte_totale = data["perte_totale_station_eur"]

    n      = len(times)
    labels = [fmt_date(t) for t in times]

    # ── Chronologie tableau
    rows_html = ""
    asset0 = next((r for r in resultats if r["type"]=="forfaits"), resultats[0])
    for h in asset0["chronologie"]:
        td  = fmt_date(h["time"])
        bgs = " ".join(badge_statut(v2) for v2 in list(h["statuts_remontees"].values())[:3])
        fc  = ' <small style="color:#2563eb;font-weight:600" data-i18n="forecast"></small>' if h["is_forecast"] else ""
        if h["taux_activite"]==0:   bg='style="background:#fff5f5"'
        elif h["taux_activite"]<1:  bg='style="background:#fffbeb"'
        elif h["is_forecast"]:      bg='style="background:#f0f9ff"'
        else:                       bg=""
        rows_html += f"""<tr {bg}>
          <td>{td}{fc}</td><td>{h['vent_kmh']:.0f} km/h</td><td>{h['neige_cmh']:.1f} cm/h</td>
          <td>{h['temp_c']:.1f}°C</td><td>{h['indice_alea']:.2f}</td><td>{bgs}</td>
          <td>{h['accessibilite']:.0%}</td><td>{h['taux_activite']:.0%}</td>
          <td style="text-align:right;font-weight:600">{fmt_eur(h['perte_eur'])}</td>
        </tr>"""

    # ── KPI cards
    cards_html = ""
    for s in resultats:
        cards_html += f"""
        <div class="card {'card-resto' if s['type']=='restaurant' else ''}">
          <div class="card-type" data-i18n="type_{s['type']}">{s['type'].replace('_',' ')}</div>
          <div class="card-nom">{s['asset_nom']}</div>
          <div class="kpis">
            <div class="kpi"><div class="kv red">{fmt_eur(s['perte_totale_eur'])}</div><div class="kl" data-i18n="estimated_loss">Perte estimée</div></div>
            <div class="kpi"><div class="kv">{s['heures_arret']}h</div><div class="kl" data-i18n="stopped">À l'arrêt</div></div>
            <div class="kpi"><div class="kv">{s['heures_degradees']}h</div><div class="kl" data-i18n="degraded">Dégradées</div></div>
            <div class="kpi"><div class="kv">{s['accessibilite_min']:.0%}</div><div class="kl" data-i18n="min_access">Access. min</div></div>
          </div>
        </div>"""

    hyp_html = "".join(f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in hyps.items())

    taux0  = [h["taux_activite"]*100 for h in asset0["chronologie"]]
    cumul0 = []
    c = 0
    for h in asset0["chronologie"]:
        c += h["perte_eur"]
        cumul0.append(round(c))

    labels_js    = json.dumps(labels)
    vent_js      = json.dumps(vent)
    neige_js     = json.dumps(neige)
    temp_js      = json.dumps(temp)
    indices_js   = json.dumps(indices)
    now_js       = now_idx
    resultats_js = json.dumps(resultats)
    remontees_js = json.dumps(remontees)
    taux0_js     = json.dumps(taux0)
    cumul0_js    = json.dumps(cumul0)
    n_days       = n // 24

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>TWICE — Val d'Isère Digital Twin</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,sans-serif;background:#f0f2f5;color:#1e2433;font-size:14px}}

header{{background:#1e2433;color:#fff;padding:18px 40px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}}
header h1{{font-size:20px;font-weight:600}}
header .sub{{color:#8892a4;font-size:12px;margin-top:3px}}
.badge-proto{{background:#2563eb;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:12px;letter-spacing:.5px}}
.meta{{text-align:right;font-size:12px;color:#8892a4}}

/* ── Sélecteur de langue ── */
.lang-bar{{background:#16202e;padding:6px 40px;display:flex;align-items:center;gap:6px;border-bottom:1px solid #2a3444}}
.lang-label{{font-size:11px;color:#8892a4;margin-right:6px}}
.lang-btn{{background:transparent;border:1px solid #3a4558;border-radius:6px;color:#c8d0db;
           font-size:12px;padding:4px 10px;cursor:pointer;transition:all .15s;white-space:nowrap}}
.lang-btn:hover{{background:#2a3444;color:#fff}}
.lang-btn.active{{background:#2563eb;border-color:#2563eb;color:#fff;font-weight:600}}

.tabs{{background:#fff;border-bottom:1px solid #e4e6ea;padding:0 40px;display:flex}}
.tab{{padding:14px 24px;cursor:pointer;font-size:13px;font-weight:500;color:#6b7280;border-bottom:2px solid transparent;transition:all .2s}}
.tab.active{{color:#2563eb;border-bottom-color:#2563eb}}
.tab:hover:not(.active){{color:#374151}}

.panel{{display:block;visibility:hidden;height:0;overflow:hidden}}
.panel.active{{visibility:visible;height:auto;overflow:visible}}

.sim-bar{{background:#fff;border-bottom:1px solid #e4e6ea;padding:16px 40px;display:none;align-items:flex-end;gap:20px;flex-wrap:wrap}}
.sim-bar.active{{display:flex}}
.sim-field{{display:flex;flex-direction:column;gap:4px}}
.sim-field label{{font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.5px}}
.sim-field input{{width:110px;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;font-family:Inter,sans-serif}}
.sim-field input:focus{{outline:none;border-color:#2563eb;box-shadow:0 0 0 2px rgba(37,99,235,.15)}}
.btn{{padding:9px 22px;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;font-family:Inter,sans-serif}}
.btn-primary{{background:#2563eb;color:#fff}}
.btn-primary:hover{{background:#1d4ed8}}

main{{padding:24px 40px;max-width:1400px;margin:0 auto}}
section{{margin-bottom:32px}}
h2{{font-size:15px;font-weight:600;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #1e2433;display:flex;align-items:center;gap:8px}}
.num{{font-size:10px;font-weight:700;color:#2563eb;background:#eff6ff;padding:2px 7px;border-radius:3px;letter-spacing:1px}}

.kpi-total{{background:linear-gradient(135deg,#1e2433,#2563eb);color:#fff;border-radius:10px;padding:20px 28px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
.kpi-total .label{{font-size:12px;color:rgba(255,255,255,.7);text-transform:uppercase;letter-spacing:.8px}}
.kpi-total .value{{font-size:28px;font-weight:700;margin-top:4px}}

.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}}
.card{{background:#fff;border:1px solid #e4e6ea;border-radius:8px;padding:16px;border-left:3px solid #2563eb}}
.card-resto{{border-left-color:#7c3aed}}
.card-type{{font-size:10px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.7px;margin-bottom:4px}}
.card-nom{{font-size:14px;font-weight:600;margin-bottom:12px}}
.kpis{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.kv{{font-size:18px;font-weight:700}}
.kv.red{{color:#dc2626}}
.kl{{font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:.4px;margin-top:2px}}

#map,#map-sim{{height:480px;border-radius:8px;border:1px solid #e4e6ea}}

.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:16px}}
.chart-box{{background:#fff;border:1px solid #e4e6ea;border-radius:8px;padding:18px 20px}}
.chart-box h3{{font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.7px;margin-bottom:14px}}

.tbl-wrap{{background:#fff;border:1px solid #e4e6ea;border-radius:8px;overflow:auto;max-height:440px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
thead tr{{background:#1e2433;color:#fff;position:sticky;top:0;z-index:1}}
thead th{{padding:9px 10px;text-align:left;font-weight:500;font-size:10px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap}}
tbody tr{{border-bottom:1px solid #f0f1f3}}
tbody tr:hover{{filter:brightness(.97)}}
tbody td{{padding:6px 10px;vertical-align:middle}}
.hyp-tbl{{width:100%;border-collapse:collapse;font-size:13px}}
.hyp-tbl td{{padding:7px 12px;border-bottom:1px solid #f0f1f3}}
.hyp-tbl tr:last-child td{{border-bottom:none}}

footer{{text-align:center;padding:18px;font-size:11px;color:#9ca3af;border-top:1px solid #e4e6ea;margin-top:16px}}
</style>
</head>
<body>

<header>
  <div>
    <h1>TWICE &mdash; Digital Twin Val d'Is&egrave;re</h1>
    <div class="sub" data-i18n="subtitle">Interruptions de service liées aux intempéries · Domaine skiable</div>
  </div>
  <div class="meta">
    <div class="badge-proto">PROTOTYPE</div>
    <div style="margin-top:6px" data-i18n-tpl="generated_at" data-i18n-val="{gen_at}"></div>
    <div style="margin-top:2px;color:#fff;font-size:11px">
      <span data-i18n="total_loss_header">Perte totale fenêtre :</span> <b>{fmt_eur(perte_totale)}</b>
    </div>
  </div>
</header>

<!-- Barre de sélection de langue -->
<div class="lang-bar">
  <span class="lang-label" data-i18n="lang_label">🌐 Langue :</span>
  <button class="lang-btn active" onclick="setLang('fr')">🇫🇷 Français</button>
  <button class="lang-btn" onclick="setLang('en')">🇬🇧 English</button>
  <button class="lang-btn" onclick="setLang('lb')">🇱🇺 Lëtzebuergesch</button>
  <button class="lang-btn" onclick="setLang('de')">🇩🇪 Deutsch</button>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('realtime',this)" data-i18n="tab_realtime">📡 Temps réel &amp; prévisions 7j</div>
  <div class="tab" onclick="switchTab('simulation',this)" data-i18n="tab_simulation">🎛 Simulation scénario</div>
</div>

<div class="sim-bar" id="sim-bar">
  <div class="sim-field">
    <label data-i18n="sim_wind">Vent max (km/h)</label>
    <input type="number" id="sim-vent" value="65" min="0" max="150">
  </div>
  <div class="sim-field">
    <label data-i18n="sim_snow">Neige (cm/h)</label>
    <input type="number" id="sim-neige" value="5" min="0" max="50" step="0.5">
  </div>
  <div class="sim-field">
    <label data-i18n="sim_temp">Température (°C)</label>
    <input type="number" id="sim-temp" value="-8" min="-30" max="5">
  </div>
  <div class="sim-field">
    <label data-i18n="sim_duration">Durée (heures)</label>
    <input type="number" id="sim-duree" value="12" min="1" max="72">
  </div>
  <button class="btn btn-primary" onclick="runSimulation()" data-i18n="sim_run">▶ Simuler</button>
  <div id="sim-status" style="font-size:12px;color:#6b7280;align-self:center"></div>
</div>

<!-- PANEL TEMPS REEL -->
<div id="panel-realtime" class="panel active">
<main>
  <section>
    <h2><span class="num">01</span> <span data-i18n="section_summary">Synthèse des impacts</span> — {n}h ({n_days}j)</h2>
    <div class="kpi-total">
      <div>
        <div class="label" data-i18n="total_loss_all">Perte totale estimée — tous assets</div>
        <div class="value">{fmt_eur(perte_totale)}</div>
      </div>
      <div style="text-align:right">
        <div class="label" data-i18n="analysis_window">Fenêtre d'analyse</div>
        <div style="font-size:15px;font-weight:600;margin-top:4px">{n}h ({n_days}j)</div>
      </div>
    </div>
    <div class="cards">{cards_html}</div>
  </section>
  <section>
    <h2><span class="num">02</span> <span data-i18n="section_map">Carte des impacts</span></h2>
    <div id="map"></div>
  </section>
  <section>
    <h2><span class="num">03</span> <span data-i18n="section_charts">Visualisation temporelle</span></h2>
    <div class="charts">
      <div class="chart-box"><h3 data-i18n="chart_wind_snow">Vent (km/h) &amp; Neige (cm/h)</h3><canvas id="cMeteo" height="200"></canvas></div>
      <div class="chart-box"><h3 data-i18n="chart_alea">Indice d'aléa composite</h3><canvas id="cAlea" height="200"></canvas></div>
      <div class="chart-box"><h3 data-i18n="chart_activity">Taux d'activité — Forfaits Bellevarde</h3><canvas id="cTaux" height="200"></canvas></div>
      <div class="chart-box"><h3 data-i18n="chart_losses">Pertes cumulées — Forfaits Bellevarde</h3><canvas id="cPertes" height="200"></canvas></div>
    </div>
  </section>
  <section>
    <h2><span class="num">04</span> <span data-i18n="section_chrono">Chronologie détaillée — Forfaits Bellevarde</span></h2>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th data-i18n="th_datetime">Date/Heure</th>
          <th data-i18n="th_wind">Vent</th>
          <th data-i18n="th_snow">Neige</th>
          <th data-i18n="th_temp">Temp.</th>
          <th data-i18n="th_index">Indice</th>
          <th data-i18n="th_lifts">Remontées (top 3)</th>
          <th data-i18n="th_access">Access.</th>
          <th data-i18n="th_rate">Taux</th>
          <th style="text-align:right" data-i18n="th_loss">Perte</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </section>
  <section>
    <h2><span class="num">05</span> <span data-i18n="section_hyp">Hypothèses du modèle</span></h2>
    <div class="tbl-wrap"><table class="hyp-tbl">{hyp_html}</table></div>
  </section>
</main>
</div>

<!-- PANEL SIMULATION -->
<div id="panel-simulation" class="panel">
<main>
  <section>
    <h2><span class="num">01</span> <span data-i18n="sim_map_title">Carte des impacts simulés</span></h2>
    <div id="map-sim"></div>
  </section>
  <section>
    <h2><span class="num">02</span> <span data-i18n="sim_assets_title">Impacts par asset</span></h2>
    <div class="kpi-total">
      <div>
        <div class="label" data-i18n="sim_total_loss">Perte totale simulée</div>
        <div class="value" id="sim-perte-total" data-i18n="sim_launch_hint">Lancez une simulation ▲</div>
      </div>
      <div style="text-align:right">
        <div class="label" data-i18n="sim_duration_label">Durée simulée</div>
        <div style="font-size:15px;font-weight:600;margin-top:4px" id="sim-duree-label">—</div>
      </div>
    </div>
    <div class="cards" id="sim-cards"></div>
  </section>
  <section>
    <h2><span class="num">03</span> <span data-i18n="sim_charts_title">Visualisation du scénario</span></h2>
    <div class="charts">
      <div class="chart-box"><h3 data-i18n="sim_chart_alea">Indice d'aléa simulé</h3><canvas id="cSimAlea" height="200"></canvas></div>
      <div class="chart-box"><h3 data-i18n="sim_chart_activity">Taux d'activité simulé — Forfaits Bellevarde</h3><canvas id="cSimTaux" height="200"></canvas></div>
    </div>
  </section>
</main>
</div>

<footer>TWICE Prototype &middot; <span data-i18n="footer_meteo">Météo</span> : Open-Meteo &middot; <span data-i18n="footer_map">Fond carte</span> : OpenStreetMap contributors &middot; Val d'Isère (STVI)</footer>

<script>
// ════════════════════════════════════════════════════════════
// TRADUCTIONS
// ════════════════════════════════════════════════════════════
var I18N = {{
  fr: {{
    subtitle:          "Interruptions de service liées aux intempéries · Domaine skiable",
    lang_label:        "🌐 Langue :",
    generated_at:      "Généré le {{val}} UTC",
    total_loss_header: "Perte totale fenêtre :",
    tab_realtime:      "📡 Temps réel & prévisions 7j",
    tab_simulation:    "🎛 Simulation scénario",
    sim_wind:          "Vent max (km/h)",
    sim_snow:          "Neige (cm/h)",
    sim_temp:          "Température (°C)",
    sim_duration:      "Durée (heures)",
    sim_run:           "▶ Simuler",
    sim_complete:      "Simulation complète.",
    section_summary:   "Synthèse des impacts",
    total_loss_all:    "Perte totale estimée — tous assets",
    analysis_window:   "Fenêtre d'analyse",
    section_map:       "Carte des impacts",
    section_charts:    "Visualisation temporelle",
    chart_wind_snow:   "Vent (km/h) & Neige (cm/h)",
    chart_alea:        "Indice d'aléa composite",
    chart_activity:    "Taux d'activité — Forfaits Bellevarde",
    chart_losses:      "Pertes cumulées — Forfaits Bellevarde",
    section_chrono:    "Chronologie détaillée — Forfaits Bellevarde",
    th_datetime:       "Date/Heure",
    th_wind:           "Vent",
    th_snow:           "Neige",
    th_temp:           "Temp.",
    th_index:          "Indice",
    th_lifts:          "Remontées (top 3)",
    th_access:         "Access.",
    th_rate:           "Taux",
    th_loss:           "Perte",
    section_hyp:       "Hypothèses du modèle",
    sim_map_title:     "Carte des impacts simulés",
    sim_assets_title:  "Impacts par asset",
    sim_total_loss:    "Perte totale simulée",
    sim_launch_hint:   "Lancez une simulation ▲",
    sim_duration_label:"Durée simulée",
    sim_charts_title:  "Visualisation du scénario",
    sim_chart_alea:    "Indice d'aléa simulé",
    sim_chart_activity:"Taux d'activité simulé — Forfaits Bellevarde",
    footer_meteo:      "Météo",
    footer_map:        "Fond carte",
    forecast:          "PRÉV.",
    estimated_loss:    "Perte estimée",
    stopped:           "À l'arrêt",
    degraded:          "Dégradées",
    min_access:        "Access. min",
    type_forfaits:     "Forfaits",
    type_restaurant:   "Restaurant",
    type_ecole_ski:    "École de ski",
    now_label:         "maintenant",
    popup_type:        "Type",
    popup_status:      "Statut",
    popup_sector:      "Secteur",
    popup_rate:        "Taux",
    popup_total_loss:  "Perte totale",
    popup_loss:        "Perte",
    status_open:       "ouvert",
    status_reduced:    "réduit",
    status_closed:     "fermé",
    h_phenomenon:      "h de phénomène",
    activity_rate:     "Taux activité",
    accessibility:     "Accessibilité",
    duration_impact:   "Durée impact",
  }},
  en: {{
    subtitle:          "Weather-related service interruptions · Ski resort",
    lang_label:        "🌐 Language:",
    generated_at:      "Generated on {{val}} UTC",
    total_loss_header: "Total window loss:",
    tab_realtime:      "📡 Live & 7-day forecast",
    tab_simulation:    "🎛 Scenario simulation",
    sim_wind:          "Max wind (km/h)",
    sim_snow:          "Snowfall (cm/h)",
    sim_temp:          "Temperature (°C)",
    sim_duration:      "Duration (hours)",
    sim_run:           "▶ Run simulation",
    sim_complete:      "Simulation complete.",
    section_summary:   "Impact summary",
    total_loss_all:    "Total estimated loss — all assets",
    analysis_window:   "Analysis window",
    section_map:       "Impact map",
    section_charts:    "Time series",
    chart_wind_snow:   "Wind (km/h) & Snow (cm/h)",
    chart_alea:        "Composite hazard index",
    chart_activity:    "Activity rate — Bellevarde ski passes",
    chart_losses:      "Cumulative losses — Bellevarde ski passes",
    section_chrono:    "Detailed timeline — Bellevarde ski passes",
    th_datetime:       "Date/Time",
    th_wind:           "Wind",
    th_snow:           "Snow",
    th_temp:           "Temp.",
    th_index:          "Index",
    th_lifts:          "Lifts (top 3)",
    th_access:         "Access.",
    th_rate:           "Rate",
    th_loss:           "Loss",
    section_hyp:       "Model assumptions",
    sim_map_title:     "Simulated impact map",
    sim_assets_title:  "Impact by asset",
    sim_total_loss:    "Total simulated loss",
    sim_launch_hint:   "Run a simulation ▲",
    sim_duration_label:"Simulated duration",
    sim_charts_title:  "Scenario visualisation",
    sim_chart_alea:    "Simulated hazard index",
    sim_chart_activity:"Simulated activity rate — Bellevarde ski passes",
    footer_meteo:      "Weather",
    footer_map:        "Map tiles",
    forecast:          "FCST.",
    estimated_loss:    "Estimated loss",
    stopped:           "Stopped",
    degraded:          "Degraded",
    min_access:        "Min. access.",
    type_forfaits:     "Ski passes",
    type_restaurant:   "Restaurant",
    type_ecole_ski:    "Ski school",
    now_label:         "now",
    popup_type:        "Type",
    popup_status:      "Status",
    popup_sector:      "Sector",
    popup_rate:        "Rate",
    popup_total_loss:  "Total loss",
    popup_loss:        "Loss",
    status_open:       "open",
    status_reduced:    "reduced",
    status_closed:     "closed",
    h_phenomenon:      "h of event",
    activity_rate:     "Activity rate",
    accessibility:     "Accessibility",
    duration_impact:   "Duration",
  }},
  lb: {{
    subtitle:          "Wiederbedéngte Serviceënnerbriechungen · Skigebitt",
    lang_label:        "🌐 Sprooch:",
    generated_at:      "Generéiert de {{val}} UTC",
    total_loss_header: "Total Verloscht Fënster:",
    tab_realtime:      "📡 Echtzäit & 7-Deeg Previsioun",
    tab_simulation:    "🎛 Szenario Simulatioun",
    sim_wind:          "Max Wand (km/h)",
    sim_snow:          "Schnéifall (cm/h)",
    sim_temp:          "Temperatur (°C)",
    sim_duration:      "Dauer (Stonnen)",
    sim_run:           "▶ Simuléieren",
    sim_complete:      "Simulatioun ofgeschloss.",
    section_summary:   "Impakt Zesummefaassung",
    total_loss_all:    "Geschätzten Gesamtverloscht — all Assetë",
    analysis_window:   "Analysefënster",
    section_map:       "Impaktkärt",
    section_charts:    "Zäitsäit Grafiken",
    chart_wind_snow:   "Wand (km/h) & Schnéi (cm/h)",
    chart_alea:        "Komposit Geforindex",
    chart_activity:    "Aktivitéitsquote — Bellevarde Skipassë",
    chart_losses:      "Kumuléiert Verloscht — Bellevarde Skipassë",
    section_chrono:    "Detailléiert Chronologie — Bellevarde Skipassë",
    th_datetime:       "Datum/Zäit",
    th_wind:           "Wand",
    th_snow:           "Schnéi",
    th_temp:           "Temp.",
    th_index:          "Index",
    th_lifts:          "Skillifte (top 3)",
    th_access:         "Accès",
    th_rate:           "Quote",
    th_loss:           "Verloscht",
    section_hyp:       "Modell Hypothesen",
    sim_map_title:     "Simuléiert Impaktkärt",
    sim_assets_title:  "Impakt pro Asset",
    sim_total_loss:    "Simuléierten Gesamtverloscht",
    sim_launch_hint:   "Simulatioun starten ▲",
    sim_duration_label:"Simuléiert Dauer",
    sim_charts_title:  "Szenario Visualiséierung",
    sim_chart_alea:    "Simuléierten Geforindex",
    sim_chart_activity:"Simuléiert Aktivitéitsquote — Bellevarde",
    footer_meteo:      "Wieder",
    footer_map:        "Kärtëgrondlag",
    forecast:          "PREV.",
    estimated_loss:    "Geschätzten Verloscht",
    stopped:           "Gestoppt",
    degraded:          "Verschlechtert",
    min_access:        "Min. Accès",
    type_forfaits:     "Skipassë",
    type_restaurant:   "Restaurant",
    type_ecole_ski:    "Skischoul",
    now_label:         "elo",
    popup_type:        "Typ",
    popup_status:      "Status",
    popup_sector:      "Secteur",
    popup_rate:        "Quote",
    popup_total_loss:  "Gesamtverloscht",
    popup_loss:        "Verloscht",
    status_open:       "op",
    status_reduced:    "reduzéiert",
    status_closed:     "zou",
    h_phenomenon:      "h Evenement",
    activity_rate:     "Aktivitéitsquote",
    accessibility:     "Accessibilitéit",
    duration_impact:   "Dauer",
  }},
  de: {{
    subtitle:          "Wetterbedingte Betriebsunterbrechungen · Skigebiet",
    lang_label:        "🌐 Sprache:",
    generated_at:      "Erstellt am {{val}} UTC",
    total_loss_header: "Gesamtverlust Zeitfenster:",
    tab_realtime:      "📡 Echtzeit & 7-Tage-Prognose",
    tab_simulation:    "🎛 Szenario-Simulation",
    sim_wind:          "Maximalwind (km/h)",
    sim_snow:          "Schneefall (cm/h)",
    sim_temp:          "Temperatur (°C)",
    sim_duration:      "Dauer (Stunden)",
    sim_run:           "▶ Simulieren",
    sim_complete:      "Simulation abgeschlossen.",
    section_summary:   "Zusammenfassung der Auswirkungen",
    total_loss_all:    "Geschätzter Gesamtverlust — alle Assets",
    analysis_window:   "Analysefenster",
    section_map:       "Auswirkungskarte",
    section_charts:    "Zeitliche Visualisierung",
    chart_wind_snow:   "Wind (km/h) & Schnee (cm/h)",
    chart_alea:        "Komposit-Gefahrenindex",
    chart_activity:    "Aktivitätsrate — Bellevarde Skipässe",
    chart_losses:      "Kumulierte Verluste — Bellevarde Skipässe",
    section_chrono:    "Detaillierte Chronologie — Bellevarde Skipässe",
    th_datetime:       "Datum/Uhrzeit",
    th_wind:           "Wind",
    th_snow:           "Schnee",
    th_temp:           "Temp.",
    th_index:          "Index",
    th_lifts:          "Lifte (top 3)",
    th_access:         "Zugängl.",
    th_rate:           "Rate",
    th_loss:           "Verlust",
    section_hyp:       "Modellannahmen",
    sim_map_title:     "Simulierte Auswirkungskarte",
    sim_assets_title:  "Auswirkungen pro Asset",
    sim_total_loss:    "Simulierter Gesamtverlust",
    sim_launch_hint:   "Simulation starten ▲",
    sim_duration_label:"Simulierte Dauer",
    sim_charts_title:  "Szenario-Visualisierung",
    sim_chart_alea:    "Simulierter Gefahrenindex",
    sim_chart_activity:"Simulierte Aktivitätsrate — Bellevarde",
    footer_meteo:      "Wetter",
    footer_map:        "Kartenhintergrund",
    forecast:          "PROG.",
    estimated_loss:    "Geschätzter Verlust",
    stopped:           "Gestoppt",
    degraded:          "Eingeschränkt",
    min_access:        "Min. Zugängl.",
    type_forfaits:     "Skipässe",
    type_restaurant:   "Restaurant",
    type_ecole_ski:    "Skischule",
    now_label:         "jetzt",
    popup_type:        "Typ",
    popup_status:      "Status",
    popup_sector:      "Sektor",
    popup_rate:        "Rate",
    popup_total_loss:  "Gesamtverlust",
    popup_loss:        "Verlust",
    status_open:       "offen",
    status_reduced:    "eingeschränkt",
    status_closed:     "geschlossen",
    h_phenomenon:      "h Ereignis",
    activity_rate:     "Aktivitätsrate",
    accessibility:     "Zugänglichkeit",
    duration_impact:   "Dauer",
  }}
}};

var currentLang = 'fr';

function t(key) {{
  return (I18N[currentLang] && I18N[currentLang][key]) || (I18N['fr'][key]) || key;
}}

function applyTranslations() {{
  // data-i18n : remplacement direct du textContent
  document.querySelectorAll('[data-i18n]').forEach(function(el) {{
    var key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  }});
  // data-i18n-tpl : template avec valeur injectée
  document.querySelectorAll('[data-i18n-tpl]').forEach(function(el) {{
    var key = el.getAttribute('data-i18n-tpl');
    var val = el.getAttribute('data-i18n-val') || '';
    el.textContent = t(key).replace('{{{{val}}}}', val);
  }});
  // Boutons langue
  document.querySelectorAll('.lang-btn').forEach(function(btn) {{
    btn.classList.remove('active');
    if(btn.getAttribute('onclick').includes("'"+currentLang+"'")) btn.classList.add('active');
  }});
  // Recharger les popups des marqueurs (ils contiennent du texte traduit)
  refreshMapPopups();
  refreshSimMapPopups();
  // Titre du graphique "maintenant"
  // (géré dynamiquement dans nowPlugin)
}}

function setLang(lang) {{
  currentLang = lang;
  document.documentElement.lang = lang;
  applyTranslations();
}}

// ════════════════════════════════════════════════════════════
// DONNÉES
// ════════════════════════════════════════════════════════════
var LABELS    = {labels_js};
var VENT      = {vent_js};
var NEIGE     = {neige_js};
var TEMP      = {temp_js};
var INDICES   = {indices_js};
var NOW       = {now_js};
var RESULTATS = {resultats_js};
var REMONTEES = {remontees_js};
var TAUX0     = {taux0_js};
var CUMUL0    = {cumul0_js};
var N         = LABELS.length;
var GEN_AT    = "{gen_at}";

var GRID = '#e9eaec';
var TF   = {{family:'Inter',size:10}};

var nowPlugin = {{
  id:'nowLine',
  afterDatasetsDraw:function(chart){{
    var ctx=chart.ctx, ca=chart.chartArea, sc=chart.scales;
    if(!ca||!sc.x) return;
    var x=sc.x.getPixelForValue(NOW);
    if(isNaN(x)) return;
    ctx.save();
    ctx.strokeStyle='#dc2626'; ctx.lineWidth=1.5; ctx.setLineDash([4,3]);
    ctx.beginPath(); ctx.moveTo(x,ca.top); ctx.lineTo(x,ca.bottom); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle='#dc2626'; ctx.font='bold 9px Inter'; ctx.textAlign='center';
    ctx.fillText(t('now_label'),x,ca.top-4);
    ctx.restore();
  }}
}};

var xCfg = {{
  ticks:{{font:TF,maxRotation:45,callback:function(v,i){{return i%12===0?LABELS[i]:'';}}}},
  grid:{{color:GRID}}
}};
function baseOpts(scales){{
  return {{responsive:true,maintainAspectRatio:true,animation:false,
    plugins:{{legend:{{labels:{{font:TF,boxWidth:12}}}}}},scales:scales}};
}}
function fmtEur(v){{return Math.round(v).toLocaleString('fr-FR')+' EUR';}}

// ════════════════════════════════════════════════════════════
// TABS
// ════════════════════════════════════════════════════════════
function switchTab(name, el){{
  document.querySelectorAll('.tab').forEach(function(t){{t.classList.remove('active');}});
  el.classList.add('active');
  document.querySelectorAll('.panel').forEach(function(p){{p.classList.remove('active');}});
  document.getElementById('panel-'+name).classList.add('active');
  var sb = document.getElementById('sim-bar');
  if(name==='simulation'){{
    sb.classList.add('active');
    if(mapSim) mapSim.invalidateSize();
  }} else {{
    sb.classList.remove('active');
    if(map) map.invalidateSize();
  }}
}}

// ════════════════════════════════════════════════════════════
// CARTE TEMPS RÉEL
// ════════════════════════════════════════════════════════════
var map = L.map('map').setView([45.448, 6.985], 13);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{
  attribution:'&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>',maxZoom:18
}}).addTo(map);

var ASSET_ICONS = {{'forfaits':'⛷','restaurant':'🍽','ecole_ski':'🎿'}};
function couleurTaux(taux){{return taux===0?'#dc2626':taux<1?'#f59e0b':'#16a34a';}}
function couleurStatut(s){{return s==='ferme'?'#dc2626':s==='reduit'?'#f59e0b':'#16a34a';}}

// On stocke les marqueurs pour pouvoir rafraîchir leurs popups
var rtLiftMarkers = [], rtAssetMarkers = [];

function buildLiftPopup(r, statut){{
  return '<b>'+r.nom+'</b><br>'+t('popup_type')+' : '+r.type+'<br>'+t('popup_status')+' : <b>'+t('status_'+statut)+'</b><br>'+t('popup_sector')+' : '+r.secteur;
}}
function buildAssetPopup(a, taux, perte){{
  return '<b>'+a.asset_nom+'</b><br>'+t('popup_rate')+' : <b>'+(taux*100).toFixed(0)+'%</b><br>'+t('popup_total_loss')+' : <b>'+fmtEur(perte)+'</b>';
}}

REMONTEES.forEach(function(r){{
  var statut='ouvert';
  if(RESULTATS.length>0 && RESULTATS[0].chronologie[NOW]){{
    statut=RESULTATS[0].chronologie[NOW].statuts_remontees[r.id]||'ouvert';
  }}
  var col=couleurStatut(statut);
  var icon=L.divIcon({{
    html:'<div style="background:'+col+';width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
    className:'',iconSize:[14,14],iconAnchor:[7,7]
  }});
  var m=L.marker([r.lat,r.lon],{{icon:icon}}).addTo(map);
  m.bindPopup(buildLiftPopup(r,statut));
  m._twiceStatut=statut; m._twiceR=r;
  rtLiftMarkers.push(m);
}});

RESULTATS.forEach(function(a){{
  var taux=a.chronologie[NOW]?a.chronologie[NOW].taux_activite:1;
  var col=couleurTaux(taux);
  var emoji=ASSET_ICONS[a.type]||'📍';
  var label=a.asset_nom.split('—')[0].trim();
  var icon=L.divIcon({{
    html:'<div style="background:white;border:2px solid '+col+';border-radius:6px;padding:2px 6px;font-size:11px;font-weight:600;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.3)">'+emoji+' '+label+'</div>',
    className:'',iconSize:null,iconAnchor:[0,12]
  }});
  var m=L.marker([a.lat,a.lon],{{icon:icon}}).addTo(map);
  m.bindPopup(buildAssetPopup(a,taux,a.perte_totale_eur));
  m._twicea=a; m._twiceTaux=taux;
  rtAssetMarkers.push(m);
}});

function refreshMapPopups(){{
  rtLiftMarkers.forEach(function(m){{m.setPopupContent(buildLiftPopup(m._twiceR,m._twiceStatut));}});
  rtAssetMarkers.forEach(function(m){{m.setPopupContent(buildAssetPopup(m._twicea,m._twiceTaux,m._twicea.perte_totale_eur));}});
}}

// ════════════════════════════════════════════════════════════
// GRAPHIQUES TEMPS RÉEL
// ════════════════════════════════════════════════════════════
new Chart(document.getElementById('cMeteo'),{{
  type:'bar',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[
    {{type:'line',label:'Vent (km/h)',data:VENT,borderColor:'#2563eb',borderWidth:2,pointRadius:0,yAxisID:'yV',fill:false}},
    {{type:'bar',label:'Neige (cm/h)',data:NEIGE,
      backgroundColor:LABELS.map(function(_,i){{return i<=NOW?'rgba(99,179,237,.7)':'rgba(99,179,237,.25)'}}),yAxisID:'yN'}}
  ]}},
  options:baseOpts({{x:xCfg,
    yV:{{type:'linear',position:'left',grid:{{color:GRID}},ticks:{{font:TF}},title:{{display:true,text:'km/h',font:{{size:9}}}}}},
    yN:{{type:'linear',position:'right',grid:{{drawOnChartArea:false}},ticks:{{font:TF}},title:{{display:true,text:'cm/h',font:{{size:9}}}}}}
  }})
}});
new Chart(document.getElementById('cAlea'),{{
  type:'line',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[{{label:"Index",data:INDICES,borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.08)',borderWidth:2,pointRadius:0,fill:true,tension:.3}}]}},
  options:baseOpts({{x:xCfg,y:{{min:0,max:1,grid:{{color:GRID}},ticks:{{font:TF}}}}}})
}});
new Chart(document.getElementById('cTaux'),{{
  type:'line',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[{{label:'%',data:TAUX0,borderColor:'#2563eb',backgroundColor:'rgba(37,99,235,.08)',borderWidth:2,pointRadius:0,fill:true,stepped:true}}]}},
  options:baseOpts({{x:xCfg,y:{{min:0,max:105,grid:{{color:GRID}},ticks:{{font:TF,callback:function(v){{return v+'%';}}}}}}}}),
}});
new Chart(document.getElementById('cPertes'),{{
  type:'line',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[{{label:'EUR',data:CUMUL0,borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.07)',borderWidth:2,pointRadius:0,fill:true,tension:.3}}]}},
  options:baseOpts({{x:xCfg,y:{{grid:{{color:GRID}},ticks:{{font:TF,callback:function(v){{return v.toLocaleString('fr-FR')+' EUR';}}}}}}}}),
}});

// ════════════════════════════════════════════════════════════
// CARTE SIMULATION
// ════════════════════════════════════════════════════════════
var mapSim = L.map('map-sim').setView([45.448,6.985],13);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{
  attribution:'&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>',maxZoom:18
}}).addTo(mapSim);
var simMarkersLayer = L.layerGroup().addTo(mapSim);
var simMarkersData = []; // pour rafraîchir les popups

function buildSimLiftPopup(r, ss){{
  return '<b>'+r.nom+'</b><br>'+t('popup_status')+' : <b>'+t('status_'+ss)+'</b>';
}}
function buildSimAssetPopup(a){{
  return '<b>'+a.nom+'</b><br>'+t('popup_rate')+' : <b>'+(a.taux*100).toFixed(0)+'%</b><br>'+t('popup_loss')+' : <b>'+fmtEur(a.perte)+'</b>';
}}
function refreshSimMapPopups(){{
  simMarkersData.forEach(function(item){{
    if(item.type==='lift') item.marker.setPopupContent(buildSimLiftPopup(item.r,item.ss));
    else item.marker.setPopupContent(buildSimAssetPopup(item.a));
  }});
}}

// ════════════════════════════════════════════════════════════
// SIMULATION
// ════════════════════════════════════════════════════════════
var STAT_SCORE={{'ouvert':1,'reduit':.5,'ferme':0}};
var chartSimAlea=null, chartSimTaux=null;

function indiceComposite(vent,neige,temp){{
  var iv=Math.min(vent/80,1), in_=Math.min(neige/20,1), ig=temp<-15?0.2:0;
  return Math.min(Math.max(iv,in_)+ig,1);
}}
function statutRemontee(r,idx){{
  if(idx>=r.seuil_fermeture) return 'ferme';
  if(idx>=r.seuil_impact)    return 'reduit';
  return 'ouvert';
}}
function tauxActivite(acc){{
  if(acc>=0.7) return 1;
  if(acc<=0.4) return 0;
  return (acc-0.4)/0.3;
}}
function accSim(asset, statuts){{
  var secteurRem=REMONTEES.filter(function(r){{return r.secteur===asset.secteur;}});
  if(asset.secteur==='station') secteurRem=REMONTEES;
  if(secteurRem.length===0) secteurRem=REMONTEES;
  var score=0, poids=0;
  secteurRem.forEach(function(r){{
    var p=1;
    var sc=STAT_SCORE[statuts[r.id]];
    score+=p*(sc!==undefined?sc:1);
    poids+=p;
  }});
  return poids>0?score/poids:1;
}}

function runSimulation(){{
  var vent  = parseFloat(document.getElementById('sim-vent').value)||0;
  var neige = parseFloat(document.getElementById('sim-neige').value)||0;
  var temp  = parseFloat(document.getElementById('sim-temp').value)||0;
  var duree = parseInt(document.getElementById('sim-duree').value)||12;

  var idx = indiceComposite(vent,neige,temp);
  var statuts={{}};
  REMONTEES.forEach(function(r){{statuts[r.id]=statutRemontee(r,idx);}});

  // Série temporelle
  var simLabels=[], simIndices=[];
  for(var i=0;i<6;i++){{simLabels.push('h\u2212'+(6-i));simIndices.push(0);}}
  for(var i=0;i<duree;i++){{simLabels.push('h+'+(i+1));simIndices.push(parseFloat(idx.toFixed(3)));}}
  for(var i=0;i<6;i++){{simLabels.push('h+'+(duree+i+1));simIndices.push(0);}}

  // Calcul pertes
  var totalPerte=0;
  var simAssets=RESULTATS.map(function(a){{
    var acc=accSim(a,statuts);
    var taux=tauxActivite(acc);
    var perte=(a.ca_jour_eur/10)*(1-taux)*duree;
    totalPerte+=perte;
    return {{nom:a.asset_nom,type:a.type,secteur:a.secteur,lat:a.lat,lon:a.lon,
             taux:taux,perte:perte,acc:acc,asset_id:a.asset_id}};
  }});

  // KPI
  document.getElementById('sim-perte-total').textContent=fmtEur(totalPerte);
  document.getElementById('sim-duree-label').textContent=duree+' '+t('h_phenomenon');

  // Cards
  var html='';
  simAssets.forEach(function(a){{
    var col=couleurTaux(a.taux);
    var emoji=ASSET_ICONS[a.type]||'📍';
    html+='<div class="card" style="border-left-color:'+col+'">';
    html+='<div class="card-type">'+t('type_'+a.type)+'</div>';
    html+='<div class="card-nom">'+a.nom+'</div>';
    html+='<div class="kpis">';
    html+='<div class="kpi"><div class="kv red">'+fmtEur(a.perte)+'</div><div class="kl">'+t('estimated_loss')+'</div></div>';
    html+='<div class="kpi"><div class="kv">'+(a.taux*100).toFixed(0)+'%</div><div class="kl">'+t('activity_rate')+'</div></div>';
    html+='<div class="kpi"><div class="kv">'+(a.acc*100).toFixed(0)+'%</div><div class="kl">'+t('accessibility')+'</div></div>';
    html+='<div class="kpi"><div class="kv">'+duree+'h</div><div class="kl">'+t('duration_impact')+'</div></div>';
    html+='</div></div>';
  }});
  document.getElementById('sim-cards').innerHTML=html;

  // Mise à jour carte simulation
  simMarkersLayer.clearLayers();
  simMarkersData=[];

  REMONTEES.forEach(function(r){{
    var ss=statuts[r.id]||'ouvert';
    var col=couleurStatut(ss);
    var icon=L.divIcon({{
      html:'<div style="background:'+col+';width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
      className:'',iconSize:[14,14],iconAnchor:[7,7]
    }});
    var m=L.marker([r.lat,r.lon],{{icon:icon}}).addTo(simMarkersLayer);
    m.bindPopup(buildSimLiftPopup(r,ss));
    simMarkersData.push({{type:'lift',marker:m,r:r,ss:ss}});
  }});

  simAssets.forEach(function(a){{
    var col=couleurTaux(a.taux);
    var emoji=ASSET_ICONS[a.type]||'📍';
    var label=a.nom.split('—')[0].trim();
    var icon=L.divIcon({{
      html:'<div style="background:white;border:2px solid '+col+';border-radius:6px;padding:2px 6px;font-size:11px;font-weight:600;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.3)">'+emoji+' '+label+'</div>',
      className:'',iconSize:null,iconAnchor:[0,12]
    }});
    var m=L.marker([a.lat,a.lon],{{icon:icon}}).addTo(simMarkersLayer);
    m.bindPopup(buildSimAssetPopup(a));
    simMarkersData.push({{type:'asset',marker:m,a:a}});
  }});

  mapSim.invalidateSize();

  // Graphiques
  var simTaux=simIndices.map(function(ix){{
    var ss=statutRemontee(REMONTEES[0],ix);
    return tauxActivite(STAT_SCORE[ss])*100;
  }});

  if(chartSimAlea){{chartSimAlea.destroy();chartSimAlea=null;}}
  chartSimAlea=new Chart(document.getElementById('cSimAlea'),{{
    type:'line',
    data:{{labels:simLabels,datasets:[{{label:t('chart_alea'),data:simIndices,
      borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.1)',borderWidth:2,pointRadius:0,fill:true,tension:.1}}]}},
    options:{{responsive:true,maintainAspectRatio:true,animation:false,
      plugins:{{legend:{{labels:{{font:TF,boxWidth:12}}}}}},
      scales:{{x:{{ticks:{{font:TF,maxRotation:45}},grid:{{color:GRID}}}},y:{{min:0,max:1,grid:{{color:GRID}},ticks:{{font:TF}}}}}}}}
  }});

  if(chartSimTaux){{chartSimTaux.destroy();chartSimTaux=null;}}
  chartSimTaux=new Chart(document.getElementById('cSimTaux'),{{
    type:'line',
    data:{{labels:simLabels,datasets:[{{label:'%',data:simTaux,
      borderColor:'#2563eb',backgroundColor:'rgba(37,99,235,.08)',borderWidth:2,pointRadius:0,fill:true,stepped:true}}]}},
    options:{{responsive:true,maintainAspectRatio:true,animation:false,
      plugins:{{legend:{{labels:{{font:TF,boxWidth:12}}}}}},
      scales:{{x:{{ticks:{{font:TF,maxRotation:45}},grid:{{color:GRID}}}},
               y:{{min:0,max:105,grid:{{color:GRID}},ticks:{{font:TF,callback:function(v){{return v+'%';}}}}}}}}}}
  }});

  document.getElementById('sim-status').textContent=t('sim_complete');
}}

// ════════════════════════════════════════════════════════════
// INIT : appliquer la langue par défaut
// ════════════════════════════════════════════════════════════
applyTranslations();
</script>
</body>
</html>"""


def main():
    print("Chargement resultats...")
    with open("outputs/resultats_latest.json", encoding="utf-8") as f:
        data = json.load(f)
    print("Generation rapport HTML...")
    html = generate(data)
    os.makedirs("docs", exist_ok=True)
    Path("outputs/rapport.html").write_text(html, encoding="utf-8")
    Path("docs/rapport.html").write_text(html, encoding="utf-8")
    print(f"Rapport genere ({len(html)//1024} KB) : outputs/rapport.html + docs/rapport.html")


if __name__ == "__main__":
    main()
