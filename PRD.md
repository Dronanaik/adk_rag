# Product Requirements Document (PRD): Agentic RAG System with Centralized Memory and Knowledge Graph

- **Document Version:** 1.0.0
- **Status:** Approved — Baseline Source of Truth
- **Target System:** Collaborative Multi-Agent RAG with Centralized Memory & Knowledge Graph Grounding

---

## 0. Assumptions & Approved Architectural Decisions

To prevent over-engineering and establish a clear baseline for implementation, the following assumptions and stakeholder-approved architectural decisions govern the build.

### 0.1 Explicit Assumptions (`[ASSUMPTION]`)
- **[ASSUMPTION A-01] Workspace Context:** The system will be built in Python using **Google Agent Development Kit (ADK)** and **Gemini models** for orchestration, embeddings, and entity extraction.
- **[ASSUMPTION A-02] Corpus Scale for MVP:** The initial target corpus is small-to-medium scale (up to 1,000 documents / ~50,000 chunks) to validate accuracy, graph traversal, and memory sharing before optimizing for distributed petabyte-scale storage.
- **[ASSUMPTION A-03] Supported Document Formats:** MVP ingestion supports text-based `.pdf`, `.md`, and `.txt` files. Complex OCR for scanned images, audio, and video is deferred.
- **[ASSUMPTION A-04] Single-Workspace Deployment:** The MVP operates within a single shared organization workspace with role-based views (`Researcher` vs. `Admin`) rather than full multi-tenant SaaS isolation.
- **[ASSUMPTION A-05] Bounded Graph Traversal:** Knowledge Graph queries are bounded to a maximum of 2 hops from matched seed entities during standard query execution to keep latency predictable.

### 0.2 Approved Architectural Decisions (`[APPROVED]`)
| ID | Decision Topic | Approved Choice | Status | Architectural Impact |
| :--- | :--- | :--- | :--- | :--- |
| **D-01** | **Agent Orchestration Framework** | **Google ADK (Python)** | **APPROVED** | Standardizes agent lifecycle, tool registration, and native session/memory primitives. |
| **D-02** | **Storage Stack (Vector + Graph + Memory)** | **Supabase PostgreSQL (`pgvector` + Relational Graph Tables + JSONB Memory)** | **APPROVED** | Unified cloud/local Postgres storage for vectors, Knowledge Graph nodes/edges, sessions, traces, and centralized memory. |
| **D-03** | **Knowledge Graph Schema Mode** | **Schema-Guided Extraction** (predefined core entity/relation types + fallback `RELATED_TO`) | **APPROVED** | Prevents noisy/fragmented graphs and ensures consistent multi-hop traversal. |
| **D-04** | **Shared Memory Write Policy** | **Verified-Only Writes** (Only the Memory Agent commits distilled facts after synthesis verification) | **APPROVED** | Prevents hallucinated or intermediate scratchpad noise from polluting long-term shared memory. |
| **D-05** | **Authentication Mechanism** | **Lightweight Role Selector / API Key Auth** | **APPROVED** | Keeps MVP focused on core Agentic RAG, KG, and Memory mechanics while enforcing `Researcher` vs. `Admin` permissions. |

---

## 1. Problem, Value Proposition, and Target Users

### 1.1 Problem Statement
Standard Retrieval-Augmented Generation (RAG) systems rely on single-pass vector similarity search over isolated text chunks and stateless LLM calls. This creates four critical failure modes in complex knowledge work:
1. **Failure on Multi-Hop Reasoning:** Vector search struggles to connect facts spread across multiple documents when the connection depends on explicit entity relationships rather than surface-level lexical/semantic similarity.
2. **Context Loss & Siloed Agents:** In multi-agent workflows, agents often operate with isolated prompts, losing important context from earlier turns or duplicating retrieval work already performed by peer agents.
3. **Lack of Episodic & Semantic Continuity:** Valuable insights, resolved entity aliases, and user constraints discovered in one task are forgotten in subsequent interactions.
4. **Opaque Provenance:** Users cannot easily verify *why* an answer was generated, which specific document passages or knowledge graph relationships grounded each claim, or which agent produced which reasoning step.

