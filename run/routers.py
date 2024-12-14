# route_setup.py
from fastapi import FastAPI

# Import all routers here
from routers.health import router as health_router
from routers.msgraph import router_onenote
from routers.dev.tests import timetable_test
from routers.database import admin
from routers.database.init import entity_init, calendar, timetables, curriculum, get_data
from routers.database.tools import get_nodes, get_nodes_and_edges, tldraw_filesystem, reactflow_router, get_events
from routers.transcribe import utterance
from routers.llm.private.ollama import ollama
from routers.llm.public.openai import openai
from routers.connections.arbor_router import router as arbor_router
from routers.langchain.neo4j_graph_qa import router as graph_qa_router
from routers.langchain.interactive_langgraph_query import router as interactive_langgraph_query_router
from routers.rpi import rpi_whisperlive_client
from routers.external import youtube

def register_routes(app: FastAPI):
    # Health check route
    app.include_router(health_router, prefix="/api", tags=["Health"])

    # Microsoft Graph Routes
    app.include_router(router_onenote.router, prefix="/api/msgraph", tags=["Microsoft Graph"])

    # Database Routes
    app.include_router(admin.router, prefix="/api/database/admin", tags=["Admin"])
    app.include_router(get_data.router, prefix="/api/database/upload", tags=["Upload"])
    app.include_router(get_events.router, prefix="/api/calendar", tags=["Calendar"])
    app.include_router(get_nodes.router, prefix="/api/database/tools", tags=["Tools"])
    app.include_router(entity_init.router, prefix="/api/database/entity", tags=["Entity"])
    app.include_router(get_nodes_and_edges.router, prefix="/api/database/tools", tags=["Tools"])
    app.include_router(reactflow_router.router, prefix="/api/database/tools", tags=["Tools"])
    app.include_router(calendar.router, prefix="/api/database/calendar", tags=["Calendar"])
    app.include_router(timetables.router, prefix="/api/database/timetables", tags=["Timetables"])
    app.include_router(curriculum.router, prefix="/api/database/curriculum", tags=["Curriculum"])

    # Database Filesystem Routes
    app.include_router(tldraw_filesystem.router, prefix="/api/database/tldraw_fs", tags=["TLDraw Filesystem"])

    # Transcription Routes
    app.include_router(utterance.router, prefix="/api/transcribe/utterance", tags=["Utterance"])

    # LLM Routes
    app.include_router(ollama.router, prefix="/api/llm/private/ollama", tags=["LLM"])
    app.include_router(openai.router, prefix="/api/llm/public/openai", tags=["LLM"])

    # Langchain Routes
    app.include_router(graph_qa_router, prefix="/api/langchain/graph_qa", tags=["Langchain"])
    app.include_router(interactive_langgraph_query_router, prefix="/api/langchain/interactive_langgraph_query", tags=["Langchain"])

    # External Routes
    app.include_router(youtube.router, prefix="/api/external", tags=["External"])

    # Arbor Data Routes
    app.include_router(arbor_router, prefix="/api/arbor", tags=["Arbor Data"])

    # RPi Routes
    app.include_router(rpi_whisperlive_client.router, prefix="/api/rpi", tags=["RPi"])

    # Test Routes
    app.include_router(timetable_test.router, prefix="/api/tests", tags=["Tests"])
