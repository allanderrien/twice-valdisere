"""
TWICE — Generateur rapport HTML
Val d'Isere : carte Leaflet + graphiques + module simulation JS
Carte simulation initialisee au chargement (panel visible=hidden via CSS visibility)
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
        td   = fmt_date(h["time"])
        bgs  = " ".join(badge_statut(v2) for v2 in list(h["statuts_remontees"].values())[:3])
        fc   = ' <small style="color:#2563eb;font-weight:600">PREV.</small>' if h["is_forecast"] else ""
        if h["taux_activite"]==0:    bg='style="background:#fff5f5"'
        elif h["taux_activite"]<1:   bg='style="background:#fffbeb"'
        elif h["is_forecast"]:       bg='style="background:#f0f9ff"'
        else:                        bg=""
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
          <div class="card-type">{s['type'].replace('_',' ')}</div>
          <div class="card-nom">{s['asset_nom']}</div>
          <div class="kpis">
            <div class="kpi"><div class="kv red">{fmt_eur(s['perte_totale_eur'])}</div><div class="kl">Perte estimée</div></div>
            <div class="kpi"><div class="kv">{s['heures_arret']}h</div><div class="kl">À l'arrêt</div></div>
            <div class="kpi"><div class="kv">{s['heures_degradees']}h</div><div class="kl">Dégradées</div></div>
            <div class="kpi"><div class="kv">{s['accessibilite_min']:.0%}</div><div class="kl">Access. min</div></div>
          </div>
        </div>"""

    hyp_html = "".join(f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in hyps.items())

    # Séries graphiques
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