### 1.2 Value Proposition
The **Agentic RAG System with Centralized Memory and Knowledge Graph** provides a collaborative multi-agent architecture that:
- **Combines Vector Search + Knowledge Graph Traversal:** Grounds answers in both unstructured document passages and structured entity-relationship paths.
- **Shares Context via Centralized Memory:** Gives specialized agents access to a unified short-term working scratchpad and a persistent long-term memory of verified facts, user preferences, and prior conclusions.
- **Delivers End-to-End Traceability:** Every generated claim is linked to source document chunks, Knowledge Graph triples, and an inspectable step-by-step agent execution trace.

### 1.3 Target Users & Personas
| Persona | Role Description | Primary Goals | Key Pain Points Solved |
| :--- | :--- | :--- | :--- |
| **Domain Researcher / Analyst** | Primary end-user querying complex technical, legal, financial, or research corpora. | Get accurate, synthesized answers to complex multi-part questions with verifiable citations. | Eliminates manual cross-referencing across documents and repeating context across follow-up queries. |
| **Knowledge Curator / Admin** | Manages the document corpus, knowledge graph quality, and shared memory store. | Ingest documents reliably, inspect extracted entities/relations, and prune outdated or incorrect shared memories. | Provides visibility into how documents are chunked, indexed, and linked in the Knowledge Graph. |
| **AI Engineer / Operator** | Monitors and tunes agent behavior and retrieval quality. | Inspect agent handoffs, tool calls, retrieval scores, and grounding verification results. | Replaces "black-box" RAG failures with transparent per-agent execution traces. |

---

## 2. Core User Journeys and User Stories

### 2.1 Core User Journeys

#### Journey 1: Document Ingestion & Knowledge Graph Indexing
1. **Upload:** Admin uploads one or more documents (`.pdf`, `.md`, `.txt`) via the Knowledge Base Manager.
2. **Chunking & Embedding:** System splits documents into deterministic chunks with source metadata (document title, page/section, character offsets) and generates vector embeddings.
3. **Entity & Relationship Extraction:** Ingestion pipeline extracts canonical entities (nodes) and relationships (edges) from each chunk, recording the exact `chunk_id` on every edge for provenance.
4. **Graph Merge & Index Commit:** Entities are deduplicated/resolved against existing nodes in the Knowledge Graph, vectors are stored, and document status updates to `Indexed`.

#### Journey 2: Multi-Agent Collaborative Query & Grounded Response
1. **Query Submission:** Researcher submits a complex question in the Chat Workspace.
2. **Orchestration & Memory Lookup:** The **Orchestrator Agent** reads the **Centralized Memory** (session context + relevant long-term shared facts) and decomposes the user query into sub-tasks.
3. **Parallel/Sequential Specialist Execution:**
   - **Vector Retrieval Agent** fetches top-K semantically relevant document chunks.
   - **Knowledge Graph Agent** identifies seed entities in the query and traverses 1–2 hops in the KG to retrieve connected entities, relationship paths, and their backing source chunks.
4. **Shared Scratchpad Aggregation:** Retrieved chunks, KG paths, and memory entries are written to the active turn's centralized working memory.
5. **Grounded Synthesis & Verification:** The **Synthesis & Grounding Agent** drafts a response strictly constrained by the aggregated evidence, attaches inline citations (`[Doc-ID, Chunk-ID]` and `[KG-Path]`), and verifies that no unsupported claims exist.
6. **Memory Consolidation:** The **Memory Agent** extracts any newly established high-confidence facts or user constraints from the turn and persists them to Centralized Memory for future reuse.
7. **Response Delivery:** User views the streamed answer alongside clickable citations, the local KG subgraph used, and the collapsible agent execution trace.

#### Journey 3: Cross-Turn & Cross-Task Memory Reuse
1. **Follow-up / Related Task:** Researcher asks a follow-up question or starts a new session referencing an entity or project analyzed previously.
2. **Memory Recall:** Memory Agent retrieves prior verified conclusions and entity context from Centralized Memory.
3. **Optimized Execution:** Orchestrator reuses the retrieved context, skipping redundant broad searches and focusing specialist agents only on net-new information gaps.

#### Journey 4: Provenance Inspection & Memory Curation
1. **Citation Audit:** Researcher clicks an inline citation badge in a response.
2. **Source & Graph Inspection:** Side panel highlights the exact source text passage, similarity score, and the Knowledge Graph nodes/edges that connected the concepts.
3. **Memory Curation (Admin):** Admin opens the Memory Explorer, reviews stored long-term facts, and deletes or edits an obsolete memory entry so future agent runs do not use stale context.

