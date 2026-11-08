import { useEffect, useRef, useState } from 'react'
import { Send, Link as LinkIcon, RefreshCw, MessageSquare, Brain, Lock } from 'lucide-react'
import { sendMessage } from '../api.js'
import ChatMessage from './ChatMessage.jsx'
import styles from './ChatTab.module.css'

const SUGGESTED_QUESTIONS = [
  'Summarize the key concepts and how they relate to each other.',
  'What are the main entities and relationships in my knowledge graph?',
  'Explain the core architecture and technical components described.',
  'What are the key findings, metrics, or conclusions?',
]

export default function ChatTab({ userId }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(queryText) {
    const query = (queryText || input).trim()
    if (!query || loading) return

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: query,
      userId,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const data = await sendMessage(query, userId, sessionId)

      if (!sessionId) setSessionId(data.session_id)

      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: data.answer,
          toolsUsed: data.tools_used || [],
          timestamp: new Date().toISOString(),
        },
      ])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'error',
          content: `Error: ${err.message}`,
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleNewSession() {
    setMessages([])
    setSessionId(null)
    setInput('')
    inputRef.current?.focus()
  }

  return (
    <div className={`${styles.wrap} fade-in`}>
      {/* Header row */}
      <div className={styles.headerRow}>
        <div>
          <h2 className={styles.title}>Agentic RAG + Knowledge Graph Chat</h2>
          <p className={styles.sub}>
            The Google ADK agent autonomously selects between <code>hybrid_search</code>, <code>vector_search</code> (Neon pgvector), <code>graph_search</code>, and <code>get_entity_relationships</code> (Neo4j).
          </p>
        </div>
        <div className={styles.headerActions}>
          {sessionId && (
            <span className="badge badge-teal" title={`Session: ${sessionId}`}>
              <LinkIcon size={12} style={{ marginRight: '4px' }} /> Session active
            </span>
          )}
          {messages.length > 0 && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleNewSession}
              id="new-session-btn"
            >
              <RefreshCw size={14} style={{ marginRight: '4px' }} /> New session
            </button>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className={`glass-card ${styles.chatArea}`}>
        {messages.length === 0 ? (
          <div className={styles.emptyChat}>
            <div className={styles.emptyChatIconWrap}>
              <MessageSquare size={30} />
            </div>
            <h3>Ask your Agentic RAG + Knowledge Graph Assistant</h3>
            <p>
              Combines semantic chunk retrieval from <strong>Neon PostgreSQL (pgvector)</strong> with structured entity traversal in <strong>Neo4j</strong>.
            </p>

            {/* Suggested questions */}
            <div className={styles.suggestions}>
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  className={styles.suggestion}
                  onClick={() => handleSend(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className={styles.messageList}>
            {messages.map(msg => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className={styles.typingIndicator}>
                <div className={styles.typingAvatar}>
                  <Brain size={18} />
                </div>
                <div className={styles.typingBubble}>
                  <span className={styles.dot} />
                  <span className={styles.dot} />
                  <span className={styles.dot} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className={`glass-card ${styles.inputArea}`}>
        <textarea
          ref={inputRef}
          className={`input ${styles.chatInput}`}
          placeholder="Ask about concepts, facts, or entity relationships… (Enter to send, Shift+Enter for new line)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={loading}
          id="chat-input"
        />
        <button
          className={`btn btn-primary ${styles.sendBtn}`}
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          aria-label="Send message"
          title="Send"
          id="send-btn"
        >
          {loading ? (
            <span className="spinner" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>

      {/* Info footer */}
      <div className={styles.infoFooterWrap}>
        <Lock size={14} color="var(--text-muted)" />
        <p className={styles.infoFooter}>
          User-scoped workspace (<strong>{userId}</strong>). Document citations appear as{' '}
          <code>[Source: filename, chunk N]</code> and graph citations as{' '}
          <code>[Graph: Source -&gt; RELATION -&gt; Target]</code>.
        </p>
      </div>
    </div>
  )
}
