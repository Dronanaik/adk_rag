# Design System & UX Specification (DESIGN.md)
**Product:** Agentic RAG System with Centralized Memory and Knowledge Graph  
**Version:** 1.0.0  
**Status:** Approved Baseline — Source of Truth for UI/UX Implementation  
**Reference:** Paired with `PRD.md` (v1.0.0)

---

## 1. Visual Direction and Design Principles

### 1.1 Aesthetic Direction: "Archival Research & Systems Workbench"
The interface is a **high-density, high-trust research and observability workbench**—not a consumer chatbot or a promotional SaaS landing page. It combines the editorial readability of a reference library with the structured telemetry of a developer observability tool.

**Anti-Patterns (Strictly Forbidden):**
- No neon purple/magenta/cyan "AI glow" gradients, animated sparkles, or floating 3D orbs.
- No heavy glassmorphism (`backdrop-filter` blur over busy backgrounds) or oversized drop shadows.
- No decorative illustrations or marketing fluff in empty states.
- No unbounded full-screen chat bubbles that obscure source evidence.

**Visual Signatures:**
- **Hairline Structural Grid:** Panes and cards are separated by crisp `1px solid` structural borders (`Border-Subtle`) rather than floating shadows.
- **Tri-Pillar Provenance Coding:** Every piece of evidence is visually categorized into one of three distinct, colorblind-safe provenance channels: **Document Chunks (`Doc`)**, **Knowledge Graph (`KG`)**, and **Centralized Memory (`Mem`)**.
- **Monospace Telemetry:** Agent execution timings, similarity scores, SHA-256 hashes, chunk offsets, and graph predicates use tabular monospace typography for rapid scanning.

### 1.2 Core Design Principles
1. **Evidence First, Prose Second:** A synthesized answer is only as valuable as its backing proof. Inline citations, source passages, and Knowledge Graph paths must remain visible alongside the conversation without losing scroll context.
2. **Transparent Agent Mechanics:** Users must never wonder why a response is taking several seconds. Active Google ADK agent handoffs (`Orchestrator` → `Memory` → `Vector/KG` → `Verifier`) are surfaced progressively and calmly.
3. **Honest Abstention Over Plausible Guessing:** When retrieval confidence is insufficient or the Knowledge Graph fallback is triggered, the UI communicates the boundary clearly using structured diagnostic cards rather than generic error text.
4. **Zero-Friction Inspection:** Clicking any citation pill, entity node, or memory tag immediately opens and highlights the exact backing record in the right-hand Provenance Inspector within a single click.

---

## 2. Colors and Typography

### 2.1 Color System & Semantic Tokens
The application defaults to a **Warm Editorial Light Mode** optimized for extended reading of document chunks and technical text, with a calibrated **Carbon Slate Dark Mode**.

#### Surface & Neutral Tokens
| Token Name | Role / Usage | Light Mode (Default) | Dark Mode |
| :--- | :--- | :--- | :--- |
| `Surface-Canvas` | Primary application background & reading pane | `#FAF9F6` (Warm Alabaster) | `#0F1115` (Carbon Slate) |
| `Surface-Panel` | Left sidebar, right provenance drawer, table headers | `#F3F2EE` (Stone 100) | `#161920` (Slate 900) |
| `Surface-Card` | Elevated cards, active input box, trace nodes | `#FFFFFF` (Pure White) | `#1C2029` (Slate 850) |
| `Surface-Highlight` | Active citation target highlight in chunk viewer | `#FEF3C7` (Warm Amber 100) | `#3B2F13` (Muted Gold Tint) |
| `Text-Primary` | Body copy, synthesized responses, headings | `#141413` (Ink Black) | `#F3F4F6` (Gray 100) |
| `Text-Secondary` | Metadata labels, secondary descriptions, subtitles | `#575653` (Stone 600) | `#9CA3AF` (Gray 400) |
| `Text-Muted` | Timestamps, character offsets, disabled labels | `#85847E` (Stone 400) | `#6B7280` (Gray 500) |
| `Border-Subtle` | Structural pane dividers, table rows, card borders | `#E5E4DF` (Stone 200) | `#262B36` (Slate 800) |
| `Border-Focus` | Active input ring, selected citation card border | `#1D4ED8` (Cobalt 700) | `#60A5FA` (Cobalt 400) |

