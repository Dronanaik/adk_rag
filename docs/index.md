---
title: ADK Agentic RAG + Knowledge Graph
hide:
  - toc
---

<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;600;700;800&display=swap" rel="stylesheet">
<script>document.body.classList.add('adk-landing-page');</script>

<div class="adk-landing">

<!-- Ambient Glows -->
<div class="glow glow-tl"></div>
<div class="glow glow-tr"></div>

<!-- Clean Hero Section (Description + Navigation Buttons Only) -->
<div class="hero-clean">
  <span class="feature-badge">v2.6.0 · Hybrid RAG · Knowledge Graph · Persistent Memory · Live Voice</span>
  <h1>Where Knowledge Connects, <span class="hero-punchline">Agents Reason &amp; Speak.</span></h1>
  <p>An enterprise-ready <strong>Hybrid Document Intelligence Platform</strong> built with <strong>Google Agent Development Kit (ADK)</strong>. Authenticate with <strong>Neon PostgreSQL</strong>, ingest 13 document formats through a live 5-step dual vector + <strong>Neo4j</strong> graph pipeline, persist multi-session chat &amp; long-term memories, explore interactive knowledge topologies, and converse in real time with a <strong>Gemini Live Voice Agent</strong>.</p>

  <div class="hero-actions">
    <a href="INSTALLATION/" class="btn btn-primary">Start Building →</a>
  </div>
</div>