### 2.2 User Stories
| ID | Persona | User Story | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **US-01** | Knowledge Admin | As an Admin, I want to upload documents and have them automatically chunked, embedded, and parsed into Knowledge Graph entities and relationships, so that agents can query both text and graph structure. | - Accepts `.pdf`, `.md`, `.txt` up to 25 MB per file.<br>- Displays real-time ingestion status.<br>- Persists chunks, embeddings, KG nodes, and KG edges linked to `chunk_id`. |
| **US-02** | Researcher | As a Researcher, I want my complex question decomposed and answered by specialized agents using both documents and the Knowledge Graph, so that multi-hop questions are answered accurately. | - Orchestrator routes tasks to Vector, KG, and Memory agents.<br>- Final response synthesizes findings from both vector chunks and KG relationships. |
| **US-03** | Researcher | As a Researcher, I want every factual claim in an answer to include an inline citation to the source document chunk and/or KG relationship, so that I can trust and verify the output. | - Every factual paragraph/claim has a clickable citation tag.<br>- Clicking a tag opens the exact chunk text, document title, and KG triple. |
| **US-04** | Researcher | As a Researcher, I want the system to remember context, resolved entities, and key findings across turns and sessions, so that I do not have to repeat background information. | - Short-term session memory tracks conversation history.<br>- Shared semantic/episodic memory persists verified facts across sessions.<br>- Trace indicates when Centralized Memory items were retrieved and used. |
| **US-05** | Researcher | As a Researcher, I want the system to explicitly state when the knowledge base lacks sufficient evidence to answer my question, so that I am protected from hallucinations. | - When retrieval scores and KG matches fall below threshold, the system abstains from guessing and clearly reports what information is missing. |
| **US-06** | AI Operator / Researcher | As an Operator, I want to inspect the step-by-step execution trace of all agents involved in a response, so that I can understand how the answer was constructed and debug failures. | - Each response includes a collapsible trace showing agent sequence, sub-queries, retrieved chunk/edge IDs, confidence scores, and step latency. |
| **US-07** | Knowledge Admin | As an Admin, I want to view and delete documents from the knowledge base and have their associated chunks and orphaned KG edges cleaned up, so that stale data does not pollute answers. | - Deleting a document removes its chunks, embeddings, and KG edges exclusively backed by that document. |
| **US-08** | Knowledge Admin | As an Admin, I want to inspect and delete entries in the Centralized Memory store, so that incorrect or outdated shared memories can be removed. | - Memory Explorer lists stored memory items with timestamps, scope, and source turn.<br>- Admin can delete individual memory entries or clear session memory. |

---

## 3. Features and Functional Requirements

### 3.1 Multi-Agent Orchestration & Specialized Agents
| Req ID | Priority | Requirement Description |
| :--- | :--- | :--- |
| **FR-01** | **P0 (MVP)** | **Orchestrator / Coordinator Agent:** Receives user input, consults Centralized Memory, analyzes intent, decomposes complex queries into sub-queries, delegates to specialized agents, and enforces a maximum iteration limit (default: 5 agent steps per turn). |
| **FR-02** | **P0 (MVP)** | **Document Retrieval Agent (Vector/Hybrid):** Executes semantic vector search (and optional keyword/BM25 lexical match) over the document chunk store, returning top-K chunks with similarity scores and metadata. |
| **FR-03** | **P0 (MVP)** | **Knowledge Graph Agent:** Extracts candidate entities from the sub-query, resolves them against canonical KG nodes, and traverses 1 to $N$ hops ($N \le 2$ by default) to return relevant triples (`Entity A -> Relation -> Entity B`) and their linked source `chunk_id`s. |
| **FR-04** | **P0 (MVP)** | **Centralized Memory Agent / Service:** Retrieves relevant short-term working context and long-term episodic/semantic memories prior to synthesis, and commits distilled, verified facts to long-term memory post-synthesis. |
| **FR-05** | **P0 (MVP)** | **Synthesis & Grounding Verifier Agent:** Synthesizes evidence from the shared working scratchpad into a coherent response, enforces strict inline citation formatting, checks that claims are supported by retrieved chunks/edges, and triggers a single targeted re-retrieval if critical evidence is missing. |
| **FR-06** | **P0 (MVP)** | **Structured Inter-Agent State Contract:** All agents read from and write to a standardized, typed turn state object inside Centralized Working Memory (containing sub-queries, retrieved chunks, retrieved KG subgraph, memory hits, and verification status). |

