from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

from app.config import TOP_K
from app.rag_store import search_documents

def search_user_documents(
    query: str,
    tool_context: ToolContext,
) -> dict:
    """
    Search the authenticated user's uploaded documents.

    Args:
        query: A precise search query describing the information needed.
        tool_context: ADK context containing the current user information.

    Returns:
        Relevant document chunks with source metadata.
    """

    user_id = tool_context.user_id

    if not user_id:
        return {
            "error": "User identity is missing."
        }

    matches = search_documents(
        user_id=user_id,
        query=query,
        top_k=TOP_K,
    )

    if not matches:
        return {
            "found": False,
            "message": "No relevant document content was found.",
            "sources": [],
        }

    sources = []

    for index, match in enumerate(matches, start=1):
        metadata = match["metadata"]

        sources.append(
            {
                "source_number": index,
                "filename": metadata.get("filename"),
                "document_id": metadata.get("document_id"),
                "chunk_index": metadata.get("chunk_index"),
                "distance": match["distance"],
                "text": match["text"],
            }
        )

    return {
        "found": True,
        "sources": sources,
    }

root_agent = LlmAgent(
    name="document_rag_agent",
    model="gemini-2.5-pro",
    description="Answers questions using the user's uploaded documents.",
    instruction="""
You are a document question-answering assistant.

Follow these rules:

1. Use the search_user_documents tool for questions that may require
   information from uploaded documents.

2. Answer using the retrieved document content.

3. Do not invent facts that are not present in the retrieved content.

4. If the retrieved content does not answer the question, clearly say:
   "I could not find that information in the uploaded documents."

5. Include source citations in this format:
   [Source: filename, chunk N]

6. If multiple sources support the answer, cite all relevant sources.

7. Treat the current user message as higher priority than old document
   content.

8. Never reveal documents belonging to another user.
""",
    tools=[
        search_user_documents,
    ],
)