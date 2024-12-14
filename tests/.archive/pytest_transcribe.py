import os
import pytest
from fastapi.testclient import TestClient
from main import app  # Adjust the import based on your project structure

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_env():
    os.environ["WHISPERLIVE_HOST"] = "localhost"
    os.environ["WHISPERLIVE_PORT"] = "9090"

def test_start_transcription():
    user_id = "test_user"
    response = client.post(f"/transcribe/live/start_transcription/{user_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Transcription started", "user_id": user_id}

def test_handle_whisper_live_eos_utterance():
    user_id = "test_user"
    data = {
        "utterance": "Hello, world!",
        "start": 0,
        "end": 1,
        "eos": True
    }
    response = client.post(f"/transcribe/utterance/handle_whisper_live_eos_utterance/{user_id}", json=data)
    assert response.status_code == 200
    assert response.json() == {"message": "Utterance logged successfully"}

def test_get_utterances():
    user_id = "test_user"
    response = client.get(f"/transcribe/utterance/get_utterances/{user_id}")
    assert response.status_code == 200
    assert "utterances" in response.json()