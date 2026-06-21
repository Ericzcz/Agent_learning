import json
import os.path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.main import app


REFRESH_URL = '/refresh'
URL = '/is-bitcoin-lit'
EXPECTED_FIELDS = (
    'hourly_average_of_averages',
    'sentiment_direction',
    'price_direction',
)
JSON_FIXTURE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    'coingecko_market_chart_response.json',
)


@pytest.fixture
def mock_bitcoin_api():
    with mock.patch('httpx.AsyncClient.get') as mock_get:
        mock_response = mock.MagicMock()

        with open(JSON_FIXTURE) as f:
            mock_response.json.return_value = json.loads(f.read())

        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        yield mock_get


def test_api(mock_bitcoin_api: mock.MagicMock):
    with TestClient(app) as client:
        refresh_res = client.post(REFRESH_URL)
        summary = refresh_res.json()

        assert refresh_res.status_code == 200

        for field in EXPECTED_FIELDS:
            assert field in summary

        assert summary['sentiment_direction'] == 'unavailable'
        assert summary['price_direction'] == 'rising'
        assert summary['hourly_average_of_averages']
        assert all(
            datapoint['sentiment'] is None
            for datapoint in summary['hourly_average_of_averages']
        )

        res = client.get(URL)
        cached_summary = res.json()

        assert res.status_code == 200
        assert cached_summary['price_direction'] == 'rising'
        assert cached_summary['sentiment_direction'] == 'unavailable'
