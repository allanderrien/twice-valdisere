"""
TWICE — Digital Twin Val d'Isere
Module temps reel : Open-Meteo -> JSON
Chaine : meteo -> indice_alea -> statut_remontee -> accessibilite_secteur -> pertes
"""

import json
import requests
from datetime import datetime, timezone

# ============================================================
# PARAMETRES
# ============================================================
LAT           = 45.4478
LON           = 6.9797
PAST_DAYS     = 2
FORECAST_DAYS = 7

# Seuils alea (indices 0-1)
# Indice composite = max(vent/80, neige/20, 0 si temp>-2 sinon 0)
# Remontee fermee si indice >= seuil_fermeture
# Remontee reduite si indice >= seuil_impact

# ============================================================
# RESEAU DE REMONTEES (remontees d'acces critiques uniquement)
# ============================================================
REMONTEES = [
    {
        "id":              "olympique",
        "nom":             "Téléphérique de l'Olympique",
        "type":            "telepherique",
        "secteur":         "bellevarde",
        "lat":             45.4502,
        "lon":             6.9726,
        "altitude_aval":   1850,
        "altitude_amont":  2689,
        "seuil_impact":    0.45,   # vent ~36 km/h ou neige ~9 cm/h
        "seuil_fermeture": 0.75,   # vent ~60 km/h ou neige ~15 cm/h
        "poids_forfait":   4,      # contribution relative au CA forfaits
    },
    {
        "id":              "funival",
        "nom":             "Funival (La Daille)",
        "type":            "funiculaire",
        "secteur":         "bellevarde",
        "lat":             45.4558,
        "lon":             6.9635,
        "altitude_aval":   1785,
        "altitude_amont":  2660,
        "seuil_impact":    0.35,   # moins sensible au vent (souterrain)
        "seuil_fermeture": 0.85,   # ferme rarement
        "poids_forfait":   3,
    },
    {
        "id":              "solaise",
        "nom":             "Télécabine de Solaise",
        "type":            "telecabine",
        "secteur":         "solaise",
        "lat":             45.4468,
        "lon":             6.9768,
        "altitude_aval":   1838,
        "altitude_amont":  2555,
        "seuil_impact":    0.40,
        "seuil_fermeture": 0.72,
        "poids_forfait":   3,
    },
    {
        "id":              "fornet",
        "nom":             "Téléphérique du Fornet",
        "type":            "telepherique",
        "secteur":         "fornet",
        "lat":             45.4623,
        "lon":             7.0052,
        "altitude_aval":   1900,
        "altitude_amont":  2330,
        "seuil_impact":    0.40,
        "seuil_fermeture": 0.68,
        "poids_forfait":   2,
    },
    {
        "id":              "daille",
        "nom":             "Télécabine de La Daille",
        "type":            "telecabine",
        "secteur":         "bellevarde",
        "lat":             45.4548,
        "lon":             6.9648,
        "altitude_aval":   1785,
        "altitude_amont":  2100,
        "seuil_impact":    0.42,
        "seuil_fermeture": 0.70,
        "poids_forfait":   2,
    },
]

