import requests

from Player import Player


class SportDB:
    BASE_URL = "https://api.sportdb.dev/api"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Accept": "application/json"
        })

    def _get(self, endpoint: str, params=None):
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    # ---------------------------
    # Players
    # ---------------------------
    def search_players(self, query: str, page: int = 1) -> list[Player]:
        data = self._get(
            f"transfermarkt/players/search/{query}",
            params={"pageNumber": page}
        )
        return [Player.from_dict(p) for p in data["results"]]

    def get_player(self, player_id: str):
        """
        Get a player's full profile.
        """
        endpoint = f"transfermarkt/players/{player_id}"
        return self._get(endpoint)