### 3.2 Centralized Memory System
| Req ID | Priority | Requirement Description |
| :--- | :--- | :--- |
| **FR-07** | **P0 (MVP)** | **Three-Tier Memory Architecture:**<br>1. **Working Scratchpad (Turn-Scoped):** Holds active sub-queries, intermediate agent outputs, and candidate evidence during a single request lifecycle.<br>2. **Session Memory (Conversation-Scoped):** Maintains multi-turn conversation history and active entity references within a thread.<br>3. **Shared Long-Term Memory (Workspace/User-Scoped):** Stores distilled episodic summaries and semantic facts reusable across sessions and agents. |
| **FR-08** | **P0 (MVP)** | **Semantic Memory Retrieval:** Long-term memory entries are embedded and indexed so any agent (via the Memory Agent) can query relevant prior findings by semantic similarity and entity tags. |
| **FR-09** | **P0 (MVP)** | **Memory Deduplication & Conflict Resolution:** Before writing a new long-term memory entry, the Memory Agent checks for existing similar entries; if a conflict or update is detected, it supersedes the older entry and preserves provenance links. |
| **FR-10** | **P0 (MVP)** | **Memory Provenance Attribution:** Every long-term memory entry stores the `session_id`, `turn_id`, timestamp, and the underlying `document_id`/`chunk_id` citations that originally validated the fact. |
| **FR-11** | **P0 (MVP)** | **Memory Inspection & Pruning Controls:** Users/Admins can view which memory entries were injected into a prompt and manually delete specific memory records. |

### 3.3 Knowledge Base & Knowledge Graph Pipeline
| Req ID | Priority | Requirement Description |
| :--- | :--- | :--- |
| **FR-12** | **P0 (MVP)** | **Document Ingestion & Deterministic Chunking:** Parses `.pdf`, `.md`, and `.txt` files into text chunks with configurable chunk size (default: 512–1000 tokens) and overlap (default: 100 tokens), preserving document title, page/section headers, and character offsets. |
| **FR-13** | **P0 (MVP)** | **Automated Entity & Relation Extraction:** Uses structured LLM extraction during ingestion to identify entities (`name`, `type`, `description`) and directed relationships (`source_entity`, `relation_type`, `target_entity`, `evidence_snippet`, `chunk_id`). |
| **FR-14** | **P0 (MVP)** | **Entity Resolution & Canonicalization:** Normalizes entity names (case-insensitivity, whitespace normalization, and alias mapping) during ingestion so mentions across different documents link to the same canonical node in the Knowledge Graph. |
| **FR-15** | **P0 (MVP)** | **Bidirectional Chunk-to-Graph Provenance:** Every KG node and edge maintains a list of supporting `chunk_id`s and `document_id`s; every `chunk_id` can look up all entities mentioned within it. |
| **FR-16** | **P0 (MVP)** | **Cascading Deletion & Re-indexing:** Deleting a document purges its chunks, vectors, and any KG edges/nodes that no longer have supporting chunks from other documents. |
| **FR-17** | **P1 (Post-MVP)** | **Incremental Graph Community Summarization:** Pre-computes high-level summaries of densely connected entity clusters (GraphRAG community summaries) for broad thematic queries. |

### 3.4 Traceability, Citations & Explainability
| Req ID | Priority | Requirement Description |
| :--- | :--- | :--- |
| **FR-18** | **P0 (MVP)** | **Mandatory Inline Citations:** All factual statements in generated responses must include clickable citation markers (e.g., `[Doc: <Title>, Chunk #]`, `[KG: <EntityA> -> <Relation> -> <EntityB>]`, or `[Memory: <MemoryID>]`). |
| **FR-19** | **P0 (MVP)** | **Source Evidence Drawer:** Clicking any citation opens a side panel displaying the full verbatim text of the source chunk, metadata, similarity score, and the local KG triples extracted from that chunk. |
| **FR-20** | **P0 (MVP)** | **Agent Execution Trace Log:** Records and displays a structured timeline for every query turn showing: participating agents, input parameters, tool invocations, retrieved item counts, execution duration (ms), and grounding verification outcome. |

---

## 4. Non-Functional Requirements (NFRs)

