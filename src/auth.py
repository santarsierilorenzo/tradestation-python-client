from typing import Dict, Optional
from threading import Lock
import requests
import json
import time
import os


class TokenManager:
    """
    Manages the lifecycle of an OAuth2 access token.

    Responsibilities:
    - Load token data from a local JSON file.
    - Automatically refresh the token when it expires.
    - Ensure thread-safe access to the token using a shared mutex.
    """

    # A shared mutex (mutual exclusion lock) ensuring that only one thread
    # can perform a token refresh at a time, preventing race conditions.
    _lock = Lock()

    def __init__(
        self,
        token_file: Optional[str] = ".token.json"
    ) -> None:
        """
        Initializes the TokenManager.

        Args:
            token_file (str, optional): Path to the JSON file storing token
                                        data. Defaults to ".token.json".

        Loads token data from the specified file. If the file does not exist or
        lacks valid fields, an empty dictionary is used instead. The
        `token_data` attribute will store the active token information.
        """
        self.token_file = token_file
        self.token_data = self._load()

    def _load(self) -> Dict:
        """
        Loads token data from the configured JSON file.

        Returns:
            dict: The token data if the file exists and contains all required
                keys. Returns an empty dictionary if the file is missing,
                malformed, or missing any required parameters.
        """
        if not os.path.exists(self.token_file):
            return {}

        with open(self.token_file, "r") as f:
            try:
                token_data = json.load(f)
            except json.JSONDecodeError:
                return {}

        # Required fields for a valid token file
        required_keys = {
            "access_token",
            "id_token",
            "scope",
            "expires_in",
            "token_type",
            "refresh_token",
            "obtained_at"
        }

        # Verify all required keys are present
        if not required_keys.issubset(token_data.keys()):
            return {}

        return token_data

    def _save(
        self,
        data: Dict
    ) -> None:
        """
        Persist the Bearer token data both in memory and on disk.

        Args:
            data (dict): The token data returned from the API response.

        The method updates the `obtained_at` timestamp (in seconds since
        epoch), writes the data to the configured JSON file, and updates the
        in-memory `token_data` reference.
        """
        # Record the approximate time the token was obtained.
        data["obtained_at"] = int(time.time())

        # Save the token data to disk (overwrites existing file).
        with open(self.token_file, "w") as f:
            json.dump(data, f)

        self.token_data = data

    def _is_expired(self) -> bool:
        """
        Check whether the current Bearer token has expired.

        Returns:
            bool: True if the token is expired or missing, False otherwise.
        """
        # If no token data is loaded, treat it as expired.
        if not self.token_data:
            return True

        # Compute the expiration timestamp.
        # A 30-second safety buffer is subtracted since 'obtained_at' is an
        # estimate.
        exp = (
            self.token_data["obtained_at"]
            + self.token_data["expires_in"]
            - 30
        )

        # Return True if the current time is beyond the expiration threshold.
        return time.time() >= exp

    def _refresh(self) -> str:
        """
        Requests a new TradeStation access token using the existing refresh
        token and updates the internal token data.

        Returns:
            str: The new access token.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails or
            the server responds with an error status code.
        """
        url = os.getenv("TS_TOKEN_URL")
        if not url:
            raise ValueError("Missing environment variable: TS_TOKEN_URL")

        payload = {
            "grant_type": "refresh_token",
            "client_id": os.getenv("TS_CLIENT_ID"),
            "client_secret": os.getenv("TS_CLIENT_SECRET"),
            "refresh_token": os.getenv("TS_REFRESH_TOKEN"),
        }

        headers = {
            "content-type": os.getenv(
                "TS_CONTENT_TYPE", "application/x-www-form-urlencoded"
            )
        }

        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()  # raises if not 2xx

        new_data = response.json()

        # Ensure the refresh_token is preserved if the API doesn't return it
        new_data["refresh_token"] = new_data.get(
            "refresh_token", payload["refresh_token"]
        )

        self._save(new_data)
        return new_data["access_token"]

    def get_token(self) -> str:
        """
        Public method used to obtain a valid Bearer token for API requests.

        This method is thread-safe:
        - If no token is loaded or the current token has expired, it acquires
        the class-level lock and triggers a refresh.
        - Otherwise, it simply returns the existing valid token.

        Returns:
            str: The active access token.
        """
        with TokenManager._lock:
            # If the token is missing or expired, refresh it.
            if not self.token_data or self._is_expired():
                return self._refresh()

            # Otherwise, return the current valid access token.
            return self.token_data["access_token"]
