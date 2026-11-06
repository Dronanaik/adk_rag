---
title: ADK Agentic RAG + Knowledge Graph
hide:
  - navigation
  - toc
---

<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script>document.body.classList.add('adk-landing-page');</script>

<div class="adk-landing">

<!-- Ambient Glows -->
<div class="glow glow-tl"></div>
<div class="glow glow-tr"></div>
<div class="glow glow-mr"></div>

<!-- Hero Section -->
<div class="hero-grid">
  <div class="hero-content">
    <h1>Where Knowledge Connects, <span class="hero-punchline">Agents Reason.</span></h1>
    <p>An enterprise-ready <strong>Hybrid Document Intelligence Platform</strong> built with <strong>Google Agent Development Kit (ADK)</strong>. Authenticate with <strong>Neon PostgreSQL</strong>, ingest documents through a live 5-step dual vector + graph pipeline, explore interactive <strong>Neo4j</strong> knowledge topologies, and converse with a multi-tool reasoning agent.</p>
    <div class="hero-actions">
      <a href="INSTALLATION/" class="btn btn-primary">Start building</a>
      <a href="USER_GUIDE/" class="btn btn-secondary">Interactive User Guide</a>
      <a href="ARCHITECTURE/" class="btn btn-accent">System Architecture</a>
    </div>
  </div>
  <div class="hero-visual">
    <!-- Tabbed Code Window (adk.dev style) -->
    <div class="tabbed-area" id="tabbed-area">
      <div class="mac-window">
        <div class="window-header">
          <div class="window-dots">
            <span class="window-dot red"></span>
            <span class="window-dot yellow"></span>
            <span class="window-dot green"></span>
          </div>
          <span class="window-title">adk_rag — hybrid_rag_kg_agent</span>
        </div>
        <div class="iterm-tab-bar">
          <div class="iterm-tab active" data-lang="python">ADK Agent</div>
          <div class="iterm-tab" data-lang="sql">Hybrid SQL</div>
          <div class="iterm-tab" data-lang="cypher">Neo4j Cypher</div>
          <div class="iterm-tab" data-lang="fastapi">FastAPI</div>
        </div>

<div class="code-content" id="code-python"><pre><span class="kw">from</span> google.adk.agents <span class="kw">import</span> <span class="fn">LlmAgent</span>
<span class="kw">from</span> app.rag_store <span class="kw">import</span> hybrid_search, vector_search
<span class="kw">from</span> app.graph_store <span class="kw">import</span> graph_search, get_entity_relationships

root_agent = <span class="fn">LlmAgent</span>(
    name=<span class="str">"hybrid_rag_kg_agent"</span>,
    model=<span class="str">"gemini-2.5-pro"</span>,
    instruction=build_agent_instruction,
    tools=[
        hybrid_search,
        vector_search,
        graph_search,
        get_entity_relationships,
    ],
)</pre></div>

<div class="code-content" id="code-sql" style="display:none"><pre><span class="cm">-- 70% pgvector HNSW Cosine + 30% PostgreSQL GIN Full-Text</span>
<span class="kw">SELECT</span> chunk_id, filename, content,
       (<span class="fn">0.7</span> * (<span class="fn">1</span> - (embedding &lt;=&gt; <span class="str">%(query_vec)s</span>::vector)) +
        <span class="fn">0.3</span> * <span class="fn">ts_rank_cd</span>(
          <span class="fn">to_tsvector</span>(<span class="str">'english'</span>, content),
          <span class="fn">plainto_tsquery</span>(<span class="str">'english'</span>, <span class="str">%(query)s</span>)
        )) <span class="kw">AS</span> combined_score
<span class="kw">FROM</span> document_chunks
<span class="kw">WHERE</span> user_id = <span class="str">%(user_id)s</span>
<span class="kw">ORDER BY</span> combined_score <span class="kw">DESC LIMIT</span> <span class="fn">5</span>;</pre></div>

<div class="code-content" id="code-cypher" style="display:none"><pre><span class="cm">// Multi-Hop Tenant-Isolated Neo4j Knowledge Graph Traversal</span>
<span class="kw">MATCH</span> (s:<span class="fn">Entity</span> {user_id: <span class="str">$user_id</span>})
      -[r:<span class="fn">RELATES_TO</span> {user_id: <span class="str">$user_id</span>}]-&gt;
      (t:<span class="fn">Entity</span> {user_id: <span class="str">$user_id</span>})