| ID | Category | Requirement | Target / Metric |
| :--- | :--- | :--- | :--- |
| **NFR-01** | **Performance** | **Streaming Time-to-First-Status (TTFS):** UI must display real-time agent step transitions immediately after query submission. | `< 500 ms` to first status event |
| **NFR-02** | **Performance** | **End-to-End Query Latency:** Total time for multi-agent retrieval (Vector + KG + Memory) and synthesis start on standard queries. | P50 `< 6 seconds`, P95 `< 15 seconds` |
| **NFR-03** | **Execution Safety** | **Bounded Agent Loops:** Hard circuit-breaker on Orchestrator/Sub-agent loops to prevent infinite recursion or runaway token spend. | Max `5` steps or `30 seconds` timeout per turn |
| **NFR-04** | **Grounding & Accuracy** | **Zero Uncited Claims Policy:** Synthesis Agent must reject or flag any claim that cannot be traced to a retrieved chunk, KG edge, or verified memory record. | `100%` of factual claims accompanied by provenance IDs |
| **NFR-05** | **Reliability** | **Graceful Degradation:** If the Knowledge Graph yields zero matching entities, the system must seamlessly complete the response using Vector Retrieval + Memory without crashing. | `0` unhandled exceptions on empty subgraph matches |
| **NFR-06** | **Data Integrity** | **Idempotent Ingestion:** Re-uploading an identical document (matched by SHA-256 content hash) must either skip duplicate processing or cleanly replace the prior version without duplicating chunks/edges. | Deterministic SHA-256 deduplication |
| **NFR-07** | **Concurrency** | **Safe Concurrent Memory Access:** Multiple simultaneous sessions or sub-agents reading/writing to Centralized Memory must use transactional writes to prevent race conditions. | ACID-compliant memory state commits |
| **NFR-08** | **Security** | **Secret & Credential Management:** All LLM API keys and database credentials must be loaded strictly via environment variables (`.env`), never hardcoded or exposed to the client UI. | Zero secrets in client bundle or logs |

---

## 5. Pages / Screens

The MVP user interface is a clean, purpose-built web application consisting of **4 core screens**:

### 5.1 Screen 1: Collaborative Chat & Research Workspace (Primary Screen)
- **Left Sidebar:** Session history list, "New Research Session" button, and active memory scope toggle (`Session Only` vs. `Session + Shared Workspace Memory`).
- **Center Pane (Conversation Stream):**
  - User messages and streamed Assistant responses with clickable inline citation badges (`[1]`, `[KG-1]`, `[Mem-1]`).
  - **Live Agent Activity Banner:** Expandable step indicator showing active agent work (e.g., *Orchestrator → Consulting Memory → Querying Knowledge Graph (2 hops) → Synthesizing & Verifying*).
- **Right Drawer (Provenance & Trace Inspector — Tabbed):**
  - **Tab 1: Sources & Citations:** Verbatim document chunk text highlighted for the selected citation, document metadata, and cosine similarity score.
  - **Tab 2: Knowledge Graph Subgraph:** Visual/interactive node-link view (and structured table list) of the specific entities and relationship paths retrieved for the current turn.
  - **Tab 3: Agent Execution Trace:** Chronological log of each agent step, tool call inputs/outputs, latency, and grounding check status.

### 5.2 Screen 2: Knowledge Base & Ingestion Manager
- **Upload Panel:** Drag-and-drop file uploader supporting `.pdf`, `.md`, `.txt` with batch progress indicator.
- **Document Registry Table:** Columns for Document Title, File Type, Upload Date, Content Hash, Status (`Queued`, `Chunking`, `Extracting KG`, `Indexed`, `Failed`), Chunk Count, Extracted Entity Count, Extracted Relation Count, and Actions (`Inspect Chunks`, `Re-index`, `Delete`).

### 5.3 Screen 3: Knowledge Graph & Centralized Memory Explorer
- **Sub-view A: Knowledge Graph Explorer:**
  - Search bar to look up entities by name or filter by entity type.
  - Entity detail card showing description, connected 1-hop relationships (`Subject -> Predicate -> Object`), and clickable links to the source document chunks where those relationships were discovered.
- **Sub-view B: Centralized Memory Manager:**
  - Filterable table/cards of stored **Long-Term Semantic/Episodic Memories** and **Active Session Memories**.
  - Displays memory content, creation timestamp, originating session/turn link, supporting source citations, and a `Delete / Forget` action button.

