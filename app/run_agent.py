import asyncio

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.agent import root_agent

APP_NAME = "document_rag_app"

async def main():
    user_id = "user_123"

    session_service = InMemorySessionService()

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
    )

    question = "Why Self-Attention?"

    message = types.Content(
        role="user",
        parts=[
            types.Part(text=question)
        ],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response():
            print(event.content)

if __name__ == "__main__":
    asyncio.run(main())