<span class="kw">WHERE</span> <span class="fn">toLower</span>(s.name) <span class="kw">CONTAINS</span> <span class="str">$term</span>
   <span class="kw">OR</span> <span class="fn">toLower</span>(r.fact) <span class="kw">CONTAINS</span> <span class="str">$term</span>
<span class="kw">RETURN</span> s.name <span class="kw">AS</span> source, r.relation_type <span class="kw">AS</span> relation,
       t.name <span class="kw">AS</span> target, r.fact <span class="kw">AS</span> fact
<span class="kw">LIMIT</span> <span class="fn">15</span>;</pre></div>

<div class="code-content" id="code-fastapi" style="display:none"><pre><span class="kw">@app.post</span>(<span class="str">"/chat"</span>, response_model=<span class="fn">ChatResponse</span>)
<span class="kw">async def</span> <span class="fn">chat_endpoint</span>(
    req: <span class="fn">ChatRequest</span>,
    current_user: <span class="fn"> dict</span> = <span class="fn">Depends</span>(get_current_user),
):
    result = <span class="kw">await</span> <span class="fn">ask_agent</span>(
        question=req.question,
        user_id=current_user[<span class="str">"user_id"</span>],
        session_id=req.session_id,
    )
    <span class="kw">return</span> <span class="fn">ChatResponse</span>(**result)</pre></div>

        <!-- Install info synced with tabs -->
        <div class="install-info" id="install-python">
          <div class="install-cmd">
            <code>pip install -r requirements.txt &amp;&amp; uvicorn app.main:app --reload</code>
            <button class="copy-btn" data-copy="pip install -r requirements.txt && uvicorn app.main:app --reload" title="Copy to clipboard">📋</button>
          </div>
        </div>
        <div class="install-info" id="install-sql" style="display:none">
          <div class="install-cmd">
            <code>psql "$NEON_DATABASE_URL" -f sql/neon_init.sql</code>
            <button class="copy-btn" data-copy='psql "$NEON_DATABASE_URL" -f sql/neon_init.sql' title="Copy to clipboard">📋</button>
          </div>
        </div>
        <div class="install-info" id="install-cypher" style="display:none">
          <div class="install-cmd">
            <code>NEO4J_URI=neo4j+s://&lt;instance&gt;.databases.neo4j.io</code>
            <button class="copy-btn" data-copy="NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io" title="Copy to clipboard">📋</button>
          </div>
        </div>
        <div class="install-info" id="install-fastapi" style="display:none">
          <div class="install-cmd">
            <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run dev</code>
            <button class="copy-btn" data-copy="cd frontend && npm install && npm run dev" title="Copy to clipboard">📋</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Feature Split 1: 5-Step Dual Ingestion -->
<div class="feature-split reverse">
  <div class="feature-text">
    <span class="feature-badge">5-Step Dual Ingestion</span>
    <h2>Ingest once. Index vectors and graphs <i>simultaneously</i>.</h2>
    <p>Upload PDF, DOCX, Markdown, CSV, JSON, or plain-text files. Watch real-time 800ms telemetry as documents are parsed, semantically chunked (1,200 chars), batch-embedded into 768-dim vectors in <strong>Neon PostgreSQL</strong>, and extracted into structured <strong>Neo4j</strong> entity-relationship triplets.</p>
    <a href="INGESTION/" class="btn btn-accent" style="margin-top:12px">Explore Ingestion Pipeline</a>
  </div>
  <div class="feature-visual">
    <div class="mac-window terminal">
      <div class="window-header">
        <div class="window-dots">
          <span class="window-dot red"></span>
          <span class="window-dot yellow"></span>
          <span class="window-dot green"></span>
        </div>
        <span class="window-title">POST /upload — Live 5-Step Telemetry</span>
      </div>
      <div class="terminal-body">
        <div class="term-line"><span class="term-prompt">$</span><span class="term-cmd">curl -X POST /upload -F "file=@architecture_spec.pdf"</span></div>
        <div class="term-line"><span class="term-success">✔ [Step 1/5]</span> <span class="term-system">Text Extraction (pypdf): 18 pages, 42,810 chars</span></div>
        <div class="term-line"><span class="term-success">✔ [Step 2/5]</span> <span class="term-system">Semantic Chunking: 38 chunks (1200 size / 200 overlap)</span></div>
        <div class="term-line"><span class="term-success">✔ [Step 3/5]</span> <span class="term-system">Gemini Embeddings: 38 × 768-dim (gemini-embedding-001)</span></div>
        <div class="term-line"><span class="term-success">✔ [Step 4/5]</span> <span class="term-system">Neon PostgreSQL: Indexed HNSW (m=16) + GIN tsvector</span></div>
        <div class="term-line"><span class="term-success">✔ [Step 5/5]</span> <span class="term-accent">Neo4j AuraDB: Merged 29 (:Entity) &amp; 44 [:RELATES_TO]</span></div>
        <div class="term-line" style="margin-top:12px"><span class="term-success">✨ Ingestion Complete</span> <span class="term-system">— Ready for Hybrid &amp; Graph Retrieval</span></div>
      </div>
    </div>
  </div>