# ============================================================
# MODULES DE REVENUS (assets)
# ============================================================
# CA en EUR/jour en pic de saison (fevrier)
# Val d'Isere : ~170M EUR/saison, ~1.4M EUR/jour en pic
# Repartition estimee : forfaits 55%, restos 20%, ESF 15%, hebergement 10%
ASSETS = [
    # --- FORFAITS (revenus directs STVI) ---
    {
        "id":          "forfaits_bellevarde",
        "nom":         "Forfaits — Secteur Bellevarde",
        "type":        "forfaits",
        "secteur":     "bellevarde",
        "lat":         45.4502,
        "lon":         6.9726,
        "ca_jour":     330000,
        "remontees_critiques": {"olympique": 4, "funival": 3, "daille": 2},
    },
    {
        "id":          "forfaits_solaise",
        "nom":         "Forfaits — Secteur Solaise",
        "type":        "forfaits",
        "secteur":     "solaise",
        "lat":         45.4400,
        "lon":         6.9810,
        "ca_jour":     230000,
        "remontees_critiques": {"solaise": 5},
    },
    {
        "id":          "forfaits_fornet",
        "nom":         "Forfaits — Secteur Fornet/Pissaillas",
        "type":        "forfaits",
        "secteur":     "fornet",
        "lat":         45.4623,
        "lon":         7.0052,
        "ca_jour":     110000,
        "remontees_critiques": {"fornet": 5},
    },
    # --- RESTAURANTS D'ALTITUDE ---
    {
        "id":          "folie_douce",
        "nom":         "La Folie Douce",
        "type":        "restaurant",
        "secteur":     "bellevarde",
        "lat":         45.4558,
        "lon":         6.9648,
        "ca_jour":     55000,
        "remontees_critiques": {"daille": 4, "olympique": 2},
    },
    {
        "id":          "bellevarde_resto",
        "nom":         "Le Bellevarde / Maison Louly",
        "type":        "restaurant",
        "secteur":     "bellevarde",
        "lat":         45.4495,
        "lon":         6.9718,
        "ca_jour":     35000,
        "remontees_critiques": {"olympique": 4, "funival": 3},
    },
    {
        "id":          "refuge_solaise",
        "nom":         "Le Refuge de Solaise",
        "type":        "restaurant",
        "secteur":     "solaise",
        "lat":         45.4389,
        "lon":         6.9798,
        "ca_jour":     28000,
        "remontees_critiques": {"solaise": 5},
    },
    {
        "id":          "ouillette",
        "nom":         "L'Ouillette",
        "type":        "restaurant",
        "secteur":     "solaise",
        "lat":         45.4375,
        "lon":         6.9821,
        "ca_jour":     18000,
        "remontees_critiques": {"solaise": 5},
    },
    {
        "id":          "signal_fornet",
        "nom":         "Le Signal (Fornet)",
        "type":        "restaurant",
        "secteur":     "fornet",
        "lat":         45.4631,
        "lon":         7.0058,
        "ca_jour":     22000,
        "remontees_critiques": {"fornet": 5},
    },
    {
        "id":          "cascade_pissaillas",
        "nom":         "La Cascade (Pissaillas)",
        "type":        "restaurant",
        "secteur":     "fornet",
        "lat":         45.4701,
        "lon":         7.0215,
        "ca_jour":     15000,
        "remontees_critiques": {"fornet": 4},
    },
    # --- ESF / ECOLES DE SKI ---
    {
        "id":          "esf",
        "nom":         "ESF Val d'Isère",
        "type":        "ecole_ski",
        "secteur":     "station",
        "lat":         45.4478,
        "lon":         6.9797,
        "ca_jour":     95000,
        "remontees_critiques": {"olympique": 2, "solaise": 2, "funival": 1, "fornet": 1},
    },
]

STATUT_SCORE = {"ouvert": 1.0, "reduit": 0.5, "ferme": 0.0}
SEUIL_NORMAL = 0.70
SEUIL_ARRET  = 0.40


# ============================================================
# FONCTIONS
# ============================================================

def fetch_meteo():
    """Recupere meteo Open-Meteo : vent, neige, temperature"""
    url    = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":        LAT,
        "longitude":       LON,
        "hourly":          "windspeed_10m,snowfall,temperature_2m",
        "wind_speed_unit": "kmh",
        "past_days":       PAST_DAYS,
        "forecast_days":   FORECAST_DAYS,
        "timezone":        "Europe/Paris",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    d = r.json()["hourly"]

    times   = d["time"]
    vent    = [float(v or 0) for v in d["windspeed_10m"]]
    neige   = [float(v or 0) for v in d["snowfall"]]
    temp    = [float(v or 0) for v in d["temperature_2m"]]

    now_str   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    now_index = max(i for i, t in enumerate(times) if t <= now_str)

    return times, vent, neige, temp, now_index


def indice_composite(vent_kmh, neige_cmh, temp_c):
    """
    Indice alea [0-1] composite :
    - Composante vent : vent / 80 km/h (fermeture telepherique ~80 km/h)
    - Composante neige : neige / 20 cm/h (vis. nulle, avalanche)
    - Composante givre : si temp < -15°C, +0.2 (risque givrage cables)
    """
    i_vent  = min(vent_kmh / 80.0, 1.0)
    i_neige = min(neige_cmh / 20.0, 1.0)
    i_givre = 0.2 if temp_c < -15 else 0.0
    return round(min(max(i_vent, i_neige) + i_givre, 1.0), 3)


