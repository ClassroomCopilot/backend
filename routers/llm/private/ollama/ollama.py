# Import necessary libraries
import os
from dotenv import load_dotenv, find_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import ollama
from ollama import Client

load_dotenv(find_dotenv())

router = APIRouter()
## client = Client(host='http://localhost:11434')

ollama_host = os.getenv("HOST_OLLAMA")
ollama_port = os.getenv("PORT_OLLAMA")

if not ollama_host or not ollama_port:
    raise ValueError("Environment variables HOST_OLLAMA or PORT_OLLAMA are not set")

client = Client(host=f'http://{ollama_host}:{ollama_port}')

class UserRequest(BaseModel):
    question: str
    model: str = "llama3"
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None

@router.post("/ollama_text_prompt")
async def ollama_text_prompt(user_request: UserRequest):
    model_name = user_request.model
    question = user_request.question
    options = {
        "temperature": user_request.temperature,
        "top_p": user_request.top_p,
        "max_tokens": user_request.max_tokens,
    }

    supported_models = ["llama2", "llama3", "mistral", "llama3"]
    if model_name not in supported_models:
        raise HTTPException(status_code=400, detail="Model not supported")

    messages = [{"role": "user", "content": question}]
    try:
        response = client.chat(model=model_name, messages=messages, options=options)
        if "message" in response and "content" in response["message"]:
            return {"model": model_name, "response": response["message"]["content"]}
        else:
            raise HTTPException(status_code=500, detail="Invalid response structure from model")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class GenerateRequest(BaseModel):
    model: str
    prompt: str

@router.post("/ollama_generate")
async def ollama_generate(request: GenerateRequest):
    try:
        response = client.generate(model=request.model, prompt=request.prompt)
        return {"model": request.model, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class VisionRequest(BaseModel):
    model: str
    image_path: str
    prompt: str

@router.post("/ollama_vision_prompt")
async def ollama_vision_prompt(request: VisionRequest):
    try:
        response = client.vision(model=request.model, image_path=request.image_path, prompt=request.prompt)
        return {"model": request.model, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class Message(BaseModel):
    role: str
    content: str

class CopilotRequest(BaseModel):
    model: str
    messages: List[Message]
    options: Optional[Dict[str, float]] = None
    
@router.post("/ollama_copilot_prompt")
async def ollama_copilot_prompt(request: CopilotRequest):
    model_name = request.model
    messages = request.messages
    options = request.options or {}
    print(f"Model: {model_name}, Messages: {messages}, Options: {options}")

    try:
        print("Generating response...")
        response = ollama.chat(model=model_name, messages=messages, **options)
        print(f"Response: {response}")
        if "message" in response and "content" in response["message"]:
            print(f"Response: {response['message']['content']}")
            return {"model": model_name, "response": response["message"]["content"]}
        else:
            print(f"Invalid response structure from model: {response}")
            raise HTTPException(status_code=500, detail="Invalid response structure from model")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))