</div>

<!-- Feature Split 2: Hybrid RAG + Graph Workflows -->
<div class="feature-split">
  <div class="feature-text">
    <span class="feature-badge">Hybrid RAG + Graph Workflows</span>
    <h2>Semantic precision. Multi-hop graph reasoning.</h2>
    <p>Traditional vector-only RAG misses global entity relationships and exact technical identifiers. ADK Agentic RAG fuses <strong>70% pgvector HNSW cosine similarity</strong> + <strong>30% PostgreSQL GIN full-text ranking</strong> with deterministic <strong>Neo4j</strong> relationship traversal.</p>
    <a href="CHAT/" class="btn btn-accent" style="margin-top:12px">Explore Agent Tools</a>
  </div>
  <div class="feature-visual">
    <div class="cc-compare">
      <div class="cc-side">
        <div class="cc-side-label cc-label-dim">STANDARD VECTOR-ONLY RAG</div>
        <div class="cc-stack cc-stack-bad">
          <div class="cc-row cc-dim">Isolated text chunks only</div>
          <div class="cc-row cc-dim">Misses exact error codes / SKUs</div>
          <div class="cc-row cc-dim">No cross-document entity links</div>
          <div class="cc-row cc-dim">Single retrieval strategy</div>
        </div>
      </div>
      <div class="cc-arrow">→</div>
      <div class="cc-side">
        <div class="cc-side-label cc-label-bright">ADK HYBRID + NEO4J GRAPH RAG</div>
        <div class="cc-stack cc-stack-good">
          <div class="cc-row">70% Vector + 30% FTS (Neon Postgres)</div>
          <div class="cc-row">Multi-hop (:Entity)-[:RELATES_TO]</div>
          <div class="cc-row">Autonomous 4-Tool ADK LlmAgent</div>
          <div class="cc-row">Inline [Source] &amp; [Graph] citations</div>
        </div>
      </div>
    </div>
    <div class="eval-grid">
      <div class="eval-card pass">
        <div class="eval-title"><span>hybrid_search</span><span class="eval-status pass">● Neon SQL</span></div>
        <div class="eval-desc">70% HNSW cosine + 30% GIN tsvector ranking</div>
      </div>
      <div class="eval-card pass">
        <div class="eval-title"><span>graph_search</span><span class="eval-status pass">● Neo4j</span></div>
        <div class="eval-desc">Entity &amp; relationship fact pattern matching</div>
      </div>
      <div class="eval-card pass">
        <div class="eval-title"><span>vector_search</span><span class="eval-status pass">● pgvector</span></div>
        <div class="eval-desc">Pure 768-dim conceptual similarity lookup</div>
      </div>
      <div class="eval-card pass">
        <div class="eval-title"><span>get_entity_relationships</span><span class="eval-status pass">● 1-Hop Graph</span></div>
        <div class="eval-desc">Incoming &amp; outgoing neighborhood traversal</div>
      </div>
    </div>
  </div>
</div>

