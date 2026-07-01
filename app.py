import importlib.util
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent
MCP_SERVER = REPO_ROOT / "scripts" / "mcpServer.py"

_spec = importlib.util.spec_from_file_location("mcpServer", MCP_SERVER)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules["mcpServer"] = _mod
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

agent_executor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_executor

    gen_chunks_tool = StructuredTool.from_function(
        func=_mod.gen_chunks,
        name="gen_chunks",
        description=_mod.gen_chunks.__doc__,
    )
    run_pipeline_tool = StructuredTool.from_function(
        func=_mod.run_pipeline,
        name="run_pipeline",
        description=_mod.run_pipeline.__doc__,
    )

    rchat_key = os.getenv("RCHAT_API_KEY")
    rchat_model = "gemma-4-31B-it"
    raw_endpoint = "https://rchat.nist.gov/api/v1/chat/completions"
    clean_base_url = raw_endpoint.replace("/chat/completions", "")

    rchat_llm = ChatOpenAI(
        model=rchat_model,
        api_key=rchat_key,
        base_url=clean_base_url,
        temperature=0.0,
    )

    mcp_client = MultiServerMCPClient({
        "ncnr-api-server": {
            "transport": "stdio",
            "command": "npx.cmd",
            "args": [
                "--yes",
                "@ivotoby/openapi-mcp-server",
                "--api-base-url", "https://ncnr.nist.gov/ncnrdata/metadata/api/v1",
                "--openapi-spec", str(REPO_ROOT / "openAPI.json"),
            ],
        },
    })

    print("Connecting to MCP servers...")
    tools = await mcp_client.get_tools() + [gen_chunks_tool, run_pipeline_tool]

    system_instruction = (
        "You are an intelligent data router for the NIST Center for Neutron Research (NCNR).\n"
        "You have access to structured API databases and an unstructured RAG vector database.\n\n"
        "Available tools:\n"
        "--- STRUCTURED API TOOLS ---\n"
        "- 'search-instruments': Use this if the user asks for available, active, or listed instruments.\n"
        "- 'search-experiments': Use this if the user asks for specific research runs, IDs, or experiments.\n"
        "- 'search-datafiles': Use this if the user asks for specific files or raw data arrays.\n\n"
        "--- RAG & KNOWLEDGE TOOLS ---\n"
        "- 'gen_chunks': Use this if the user asks general knowledge questions, wants to search manuals, "
        "or asks for semantic information that requires looking up text from the local vector database.\n"
        "- 'run_pipeline': ONLY use this if the user explicitly asks you to 'ingest documents', "
        "'update the database', or 'run the pipeline'. This triggers a heavy ingestion process.\n\n"
        "CRITICAL TOOL RULES:\n"
        "1. ONLY include arguments that are explicitly requested by the user.\n"
        "2. DO NOT pass empty strings, 'None', or null for optional parameters. Omit them entirely.\n"
        "3. Do not say 'I cannot access the database'. Do not tell the user to visit a website."
    )

    memory = MemorySaver()
    agent_executor = create_agent(
        model=rchat_llm,
        tools=tools,
        system_prompt=system_instruction,
        checkpointer=memory,
    )

    print("Agent ready at http://127.0.0.1:8000")
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(REPO_ROOT / "static")), name="static")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(REPO_ROOT / "static" / "index.html", encoding="utf-8") as f:
        return f.read()


@app.post("/chat")
async def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    result = await agent_executor.ainvoke(
        {"messages": [("user", req.message)]},
        config=config,
    )
    final_msg = result["messages"][-1]
    content = final_msg.content
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return {"response": content}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