#### Brand & Primary Action Tokens
| Token Name | Role / Usage | Light Mode | Dark Mode |
| :--- | :--- | :--- | :--- |
| `Action-Primary-Bg` | Primary buttons ("Submit", "Upload Documents") | `#18181B` (Zinc 900) | `#F4F4F5` (Zinc 100) |
| `Action-Primary-Text` | Text on primary buttons | `#FFFFFF` | `#18181B` |
| `Action-Hover-Bg` | Primary button hover state | `#27272A` (Zinc 800) | `#E4E4E7` (Zinc 200) |
| `Action-Secondary-Bg` | Secondary action buttons, filter pills | `#EAE9E4` (Stone 150) | `#262B36` (Slate 800) |

#### Provenance Pillar Tokens (Core Domain Identity)
To distinguish where knowledge originated, the UI uses three dedicated semantic palettes across inline citation pills, graph nodes, and trace badges:

| Provenance Pillar | Badge Prefix | Primary Accent (Text/Icon) | Surface Tint (Pill/Card Bg) | Border Accent | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Document Chunk** | `[Doc]` | `#1E40AF` (Light) / `#93C5FD` (Dark) | `#EFF6FF` (Light) / `#172554` (Dark) | `#BFDBFE` / `#1E3A8A` | Verbatim passage retrieved via `pgvector` similarity search. |
| **2. Knowledge Graph** | `[KG]` | `#065F46` (Light) / `#6EE7B7` (Dark) | `#ECFDF5` (Light) / `#064E3B` (Dark) | `#A7F3D0` / `#065F46` | Structured entity/relationship path (`Subject -> Predicate -> Object`). |
| **3. Centralized Memory** | `[Mem]` | `#92400E` (Light) / `#FCD34D` (Dark) | `#FFFBEB` (Light) / `#451A03` (Dark) | `#FDE68A` / `#78350F` | Recalled fact or constraint from Session or Long-Term Shared Memory. |

#### System Status Tokens
| Status | Usage | Foreground | Background Tint | Border |
| :--- | :--- | :--- | :--- | :--- |
| **Success / Grounded** | `GROUNDED` badge, `INDEXED` document status | `#15803D` | `#F0FDF4` | `#BBF7D0` |
| **Warning / Fallback** | `PARTIAL` grounding, KG timeout fallback, `EXTRACTING_KG` | `#B45309` | `#FFFBEB` | `#FDE68A` |
| **Danger / Error** | `FAILED` ingestion, delete confirmation, ungrounded alert | `#B91C1C` | `#FEF2F2` | `#FECACA` |
| **Info / Active Step** | `CHUNKING`, active agent execution spinner | `#1D4ED8` | `#EFF6FF` | `#BFDBFE` |

### 2.2 Typography System

#### Font Families
1. **`Font-Sans` (`Inter` or system fallback `-apple-system, BlinkMacSystemFont`):** Used for all UI controls, navigation, headings, tables, and synthesized chat responses.
2. **`Font-Mono` (`JetBrains Mono` or `IBM Plex Mono`):** Used for citation badges, Knowledge Graph predicates (`DEPENDS_ON`), similarity scores (`0.89`), latency metrics (`420ms`), UUIDs/hashes, and agent trace payloads. Must always enable `font-variant-numeric: tabular-nums`.
3. **`Font-Serif` (`Source Serif 4` or `Newsreader` — Optional for Verbatim Source Chunks):** Used inside the Source Evidence Drawer to visually distinguish raw quoted document text from AI-synthesized prose.