<!-- Feature Split 3: Bioluminescent React UI -->
<div class="feature-split reverse">
  <div class="feature-text">
    <span class="feature-badge">Bioluminescent Neural Forest UI</span>
    <h2>Five specialized workspaces. Multi-tenant isolation.</h2>
    <p>Authenticate via <strong>Neon PostgreSQL</strong> (<code>PBKDF2-SHA256</code> + <code>HS256</code> JWT) with strict per-user isolation across both databases. Move seamlessly between the <strong>Telemetry Dashboard</strong>, <strong>5-Step Upload Pipeline</strong>, <strong>Agentic Chat</strong>, <strong>Interactive Neo4j Force-Directed Canvas</strong>, and <strong>System Health Monitor</strong>.</p>
    <a href="USER_GUIDE/" class="btn btn-accent" style="margin-top:12px">Open Interactive User Guide</a>
  </div>
  <div class="feature-visual">
    <div class="ui-wrapper">
      <img src="assets/bg-neural-tree.jpg" alt="Bioluminescent Neural Forest Theme" class="devui-img">
    </div>
  </div>
</div>

<!-- Feature Split 4: Technical Specifications -->
<div class="feature-split">
  <div class="feature-text">
    <span class="feature-badge">Production Engineering</span>
    <h2>Built for scale with Neon, Neo4j &amp; Google ADK.</h2>
    <p>Engineered with pooled <code>psycopg3</code> connections, HNSW vector indexes, GIN full-text indexes, Neo4j uniqueness constraints, and one-click cascade deletion that prunes orphaned graph entities automatically.</p>
    <a href="TECHNICAL_SPECIFICATIONS/" class="btn btn-accent" style="margin-top:12px">View Technical Specifications</a>
  </div>
  <div class="feature-visual">
    <div class="metrics-dashboard">
      <table class="metrics-table">
        <thead>
          <tr>
            <th>Subsystem</th>
            <th>Technology / Model</th>
            <th>Specification</th>
          </tr>
        </thead>
        <tbody>
          <tr class="metric-green">
            <td>Agent Framework</td>
            <td>Google ADK (<code>LlmAgent</code>)</td>
            <td class="delta-green">Gemini 2.5 Pro</td>
          </tr>
          <tr class="metric-green">
            <td>Vector + FTS Store</td>
            <td>Neon PostgreSQL + <code>pgvector</code></td>
            <td class="delta-green">768-dim HNSW + GIN</td>
          </tr>
          <tr class="metric-green">
            <td>Knowledge Graph</td>
            <td>Neo4j AuraDB + Gemini Flash</td>
            <td class="delta-green">Structured Triplets</td>
          </tr>
          <tr class="metric-green">
            <td>Authentication</td>
            <td>Neon <code>users</code> Table</td>
            <td class="delta-green">PBKDF2 + HS256 JWT</td>
          </tr>
          <tr class="metric-green">
            <td>Multi-Tenancy</td>
            <td>Dual-Store Partitioning</td>
            <td class="delta-green">Strict user_id Scope</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- Ready to Build CTA Section -->
<div class="ceiling-section">
  <h2>Ready to build your Hybrid RAG + Knowledge Graph agent?</h2>
  <p class="section-subtitle">Follow our step-by-step guides to configure Neon PostgreSQL, Neo4j AuraDB, and Google Gemini, and launch the full-stack platform in minutes.</p>
  <a href="INSTALLATION/" class="btn btn-primary">Start building</a>
</div>

