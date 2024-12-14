from fastapi import APIRouter, Request
import os
import queue
from dotenv import load_dotenv
import json

load_dotenv()

router = APIRouter()

@router.post("/handle_whisper_live_eos_utterance/{user_id}")
async def handle_whisper_live_eos_utterance(user_id: str, request: Request):
    data = await request.json()
    utterance = data.get("utterance")
    print(f"Utterance: {utterance}")
    start = data.get("start")
    end = data.get("end")
    print(f"Start: {start}")
    print(f"End: {end}")
    eos = data.get("eos")
    print(f"Eos: {eos}")
    user_dir = f"../../data/users/{user_id}/transcripts"
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    log_file = os.path.join(user_dir, "utterances.log")
    with open(log_file, "a") as f:
        f.write(json.dumps(data) + "\n")

    return {"message": "Utterance logged successfully"}

@router.get("/get_utterances/{user_id}")
async def get_utterances(user_id: str):
    user_dir = f"../../data/users/{user_id}/transcripts"
    log_file = os.path.join(user_dir, "utterances.log")
    if not os.path.exists(log_file):
        return {"utterances": []}

    with open(log_file, "r") as f:
        utterances = [json.loads(line) for line in f]

    return {"utterances": utterances}