### 5.4 Screen 4: System & Retrieval Settings (Admin View)
- Read/write configuration panel for runtime parameters:
  - Retrieval Top-K chunks (default: `5`), Similarity Threshold (default: `0.65`).
  - Max KG Traversal Hops (`1` or `2`), Max Orchestrator Loop Steps (`3` to `8`).
  - Memory Auto-Consolidation toggle (`Enabled` / `Disabled`).
  - System health indicators (LLM API connectivity, Vector Store status, KG Store status).

---

## 6. Roles and Permissions

`[ASSUMPTION A-04]` The MVP uses a streamlined two-role model for human users plus an internal system role for agents.

| Capability / Action | Researcher (Standard User) | Knowledge Admin | Agent / System Internal |
| :--- | :---: | :---: | :---: |
| Create chat sessions & submit queries | Allowed | Allowed | N/A |
| View inline citations, source chunks & KG paths | Allowed | Allowed | Allowed (Read) |
| Inspect Agent Execution Traces | Allowed (Read-Only) | Allowed (Full Detail) | Allowed (Write) |
| Read from Centralized Shared Memory | Allowed | Allowed | Allowed (Read) |
| Write new facts to Shared Memory | Automatic via verified turn | Allowed (Manual + Auto) | Allowed (Memory Agent only) |
| Delete / Prune Shared Long-Term Memory entries | Own session only | All workspace memories | Allowed (Deduplication/Supersede) |
| Upload, re-index, or delete Knowledge Base documents | Read-Only | Allowed | N/A |
| Modify retrieval thresholds & system settings | Read-Only | Allowed | Read-Only |

---

## 7. Data Requirements & Core Entities

### 7.1 `Document`
- `document_id` (UUID, Primary Key)
- `title` (String)
- `filename` (String)
- `mime_type` (Enum: `application/pdf`, `text/markdown`, `text/plain`)
- `content_hash` (String, SHA-256 for idempotency)
- `status` (Enum: `QUEUED`, `CHUNKING`, `EXTRACTING_KG`, `INDEXED`, `FAILED`)
- `error_message` (String, Nullable)
- `created_at`, `updated_at` (Timestamp)

### 7.2 `DocumentChunk`
- `chunk_id` (UUID, Primary Key)
- `document_id` (UUID, Foreign Key -> `Document`)
- `chunk_index` (Integer, sequential order in document)
- `content` (Text, verbatim passage)
- `embedding` (Vector, dimension matched to embedding model)
- `metadata` (JSON: `page_number`, `section_heading`, `char_start`, `char_end`)

### 7.3 `KGEntity` (Knowledge Graph Node)
- `entity_id` (UUID, Primary Key)
- `canonical_name` (String, indexed, normalized)
- `entity_type` (String, e.g., `Person`, `Organization`, `Concept`, `System`, `Event`, `Location`)
- `aliases` (Array of Strings)
- `description` (Text, synthesized summary of entity)
- `embedding` (Vector, for fuzzy entity resolution)
- `source_chunk_ids` (Array of UUIDs -> `DocumentChunk`)

### 7.4 `KGRelationship` (Knowledge Graph Directed Edge)
- `edge_id` (UUID, Primary Key)
- `source_entity_id` (UUID, Foreign Key -> `KGEntity`)
- `target_entity_id` (UUID, Foreign Key -> `KGEntity`)
- `relation_type` (String, normalized uppercase predicate, e.g., `DEPENDS_ON`, `AUTHORED_BY`, `PART_OF`)
- `evidence_snippet` (Text, brief quote justifying the relationship)
- `weight_or_confidence` (Float, `0.0` to `1.0`)
- `source_chunk_id` (UUID, Foreign Key -> `DocumentChunk`)
- `document_id` (UUID, Foreign Key -> `Document`)

### 7.5 `ConversationSession` & `MessageTurn`
- `session_id` (UUID, Primary Key)
- `title` (String)
- `use_shared_memory` (Boolean)
- `created_at`, `updated_at` (Timestamp)
- **Turn Attributes (`MessageTurn`):** `turn_id` (UUID), `session_id` (FK), `user_query` (Text), `assistant_response` (Text), `citations` (JSON array mapping inline citation IDs to `chunk_id`, `edge_id`, or `memory_id`), `grounding_status` (Enum: `GROUNDED`, `PARTIAL`, `INSUFFICIENT_EVIDENCE`), `created_at` (Timestamp).