<!-- Documentation Portal Cards Grid (adk.dev style) -->
<div class="ceiling-section">
  <h2>Explore the Documentation</h2>
  <p class="section-subtitle">Deep-dive into every layer of the ADK Agentic RAG + Knowledge Graph platform—from interactive user workflows to database schemas and cloud deployment.</p>
  <div class="features-grid">

    <a class="carousel-card" href="INSTALLATION/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#3b82f6"><path d="m13.13 22.19-1.63-3.83c1.57-.58 3.04-1.36 4.4-2.27zM5.64 12.5l-3.83-1.63 6.1-2.77C7 9.46 6.22 10.93 5.64 12.5M21.61 2.39S16.66.269 11 5.93c-2.19 2.19-3.5 4.6-4.35 6.71-.28.75-.09 1.57.46 2.13l2.13 2.12c.55.56 1.37.74 2.12.46A19.1 19.1 0 0 0 18.07 13c5.66-5.66 3.54-10.61 3.54-10.61m-7.07 7.07c-.78-.78-.78-2.05 0-2.83s2.05-.78 2.83 0c.77.78.78 2.05 0 2.83s-2.05.78-2.83 0"/></svg>
      </span>
      <h3>Quickstart &amp; Installation</h3>
      <p>Configure environment variables, initialize Neon PostgreSQL &amp; Neo4j schemas, and run the backend and React frontend locally.</p>
      <span class="card-learn-more">Start building →</span>
    </a>

    <a class="carousel-card" href="USER_GUIDE/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#8b5cf6"><path d="M12 21.5c-1.35-.85-3.8-1.5-5.5-1.5-1.65 0-3.35.3-4.75 1.05-.1.05-.15.05-.25.05-.25 0-.5-.25-.5-.5V6c.6-.45 1.25-.75 2-1 1.11-.35 2.33-.5 3.5-.5 1.95 0 4.05.4 5.5 1.5 1.45-1.1 3.55-1.5 5.5-1.5 1.17 0 2.39.15 3.5.5.75.25 1.4.55 2 1v14.6c0 .25-.25.5-.5.5-.1 0-.15 0-.25-.05-1.4-.75-3.1-1.05-4.75-1.05-1.7 0-4.15.65-5.5 1.5M12 8v11.5c1.35-.85 3.8-1.5 5.5-1.5 1.2 0 2.4.15 3.5.5V7c-1.1-.35-2.3-.5-3.5-.5-1.7 0-4.15.65-5.5 1.5"/></svg>
      </span>
      <h3>Interactive User Guide</h3>
      <p>Visual step-by-step walkthrough of Neon authentication, 5-step document upload, Agentic Chat, and Knowledge Graph exploration.</p>
      <span class="card-learn-more">Read User Guide →</span>
    </a>

    <a class="carousel-card" href="ARCHITECTURE/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#10b981"><path d="M9 2v6h2v3H5c-1.11 0-2 .89-2 2v3H1v6h6v-6H5v-3h6v3H9v6h6v-6h-2v-3h6v3h-2v6h6v-6h-2v-3c0-1.11-.89-2-2-2h-6V8h2V2z"/></svg>
      </span>
      <h3>System Architecture</h3>
      <p>End-to-end architectural diagrams, sequence flows for authentication, dual ingestion, multi-tool ADK retrieval, and tenant isolation.</p>
      <span class="card-learn-more">Explore Architecture →</span>
    </a>

    <a class="carousel-card" href="TECHNICAL_SPECIFICATIONS/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#f59e0b"><path d="M14 2H6a2 2 0 0 0-2 2v16c0 1.11.89 2 2 2h12c1.11 0 2-.89 2-2V8zm4 18H6V4h7v5h5zm-8.46-4.35 2.09 2.09L10.35 19 7 15.65l3.35-3.35 1.28 1.26zm7.46 0L13.65 19l-1.27-1.26 2.09-2.09-2.09-2.09 1.27-1.26z"/></svg>
      </span>
      <h3>Technical Specifications</h3>
      <p>Complete engineering specs: Neon pgvector HNSW &amp; GIN schemas, Neo4j constraints, PBKDF2-SHA256 + HS256 JWT security, and formulas.</p>
      <span class="card-learn-more">View Specifications →</span>
    </a>

    <a class="carousel-card" href="INGESTION/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#06b6d4"><path d="M22 14h-2v2h-6v-3h2v-2h-2V6a2 2 0 0 0-2-2H4V2H2v8h2V8h6v3H8v2h2v5a2 2 0 0 0 2 2h8v2h2"/></svg>
      </span>
      <h3>5-Step Dual Ingestion Pipeline</h3>
      <p>How documents are parsed, semantically chunked, batch-embedded, indexed in Neon Postgres, and extracted into Neo4j triplets.</p>
      <span class="card-learn-more">Pipeline Deep Dive →</span>
    </a>

    <a class="carousel-card" href="CHAT/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#ec4899"><path d="M21.33 12.91c.09 1.55-.62 3.04-1.89 3.95l.77 1.49c.23.45.26.98.06 1.45-.19.47-.58.84-1.06 1l-.79.25a1.687 1.687 0 0 1-1.86-.55L14.44 18c-.89-.15-1.73-.53-2.44-1.1-.5.15-1 .23-1.5.23-.88 0-1.76-.27-2.5-.79-.53.16-1.07.23-1.62.22-.79.01-1.57-.15-2.3-.45a4.1 4.1 0 0 1-2.43-3.61c-.08-.72.04-1.45.35-2.11-.29-.75-.32-1.57-.07-2.33C2.3 7.11 3 6.32 3.87 5.82c.58-1.69 2.21-2.82 4-2.7 1.6-1.5 4.05-1.66 5.83-.37.42-.11.86-.17 1.3-.17 1.36-.03 2.65.57 3.5 1.64 2.04.53 3.5 2.35 3.58 4.47.05 1.11-.25 2.2-.86 3.13.07.36.11.72.11 1.09"/></svg>
      </span>
      <h3>Agentic Chat &amp; Graph Tools</h3>
      <p>How the Google ADK LlmAgent dynamically orchestrates hybrid_search, vector_search, graph_search, and get_entity_relationships.</p>
      <span class="card-learn-more">Agent Tools Guide →</span>
    </a>

    <a class="carousel-card" href="FRONTEND/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#14b8a6"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8m-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12m3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8m5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8m3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5"/></svg>
      </span>
      <h3>Bioluminescent React UI</h3>
      <p>Component hierarchy, glassmorphic design tokens, 800ms live ingestion polling, and interactive SVG Knowledge Graph canvas.</p>
      <span class="card-learn-more">Explore Frontend →</span>
    </a>

    <a class="carousel-card" href="API/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#6366f1"><path d="M7 7H5a2 2 0 0 0-2 2v8h2v-4h2v4h2V9a2 2 0 0 0-2-2m0 4H5V9h2m7-2h-4v10h2v-4h2a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2m0 4h-2V9h2m6 0v6h1v2h-4v-2h1V9h-1V7h4v2Z"/></svg>
      </span>
      <h3>REST API &amp; Cloud Deployment</h3>
      <p>Complete FastAPI endpoint reference with curl examples plus production deployment guides for Render, Netlify, Neon, and Neo4j AuraDB.</p>
      <span class="card-learn-more">View API Reference →</span>
    </a>

  </div>
