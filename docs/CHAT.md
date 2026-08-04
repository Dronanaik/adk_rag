# Chat System

How the Google ADK agent works, session lifecycle, tool calling flow, and example conversations.

---

## Overview

The chat system is powered by **Google ADK** (`google-adk`). It uses an `LlmAgent` backed by `gemini-2.5-pro` that has access to one custom tool: `search_user_documents`.

```
User asks question
        ↓
FastAPI POST /chat
        ↓
ADK Runner.run_async(user_id, session_id, message)
        ↓
LlmAgent (gemini-2.5-pro) decides to call tool
        ↓
search_user_documents(query, tool_context)
        ↓
embed query → ChromaDB search (filtered by user_id)
        ↓
Top-K relevant chunks returned to agent
        ↓
Agent generates answer with source citations
        ↓
Final response returned to user
```

---

## Agent Configuration

**File**: `app/agent.py`

```python
root_agent = LlmAgent(
    name="document_rag_agent",
    model="gemini-2.5-pro",
    description="Answers questions using the user's uploaded documents.",
    instruction="""...""",
    tools=[search_user_documents],
)
```

### Agent instructions (system prompt)

The agent is instructed to:

1. Use the `search_user_documents` tool for any question that may require document content
2. Answer only using retrieved document content
3. Never invent facts not present in the retrieved chunks
4. Say "I could not find that information" when documents don't contain the answer
5. Include source citations in the format `[Source: filename, chunk N]`
6. Cite all relevant sources when multiple chunks support an answer
7. Never reveal documents from another user

---

## The `search_user_documents` Tool

```python
def search_user_documents(query: str, tool_context: ToolContext) -> dict:
```

The tool:
1. Reads `user_id` from `tool_context.user_id` (injected by the ADK runner — not user-controlled)
2. Validates that a user ID exists
3. Calls `search_documents(user_id, query, top_k=5)`
4. Returns a structured dict of source chunks with metadata

**Return format when found**:

```json
{
  "found": true,
  "sources": [
    {
      "source_number": 1,
      "filename": "research.pdf",
      "document_id": "550e8400...",
      "chunk_index": 3,
      "distance": 0.142,
      "text": "The study found that..."
    }
  ]
}
```

**Return format when not found**:

```json
{
  "found": false,
  "message": "No relevant document content was found.",
  "sources": []
}
```

---

## Session Lifecycle

ADK uses sessions to maintain conversation history (multi-turn chat).

### In-memory sessions

The `InMemorySessionService` keeps sessions in memory for the lifetime of the server process.

```python
_session_service = InMemorySessionService()
_runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=_session_service)
```

### Session creation

- When `session_id` is `null` in the request → a **new session** is created
- When `session_id` is provided → the existing session is reused

The session ID is returned in every `/chat` response. Pass it back in the next request to continue the conversation.

### Session expiry

Sessions are lost when the backend server restarts. There is no persistence by default. For persistent sessions, replace `InMemorySessionService` with a database-backed implementation.

---

## Example Conversations

### Single-turn Q&A

**Request**:
```json
POST /chat
x-user-id: drona

{
  "query": "What programming languages are mentioned in the document?"
}
```

**Response**:
```json
{
  "answer": "Based on your uploaded documents, the following programming languages are mentioned:\n\n- Python\n- JavaScript\n- Go\n\n[Source: resume.pdf, chunk 2]\n[Source: resume.pdf, chunk 5]",
  "session_id": "abc123-def456-789"
}
```

---

### Multi-turn conversation

**Turn 1**:
```json
{"query": "What is the document about?"}
```
```json
{"answer": "The document is a research paper about...", "session_id": "session-xyz"}
```

**Turn 2** (reusing session):
```json
{"query": "What were the main findings?", "session_id": "session-xyz"}
```
```json
{"answer": "Building on the overview I gave, the main findings are...", "session_id": "session-xyz"}
```

The agent has access to the previous conversation in turn 2.

---

## When No Documents Are Found

If the user has no uploaded documents or the query doesn't match any chunks, the agent responds:

> "I could not find that information in the uploaded documents."

This happens when:
- No documents have been uploaded for this user
- The query is too dissimilar to any stored chunk
- `TOP_K` results were all retrieved but none were relevant

---

## Running the Agent via CLI

For testing without the API, use `app/run_agent.py`:

```python
# app/run_agent.py
user_id = "user_123"
question = "Why Self-Attention?"
```

```bash
python -m app.run_agent
```

This creates a session, sends one question, and prints the agent's final response.

---

## Customizing the Agent

### Change the LLM model

In `app/agent.py`:
```python
root_agent = LlmAgent(
    model="gemini-2.5-flash",  # faster, lower cost
    ...
)
```

### Change the number of retrieved chunks

In `.env`:
```env
TOP_K=10
```

### Add more tools

Additional tools can be added to the `tools` list:
```python
tools=[search_user_documents, another_tool],
```
