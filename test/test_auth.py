from unittest.mock import patch, MagicMock
from src.auth import TokenManager
import threading
import pytest
import json
import time


@pytest.fixture
def tmp_token_file(tmp_path):
    return tmp_path / ".token.json"


@pytest.fixture
def valid_token_data():
    return {
        "access_token": "abc123",
        "id_token": "id456",
        "scope": "read",
        "expires_in": 3600,
        "token_type": "Bearer",
        "refresh_token": "rftoken",
        "obtained_at": int(time.time()) - 100,
    }


def test_load_valid_token(
    tmp_token_file,
    valid_token_data
):
    tmp_token_file.write_text(json.dumps(valid_token_data))
    tm = TokenManager(token_file=str(tmp_token_file))
    assert tm.token_data == valid_token_data


def test_load_invalid_json(
    tmp_token_file
):
    tmp_token_file.write_text("{invalid_json")
    tm = TokenManager(token_file=str(tmp_token_file))
    assert tm.token_data == {}


def test_is_expired_returns_true_if_expired(
    valid_token_data
):
    valid_token_data["expires_in"] = 1
    valid_token_data["obtained_at"] = int(time.time()) - 1000
    tm = TokenManager()
    tm.token_data = valid_token_data
    assert tm._is_expired() is True


def test_is_expired_returns_false_if_valid(
    valid_token_data
):
    valid_token_data["obtained_at"] = int(time.time()) - 100
    tm = TokenManager()
    tm.token_data = valid_token_data
    assert tm._is_expired() is False


def test_save_writes_file_and_updates_memory(
    tmp_token_file,
    valid_token_data
):
    tm = TokenManager(token_file=str(tmp_token_file))
    tm._save(valid_token_data)
    saved = json.loads(tmp_token_file.read_text())

    assert "obtained_at" in saved
    assert saved["access_token"] == "abc123"
    assert tm.token_data == saved


@patch("requests.post")
@patch.dict("os.environ", {
    "TS_TOKEN_URL": "https://example.com",
    "TS_CLIENT_ID": "id",
    "TS_CLIENT_SECRET": "secret",
    "TS_REFRESH_TOKEN": "rftoken"
})
def test_refresh_success(
    mock_post,
    tmp_token_file
):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "newtoken",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    tm = TokenManager(token_file=str(tmp_token_file))
    token = tm._refresh()

    assert token == "newtoken"
    assert tm.token_data["access_token"] == "newtoken"
    mock_post.assert_called_once()


@patch.object(
    TokenManager,
    "_is_expired",
    return_value=False
)

def test_get_token_returns_existing(
    mock_expired,
    valid_token_data
):
    tm = TokenManager()
    tm.token_data = valid_token_data
    token = tm.get_token()
    assert token == "abc123"
    mock_expired.assert_called_once()


@patch.object(TokenManager, "_is_expired", return_value=True)
@patch.object(TokenManager, "_refresh", return_value="newtoken")
def test_get_token_refreshes_if_expired(
    mock_refresh,
    mock_expired,
    valid_token_data
):
    tm = TokenManager()
    tm.token_data = valid_token_data
    token = tm.get_token()
    assert token == "newtoken"
    mock_refresh.assert_called_once()


@patch.object(TokenManager, "_refresh")
def test_thread_safety(mock_refresh, valid_token_data):
    tm = TokenManager()
    tm.token_data = {}

    def fake_refresh():
        tm.token_data = valid_token_data
        return valid_token_data["access_token"]

    mock_refresh.side_effect = fake_refresh

    def worker():
        tm.get_token()

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    mock_refresh.assert_called_once()