</div>

<!-- FAQ Section (adk.dev style) -->
<div class="faq-section">
  <h2>Frequently Asked Questions</h2>
  <p class="section-subtitle">Key architectural and operational answers about ADK Agentic RAG + Knowledge Graph:</p>

  <div class="faq-grid">

  <details class="faq-item-arrow">
    <summary>Why combine Neon pgvector Hybrid Search with a Neo4j Knowledge Graph?</summary>
    <p>Vector similarity excels at conceptual semantics, and PostgreSQL Full-Text Search (<code>ts_rank_cd</code>) captures exact technical identifiers, acronyms, and SKUs. However, neither represents explicit multi-hop relationships across documents. By extracting structured <code>(:Entity)-[:RELATES_TO]-&gt;(:Entity)</code> triplets into <strong>Neo4j</strong> during ingestion and exposing all four tools to the <strong>Google ADK LlmAgent</strong>, the agent can combine local passage evidence with global graph topology in a single turn.</p>
  </details>

  <details class="faq-item-arrow">
    <summary>How does the 5-step dual ingestion pipeline work in real time?</summary>
    <p>When a user uploads a file via <code>POST /upload</code>, the backend updates an in-memory per-user stage tracker polled every <code>800ms</code> by the React UI (<code>GET /ingest/progress</code>): <strong>(1)</strong> Document parsing (<code>pypdf</code> / <code>python-docx</code> / UTF-8), <strong>(2)</strong> Paragraph-aware chunking (<code>1200</code> chars, <code>200</code> overlap), <strong>(3)</strong> Batched <code>768</code>-dim embeddings via <code>gemini-embedding-001</code>, <strong>(4)</strong> Neon PostgreSQL <code>document_chunks</code> indexing (HNSW + GIN), and <strong>(5)</strong> Gemini 2.5 Flash structured entity/relationship extraction into Neo4j.</p>
  </details>

  <details class="faq-item-arrow">
    <summary>How is multi-tenant data isolation enforced across Neon and Neo4j?</summary>
    <p>Every user authenticates against the Neon PostgreSQL <code>users</code> table using <code>PBKDF2-HMAC-SHA256</code> password hashing (120,000 iterations) and receives a signed <code>HS256</code> JWT token. Every SQL query filters on <code>WHERE user_id = %(user_id)s</code>, every Neo4j node ID is namespace-prefixed (<code>user_id::entity_name</code>) with <code>{user_id: $user_id}</code> property filters, and ADK chat sessions are keyed by <code>(app_name, user_id, session_id)</code>.</p>
  </details>

  <details class="faq-item-arrow">
    <summary>How does the Google ADK LlmAgent decide which retrieval tool to call?</summary>
    <p>The <code>hybrid_rag_kg_agent</code> is initialized with dynamic runtime instructions via <code>build_agent_instruction(ReadonlyContext)</code> and four function tools: <code>hybrid_search</code> (default for factual/technical queries), <code>vector_search</code> (for broad conceptual similarity), <code>graph_search</code> (for discovering entities and relationship facts), and <code>get_entity_relationships</code> (for 1-hop neighborhood inspection). Gemini 2.5 Pro autonomously invokes one or multiple tools before synthesizing a grounded response.</p>
  </details>

  <details class="faq-item-arrow">
    <summary>What happens when a user deletes a document?</summary>
    <p>Calling <code>DELETE /documents/{document_id}</code> performs an atomic cascade across both databases: it deletes the document and its <code>document_chunks</code> from Neon PostgreSQL, removes all <code>[:RELATES_TO {document_id}]</code> edges and the <code>(:Document)</code> node in Neo4j, and automatically prunes any orphaned <code>(:Entity)</code> nodes that no longer have any remaining relationships or document mentions.</p>
  </details>

  <details class="faq-item-arrow">
    <summary>How do I deploy the platform to production?</summary>
    <p>The backend deploys as a Python web service on <strong>Render</strong> (or Google Cloud Run) connected to serverless <strong>Neon PostgreSQL</strong> and <strong>Neo4j AuraDB</strong>, while the Vite + React frontend deploys to <strong>Netlify</strong>. Full configuration templates (<code>render.yaml</code>, <code>netlify.toml</code>) and environment variable checklists are provided in the <a href="DEPLOYMENT/">Cloud Deployment Guide</a>.</p>
  </details>

  </div>