<!-- Documentation Portal Cards Grid -->
<div class="ceiling-section">
  <h2>Explore the Documentation</h2>
  <p class="section-subtitle">Deep-dive into every layer of the ADK Agentic RAG + Knowledge Graph platform.</p>
  <div class="features-grid">

    <a class="carousel-card" href="INSTALLATION/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#0284c7"><path d="m13.13 22.19-1.63-3.83c1.57-.58 3.04-1.36 4.4-2.27zM5.64 12.5l-3.83-1.63 6.1-2.77C7 9.46 6.22 10.93 5.64 12.5M21.61 2.39S16.66.269 11 5.93c-2.19 2.19-3.5 4.6-4.35 6.71-.28.75-.09 1.57.46 2.13l2.13 2.12c.55.56 1.37.74 2.12.46A19.1 19.1 0 0 0 18.07 13c5.66-5.66 3.54-10.61 3.54-10.61m-7.07 7.07c-.78-.78-.78-2.05 0-2.83s2.05-.78 2.83 0c.77.78.78 2.05 0 2.83s-2.05.78-2.83 0"/></svg>
      </span>
      <h3>Quickstart &amp; Installation</h3>
      <p>Configure environment variables, initialize Neon PostgreSQL &amp; Neo4j schemas, and run the backend and React frontend locally.</p>
      <span class="card-learn-more">Start building →</span>
    </a>

    <a class="carousel-card" href="USER_GUIDE/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#0ea5e9"><path d="M12 21.5c-1.35-.85-3.8-1.5-5.5-1.5-1.65 0-3.35.3-4.75 1.05-.1.05-.15.05-.25.05-.25 0-.5-.25-.5-.5V6c.6-.45 1.25-.75 2-1 1.11-.35 2.33-.5 3.5-.5 1.95 0 4.05.4 5.5 1.5 1.45-1.1 3.55-1.5 5.5-1.5 1.17 0 2.39.15 3.5.5.75.25 1.4.55 2 1v14.6c0 .25-.25.5-.5.5-.1 0-.15 0-.25-.05-1.4-.75-3.1-1.05-4.75-1.05-1.7 0-4.15.65-5.5 1.5M12 8v11.5c1.35-.85 3.8-1.5 5.5-1.5 1.2 0 2.4.15 3.5.5V7c-1.1-.35-2.3-.5-3.5-.5-1.7 0-4.15.65-5.5 1.5"/></svg>
      </span>
      <h3>Interactive Walkthrough</h3>
      <p>Full video + annotated screenshots covering Auth, 5-step Upload, Persistent Chat &amp; Memory, Conversational Voice Orb, Graph Explorer, and RAG Evals.</p>
      <span class="card-learn-more">Open Walkthrough →</span>
    </a>

    <a class="carousel-card" href="ARCHITECTURE/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#10b981"><path d="M9 2v6h2v3H5c-1.11 0-2 .89-2 2v3H1v6h6v-6H5v-3h6v3H9v6h6v-6h-2v-3h6v3h-2v6h6v-6h-2v-3c0-1.11-.89-2-2-2h-6V8h2V2z"/></svg>
      </span>
      <h3>System Architecture</h3>
      <p>End-to-end architectural diagrams, sequence flows for authentication, dual ingestion, 5-tool ADK retrieval, live WebSocket voice, and tenant isolation.</p>
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
      <p>How 13 file formats are parsed via IBM Docling &amp; Vision, semantically chunked, batch-embedded, indexed in Neon Postgres, and merged into Neo4j triplets.</p>
      <span class="card-learn-more">Pipeline Deep Dive →</span>
    </a>

    <a class="carousel-card" href="CHAT/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#ec4899"><path d="M21.33 12.91c.09 1.55-.62 3.04-1.89 3.95l.77 1.49c.23.45.26.98.06 1.45-.19.47-.58.84-1.06 1l-.79.25a1.687 1.687 0 0 1-1.86-.55L14.44 18c-.89-.15-1.73-.53-2.44-1.1-.5.15-1 .23-1.5.23-.88 0-1.76-.27-2.5-.79-.53.16-1.07.23-1.62.22-.79.01-1.57-.15-2.3-.45a4.1 4.1 0 0 1-2.43-3.61c-.08-.72.04-1.45.35-2.11-.29-.75-.32-1.57-.07-2.33C2.3 7.11 3 6.32 3.87 5.82c.58-1.69 2.21-2.82 4-2.7 1.6-1.5 4.05-1.66 5.83-.37.42-.11.86-.17 1.3-.17 1.36-.03 2.65.57 3.5 1.64 2.04.53 3.5 2.35 3.58 4.47.05 1.11-.25 2.2-.86 3.13.07.36.11.72.11 1.09"/></svg>
      </span>
      <h3>Agentic Chat, Memory &amp; Voice</h3>
      <p>How the Google ADK LlmAgent &amp; Gemini Live Voice Agent orchestrate hybrid_search, vector_search, graph_search, get_entity_relationships, and load_memory.</p>
      <span class="card-learn-more">Agent &amp; Voice Guide →</span>
    </a>

    <a class="carousel-card" href="FRONTEND/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#14b8a6"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-.99 0-.83.67-1.5 1.5-1.5H16c2.76 0 5-2.24 5-5 0-4.42-4.03-8-9-8m-5.5 9c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9 8 9.67 8 10.5 7.33 12 6.5 12m3-4C8.67 8 8 7.33 8 6.5S8.67 5 9.5 5s1.5.67 1.5 1.5S10.33 8 9.5 8m5 0c-.83 0-1.5-.67-1.5-1.5S13.67 5 14.5 5s1.5.67 1.5 1.5S15.33 8 14.5 8m3 4c-.83 0-1.5-.67-1.5-1.5S16.67 9 17.5 9s1.5.67 1.5 1.5-.67 1.5-1.5 1.5"/></svg>
      </span>
      <h3>Bioluminescent React UI</h3>
      <p>Component hierarchy, VoiceOverlay &amp; AudioWorklet pipeline, History/Memory drawer, and interactive SVG Knowledge Graph canvas.</p>
      <span class="card-learn-more">Explore Frontend →</span>
    </a>

    <a class="carousel-card" href="API/">
      <span class="card-icon">
        <svg xmlns="http://www.w3.org/2000/svg" height="36px" viewBox="0 0 24 24" width="36px" fill="#6366f1"><path d="M7 7H5a2 2 0 0 0-2 2v8h2v-4h2v4h2V9a2 2 0 0 0-2-2m0 4H5V9h2m7-2h-4v10h2v-4h2a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2m0 4h-2V9h2m6 0v6h1v2h-4v-2h1V9h-1V7h4v2Z"/></svg>
      </span>
      <h3>REST &amp; WebSocket API</h3>
      <p>Complete FastAPI endpoint reference covering Auth, Ingestion, Chat Sessions, Long-Term Memories, RAG Evaluations, and WS /ws/voice.</p>
      <span class="card-learn-more">View API Reference →</span>
    </a>

  </div>
</div>

</div>

<script>
function syncLandingPageClass() {
  var isLanding = !!document.querySelector('.adk-landing');
  document.body.classList.toggle('adk-landing-page', isLanding);
}

document.addEventListener('DOMContentLoaded', syncLandingPageClass);
if (typeof document$ !== 'undefined') {
  document$.subscribe(function() { syncLandingPageClass(); });
}
</script>
