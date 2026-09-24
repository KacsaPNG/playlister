"""
Tests for Netlify Web Queue sync worker and dialog data handling.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from app.gui.netlify_sync_dialog import FetchWebQueueWorker, RemoveWebTrackWorker, normalize_api_url


def test_normalize_api_url():
    assert normalize_api_url("http://localhost:5173") == "http://localhost:5173/api/playlist"
    assert normalize_api_url("http://localhost:5173/") == "http://localhost:5173/api/playlist"
    assert normalize_api_url("http://localhost:5173/api/playlist") == "http://localhost:5173/api/playlist"
    assert normalize_api_url("my-site.netlify.app") == "https://my-site.netlify.app/api/playlist"


def test_fetch_web_queue_worker_success():
    worker = FetchWebQueueWorker("http://test.local/api/playlist")
    mock_response_data = {
        "success": True,
        "tracks": [
            {
                "id": "trk-1",
                "title": "Around the World",
                "artist": "Daft Punk",
                "upvotes": 5,
                "url": "https://www.youtube.com/watch?v=k5wwbSLZv4k",
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    received_tracks = []

    def on_finished(tracks):
        received_tracks.extend(tracks)

    worker.finished_signal.connect(on_finished)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        worker.run()

    assert len(received_tracks) == 1
    assert received_tracks[0]["title"] == "Around the World"


def test_fetch_web_queue_worker_detects_html():
    worker = FetchWebQueueWorker("http://test.local/api/playlist")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.read.return_value = b"<!doctype html><html><body>Error</body></html>"
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    errors = []

    def on_error(err):
        errors.append(err)

    worker.error_signal.connect(on_error)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        worker.run()

    assert len(errors) == 1
    assert "returned an HTML page instead of JSON API" in errors[0]


def test_remove_web_track_worker_success():
    worker = RemoveWebTrackWorker("http://test.local/api/playlist", "trk-1")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"success": True}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    results = []

    def on_finished(success, msg):
        results.append((success, msg))

    worker.finished_signal.connect(on_finished)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        worker.run()

    assert len(results) == 1
    assert results[0][0] is True