def statut_remontee(r, idx):
    if idx >= r["seuil_fermeture"]: return "ferme"
    if idx >= r["seuil_impact"]:    return "reduit"
    return "ouvert"


def accessibilite(asset, statuts):
    score = 0.0
    poids = 0.0
    for rid, p in asset["remontees_critiques"].items():
        s      = statuts.get(rid, "ouvert")
        score += p * STATUT_SCORE[s]
        poids += p
    return round(score / poids, 3) if poids else 1.0


def taux_activite(acc):
    if acc >= SEUIL_NORMAL: return 1.0
    if acc <= SEUIL_ARRET:  return 0.0
    return round((acc - SEUIL_ARRET) / (SEUIL_NORMAL - SEUIL_ARRET), 3)


def run():
    print("=== TWICE Val d'Isere — temps reel ===")
    times, vent, neige, temp, now_index = fetch_meteo()
    n = len(times)
    print(f"  {n} heures, now_index={now_index} ({times[now_index]})")

    indices = [indice_composite(vent[i], neige[i], temp[i]) for i in range(n)]

    resultats = []
    for asset in ASSETS:
        chrono = []
        for i in range(n):
            statuts = {r["id"]: statut_remontee(r, indices[i]) for r in REMONTEES}
            acc     = accessibilite(asset, statuts)
            taux    = taux_activite(acc)
            perte   = round((asset["ca_jour"] / 10.0) * (1.0 - taux), 2)  # ~10h de revenus/jour
            chrono.append({
                "time":            times[i],
                "is_forecast":     i > now_index,
                "vent_kmh":        vent[i],
                "neige_cmh":       neige[i],
                "temp_c":          temp[i],
                "indice_alea":     indices[i],
                "statuts_remontees": statuts,
                "accessibilite":   acc,
                "taux_activite":   taux,
                "perte_eur":       perte,
            })

        resultats.append({
            "asset_id":          asset["id"],
            "asset_nom":         asset["nom"],
            "type":              asset["type"],
            "secteur":           asset["secteur"],
            "lat":               asset["lat"],
            "lon":               asset["lon"],
            "ca_jour_eur":       asset["ca_jour"],
            "perte_totale_eur":  round(sum(h["perte_eur"] for h in chrono), 2),
            "heures_normales":   sum(1 for h in chrono if h["taux_activite"] == 1.0),
            "heures_degradees":  sum(1 for h in chrono if 0 < h["taux_activite"] < 1.0),
            "heures_arret":      sum(1 for h in chrono if h["taux_activite"] == 0.0),
            "accessibilite_min": min(h["accessibilite"] for h in chrono),
            "chronologie":       chrono,
        })
        print(f"  [{asset['nom'][:30]:30}] perte={resultats[-1]['perte_totale_eur']:>10,.0f} EUR")

    perte_totale_station = sum(r["perte_totale_eur"] for r in resultats)
    print(f"  TOTAL STATION : {perte_totale_station:,.0f} EUR")

    import os
    os.makedirs("outputs", exist_ok=True)
    rapport = {
        "mode":         "realtime",
        "station":      "Val d'Isere",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "now_index":    now_index,
        "hypotheses": {
            "H1": "Indice alea = max(vent/80, neige/20) + 0.2 si temp<-15°C",
            "H2": "Remontee reduite si indice >= seuil_impact, fermee si >= seuil_fermeture",
            "H3": f"Activite pleine si accessibilite >= {SEUIL_NORMAL}, arret si <= {SEUIL_ARRET}",
            "H4": "CA journalier reparti sur 10h d'exploitation",
            "H5": "CA pic saison (fevrier) : hypotheses fictives a calibrer",
            "H6": f"Fenetre = {PAST_DAYS}j historiques + {FORECAST_DAYS}j previsions Open-Meteo",
        },
        "meteo": {
            "times":  times,
            "vent":   vent,
            "neige":  neige,
            "temp":   temp,
            "now_index": now_index,
        },
        "indices_alea": indices,
        "remontees":    REMONTEES,
        "resultats":    resultats,
        "perte_totale_station_eur": round(perte_totale_station, 2),
    }

    with open("outputs/resultats_latest.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    print("  Sauvegarde : outputs/resultats_latest.json")
    print("=== TWICE termine ===")


if __name__ == "__main__":
    run()