#### Type Scale & Hierarchy
| Style Token | Font Family | Size (rem / px) | Line Height | Weight | Letter Spacing | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Heading-XL` | `Font-Sans` | `1.5rem` (24px) | `2.0rem` (32px) | `600` (SemiBold) | `-0.02em` | Screen titles (Screens 2, 3, 4) |
| `Heading-LG` | `Font-Sans` | `1.125rem` (18px) | `1.625rem` (26px) | `600` (SemiBold) | `-0.01em` | Section headers, Drawer titles, Modal headers |
| `Heading-MD` | `Font-Sans` | `0.9375rem` (15px) | `1.375rem` (22px) | `600` (SemiBold) | `0em` | Card titles, Entity canonical names, Sub-headings |
| `Body-Prose` | `Font-Sans` | `0.9375rem` (15px) | `1.6rem` (25.6px) | `400` (Regular) | `0em` | Assistant synthesized responses, user queries (max width `68ch`) |
| `Body-UI` | `Font-Sans` | `0.875rem` (14px) | `1.25rem` (20px) | `400` / `500` | `0em` | Table cells, form inputs, sidebar items, buttons |
| `Caption-Meta` | `Font-Sans` | `0.75rem` (12px) | `1.0rem` (16px) | `500` (Medium) | `+0.01em` | Column headers (uppercase), field helper text, timestamps |
| `Code-Telemetry` | `Font-Mono` | `0.75rem` (12px) | `1.125rem` (18px) | `500` (Medium) | `0em` | Citation pills, KG predicates, scores, trace latency, chunk offsets |

---

## 3. Spacing and Layout System

### 3.1 Base Spacing Scale (4px Grid)
All padding, margins, gaps, and component dimensions must snap to the 4px spatial scale:
- `space-1`: `4px` — Inline icon-to-text gap inside citation pills and badges.
- `space-2`: `8px` — Compact vertical list spacing, button internal vertical padding, tag gaps.
- `space-3`: `12px` — Default card internal padding (compact), form input padding, table cell vertical padding.
- `space-4`: `16px` — Standard card padding, panel header padding, grid gap between cards.
- `space-6`: `24px` — Section separation inside screens, chat turn vertical spacing, drawer padding.
- `space-8`: `32px` — Page container outer padding on desktop views.
- `space-12`: `48px` — Major layout block separation and empty-state vertical padding.

### 3.2 Structural App Shell
The application uses a **fixed viewport shell (`100vh` / `100dvh`, `overflow: hidden`)** with independent scrolling panes so navigation and provenance context never scroll off-screen:
1. **Top Global Utility Bar (`height: 48px`):** Displays Application Identity, Primary Screen Switcher (`Research Workspace`, `Knowledge Base`, `KG & Memory Explorer`, `Settings`), Active Role Selector (`Researcher` / `Knowledge Admin`), and System Connectivity Dot.
2. **Left Context Rail (`width: 260px`, Collapsible):** Used in Screen 1 for session history and memory scope controls, or in Screen 3 for entity/memory filtering.
3. **Center Primary Stage (`flex: 1`, `min-width: 480px`):** Independent vertical scroll container. Content within the reading column is centered and constrained to `max-width: 780px` for optimal reading ergonomics; data tables in Screens 2 and 3 expand to `max-width: 1280px`.
4. **Right Provenance & Trace Inspector (`width: 420px`, Resizable `360px–560px`, Collapsible):** Persistent side panel in Screen 1 and Screen 3 for inspecting verbatim chunks, KG subgraphs, and agent execution traces.

### 3.3 Border Radius & Elevation Rules
- `radius-sm` (`4px`): Inline citation pills, status badges, monospace predicate tags.
- `radius-md` (`6px`): Buttons, form inputs, select dropdowns, trace step cards.
- `radius-lg` (`8px`): Primary content cards, modals, upload dropzone, abstention callout cards.
- **Elevation:** Use `1px solid Border-Subtle` for 95% of containment. Reserve subtle elevation (`0 4px 12px rgba(0, 0, 0, 0.06)`) strictly for floating dropdown menus, tooltips, and slide-over drawers on smaller screens.

---

## 4. Reusable Components

### 4.1 Inline Provenance Citation Badge
- **Purpose:** Anchors every factual claim in an assistant response to its backing source (`FR-18`).
- **Anatomy:** Compact pill (`height: 20px`, `padding: 0 6px`, `radius-sm`, `Font-Mono 12px`) placed immediately after a sentence or clause.
- **Variants:**
  - **Document Citation:** `[Doc: Architecture.pdf #14]` in Cobalt (`[Doc]` palette).
  - **Knowledge Graph Citation:** `[KG: ServiceA → DEPENDS_ON → AuthDB]` in Emerald (`[KG]` palette).
  - **Memory Citation:** `[Mem: #M-042]` in Amber (`[Mem]` palette).
- **States:** Default, Hover (darkens border and displays a quick preview tooltip with the first 120 characters of the snippet), Active/Selected (adds `2px solid Border-Focus` and opens/scrolls the Right Inspector to that exact item).

### 4.2 Live Agent Activity Stepper
- **Purpose:** Provides real-time visibility into the 5-agent Google ADK workflow during query execution (`NFR-01`, `FR-20`).
- **Anatomy:** Horizontal or compact vertical accordion banner positioned directly above the streaming response.
- **Steps Displayed:**
  1. `Orchestrator` — Decomposing query & checking constraints
  2. `Memory Agent` — Recalling session & shared long-term facts (`N hits`)
  3. `Vector + KG Agents` — Retrieving top chunks (`K chunks`) & traversing 1–2 hop subgraph (`M edges`)
  4. `Synthesis Verifier` — Grounding claims & verifying citations
- **Behavior:** Active step shows a subtle pulsing dot and elapsed millisecond counter (`Font-Mono`). Once the turn completes, the banner collapses into a single summary bar: *"Grounded via 4 Doc Chunks, 2 KG Paths, 1 Shared Memory • 5 steps in 3.4s — [View Trace]"*.

### 4.3 Verbatim Source Evidence Card
- **Purpose:** Displays the exact document chunk inside Tab 1 of the Right Inspector (`FR-19`).
- **Anatomy:**
  - **Header:** Document icon, `Document.title`, Page/Section badge, and Similarity Score pill (`Score: 0.87` in `Font-Mono`).
  - **Body:** Verbatim chunk text rendered in `Font-Serif` (or clean `Font-Sans`) with the matched passage highlighted using `Surface-Highlight` and character offsets (`chars 1,420–2,110`) in `Caption-Meta`.
  - **Footer:** List of canonical KG Entity pills extracted from this specific chunk; clicking any entity pill switches to the Knowledge Graph tab centered on that node.

### 4.4 Knowledge Graph Triple & Subgraph Viewer
- **Purpose:** Makes multi-hop graph connections legible without overwhelming 3D visual clutter (`FR-03`, `FR-15`, `Section 10.2`).
- **Dual Representation:**
  1. **Structured Path List (Default & Accessible):** Renders each retrieved relationship as a horizontal flow row: `[Source Entity Pill]` ──`PREDICATE_TYPE`──▶ `[Target Entity Pill]` accompanied by a link to its backing `[Doc Chunk]` and confidence score.
  2. **2D Local Neighborhood Canvas (Interactive):** Clean, force-directed 2D node-link diagram bounded strictly to the active 1–2 hop subgraph (max ~25 nodes). Nodes are color-coded by `entity_type`; seed entities from the query have a double border ring. Includes `Zoom In`, `Zoom Out`, and `Fit View` controls.

### 4.5 Centralized Memory Entry Card
- **Purpose:** Displays and manages working, session, and shared long-term memories (`FR-07`–`FR-11`).
- **Anatomy:**
  - **Top Row:** Memory Tier badge (`SESSION`, `LONG-TERM SEMANTIC`, `LONG-TERM EPISODIC`), timestamp, and `Forget / Delete` icon button.
  - **Content:** Concise atomic fact or episodic summary statement.
  - **Provenance Footer:** Originating session/turn link (`Turn #12`), supporting `[Doc Chunk]` badges, related `KGEntity` tags, and a `Superseded by #M-089` muted badge if updated (`FR-09`).

### 4.6 Grounding Status & Abstention Callout Card
- **Purpose:** Clearly communicates the `grounding_status` (`GROUNDED`, `PARTIAL`, `INSUFFICIENT_EVIDENCE`) of a turn (`US-05`, `NFR-04`).
- **Variants:**
  - **`GROUNDED`:** Subtle green check badge in the turn footer (`All claims verified against 4 sources`).
  - **`PARTIAL` (Fallback):** Amber banner at the top of the response explaining which subsystem degraded (e.g., *"Knowledge Graph traversal timed out; response is grounded solely in document vector chunks"* or *"Orchestrator reached max 5-step limit; partial findings shown below"*).
  - **`INSUFFICIENT_EVIDENCE` (Abstention):** Neutral-amber structured diagnostic card replacing speculative prose. Lists: (1) Why the system abstained, (2) Closest entities/terms searched, and (3) Actionable next steps (e.g., *"Upload source documents covering [Topic]"*).

---

## 5. Navigation and Forms

### 5.1 Navigation Architecture
- **Primary Navigation (Top Bar):** Four top-level destinations matching the 4 MVP screens:
  1. `Research Workspace` (Screen 1)
  2. `Knowledge Base` (Screen 2 — displays active ingestion count badge when jobs are running)
  3. `Graph & Memory Explorer` (Screen 3)
  4. `System Settings` (Screen 4 — visible to all, editable only when Role is set to `Knowledge Admin`)
- **Role Switcher (`[APPROVED D-05]`):** Located in the top-right utility bar. Allows switching between `Researcher` (standard read/query permissions) and `Knowledge Admin` (unlocks document deletion, ingestion retry, global memory pruning, and settings mutation) with a clear `Role: Admin` pill indicator.
- **Cross-Screen Deep Linking:**
  - Clicking a document title in a chat citation can open its full chunk list in `Knowledge Base`.
  - Clicking `"Explore in Full Graph"` on a local subgraph card opens `Graph & Memory Explorer` pre-filtered to that `entity_id`.

### 5.2 Forms and Input Controls
- **Chat Query Composer (Screen 1):**
  - Auto-expanding multi-line textarea (`min-height: 56px`, `max-height: 200px`) anchored to the bottom of the center stage.
  - **Embedded Composer Controls:** Bottom bar inside the input container houses the **Memory Scope Pill Toggle** (`Session + Shared Memory` vs. `Session Only`), an indicator of indexed document count (`12 Docs • 340 Entities`), and the `Send` button (`Enter` to submit, `Shift + Enter` for newline).
- **Document Upload Dropzone (Screen 2):**
  - Dashed `2px` border container (`Border-Subtle`, highlights to `Border-Focus` on drag-over).
  - Explicitly states constraints upfront: *"Supported formats: `.pdf`, `.md`, `.txt` • Max 25 MB per file • Automatic SHA-256 deduplication"*.
- **Admin Configuration Controls (Screen 4):**
  - Uses paired **Slider + Numeric Input** controls for bounded parameters (`Top-K Chunks: 1–20`, `Similarity Threshold: 0.00–1.00`, `Max KG Hops: 1–2`, `Max Orchestrator Steps: 3–8`).
  - Every setting includes a `Reset to Default` link and inline helper text explaining the latency vs. recall trade-off.
  - When viewed by a `Researcher`, all form controls render in a clean `read-only` state with a lock icon and explanatory tooltip: *"Switch to Knowledge Admin role to modify system retrieval parameters."*

---

## 6. Loading, Empty, and Error States

### 6.1 Loading States
| Context | Visual Pattern | Microcopy / Telemetry |
| :--- | :--- | :--- |
| **Multi-Agent Query Turn** | Live Agent Activity Stepper (`4.2`) with active step spinner and live millisecond counter; response text streams token-by-token below. | `"Step 2/4: Traversing Knowledge Graph (2 hops from 'PaymentGateway')..."` |
| **Document Ingestion Row** | Inline status pill in the Document Registry table transitions through distinct pipeline stages with a subtle animated progress bar underneath the row. | `QUEUED` → `CHUNKING (42 chunks)` → `EXTRACTING_KG (18 entities)` → `INDEXED` |
| **Right Provenance Inspector** | Structural skeleton blocks matching the exact height of a Verbatim Evidence Card or KG Triple list (`animate-pulse` opacity `0.4` to `0.8`). | No generic spinning wheel; preserves layout stability (`CLS = 0`). |

### 6.2 Empty States
| Context | Visual Pattern & Action | Required Microcopy |
| :--- | :--- | :--- |
| **Empty Knowledge Base (0 Indexed Docs)** | Centered callout card in the Chat Workspace with a direct primary button (`Go to Knowledge Base`). Composer remains active but warns that no documents are indexed. | **Title:** *"Your Knowledge Base is empty"*<br>**Body:** *"Upload `.pdf`, `.md`, or `.txt` documents in the Knowledge Base Manager to enable grounded answers and Knowledge Graph traversal."* |
| **New Research Session** | Clean header showing active Memory Scope and 3 clickable starter query cards dynamically populated from top entities in the Knowledge Graph. | **Title:** *"Start a grounded research session"*<br>**Subtext:** *"Agents will collaborate across Vector Chunks, Knowledge Graph relationships, and Centralized Memory."* |
| **Insufficient Evidence (Abstention)** | Structured Abstention Card (`4.6`) with searched query terms and entity lookups displayed as muted pills. | **Title:** *"Insufficient evidence in Knowledge Base"*<br>**Body:** *"Neither document chunk retrieval nor 2-hop Knowledge Graph traversal returned verified evidence above the 0.65 confidence threshold."* |
| **Empty Centralized Memory** | Dashed border placeholder panel inside the Memory Explorer. | *"No long-term shared memories recorded yet. Verified facts and entity context will appear here automatically after grounded synthesis turns."* |

### 6.3 Error States
| Failure Scenario | UI Treatment & Recovery Action |
| :--- | :--- |
| **Document Ingestion Failure** | Row status badge turns red (`FAILED`). Hovering or clicking the badge reveals the exact pipeline stage and failure reason (e.g., *"PDF contains scanned images without extractable text"* or *"Gemini entity extraction rate limit"*). Provides an inline `Retry` button and `Remove` button. |
| **Partial Sub-Agent Failure (KG Timeout)** | Turn succeeds via graceful degradation (`NFR-05`). Displays an amber warning banner above the synthesized response: *"Answered using Document Chunks and Memory only — Knowledge Graph traversal timed out."* The failed step is highlighted in red inside the Agent Execution Trace tab. |
| **LLM Rate Limit / Network Error (`429`/`503`)** | The user's query text is preserved intact inside the composer. An inline error banner appears with a countdown or immediate `Retry Query` button. |
| **Destructive Action Confirmation** | Deleting a document (`FR-16`) or purging shared memory (`FR-11`) triggers a compact confirmation modal explicitly stating the cascading impact: *"Deleting `Architecture.pdf` will permanently remove 42 chunks and 19 orphaned Knowledge Graph relationships."* |

---

## 7. Interactions and Animations

### 7.1 Micro-Interactions & Cross-Highlighting
- **Citation-to-Evidence Sync:**
  - **Hovering** an inline citation pill (`[Doc: #14]`) in the chat response highlights the corresponding card in the Right Inspector (if visible) with a `Border-Focus` outline.
  - **Clicking** an inline citation pill opens the Right Inspector (if collapsed), switches to the appropriate tab (`Sources` for `[Doc]`, `Knowledge Graph` for `[KG]`, `Memory` for `[Mem]`), scrolls smoothly to the target card, and flashes a `Surface-Highlight` pulse for `1.2s`.
- **Graph Node Selection:** Clicking any node or edge in the Knowledge Graph Subgraph filters the visible source chunks below it to show only the verbatim passages (`source_chunk_ids`) where that entity or relationship was extracted.
- **Trace Step Expansion:** Clicking a step in the Agent Execution Trace expands an accordion showing the structured JSON input/output summary (`sub_queries`, `retrieved_chunk_ids`, `similarity_scores`) formatted in `Font-Mono` with a one-click `Copy JSON` button.

### 7.2 Motion & Timing Rules
- **Duration Scale:**
  - `100ms` (`ease-out`): Button hovers, citation pill hovers, tab switches.
  - `180ms` (`cubic-bezier(0.16, 1, 0.3, 1)`): Right Inspector drawer open/close, trace accordion expand/collapse, modal appearance.
- **No Decorative Motion:** Never animate text characters flying in, bouncing cards, or continuous background animations. Streaming tokens appear immediately on arrival.
- **Reduced Motion:** Respect `@media (prefers-reduced-motion: reduce)` by disabling all slide transitions and pulsing skeletons in favor of instant state changes.

---

## 8. Responsive Behavior

Although primary research workflows occur on desktop monitors, the layout adapts cleanly across three viewport tiers:

| Breakpoint Tier | Viewport Width | Layout Adaptation Rules |
| :--- | :--- | :--- |
| **1. Wide Desktop Workbench** | `>= 1280px` | Full 3-pane layout visible simultaneously in Screen 1: Left Session Rail (`260px`) + Center Chat Stage (`flex: 1`) + Right Provenance Inspector (`420px`). |
| **2. Compact Desktop / Tablet Landscape** | `768px – 1279px` | Left Session Rail collapses into a toggleable slide-over drawer triggered from the top bar. Center Chat Stage and Right Provenance Inspector (`360px`) remain side-by-side when a citation is active. Data tables allow horizontal scrolling for secondary metadata columns. |
| **3. Mobile / Narrow Viewport** | `< 768px` | Single-pane active view. Top navigation condenses into a compact menu. Clicking any inline citation pill (`[Doc]`, `[KG]`, `[Mem]`) or `"View Trace"` opens the Provenance Inspector as a **Bottom Sheet (`height: 80dvh`)** with a drag/close handle so users can inspect sources without losing their place in the conversation. |

---

## 9. Accessibility Requirements (WCAG 2.2 AA)

1. **Contrast & Color Independence:**
   - All primary and secondary text meets a minimum `4.5:1` contrast ratio against its surface (`Text-Primary` on `Surface-Canvas` exceeds `14:1`).
   - Provenance pillars (`Doc`, `KG`, `Mem`) and pipeline statuses (`INDEXED`, `FAILED`, `GROUNDED`) never rely on color alone—every badge includes an explicit text prefix (`[Doc]`, `[KG]`, `[Mem]`) and a distinct semantic icon.
2. **Keyboard Navigation & Focus Management:**
   - Every inline citation pill is a native `<button>` element reachable via `Tab` and activatable via `Enter` or `Space`.
   - Activating a citation via keyboard moves focus to the corresponding target card heading in the Right Provenance Inspector, and pressing `Escape` returns focus to the exact citation pill in the response stream.
   - All interactive controls display a visible `2px solid Border-Focus` ring with `2px` offset on `:focus-visible`.
3. **Screen Reader & ARIA Live Regions:**
   - The Live Agent Activity Stepper uses `aria-live="polite"` to announce major phase transitions (e.g., *"Searching Knowledge Graph"*, *"Response grounded and complete"*) without spamming rapid millisecond timer updates.
   - The 2D Knowledge Graph Subgraph visualization is always accompanied by the accessible **Structured Path List (`4.4`)** rendered as semantic HTML list/table markup so screen reader and keyboard-only users have 100% parity when inspecting entity relationships.
4. **Hit Targets:** All buttons, role selectors, memory delete actions, and mobile citation triggers maintain a minimum interactive target area of `32x32px` on desktop and `44x44px` on touch viewports (`< 768px`).

---

## 10. Page-Level Layout Guidance

### 10.1 Screen 1: Collaborative Chat & Research Workspace
```
+--------------------------------------------------------------------------------------------------+
| [Logo] ADK Agentic RAG   | [1. Workspace*] [2. Knowledge Base] [3. KG & Memory] [4. Settings]    |
|                                                         [DB: Connected] [Role: Knowledge Admin v]|
+--------------------+------------------------------------------------+----------------------------+
| + New Session      |  Session: Payment Service Outage Analysis      | PROVENANCE & TRACE         |
|                    |  Scope: [Session + Shared Memory (On)]         | [Sources (4)] [KG (2)]     |
| RECENT SESSIONS    |------------------------------------------------| [Agent Trace (5 steps)]    |
| * Payment Outage   |  USER                                          |----------------------------|
|   Auth Migration   |  How does PaymentGateway failure impact        | SELECTED CITATION [Doc #1] |
|   Q3 Compliance    |  downstream settlement services?               |                            |
|                    |                                                | File: Architecture.pdf     |
|--------------------|  ASSISTANT                                     | Page: 4 | Sim Score: 0.91  |
| ACTIVE MEMORY      |  +------------------------------------------+  | -------------------------- |
| 3 Shared Facts     |  | [v] Grounded in 4 Chunks, 2 KG Paths     |  | "...the PaymentGateway     |
| recalled in turn   |  |     5 agent steps • 3.1s   [Inspect ->]  |  | publishes settlement       |
|                    |  +------------------------------------------+  | events to LedgerQueue..."  |
|                    |                                                |                            |
|                    |  A failure in PaymentGateway halts batch       | Extracted Entities:        |
|                    |  clearing in SettlementWorker [Doc: Arch #1]   | (PaymentGateway)           |
|                    |  because SettlementWorker subscribes to        | (LedgerQueue)              |
|                    |  LedgerQueue [KG: PaymentGateway -> PUBLISHES  |                            |
|                    |  -> LedgerQueue]. Prior analysis also noted    | -------------------------- |
|                    |  a 15m retry SLA [Mem: #M-019].                | KG PATH [KG #1]            |
|                    |                                                | (PaymentGateway)           |
|                    |------------------------------------------------|   --[PUBLISHES_TO]-->      |
|                    |  [ Ask a follow-up question...              ]  | (LedgerQueue)              |
|                    |  [Scope: Shared Memory v]           [ Send ]   |   --[CONSUMED_BY]-->       |
|                    |                                                | (SettlementWorker)         |
+--------------------+------------------------------------------------+----------------------------+
```

### 10.2 Screen 2: Knowledge Base & Ingestion Manager
- **Top Header Bar:** Page Title (`Knowledge Base & Ingestion Pipeline`), summary metric pills (`Total Docs: 14`, `Indexed Chunks: 612`, `KG Entities: 284`, `KG Edges: 519`), and primary action button (`+ Upload Documents`).
- **Collapsible Upload Zone:** Positioned at the top of the workspace; supports drag-and-drop multi-file selection (`.pdf`, `.md`, `.txt`).
- **Document Registry Table:** Full-width structured table with sticky header:
  - **Columns:** `Document Title & Filename`, `Format`, `SHA-256 Hash` (truncated `8 chars` in `Font-Mono` with copy button), `Pipeline Status` (`QUEUED`, `CHUNKING`, `EXTRACTING_KG`, `INDEXED`, `FAILED`), `Chunks`, `Entities`, `Relations`, `Uploaded At`, and `Actions` (`Inspect Chunks`, `Re-index`, `Delete`).
- **Slide-Over Chunk Inspector:** Clicking `Inspect Chunks` on any row opens the Right Inspector showing all deterministic chunks for that document alongside the specific `KGEntity` and `KGRelationship` triples extracted from each chunk.

### 10.3 Screen 3: Knowledge Graph & Centralized Memory Explorer
- **Segmented View Switcher:** Top toggle bar switches between **Knowledge Graph Explorer (`Nodes & Edges`)** and **Centralized Memory Manager (`Working, Session & Long-Term Store`)** while sharing the Right Provenance Drawer.
- **Sub-View A: Knowledge Graph Explorer:**
  - **Filter Bar:** Search input by `canonical_name` or alias + `entity_type` filter pills (`All`, `System`, `Organization`, `Person`, `Concept`, `Event`) + `relation_type` filter dropdown.
  - **Split Workspace:** Left/Center pane lists matching canonical entities and their 1–2 hop relationship triples; Right pane renders the interactive 2D local neighborhood graph and the verbatim `DocumentChunk` passages backing the selected edge.
- **Sub-View B: Centralized Memory Manager:**
  - **Filter Bar:** Search memory content + Tier filter tabs (`All Tiers`, `Long-Term Semantic`, `Long-Term Episodic`, `Session Memory`) + toggle to `Show Superseded Memories`.
  - **Memory Registry List:** Displays `MemoryEntry` cards (`4.5`) ordered by recency or relevance, showing exact provenance links (`Turn #`, `Chunk IDs`, `Entity Tags`) and allowing one-click pruning (`Forget`) for `Knowledge Admin` users (or session-scoped deletion for `Researcher` users).

### 10.4 Screen 4: System & Retrieval Settings (Admin View)
- **Two-Column Structured Configuration Layout (`max-width: 960px`):**
  - **Card 1: Hybrid Retrieval & Grounding Thresholds:** Controls for `Vector Top-K Chunks` (default `5`), `Minimum Cosine Similarity Threshold` (default `0.65`), and `Strict Abstention Mode` (enforces `INSUFFICIENT_EVIDENCE` when below threshold).
  - **Card 2: Knowledge Graph & Orchestrator Bounds:** Controls for `Max Graph Traversal Hops` (`1` or `2`), `Max Orchestrator Agent Loop Steps` (default `5`, max `8`), and `Per-Turn Timeout` (`30s`).
  - **Card 3: Centralized Memory Policy:** Toggle for `Auto-Consolidate Verified Facts to Shared Memory` (`[APPROVED D-04]`) and a bulk maintenance action (`Clear Active Session Scratchpads`).
  - **Card 4: Infrastructure & Integration Status (Read-Only Telemetry):** Live status rows for **Google ADK Runtime**, **Gemini API (`gemini-2.5-flash` & Embedding Model)**, and **Supabase PostgreSQL (`pgvector` + KG Tables)** with connection latency in milliseconds.

