# Frontend Guide

How to set up, run, and understand the React UI for ADK RAG.

---

## Setup

### Prerequisites

- Node.js 18 or later
- npm 9 or later
- Backend running at `http://localhost:8000`

### Install and run

```bash
cd frontend
npm install
npm run dev
```

The UI is available at **http://localhost:5173**.

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`, so the frontend and backend are on different ports without CORS issues during development.

---

## Application Flow

```
1. App loads → UserIdModal appears (blocks the app)
2. User enters User ID → modal closes, main app renders
3. Main app shows: Header + Sub-header + Tab navigation
4. User switches between tabs:
   - Upload     → UploadTab
   - Documents  → DocumentsTab
   - Ingestion  → IngestionTab
   - Chat       → ChatTab
5. "Switch" button in header → returns to UserIdModal
```

---

## Component Reference

### `UserIdModal`

**Shown on**: app load  
**Purpose**: Prompts for a User ID before allowing access to the workspace.

- Validates: minimum 3 characters, non-empty
- Displays animated background blobs for visual interest
- The entered User ID is stored in React state and passed to all child components
- Does not authenticate — for production, replace with real auth

---

### `Header`

**Always visible**: sticky at the top of the page

Contains:
- **Brand** — app name (gradient text) and tagline
- **API status chip** — green dot if `/health` returns OK, red dot if offline
- **User badge** — shows active User ID with avatar initial
- **Switch button** — resets user ID and returns to the modal

**Sub-header strip**:
- Technology badges: Google ADK, Gemini Embeddings, Pinecone DB
- Model info: `gemini-2.5-pro` + `gemini-embedding-001`

---

### `Tabs`

Four tabs with icons, labels, and descriptions:

| Tab ID | Label | Icon | Description |
|--------|-------|------|-------------|
| `upload` | Upload | 📤 | Add documents |
| `documents` | Documents | 📂 | Manage & delete |
| `ingestion` | Ingestion Pipeline | ⚙️ | Pipeline status |
| `chat` | Chat | 💬 | Ask questions |

Tabs use ARIA roles (`role="tab"`, `role="tabpanel"`) for accessibility.

---

### `UploadTab`

**Path**: `src/components/UploadTab.jsx`

Features:
- **Drag-and-drop zone** — click to browse or drag a file onto the zone
- **File preview** — shows filename, size, and file type icon after selection
- **Format tags** — lists all supported extensions as badges
- **Upload button** — sends file to `POST /documents/upload`
- **Pipeline progress** — animated steps shown during upload: Extract → Chunk → Embed → Store
- **Result card** — shows document_id, filename, chunks_created, characters_extracted after success
- **Error display** — shows validation errors and API errors

Supported types are validated client-side before upload to give instant feedback.

---

### `DocumentsTab`

**Path**: `src/components/DocumentsTab.jsx`

Features:
- **Auto-loads** documents on mount via `GET /documents`
- **Refresh button** — manually re-fetches the document list
- **Document cards** — each shows: file icon, filename, chunk count badge, document ID (truncated)
- **Delete flow** — clicking Delete shows a confirmation row (Yes / Cancel) before calling `DELETE /documents/{id}`
- **Empty state** — message when no documents exist
- **Error display** — shows API errors

---

### `IngestionTab`

**Path**: `src/components/IngestionTab.jsx`

Features:
- **Stat cards** (4 cards):
  - Pipeline Status (Ready / Error)
  - Total Chunks Stored (from `/ingest/status`)
  - Supported File Types (count)
  - Embedding Dimensions (768, static)
- **Pipeline diagram** — vertical step-by-step view with connector lines:
  1. Text Extraction
  2. Text Normalization & Chunking
  3. Gemini Embedding Generation
  4. Pinecone DB Vector Storage
- **File type matrix** — table with extension, parser, notes, and status for all 13 supported types

---

### `ChatTab`

**Path**: `src/components/ChatTab.jsx`

Features:
- **Suggested questions** — clickable chips shown when the chat is empty
- **Message history** — scrollable list of user + assistant messages
- **Typing indicator** — animated dots while waiting for the agent response
- **Session management** — session ID is maintained across messages; "New session" button resets it
- **Source citation rendering** — `[Source: …]` patterns are highlighted in teal
- **Session badge** — shows "Session active" badge when a session exists
- **Keyboard shortcut** — Enter to send, Shift+Enter for new line
- **Auto-scroll** — scrolls to the latest message automatically

---

### `ChatMessage`

**Path**: `src/components/ChatMessage.jsx`

Renders a single message bubble:
- **User messages** — right-aligned, purple gradient bubble
- **Assistant messages** — left-aligned, glass card bubble
- **Error messages** — centered, red tinted
- **Citations** — `[Source: …]` fragments highlighted as teal monospace badges
- **Timestamps** — shown below each bubble

---

## API Utility (`src/api.js`)

All HTTP calls go through `src/api.js`:

```javascript
import { listDocuments, uploadDocument, deleteDocument, sendMessage, getIngestStatus, checkHealth } from './api.js'
```

All functions accept a `userId` parameter and automatically inject the `x-user-id` header.

Errors are thrown as `Error` objects with the API `detail` message.

---

## Building for Production

```bash
cd frontend
npm run build
# Output: frontend/dist/
```

Serve `frontend/dist/` with any static hosting (Nginx, Vercel, Firebase Hosting, etc.) and set the backend URL in the Vite proxy or an environment variable.

---

## Customizing the Design

The design system is in `src/index.css`. All CSS custom properties are declared under `:root`:

```css
:root {
  --accent-primary:   #6c63ff;   /* purple-blue */
  --accent-secondary: #00d4aa;   /* teal */
  --bg-primary:       #07071a;   /* dark background */
  /* ... */
}
```

Change these values to retheme the entire app.
