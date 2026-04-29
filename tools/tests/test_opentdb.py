from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from trivia_pack.models import Lang, RawQuestion
from trivia_pack.opentdb import OpenTdbClient

API = "https://opentdb.com/api.php"


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "cache"


def test_fetch_pages_until_response_code_nonzero(cache_dir: Path) -> None:
    page1 = {
        "response_code": 0,
        "results": [
            {
                "category": "Geography",
                "type": "multiple",
                "question": "Capital of Spain?",
                "correct_answer": "Madrid",
                "incorrect_answers": ["Lisbon", "Rome", "Paris"],
            }
        ],
    }
    page2 = {"response_code": 1, "results": []}

    response1 = MagicMock(spec=httpx.Response)
    response1.json.return_value = page1
    response1.raise_for_status.return_value = None

    response2 = MagicMock(spec=httpx.Response)
    response2.json.return_value = page2
    response2.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.side_effect = [response1, response2]

    with patch("httpx.Client") as mock_client_class:
        mock_client_class.return_value.__enter__.return_value = mock_client

        client = OpenTdbClient(cache_dir=cache_dir, sleep_between=0.0)
        out: list[RawQuestion] = list(client.iter_all(Lang.EN))

        assert len(out) == 1
        assert out[0].source_lang == Lang.EN
        assert out[0].opentdb_category == "Geography"
        assert out[0].question == "Capital of Spain?"
        assert out[0].answer == "Madrid"


def test_html_entities_are_decoded(cache_dir: Path) -> None:
    page = {
        "response_code": 0,
        "results": [
            {
                "category": "History",
                "type": "multiple",
                "question": "What does &quot;C&apos;est la vie&quot; mean?",
                "correct_answer": "That&#039;s life",
                "incorrect_answers": [],
            }
        ],
    }
    end = {"response_code": 1, "results": []}

    response1 = MagicMock(spec=httpx.Response)
    response1.json.return_value = page
    response1.raise_for_status.return_value = None

    response2 = MagicMock(spec=httpx.Response)
    response2.json.return_value = end
    response2.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.side_effect = [response1, response2]

    with patch("httpx.Client") as mock_client_class:
        mock_client_class.return_value.__enter__.return_value = mock_client

        client = OpenTdbClient(cache_dir=cache_dir, sleep_between=0.0)
        out = list(client.iter_all(Lang.EN))
        assert out[0].question == 'What does "C\'est la vie" mean?'
        assert out[0].answer == "That's life"


def test_cached_responses_are_replayed_without_network(cache_dir: Path) -> None:
    page = {
        "response_code": 0,
        "results": [
            {
                "category": "Sports",
                "type": "multiple",
                "question": "Q?",
                "correct_answer": "A",
                "incorrect_answers": [],
            }
        ],
    }
    end = {"response_code": 1, "results": []}

    response1 = MagicMock(spec=httpx.Response)
    response1.json.return_value = page
    response1.raise_for_status.return_value = None

    response2 = MagicMock(spec=httpx.Response)
    response2.json.return_value = end
    response2.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.get.side_effect = [response1, response2]

    with patch("httpx.Client") as mock_client_class:
        mock_client_class.return_value.__enter__.return_value = mock_client

        client = OpenTdbClient(cache_dir=cache_dir, sleep_between=0.0)
        first = list(client.iter_all(Lang.EN))
        assert len(first) == 1
        network_calls_after_first = mock_client.get.call_count

        # Second pass: cache populated → no extra HTTP calls
        second = list(client.iter_all(Lang.EN))
        assert second == first
        assert mock_client.get.call_count == network_calls_after_first


def test_cache_file_is_human_readable_json(cache_dir: Path) -> None:
    cache_dir.mkdir()
    sample = [
        {
            "source_lang": "EN",
            "opentdb_category": "Geography",
            "question": "Q?",
            "answer": "A",
        }
    ]
    (cache_dir / "opentdb_en.json").write_text(json.dumps(sample), encoding="utf-8")

    client = OpenTdbClient(cache_dir=cache_dir, sleep_between=0.0)
    cached = list(client.iter_all(Lang.EN))
    assert len(cached) == 1
    assert cached[0].question == "Q?"