### 7.6 `MemoryEntry` (Centralized Memory Record)
- `memory_id` (UUID, Primary Key)
- `memory_tier` (Enum: `WORKING`, `SESSION`, `LONG_TERM_SEMANTIC`, `LONG_TERM_EPISODIC`)
- `session_id` (UUID, Nullable for global workspace memories)
- `content` (Text, distilled atomic fact or episodic summary)
- `embedding` (Vector, for semantic memory recall)
- `related_entities` (Array of `entity_id` UUIDs)
- `source_turn_id` (UUID, Foreign Key -> `MessageTurn`)
- `supporting_chunk_ids` (Array of UUIDs -> `DocumentChunk`)
- `superseded_by_id` (UUID, Nullable, points to newer `MemoryEntry` if updated)
- `created_at` (Timestamp)

### 7.7 `AgentExecutionTrace`
- `trace_id` (UUID, Primary Key)
- `turn_id` (UUID, Foreign Key -> `MessageTurn`)
- `step_order` (Integer)
- `agent_name` (Enum: `Orchestrator`, `VectorRetriever`, `KGRetriever`, `MemoryAgent`, `SynthesisVerifier`)
- `action_or_tool` (String)
- `input_payload` (JSON)
- `output_summary` (JSON, including retrieved IDs and scores)
- `latency_ms` (Integer)
- `status` (Enum: `SUCCESS`, `FALLBACK`, `ERROR`)

---

## 8. Integrations

| Integration Type | Purpose | Approved MVP Specification |
| :--- | :--- | :--- |
| **1. Agent Framework** | Multi-agent orchestration, tool calling, and state management. | **Google ADK (Agent Development Kit)** `[APPROVED D-01]` |
| **2. LLM & Embedding Provider** | Query decomposition, schema-guided entity/relation extraction, grounded synthesis, and text embeddings. | **Google Gemini API** (e.g., `gemini-2.5-flash` for fast agent routing & KG extraction; `gemini-embedding-001` / `text-embedding-004` for vectors). |
| **3. Vector & Relational Store** | Persistent storage for document chunks, embeddings, sessions, traces, and centralized memory. | **Supabase PostgreSQL + `pgvector`** `[APPROVED D-02]` |
| **4. Knowledge Graph Store** | Storage and multi-hop traversal of `KGEntity` nodes and `KGRelationship` edges. | **Supabase PostgreSQL** relational adjacency tables (`kg_entities`, `kg_relationships`) with indexed 1–2 hop recursive CTE / SQL traversal functions `[APPROVED D-02]`. |
| **5. Document Parser** | Extracting clean text and page metadata from uploaded files. | Standard lightweight Python parsers (`pypdf`/`pymupdf` for PDF, native UTF-8 parser for `.md`/`.txt`). |

---

## 9. Loading, Empty, and Error States

### 9.1 Loading States
- **Chat Query Execution:** Displays a live, non-blocking progress stepper showing which specialized agent is currently active (*1. Recalling Centralized Memory → 2. Searching Document Chunks & Knowledge Graph → 3. Verifying Grounding & Synthesizing*).
- **Document Ingestion:** Document row shows a granular status badge (`Chunking...` → `Extracting Entities...` → `Indexing...`) with a progress spinner; user can continue chatting with already-indexed documents while ingestion runs asynchronously.
- **Graph / Citation Drawer Loading:** Skeleton placeholder cards while fetching source chunk text and local 1-hop neighborhood.

### 9.2 Empty States
- **Empty Knowledge Base (Zero Documents):** Chat workspace displays a prominent callout banner: *"Your Knowledge Base is empty. Upload documents in the Knowledge Base Manager to enable grounded answers and Knowledge Graph traversal"* with a direct button to Screen 2.
- **Empty Conversation Session:** Displays example starter queries tailored to indexed documents (or generic multi-hop prompt templates) and shows current active memory scope.
- **No Matching Evidence Found (Abstention State):** When neither Vector Search, KG Traversal, nor Centralized Memory returns results above the confidence threshold, the assistant returns a structured abstention card: *"I could not find sufficient evidence in the uploaded documents or Knowledge Graph to answer this question reliably"* along with the closest searched entities/terms.
- **Empty Centralized Memory:** Memory Explorer displays: *"No long-term shared memories recorded yet. Verified facts and entity context will appear here as agents collaborate across sessions."*

