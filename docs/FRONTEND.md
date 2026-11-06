# Frontend Application Guide

The frontend (`frontend/`) is a **React 18 + Vite** single-page application styled with a **Bioluminescent Neural Forest Theme** (`#06120f` deep twilight pine canvas, `bg-neural-tree.jpg` Tree of Knowledge backdrop, translucent emerald glass cards, Bioluminescent Cyan `#22d3ee` and Firefly Root Gold `#fbbf24` accents) and an interactive SVG **Knowledge Graph Explorer**.

---

## Component Hierarchy

```mermaid
flowchart TD
    Main["main.jsx"] --> App["App.jsx\n(Root Auth & Tab State)"]
    App -->|Unauthenticated| AuthModal["UserIdModal.jsx\n(Neon PostgreSQL Sign In / Create Account)"]
    App -->|Authenticated| Header["Header.jsx\n(Status Pill, User Profile, Sign Out)"]
    App -->|Authenticated| Tabs["Tabs.jsx\n(5-Tab Navigation Bar)"]
    Tabs --> T1["1. UploadTab.jsx\n(Drag & Drop File Upload)"]
    Tabs --> T2["2. IngestionTab.jsx\n(Live 5-Step Progress & DB Metrics)"]
    Tabs --> T3["3. DocumentsTab.jsx\n(Document List & Cascade Delete)"]
    Tabs --> T4["4. ChatTab.jsx + ChatMessage.jsx\n(Agentic Chat with Tool Badges & Citations)"]
    Tabs --> T5["5. GraphTab.jsx\n(Interactive SVG Neo4j Knowledge Graph)"]
```

---

## Component Reference (`frontend/src/components/`)

| Component | File | Description |
|-----------|------|-------------|
| **Authentication Screen** | `UserIdModal.jsx` | Full Sign In / Create Account interface backed by `/auth/login` and `/auth/signup` on Neon PostgreSQL. Stores the returned JWT in `localStorage`. |
| **Top Header** | `Header.jsx` | Sticky top bar displaying the application title, real-time `API Ready` / `API Offline` indicator, signed-in user's name and email, and a **Sign Out** button. |
| **Tab Navigation** | `Tabs.jsx` | Five-tab bar ordered: `Upload` → `Ingestion Pipeline` → `Documents` → `Agentic Chat` → `Knowledge Graph`. Displays live count badges on **Documents** and **Knowledge Graph**. |
| **Upload Tab** | `UploadTab.jsx` | Drag-and-drop file selector supporting 12 document formats. Automatically redirects to the **Ingestion Pipeline** tab as soon as an upload starts. |
| **Ingestion Pipeline Tab** | `IngestionTab.jsx` | Polls `GET /ingest/progress` every `800ms` during upload so only the active step spins (`In Progress...`), finished steps show green checkmarks (`Completed`), and upcoming steps show `Queued`. Also displays Neon PostgreSQL & Neo4j metrics and the dual storage architecture diagram. |
| **Documents Tab** | `DocumentsTab.jsx` | Lists all documents owned by the user with chunk, entity, and relationship counts, plus one-click cascade deletion across Neon PostgreSQL and Neo4j. |
| **Agentic Chat Tab** | `ChatTab.jsx` & `ChatMessage.jsx` | Multi-turn chat interface with suggested starter prompts, animated typing indicators, tool execution badges (`hybrid_search`, `vector_search`, `graph_search`, `get_entity_relationships`), and highlighted `[Source: ...]` / `[Graph: ...]` citations. |
| **Knowledge Graph Tab** | `GraphTab.jsx` | Interactive SVG radial/force-layout canvas for exploring Neo4j `:Entity` nodes and `:RELATES_TO` edges, complete with category filter pills, real-time keyword search, zoom controls, a 1-hop Entity Inspector drawer, and a structured triplets table. |

---

## Design System (`frontend/src/index.css`)

The UI uses CSS custom properties defined in `frontend/src/index.css`:

| Token | Value | Purpose |
|-------|-------|---------|
| `--bg-primary` | `#06120f` | Deep twilight forest base canvas |
| `--bg-card` | `rgba(10, 27, 22, 0.82)` | Translucent blurred emerald-pine glass cards |
| `--border-subtle` | `rgba(52, 211, 153, 0.20)` | Subtle bioluminescent emerald border |
| `--accent-primary` | `#22d3ee` | Primary Bioluminescent Neural Cyan accent |
| `--accent-secondary` | `#fbbf24` | Secondary Firefly Root Gold accent |
| `--accent-success` | `#34d399` | Living Canopy Emerald (completed pipeline steps & online health badges) |
| `--accent-danger` | `#f87171` | Error alerts and delete actions |
| `--text-primary` | `#ecfdf5` | High-contrast bioluminescent mint-ivory primary text |
| `--text-secondary` | `#a7d7c5` | Soft sage-cyan secondary descriptions and metadata |

---

## API Client (`frontend/src/api.js`)

All HTTP calls are centralized in `frontend/src/api.js`:
- Automatically attaches `Authorization: Bearer <jwt_token>` from `localStorage`.
- Automatically clears expired sessions on `HTTP 401` and dispatches an `adk_auth_expired` window event so `App.jsx` smoothly returns the user to the Sign In page.
