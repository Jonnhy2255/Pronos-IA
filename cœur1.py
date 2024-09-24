import requests
from bs4 import BeautifulSoup
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.parse
from colorama import Fore

# Dictionnaire des ligues avec les URLs
leagues_urls = {
    'premier league': 'https://www.espn.com/soccer/table/_/league/eng.1',
    'la liga': 'https://www.espn.com/soccer/table/_/league/esp.1',
    'serie a': 'https://www.espn.com/soccer/table/_/league/ita.1',
    'bundesliga': 'https://africa.espn.com/football/table/_/league/ger.1/season/2024'
}

# Dictionnaire des équipes avec leurs URL correspondantes pour les résultats, fixtures et stats
teams_urls = {
    "Bournemouth": {
        "results": "https://www.espn.com/soccer/team/results/_/id/349/afc-bournemouth",
        "fixtures": "https://www.espn.com/soccer/team/fixtures/_/id/349/afc-bournemouth",
        "stats": "https://africa.espn.com/football/team/stats/_/id/349/league/ENG.1/view/performance"
    },
    "Arsenal": {
        "results": "https://www.espn.com/soccer/team/results/_/id/359/arsenal",
        "fixtures": "https://www.espn.com/soccer/team/fixtures/_/id/359/arsenal",
        "stats": "https://africa.espn.com/football/team/stats/_/id/359/league/ENG.1/view/performance"
    },
    "Aston Villa": {
        "results": "https://www.espn.com/soccer/team/results/_/id/362/aston-villa",
        "fixtures": "https://www.espn.com/soccer/team/fixtures/_/id/362/aston-villa",
        "stats": "https://africa.espn.com/football/team/stats/_/id/362/league/ENG.1/view/performance"
    }
}

# En-têtes HTTP pour imiter un navigateur
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Fonction pour obtenir le classement d'une équipe à partir de son nom
def get_team_position(team_name):
    for league_name, url in leagues_urls.items():
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraction des données de classement
            table_rows = soup.find_all('tr', class_='Table__TR')

            for row in table_rows:
                position = row.find('span', class_='team-position').text if row.find('span', class_='team-position') else None
                team = row.find('span', class_='hide-mobile').text if row.find('span', 'hide-mobile') else None
                if position and team:
                    if team_name.lower() in team.lower():
                        return int(position), league_name.capitalize()

        except Exception as e:
            print(Fore.RED + f"Une erreur est survenue lors de la récupération du classement pour {league_name}: {e}")

    print(Fore.RED + f"L'équipe '{team_name}' n'a pas été trouvée dans les ligues suivies.")
    return None, None

# Fonction pour scraper les résultats ou les fixtures d'une équipe
def scrape_team_data(team_name, action):
    url = teams_urls.get(team_name, {}).get(action, None)
    if not url:
        return {"error": f"URL non trouvée pour {team_name} et action {action}."}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        matches = soup.find_all('tr', class_='Table__TR')
        results = []

        for match in matches:
            date = match.find('div', class_='matchTeams').text.strip() if match.find('div', class_='matchTeams') else "N/A"
            teams = match.find_all('a', class_='AnchorLink Table__Team')
            if len(teams) == 2:
                team1 = teams[0].text.strip()
                team2 = teams[1].text.strip()
            else:
                team1 = team2 = "N/A"
            competition = match.find_all('a', class_='AnchorLink')[1].text.strip() if len(match.find_all('a', 'AnchorLink')) > 1 else "N/A"
            score = match.find('span').text.strip() if match.find('span') else "N/A"
            status = match.find_all('a', class_='AnchorLink')[-1].text.strip() if match.find_all('a', 'AnchorLink') else "N/A"

            if date != "N/A" and team1 != "N/A" and team2 != "N/A" and score != "N/A":
                results.append({
                    "date": date,
                    "team1": team1,
                    "team2": team2,
                    "competition": competition,
                    "score": score,
                    "status": status
                })

        return results

    except Exception as e:
        return {"error": f"Une erreur est survenue pour {team_name}: {e}"}

# Fonction pour scraper les statistiques d'une équipe
def scrape_team_stats(team_name):
    url = teams_urls.get(team_name, {}).get('stats', None)
    if not url:
        return {"error": f"URL non trouvée pour {team_name} et action stats."}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        stats_table = soup.find('table', class_='Table')
        if not stats_table:
            return {"error": "Tableau de statistiques non trouvé."}

        stats = {}
        rows = stats_table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                stat_name = cols[0].text.strip()
                stat_value = cols[1].text.strip()
                stats[stat_name] = stat_value

        return stats

    except Exception as e:
        return {"error": f"Une erreur est survenue pour {team_name}: {e}"}

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)

        action = query.get('action', [None])[0]
        team_name = query.get('team_name', [None])[0]

        if action in ['results', 'fixtures', 'stats']:
            if team_name in teams_urls:
                if action == 'stats':
                    result = scrape_team_stats(team_name)
                else:
                    result = scrape_team_data(team_name, action)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Équipe non trouvée: {team_name}."}).encode())
        elif action == 'rankings':
            position, league = get_team_position(team_name)
            if position:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"team_name": team_name, "position": position, "league": league}).encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Équipe non trouvée."}).encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Action invalide."}).encode())

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Serving on port {port}...')
    httpd.serve_forever()

if __name__ == "__main__":
    run()