### 9.3 Error States
- **Document Ingestion Failure (Corrupt PDF / Empty Text / Extraction Error):** Document status changes to `Failed` with a clear tooltip explaining the failure stage (e.g., *"PDF contains scanned images without extractable text"* or *"LLM entity extraction timed out"*) and a `Retry Ingestion` button.
- **Sub-Agent / Tool Timeout or Partial Failure:** If the Knowledge Graph Agent times out or fails during a turn, the Orchestrator logs a `FALLBACK` status in `AgentExecutionTrace`, displays a subtle warning badge (*"Answered using document chunks only; Knowledge Graph lookup timed out"*), and completes the response using Vector + Memory results.
- **LLM API Rate Limit / Quota Error (`429` / `503`):** System applies exponential backoff (up to 2 retries); if still failing, preserves the user's input message in the UI and displays an actionable retry banner.
- **Orchestrator Max-Step Circuit Breaker:** If a complex query hits the maximum agent loop limit without full resolution, the Synthesis Agent synthesizes the best partial answer strictly from evidence gathered so far and explicitly lists which sub-questions remained unresolved.

---

## 10. MVP Scope, Out-of-Scope Items, and Success Criteria

### 10.1 MVP Scope (Must-Have for v1.0)
1. **End-to-End Ingestion Pipeline:** Upload `.pdf`, `.md`, `.txt` → deterministic chunking → vector embedding → LLM entity/relation triple extraction → entity canonicalization → storage with chunk provenance.
2. **Five-Role Multi-Agent Workflow:** Orchestrator, Vector Retrieval Agent, Knowledge Graph Agent, Centralized Memory Agent, and Synthesis/Grounding Verifier Agent sharing a structured state contract.
3. **Centralized Memory System:** Working turn scratchpad + multi-turn session history + cross-session semantic/episodic memory with provenance and manual deletion controls.
4. **Traceable Grounded Responses:** Inline citations linking every factual claim to source chunks, KG triples, or memory entries, plus a refusal/abstention mechanism when evidence is absent.
5. **Four-Screen Web UI:** Chat Workspace with Provenance/Trace Inspector, Knowledge Base Manager, KG & Memory Explorer, and Admin Settings.

### 10.2 Out-of-Scope Items (Explicitly Excluded to Prevent Over-Engineering)
- **Multimodal / OCR Ingestion:** Audio, video, spreadsheets, and complex OCR on scanned handwritten PDFs.
- **External Autonomous Web Browsing:** Agents will strictly query the internal Knowledge Base, Knowledge Graph, and Centralized Memory—no live internet scraping during RAG queries.
- **Enterprise Multi-Tenancy & Billing:** SSO/SAML, complex RBAC hierarchies, usage metering, and Stripe billing.
- **Heavy 3D / Full-Corpus Graph Rendering:** The UI will render focused local subgraphs (1–2 hops around query/selected entities) rather than attempting to render 100,000+ nodes simultaneously in the browser.
- **Automated Model Fine-Tuning:** All learning and cross-session adaptation happens through Centralized Memory and Knowledge Graph updates, not LLM weight fine-tuning.

### 10.3 Success Criteria & Verification Gates
| Metric / Criterion | Target Benchmark | Verification Method |
| :--- | :--- | :--- |
| **1. Citation & Provenance Completeness** | `100%` of synthesized factual responses contain valid, clickable links to existing `chunk_id`s, `edge_id`s, or `memory_id`s. | Automated schema validation on `MessageTurn.citations` and UI click-through test. |
| **2. Multi-Hop Knowledge Graph Utility** | System accurately answers 2-hop relationship queries (where Fact A->B is in Document 1 and Fact B->C is in Document 2) that single-chunk vector search misses. | End-to-end test suite with a synthetic multi-document test corpus containing disjoint cross-document entity links. |
| **3. Centralized Memory Reuse** | Facts or constraints established in Session 1 are recalled by the Memory Agent in Session 2 and visible in the execution trace without re-prompting the user. | Two-session integration test verifying `MemoryAgent` recall and trace attribution. |
| **4. Hallucination Abstention Rate** | `100%` abstention on out-of-domain test queries that have zero supporting chunks or entities in the knowledge base. | Negative test suite of 10 out-of-corpus questions verifying `INSUFFICIENT_EVIDENCE` status. |
| **5. Execution Trace Transparency** | Every completed query turn logs a complete `AgentExecutionTrace` with non-null agent names, step order, latency, and retrieved artifact IDs. | Inspection of trace drawer and database records after query execution. |