</div>

</div>

<script>
function syncLandingPageClass() {
  var isLanding = !!document.querySelector('.adk-landing');
  document.body.classList.toggle('adk-landing-page', isLanding);
}

// Event delegation for tab switching and copy buttons (survives MkDocs instant navigation)
document.addEventListener('click', function(e) {
  var tab = e.target.closest('.iterm-tab');
  if (tab) {
    var lang = tab.getAttribute('data-lang');
    var allTabs = document.querySelectorAll('.iterm-tab');
    var langs = ['python', 'sql', 'cypher', 'fastapi'];
    allTabs.forEach(function(t) { t.classList.remove('active'); });
    tab.classList.add('active');
    langs.forEach(function(l) {
      var codeEl = document.getElementById('code-' + l);
      var installEl = document.getElementById('install-' + l);
      if (codeEl) codeEl.style.display = l === lang ? 'block' : 'none';
      if (installEl) installEl.style.display = l === lang ? 'flex' : 'none';
    });
    return;
  }

  var btn = e.target.closest('.copy-btn');
  if (btn) {
    var text = btn.getAttribute('data-copy');
    navigator.clipboard.writeText(text).then(function() {
      var orig = btn.textContent;
      btn.textContent = '✅';
      setTimeout(function() { btn.textContent = orig; }, 1500);
    });
  }
});

document.addEventListener('DOMContentLoaded', syncLandingPageClass);
if (typeof document$ !== 'undefined') {
  document$.subscribe(function() { syncLandingPageClass(); });
}
</script>