header{{background:#1e2433;color:#fff;padding:22px 40px;display:flex;justify-content:space-between;align-items:center}}
header h1{{font-size:20px;font-weight:600}}
header .sub{{color:#8892a4;font-size:12px;margin-top:3px}}
.badge-proto{{background:#2563eb;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:12px;letter-spacing:.5px}}
.meta{{text-align:right;font-size:12px;color:#8892a4}}

.tabs{{background:#fff;border-bottom:1px solid #e4e6ea;padding:0 40px;display:flex}}
.tab{{padding:14px 24px;cursor:pointer;font-size:13px;font-weight:500;color:#6b7280;border-bottom:2px solid transparent;transition:all .2s}}
.tab.active{{color:#2563eb;border-bottom-color:#2563eb}}
.tab:hover:not(.active){{color:#374151}}

/* Les deux panels sont toujours dans le DOM et rendus,
   on cache/montre uniquement avec visibility+height */
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

.kpi-total{{background:linear-gradient(135deg,#1e2433,#2563eb);color:#fff;border-radius:10px;padding:20px 28px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center}}
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
    <div class="sub">Interruptions de service li&eacute;es aux intempéries &middot; Domaine skiable</div>
  </div>
  <div class="meta">
    <div class="badge-proto">PROTOTYPE</div>
    <div style="margin-top:6px">Généré le {gen_at} UTC</div>
    <div style="margin-top:2px;color:#fff;font-size:11px">Perte totale fenêtre : <b>{fmt_eur(perte_totale)}</b></div>
  </div>
</header>

<div class="tabs">
  <div class="tab active" onclick="switchTab('realtime',this)">📡 Temps réel &amp; prévisions 7j</div>
  <div class="tab" onclick="switchTab('simulation',this)">🎛 Simulation scénario</div>
</div>

<div class="sim-bar" id="sim-bar">
  <div class="sim-field"><label>Vent max (km/h)</label><input type="number" id="sim-vent" value="65" min="0" max="150"></div>
  <div class="sim-field"><label>Neige (cm/h)</label><input type="number" id="sim-neige" value="5" min="0" max="50" step="0.5"></div>
  <div class="sim-field"><label>Température (°C)</label><input type="number" id="sim-temp" value="-8" min="-30" max="5"></div>
  <div class="sim-field"><label>Durée (heures)</label><input type="number" id="sim-duree" value="12" min="1" max="72"></div>
  <button class="btn btn-primary" onclick="runSimulation()">▶ Simuler</button>
  <div id="sim-status" style="font-size:12px;color:#6b7280;align-self:center"></div>
</div>

<!-- PANEL TEMPS REEL -->
<div id="panel-realtime" class="panel active">
<main>
  <section>
    <h2><span class="num">01</span> Synthèse des impacts — {n}h ({n//24}j)</h2>
    <div class="kpi-total">
      <div><div class="label">Perte totale estimée — tous assets</div><div class="value">{fmt_eur(perte_totale)}</div></div>
      <div style="text-align:right"><div class="label">Fenêtre d'analyse</div><div style="font-size:15px;font-weight:600;margin-top:4px">{n}h ({n//24}j)</div></div>
    </div>
    <div class="cards">{cards_html}</div>
  </section>
  <section>
    <h2><span class="num">02</span> Carte des impacts</h2>
    <div id="map"></div>
  </section>
  <section>
    <h2><span class="num">03</span> Visualisation temporelle</h2>
    <div class="charts">
      <div class="chart-box"><h3>Vent (km/h) &amp; Neige (cm/h)</h3><canvas id="cMeteo" height="200"></canvas></div>
      <div class="chart-box"><h3>Indice d'aléa composite</h3><canvas id="cAlea" height="200"></canvas></div>
      <div class="chart-box"><h3>Taux d'activité — Forfaits Bellevarde</h3><canvas id="cTaux" height="200"></canvas></div>
      <div class="chart-box"><h3>Pertes cumulées — Forfaits Bellevarde</h3><canvas id="cPertes" height="200"></canvas></div>
    </div>
  </section>
  <section>
    <h2><span class="num">04</span> Chronologie détaillée — Forfaits Bellevarde</h2>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Date/Heure</th><th>Vent</th><th>Neige</th><th>Temp.</th>
          <th>Indice</th><th>Remontées (top 3)</th><th>Access.</th><th>Taux</th>
          <th style="text-align:right">Perte</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </section>
  <section>
    <h2><span class="num">05</span> Hypothèses du modèle</h2>
    <div class="tbl-wrap"><table class="hyp-tbl">{hyp_html}</table></div>
  </section>
</main>
</div>

<!-- PANEL SIMULATION — toujours rendu dans le DOM, carte initialisée au chargement -->
<div id="panel-simulation" class="panel">
<main>
  <section>
    <h2><span class="num">01</span> Carte des impacts simulés</h2>
    <div id="map-sim"></div>
  </section>
  <section>
    <h2><span class="num">02</span> Impacts par asset</h2>
    <div class="kpi-total">
      <div><div class="label">Perte totale simulée</div><div class="value" id="sim-perte-total">Lancez une simulation ▲</div></div>
      <div style="text-align:right"><div class="label">Durée simulée</div><div style="font-size:15px;font-weight:600;margin-top:4px" id="sim-duree-label">—</div></div>
    </div>
    <div class="cards" id="sim-cards"></div>
  </section>
  <section>
    <h2><span class="num">03</span> Visualisation du scénario</h2>
    <div class="charts">
      <div class="chart-box"><h3>Indice d'aléa simulé</h3><canvas id="cSimAlea" height="200"></canvas></div>
      <div class="chart-box"><h3>Taux d'activité simulé — Forfaits Bellevarde</h3><canvas id="cSimTaux" height="200"></canvas></div>
    </div>
  </section>
</main>
</div>

<footer>TWICE Prototype &middot; Météo : Open-Meteo &middot; Fond carte : OpenStreetMap contributors &middot; Station : Val d'Isère (STVI)</footer>

<script>
// ── Données injectées ──────────────────────────────────────
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

var GRID = '#e9eaec';
var TF   = {{family:'Inter',size:10}};

// ── Plugin ligne "maintenant" ──────────────────────────────
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
    ctx.fillText('maintenant',x,ca.top-4);
    ctx.restore();
  }}
}};

var xCfg = {{
  ticks:{{font:TF,maxRotation:45,callback:function(v,i){{return i%12===0?LABELS[i]:'';}}}},
  grid:{{color:GRID}}
}};

function baseOpts(scales){{
  return {{
    responsive:true,maintainAspectRatio:true,animation:false,
    plugins:{{legend:{{labels:{{font:TF,boxWidth:12}}}}}},
    scales:scales
  }};
}}

function fmtEur(v){{
  return Math.round(v).toLocaleString('fr-FR')+' EUR';
}}

// ── Tabs ──────────────────────────────────────────────────
function switchTab(name, el){{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  var sb = document.getElementById('sim-bar');
  if(name==='simulation'){{
    sb.classList.add('active');
    // La carte est deja initialisee : on force juste un recalcul de taille
    if(mapSim) mapSim.invalidateSize();
  }} else {{
    sb.classList.remove('active');
    if(map) map.invalidateSize();
  }}
}}

// ── CARTE TEMPS REEL ──────────────────────────────────────
var map = L.map('map').setView([45.448, 6.985], 13);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{
  attribution:'&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',maxZoom:18
}}).addTo(map);

var ASSET_ICONS = {{'forfaits':'⛷','restaurant':'🍽','ecole_ski':'🎿'}};

function couleurTaux(taux){{
  if(taux===0) return '#dc2626';
  if(taux<1)   return '#f59e0b';
  return '#16a34a';
}}

function couleurStatutStr(s){{
  return s==='ferme'?'#dc2626':s==='reduit'?'#f59e0b':'#16a34a';
}}

// Marqueurs remontees — temps reel
REMONTEES.forEach(function(r){{
  var statut = 'ouvert';
  if(RESULTATS.length>0 && RESULTATS[0].chronologie[NOW]){{
    statut = RESULTATS[0].chronologie[NOW].statuts_remontees[r.id] || 'ouvert';
  }}
  var col  = couleurStatutStr(statut);
  var icon = L.divIcon({{
    html:'<div style="background:'+col+';width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
    className:'',iconSize:[14,14],iconAnchor:[7,7]
  }});
  L.marker([r.lat,r.lon],{{icon:icon}}).addTo(map)
   .bindPopup('<b>'+r.nom+'</b><br>Type : '+r.type+'<br>Statut : <b>'+statut+'</b><br>Secteur : '+r.secteur);
}});

// Marqueurs assets — temps reel
RESULTATS.forEach(function(a){{
  var taux  = a.chronologie[NOW] ? a.chronologie[NOW].taux_activite : 1;
  var col   = couleurTaux(taux);
  var emoji = ASSET_ICONS[a.type]||'📍';
  var label = a.asset_nom.split('—')[0].trim();
  var icon  = L.divIcon({{
    html:'<div style="background:white;border:2px solid '+col+';border-radius:6px;padding:2px 6px;font-size:11px;font-weight:600;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.3)">'+emoji+' '+label+'</div>',
    className:'',iconSize:null,iconAnchor:[0,12]
  }});
  L.marker([a.lat,a.lon],{{icon:icon}}).addTo(map)
   .bindPopup('<b>'+a.asset_nom+'</b><br>Taux : <b>'+(taux*100).toFixed(0)+'%</b><br>Perte totale : <b>'+fmtEur(a.perte_totale_eur)+'</b>');
}});

// ── CARTE SIMULATION — initialisee maintenant, panel caché via CSS ──
// Le div map-sim est dans le DOM mais son panel a visibility:hidden et height:0.
// On utilise un conteneur invisible de meme taille pour forcer Leaflet
// a calculer ses dimensions correctement.
var mapSim = L.map('map-sim').setView([45.448,6.985],13);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{
  attribution:'&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',maxZoom:18
}}).addTo(mapSim);

// Couche de marqueurs simulation (rechargée à chaque simulation)
var simMarkersLayer = L.layerGroup().addTo(mapSim);

// ── Graphiques temps reel ─────────────────────────────────
new Chart(document.getElementById('cMeteo'),{{
  type:'bar',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[
    {{type:'line',label:'Vent (km/h)',data:VENT,borderColor:'#2563eb',borderWidth:2,pointRadius:0,yAxisID:'yV',fill:false}},
    {{type:'bar',label:'Neige (cm/h)',data:NEIGE,
      backgroundColor:LABELS.map((_,i)=>i<=NOW?'rgba(99,179,237,.7)':'rgba(99,179,237,.25)'),yAxisID:'yN'}}
  ]}},
  options:baseOpts({{
    x:xCfg,
    yV:{{type:'linear',position:'left',grid:{{color:GRID}},ticks:{{font:TF}},title:{{display:true,text:'km/h',font:{{size:9}}}}}},
    yN:{{type:'linear',position:'right',grid:{{drawOnChartArea:false}},ticks:{{font:TF}},title:{{display:true,text:'cm/h',font:{{size:9}}}}}}
  }})
}});

new Chart(document.getElementById('cAlea'),{{
  type:'line',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[{{
    label:"Indice d'alea [0-1]",data:INDICES,
    borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.08)',
    borderWidth:2,pointRadius:0,fill:true,tension:.3
  }}]}},
  options:baseOpts({{x:xCfg,y:{{min:0,max:1,grid:{{color:GRID}},ticks:{{font:TF}}}}}}),
}});

new Chart(document.getElementById('cTaux'),{{
  type:'line',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[{{
    label:'Taux activite (%)',data:TAUX0,
    borderColor:'#2563eb',backgroundColor:'rgba(37,99,235,.08)',
    borderWidth:2,pointRadius:0,fill:true,stepped:true
  }}]}},
  options:baseOpts({{x:xCfg,y:{{min:0,max:105,grid:{{color:GRID}},ticks:{{font:TF,callback:function(v){{return v+'%';}}}}}}}}),
}});

new Chart(document.getElementById('cPertes'),{{
  type:'line',plugins:[nowPlugin],
  data:{{labels:LABELS,datasets:[{{
    label:'Pertes cumulees',data:CUMUL0,
    borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.07)',
    borderWidth:2,pointRadius:0,fill:true,tension:.3
  }}]}},
  options:baseOpts({{x:xCfg,y:{{grid:{{color:GRID}},ticks:{{font:TF,callback:function(v){{return v.toLocaleString('fr-FR')+' EUR';}}}}}}}}),
}});

// ── MODULE SIMULATION ─────────────────────────────────────
var chartSimAlea = null, chartSimTaux = null;

var STAT_SCORE = {{'ouvert':1,'reduit':.5,'ferme':0}};

function indiceComposite(vent,neige,temp){{
  var iv=Math.min(vent/80,1), in_=Math.min(neige/20,1), ig=temp<-15?0.2:0;
  return Math.min(Math.max(iv,in_)+ig,1);
}}

function statutRemontee(r,idx){{
  if(idx>=r.seuil_fermeture) return 'ferme';
  if(idx>=r.seuil_impact)    return 'reduit';
  return 'ouvert';
}}

function accSim(asset, statuts){{
  // Recalcule l'accessibilite a partir des remontees_critiques de l'asset
  // On derive les poids depuis la chronologie[0] du meme asset dans RESULTATS
  var res = RESULTATS.find(function(r){{return r.asset_id===asset.asset_id;}});
  if(!res) return 1;
  var h0  = res.chronologie[0];
  if(!h0) return 1;
  // Construire poids depuis les statuts du 1er point et l'accessibilite connue
  // Approche : reproduire la ponderation via les remontees connues
  // On calcule directement via les secteurs
  var secteurRem = REMONTEES.filter(function(r){{return r.secteur===asset.secteur;}});
  if(asset.secteur==='station') secteurRem = REMONTEES; // ESF
  if(secteurRem.length===0) secteurRem = REMONTEES;
  var score=0, poids=0;
  secteurRem.forEach(function(r){{
    var p = 1; // poids uniforme si pas d'info precise
    var sc = STAT_SCORE[statuts[r.id]]; score += p * (sc !== undefined ? sc : 1);
    poids += p;
  }});
  return poids>0 ? score/poids : 1;
}}

function tauxActivite(acc){{
  if(acc>=0.7) return 1;
  if(acc<=0.4) return 0;
  return (acc-0.4)/0.3;
}}

function runSimulation(){{
  var vent  = parseFloat(document.getElementById('sim-vent').value)||0;
  var neige = parseFloat(document.getElementById('sim-neige').value)||0;
  var temp  = parseFloat(document.getElementById('sim-temp').value)||0;
  var duree = parseInt(document.getElementById('sim-duree').value)||12;

  var idx = indiceComposite(vent,neige,temp);

  // Série temporelle : 6h avant (normal) + duree h (scenario) + 6h après (retour)
  var simLabels=[], simIndices=[];
  for(var i=0;i<6;i++){{ simLabels.push('h\u2212'+(6-i)); simIndices.push(0); }}
  for(var i=0;i<duree;i++){{ simLabels.push('h+'+(i+1)); simIndices.push(parseFloat(idx.toFixed(3))); }}
  for(var i=0;i<6;i++){{ simLabels.push('h+'+(duree+i+1)); simIndices.push(0); }}

  // Statuts remontees sous le scenario
  var statuts = {{}};
  REMONTEES.forEach(function(r){{ statuts[r.id] = statutRemontee(r,idx); }});

  // Calcul pertes
  var totalPerte = 0;
  var simAssets = RESULTATS.map(function(a){{
    var acc  = accSim(a, statuts);
    var taux = tauxActivite(acc);
    var perte = (a.ca_jour_eur/10) * (1-taux) * duree;
    totalPerte += perte;
    return {{nom:a.asset_nom,type:a.type,secteur:a.secteur,lat:a.lat,lon:a.lon,
             taux:taux,perte:perte,acc:acc,asset_id:a.asset_id}};
  }});

  // KPI total
  document.getElementById('sim-perte-total').textContent = fmtEur(totalPerte);
  document.getElementById('sim-duree-label').textContent = duree+'h de phénomène';

  // Cards
  var html = '';
  simAssets.forEach(function(a){{
    var col = a.taux===0?'#dc2626':a.taux<1?'#f59e0b':'#16a34a';
    html += '<div class="card" style="border-left-color:'+col+'">';
    html += '<div class="card-type">'+a.type.replace('_',' ')+'</div>';
    html += '<div class="card-nom">'+a.nom+'</div>';
    html += '<div class="kpis">';
    html += '<div class="kpi"><div class="kv red">'+fmtEur(a.perte)+'</div><div class="kl">Perte estimée</div></div>';
    html += '<div class="kpi"><div class="kv">'+(a.taux*100).toFixed(0)+'%</div><div class="kl">Taux activité</div></div>';
    html += '<div class="kpi"><div class="kv">'+(a.acc*100).toFixed(0)+'%</div><div class="kl">Accessibilité</div></div>';
    html += '<div class="kpi"><div class="kv">'+duree+'h</div><div class="kl">Durée impact</div></div>';
    html += '</div></div>';
  }});
  document.getElementById('sim-cards').innerHTML = html;

  // Mise a jour carte simulation
  simMarkersLayer.clearLayers();

  REMONTEES.forEach(function(r){{
    var ss  = statuts[r.id]||'ouvert';
    var col = couleurStatutStr(ss);
    var icon = L.divIcon({{
      html:'<div style="background:'+col+';width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
      className:'',iconSize:[14,14],iconAnchor:[7,7]
    }});
    L.marker([r.lat,r.lon],{{icon:icon}}).addTo(simMarkersLayer)
     .bindPopup('<b>'+r.nom+'</b><br>Statut simulé : <b>'+ss+'</b>');
  }});

  simAssets.forEach(function(a){{
    var col   = couleurTaux(a.taux);
    var emoji = ASSET_ICONS[a.type]||'📍';
    var label = a.nom.split('—')[0].trim();
    var icon  = L.divIcon({{
      html:'<div style="background:white;border:2px solid '+col+';border-radius:6px;padding:2px 6px;font-size:11px;font-weight:600;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.3)">'+emoji+' '+label+'</div>',
      className:'',iconSize:null,iconAnchor:[0,12]
    }});
    L.marker([a.lat,a.lon],{{icon:icon}}).addTo(simMarkersLayer)
     .bindPopup('<b>'+a.nom+'</b><br>Taux : <b>'+(a.taux*100).toFixed(0)+'%</b><br>Perte : <b>'+fmtEur(a.perte)+'</b>');
  }});

  mapSim.invalidateSize();

  // Graphiques simulation
  var simTauxBellevarde = simIndices.map(function(ix){{
    var ss = statutRemontee(REMONTEES[0],ix); // Olympique = proxy Bellevarde
    return tauxActivite(STAT_SCORE[ss])*100;
  }});

  if(chartSimAlea){{ chartSimAlea.destroy(); chartSimAlea=null; }}
  chartSimAlea = new Chart(document.getElementById('cSimAlea'),{{
    type:'line',
    data:{{labels:simLabels,datasets:[{{
      label:"Indice d'alea",data:simIndices,
      borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.1)',
      borderWidth:2,pointRadius:0,fill:true,tension:.1
    }}]}},
    options:{{
      responsive:true,maintainAspectRatio:true,animation:false,
      plugins:{{legend:{{labels:{{font:TF,boxWidth:12}}}}}},
      scales:{{
        x:{{ticks:{{font:TF,maxRotation:45}},grid:{{color:GRID}}}},
        y:{{min:0,max:1,grid:{{color:GRID}},ticks:{{font:TF}}}}
      }}
    }}
  }});

  if(chartSimTaux){{ chartSimTaux.destroy(); chartSimTaux=null; }}
  chartSimTaux = new Chart(document.getElementById('cSimTaux'),{{
    type:'line',
    data:{{labels:simLabels,datasets:[{{
      label:'Taux activite (%)',data:simTauxBellevarde,
      borderColor:'#2563eb',backgroundColor:'rgba(37,99,235,.08)',
      borderWidth:2,pointRadius:0,fill:true,stepped:true
    }}]}},
    options:{{
      responsive:true,maintainAspectRatio:true,animation:false,
      plugins:{{legend:{{labels:{{font:TF,boxWidth:12}}}}}},
      scales:{{
        x:{{ticks:{{font:TF,maxRotation:45}},grid:{{color:GRID}}}},
        y:{{min:0,max:105,grid:{{color:GRID}},ticks:{{font:TF,callback:function(v){{return v+'%';}}}}}}
      }}
    }}
  }});

  document.getElementById('sim-status').textContent = 'Simulation complète.';
}}
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
