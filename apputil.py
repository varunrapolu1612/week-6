from __future__ import annotations

import os
import time
import typing as t
import requests
import pandas as pd

class Genius:
    """
    Minimal Genius API helper for:
      - Exercise 1: store access_token
      - Exercise 2: get_artist(search_term) -> dict
      - Exercise 3: get_artists(search_terms: list[str]) -> pd.DataFrame
    """

    BASE_URL = "https://api.genius.com"

    def __init__(self, access_token: t.Optional[str] = None, *, use_env_fallback: bool = True):
        """
        Parameters
        ----------
        access_token : str | None
            Personal API token. If None and use_env_fallback=True, tries os.environ['ACCESS_TOKEN'].
        use_env_fallback : bool
            If True and no token passed, will attempt to read from env var ACCESS_TOKEN.
        """
        if access_token is None and use_env_fallback:
            access_token = os.environ.get("ACCESS_TOKEN")

        if not access_token:
            raise ValueError(
                "No Genius access token provided. Pass access_token=... "
                "or set ACCESS_TOKEN in environment."
            )

        # Exercise 1: “save” the access token on the object
        self.access_token = access_token

        # Pre-build headers for all requests
        self._headers = {"Authorization": f"Bearer {self.access_token}"}

    # ---------------------------
    # Internals
    # ---------------------------
    def _get(self, path: str, params: dict | None = None, *, retries: int = 2, backoff: float = 0.8) -> dict:
        """Internal GET with small retry + basic error handling."""
        url = f"{self.BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        last_exc = None
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, headers=self._headers, params=params, timeout=20)
                if resp.status_code == 429:
                    # Back off if rate-limited
                    time.sleep(backoff * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                # Genius wraps payloads like {"response": {...}}
                return data
            except Exception as exc:
                last_exc = exc
                time.sleep(backoff * (attempt + 1))
        raise RuntimeError(f"Genius GET failed for {url} with params={params!r}") from last_exc

    def _search_hits(self, search_term: str, per_page: int = 10) -> list[dict]:
        """
        Call /search and return the 'hits' list.
        Mirrors the approach in your helper module (using the Genius search endpoint). :contentReference[oaicite:1]{index=1}
        """
        params = {"q": search_term, "per_page": per_page}
        data = self._get("/search", params=params)
        return data.get("response", {}).get("hits", [])

    # ---------------------------
    # Public API
    # ---------------------------
    def get_artist(self, search_term: str) -> dict:
        """
        Exercise 2:
          1) Search for `search_term`; take the first hit's primary artist id.
          2) Call /artists/{id}
          3) Return the artist JSON dictionary (the 'artist' object).
        """
        hits = self._search_hits(search_term, per_page=1)
        if not hits:
            raise ValueError(f"No Genius search hits for {search_term!r}")

        # From the first hit, grab the 'result' -> 'primary_artist' -> 'id'
        first = hits[0]
        result = first.get("result", {}) or {}
        primary_artist = result.get("primary_artist", {}) or {}
        artist_id = primary_artist.get("id")
        if artist_id is None:
            raise ValueError(f"No primary_artist id found for search term {search_term!r}")

        # /artists/{id} -> returns {"response": {"artist": {...}}}
        artist_resp = self._get(f"/artists/{artist_id}")
        artist = artist_resp.get("response", {}).get("artist", {})
        if not artist:
            raise RuntimeError(f"Genius returned no artist payload for id={artist_id}")

        return artist

    def get_artists(self, search_terms: list[str]) -> pd.DataFrame:
        """
        Exercise 3:
        Returns a DataFrame with columns:
          - search_term
          - artist_name
          - artist_id
          - followers_count  (if present; else NaN)
        """
        rows = []
        for term in search_terms:
            try:
                artist = self.get_artist(term)
                rows.append(
                    {
                        "search_term": term,
                        "artist_name": artist.get("name"),
                        "artist_id": artist.get("id"),
                        "followers_count": artist.get("followers_count"),
                    }
                )
            except Exception:
                # If anything fails for a given term, still keep a row so the caller can see it
                rows.append(
                    {
                        "search_term": term,
                        "artist_name": None,
                        "artist_id": None,
                        "followers_count": None,
                    }
                )
        return pd.DataFrame(rows)# your code here ...
