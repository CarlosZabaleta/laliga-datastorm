"""
La Liga DataStorm — Daily Data Fetcher
=======================================
Corre via GitHub Actions. Llama a API-Football (api-sports.io)
y genera archivos JSON en web/data/ que el frontend consume.

Variables de entorno:
  API_FOOTBALL_KEY  — api-sports.io API key
"""

import os, json, requests, datetime
from pathlib import Path

API_KEY  = os.environ.get("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}
OUT_DIR  = Path(__file__).parent.parent / "web" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# IDs de competiciones en API-Football
LALIGA   = 140   # La Liga
UCL      = 2     # Champions League
COPA     = 143   # Copa del Rey
SEASON   = 2025  # Temporada 2025-26

def get(endpoint: str, **params) -> dict:
    r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def save(name: str, data):
    path = OUT_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  ✓ {name}.json guardado ({len(str(data))} chars)")

# ── 1. PARTIDOS DE HOY ────────────────────────────────────────────────────────
def fetch_today():
    today = datetime.date.today().isoformat()
    result = []
    for league in [LALIGA, UCL, COPA]:
        data = get("fixtures", league=league, season=SEASON, date=today)
        for f in data.get("response", []):
            fix = f["fixture"]
            teams = f["teams"]
            goals = f["goals"]
            score = f["score"]
            result.append({
                "id":         fix["id"],
                "league_id":  f["league"]["id"],
                "league":     f["league"]["name"],
                "home":       teams["home"]["name"],
                "away":       teams["away"]["name"],
                "home_logo":  teams["home"]["logo"],
                "away_logo":  teams["away"]["logo"],
                "status":     fix["status"]["short"],
                "elapsed":    fix["status"]["elapsed"],
                "time":       fix["date"],
                "score_home": goals["home"],
                "score_away": goals["away"],
            })
    save("today", {"date": today, "fixtures": result})

# ── 2. PRÓXIMAS 2 SEMANAS ─────────────────────────────────────────────────────
def fetch_upcoming():
    today = datetime.date.today()
    end   = (today + datetime.timedelta(days=14)).isoformat()
    result = []
    for league in [LALIGA, UCL, COPA]:
        data = get("fixtures", league=league, season=SEASON,
                   from_date=today.isoformat(), to=end)
        for f in data.get("response", []):
            fix = f["fixture"]
            teams = f["teams"]
            result.append({
                "id":        fix["id"],
                "league_id": f["league"]["id"],
                "league":    f["league"]["name"],
                "home":      teams["home"]["name"],
                "away":      teams["away"]["name"],
                "date":      fix["date"],
                "status":    fix["status"]["short"],
            })
    save("upcoming", {"fixtures": result})

# ── 3. CLASIFICACIÓN LA LIGA ──────────────────────────────────────────────────
def fetch_standings():
    data = get("standings", league=LALIGA, season=SEASON)
    standings = []
    for group in data.get("response", [{}])[0].get("league", {}).get("standings", [[]]):
        for entry in group:
            t = entry["team"]
            g = entry["all"]
            standings.append({
                "rank":   entry["rank"],
                "team":   t["name"],
                "logo":   t["logo"],
                "played": g["played"],
                "won":    g["win"],
                "drawn":  g["draw"],
                "lost":   g["lose"],
                "gf":     g["goals"]["for"],
                "ga":     g["goals"]["against"],
                "gd":     entry["goalsDiff"],
                "pts":    entry["points"],
                "form":   entry.get("form", ""),
            })
    save("standings", {"standings": standings})

# ── 4. GOLEADORES ─────────────────────────────────────────────────────────────
def fetch_scorers():
    data = get("players/topscorers", league=LALIGA, season=SEASON)
    resp = data.get("response", [])
    print(f"  → API: {len(resp)} jugadores | errors: {data.get('errors')} | results: {data.get('results')}")
    players = []
    for entry in resp[:40]:
        p = entry["player"]
        s = entry["statistics"][0]
        players.append({
            "name":    p["name"],
            "photo":   p["photo"],
            "team":    s["team"]["name"],
            "goals":   s["goals"]["total"] or 0,
            "assists": s["goals"]["assists"] or 0,
            "games":   s["games"]["appearences"] or 0,
            "rating":  s["games"]["rating"],
        })
    save("scorers", {"players": players})

# ── 5. ASISTIDORES ────────────────────────────────────────────────────────────
def fetch_assisters():
    data = get("players/topassists", league=LALIGA, season=SEASON)
    players = []
    for entry in data.get("response", [])[:30]:
        p = entry["player"]
        s = entry["statistics"][0]
        players.append({
            "name":    p["name"],
            "photo":   p["photo"],
            "team":    s["team"]["name"],
            "assists": s["goals"]["assists"] or 0,
            "goals":   s["goals"]["total"] or 0,
            "games":   s["games"]["appearences"] or 0,
        })
    save("assisters", {"players": players})

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not API_KEY:
        print("[!] API_FOOTBALL_KEY no configurada")
        exit(1)

    print("⚽ La Liga DataStorm — Fetching data...")
    print("=" * 45)

    steps = [
        ("Partidos de hoy",      fetch_today),
        ("Próximas 2 semanas",   fetch_upcoming),
        ("Clasificación",        fetch_standings),
        ("Goleadores",           fetch_scorers),
        ("Asistidores",          fetch_assisters),
    ]
    for label, fn in steps:
        print(f"\n📡 {label}...")
        try:
            fn()
        except Exception as e:
            print(f"  [!] Error: {e}")

    print("\n✅ Todos los datos actualizados.")
