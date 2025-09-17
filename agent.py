import os
import json
import logging
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext
from livekit.plugins import google
from tools import get_weather, web_search
from prompt import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from mem0 import AsyncMemoryClient

# -------------------------
# Logging Configuration
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------
# Load Environment Variables
# -------------------------
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not GOOGLE_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in .env file!")
if not MEM0_API_KEY:
    raise RuntimeError("Missing MEM0_API_KEY in .env file!")
if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
    raise RuntimeError("Missing LIVEKIT configuration in .env file!")

# -------------------------
# Agent Definition
# -------------------------
class Assistant(Agent):
    def __init__(self, chat_cxt=None) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            tools=[get_weather, web_search],
        )
        self.chat_cxt = chat_cxt


# -------------------------
# Shutdown Hook
# -------------------------
async def shutdown_hook(session: AgentSession, mem0: AsyncMemoryClient, user_name: str):
    logging.info("Shutting down, saving chat context to memories...")

    message_formatted = []
    try:
        # ✅ Correct way: access ChatContext messages
        chat_ctx = session._chat_ctx
        messages = getattr(chat_ctx, "_messages", [])

        for item in messages:
            if not hasattr(item, "content") or not hasattr(item, "role"):
                continue

            # ensure text is always string
            content_str = (
                "".join(item.content) if isinstance(item.content, list) else str(item.content)
            )

            if item.role in ["user", "assistant"]:
                message_formatted.append({
                    "role": item.role,
                    "content": content_str.strip()
                })

        # ✅ Actually save into Mem0
        if message_formatted:
            await mem0.add(message_formatted, user_id=user_name)
            logging.info("✅ Successfully saved chat context to memories")
        else:
            logging.warning("⚠️ No messages to save to memory")

    except Exception as e:
        logging.error(f"❌ Failed to save chat context: {e}")


# -------------------------
# Entrypoint
# -------------------------
async def entrypoint(ctx: agents.JobContext):
    user_name = "Vicky"

    # -------------------------
    # LLM Setup
    # -------------------------
    try:
        gemini_model = google.beta.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",
            voice="Puck",
            temperature=0.8,
            instructions=AGENT_INSTRUCTION,
            max_output_tokens=2048,
        )
        logging.info("✅ Successfully initialized Gemini model")
    except Exception as e:
        logging.error(f"❌ Failed to initialize Gemini model: {e}")
        raise RuntimeError(f"Gemini model initialization failed: {e}")

    session = AgentSession(llm=gemini_model)

    # -------------------------
    # Memory Client
    # -------------------------
    try:
        mem0 = AsyncMemoryClient(api_key=MEM0_API_KEY)
        results = await mem0.get_all(user_id=user_name)
        logging.info("✅ Memory client initialized successfully")
    except Exception as e:
        logging.error(f"⚠️ Failed to initialize memory client: {e}")
        mem0 = None
        results = []

    initial_ctx = ChatContext()

    if results:
        memories = [
            {"memory": result["memory"], "updated_at": result["updated_at"]}
            for result in results
        ]
        memory_str = json.dumps(memories)
        logging.info(f"Loaded Memories: {memory_str}")

        initial_ctx.add_message(
            role="assistant",
            content=f"The user's name is {user_name}, and this is relevant context about him: {memory_str}.",
        )

    # -------------------------
    # Start Session
    # -------------------------
    await session.start(
        room=ctx.room,
        agent=Assistant(chat_cxt=initial_ctx),
        room_input_options=RoomInputOptions(
            audio_enabled=True,
            video_enabled=False
        ),
    )

    await ctx.connect()

    try:
        await session.generate_reply(instructions=SESSION_INSTRUCTION)
    except Exception as e:
        logging.error(f"❌ Error during reply generation: {e}")

    # -------------------------
    # Shutdown Callback
    # -------------------------
    async def shutdown_wrapper():
        if mem0:
            await shutdown_hook(session, mem0, user_name)

    ctx.add_shutdown_callback(shutdown_wrapper)


# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )
