# TWICE — Digital Twin Val d'Isère

Prototype de Digital Twin pour la station de ski de Val d'Isère.

**Chaîne causale** : conditions météo → indice d'aléa → statut remontées mécaniques → accessibilité secteurs → pertes par asset → perte totale station

## Deux modules

### 📡 Temps réel & prévisions
- Données météo Open-Meteo (2j historiques + 7j prévisions)
- Variables : vent (km/h), chute de neige (cm/h), température (°C)
- Calcul automatique via GitHub Actions

### 🎛 Simulation scénario
- Inputs manuels : vent max, chute de neige, température, durée
- Calcul instantané côté navigateur (pas de serveur)
- Mêmes outputs : carte + graphiques + pertes par asset

## Assets modélisés

| Asset | Type | CA/jour (pic saison) |
|-------|------|---------------------|
| Forfaits Bellevarde | Forfaits | 330 000 EUR |
| Forfaits Solaise | Forfaits | 230 000 EUR |
| Forfaits Fornet/Pissaillas | Forfaits | 110 000 EUR |
| La Folie Douce | Restaurant | 55 000 EUR |
| Le Bellevarde / Maison Louly | Restaurant | 35 000 EUR |
| Le Refuge de Solaise | Restaurant | 28 000 EUR |
| L'Ouillette | Restaurant | 18 000 EUR |
| Le Signal (Fornet) | Restaurant | 22 000 EUR |
| La Cascade (Pissaillas) | Restaurant | 15 000 EUR |
| ESF Val d'Isère | École ski | 95 000 EUR |

**Total pic saison : ~1 008 000 EUR/jour**

## Remontées modélisées

| Remontée | Type | Secteur | Seuil impact | Seuil fermeture |
|----------|------|---------|-------------|----------------|
| Téléphérique de l'Olympique | Téléphérique 3S | Bellevarde | 0.45 | 0.75 |
| Funival (La Daille) | Funiculaire | Bellevarde | 0.35 | 0.85 |
| Télécabine de Solaise | Télécabine | Solaise | 0.40 | 0.72 |
| Téléphérique du Fornet | Téléphérique | Fornet | 0.40 | 0.68 |
| Télécabine de La Daille | Télécabine | Bellevarde | 0.42 | 0.70 |

## Lancer une simulation temps réel

1. Onglet **Actions** → **TWICE — Digital Twin Val d'Isère**
2. **Run workflow**
3. Rapport disponible sur GitHub Pages :
   `https://<votre-username>.github.io/twice-valdisere/rapport.html`

## Hypothèses

| # | Description |
|---|-------------|
| H1 | Indice aléa = max(vent/80, neige/20) + 0.2 si temp < -15°C |
| H2 | Remontée réduite si indice ≥ seuil_impact, fermée si ≥ seuil_fermeture |
| H3 | Activité pleine si accessibilité ≥ 70%, arrêt si ≤ 40% |
| H4 | CA journalier réparti sur 10h d'exploitation |
| H5 | CA pic saison (février) : hypothèses fictives à calibrer |
| H6 | Fenêtre = 2j historiques + 7j prévisions Open-Meteo |

## Structure

```
src/
  twice_run.py       — simulation temps réel (Open-Meteo → JSON)
  twice_report.py    — rapport HTML (JSON → HTML avec carte + simulation)
outputs/
  resultats_latest.json
  rapport.html
docs/
  rapport.html       — servi par GitHub Pages
.github/workflows/
  twice_run.yml
```
