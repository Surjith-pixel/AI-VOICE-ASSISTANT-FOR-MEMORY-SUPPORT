import logging
import json
import os
from dotenv import load_dotenv
from mem0 import MemoryClient
from livekit.agents import function_tool, RunContext

# -------------------------
# Load env + setup
# -------------------------
load_dotenv()
MEM0_API_KEY = os.getenv("MEM0_API_KEY")
USER_NAME = os.getenv("USER_NAME", "David")

if not MEM0_API_KEY:
    raise RuntimeError("❌ Missing MEM0_API_KEY in .env")

mem0 = MemoryClient(api_key=MEM0_API_KEY)


# -------------------------
# Add memory
# -------------------------
@function_tool()
async def add_memory(context: RunContext, messages: list) -> str:
    """
    Save a list of messages to memory.
    Args:
        messages (list): [{"role": "user", "content": "Hi"}]
    """
    if not messages:
        logging.warning("⚠️ No messages provided to save")
        return "No messages to save"

    try:
        mem0.add(messages, user_id=USER_NAME)
        logging.info(f"✅ Saved {len(messages)} messages to memory for {USER_NAME}")
        return f"Saved {len(messages)} messages to memory"
    except Exception as e:
        logging.error(f"❌ Failed to add memory: {e}")
        return f"Error saving memory: {e}"


# -------------------------
# Search memory
# -------------------------
@function_tool()
async def search_memory(context: RunContext, query: str) -> str:
    """
    Search the user's memory with a query.
    Args:
        query (str): Search string
    """
    try:
        results = mem0.search(query, user_id=USER_NAME)
        memories = [
            {"memory": r["memory"], "updated_at": r["updated_at"]}
            for r in results
        ]
        return json.dumps(memories, indent=2)
    except Exception as e:
        logging.error(f"❌ Failed to search memories: {e}")
        return f"Error searching memory: {e}"


# -------------------------
# Get all memories
# -------------------------
@function_tool()
async def get_all_memories(context: RunContext) -> str:
    """
    Retrieve all stored memories for the user.
    """
    try:
        results = mem0.get_all(user_id=USER_NAME)
        memories = [
            {"memory": r["memory"], "updated_at": r["updated_at"]}
            for r in results
        ]
        return json.dumps(memories, indent=2)
    except Exception as e:
        logging.error(f"❌ Failed to fetch memories: {e}")
        return f"Error getting memories: {e}"
