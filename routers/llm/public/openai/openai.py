from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from openai import OpenAI
import os
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instantiate the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class CopilotRequest(BaseModel):
    model: str
    messages: List[Message]
    options: Optional[Dict[str, float]] = None

@router.post("/openai_copilot_prompt")
async def openai_copilot_prompt(request: CopilotRequest):
    logging.info("Received request: %s", request.model_dump_json())
    try:
        response = client.chat.completions.create(
            model=request.model,
            messages=[{"role": msg.role, "content": msg.content} for msg in request.messages],
            **(request.options or {})
        )
        logging.info("Received response: %s", response)
        return {"model": request.model, "response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GeneralOpenAIRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stop: Optional[List[str]] = None

@router.post("/openai_general_prompt")
async def openai_general_prompt(request: GeneralOpenAIRequest):
    logging.info("Received general request: %s", request.model_dump_json())
    try:
        if "gpt-4" in request.model or "gpt-3.5" in request.model:
            messages = [{"role": "user", "content": request.prompt}]
            response = client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                n=request.n,
                stop=request.stop
            )
            return {"model": request.model, "response": response.choices[0].message.content}
        else:
            response = client.completions.create(
                model=request.model,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                n=request.n,
                stop=request.stop
            )
            return {"model": request.model, "response": response.choices[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
