import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Send,
  Link as LinkIcon,
  RefreshCw,
  MessageSquare,
  Brain,
  Lock,
  History,
  Trash2,
  Plus,
  X,
} from 'lucide-react'
import {
  addMemory,
  clearAllMemories,
  deleteChatSession,
  deleteMemory,
  getChatSessionMessages,
  listChatSessions,
  listMemories,
  sendMessage,
} from '../api.js'
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

  // Persistent Chat History
  const [showHistory, setShowHistory] = useState(false)
  const [sessions, setSessions] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Long-Term Semantic Memory Modal
  const [showMemoryModal, setShowMemoryModal] = useState(false)
  const [memories, setMemories] = useState([])
  const [memoryInput, setMemoryInput] = useState('')
  const [memoryType, setMemoryType] = useState('preference')
  const [savingMemory, setSavingMemory] = useState(false)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const refreshSessions = useCallback(async () => {
    try {
      setLoadingHistory(true)
      const data = await listChatSessions(userId)
      setSessions(data?.sessions || [])
    } catch {
      // Ignore transient errors
    } finally {
      setLoadingHistory(false)
    }
  }, [userId])

  const refreshMemories = useCallback(async () => {
    try {
      const data = await listMemories(userId)
      setMemories(data?.memories || [])
    } catch {
      // Ignore transient errors
    }
  }, [userId])

  useEffect(() => {
    refreshSessions()
    refreshMemories()
  }, [refreshSessions, refreshMemories])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSelectSession(sid) {
    if (loading) return
    try {
      const data = await getChatSessionMessages(sid, userId)
      const loaded = (data?.messages || []).map((m, idx) => ({
        id: `${sid}-${idx}`,
        role: m.role,
        content: m.text,
        toolsUsed: m.tools || [],
        userId: m.role === 'user' ? userId : undefined,
        timestamp: m.timestamp ? new Date(m.timestamp * 1000).toISOString() : new Date().toISOString(),
      }))
      setSessionId(sid)
      setMessages(loaded)
    } catch {
      // Ignore if session no longer exists
    }
  }

  async function handleDeleteSession(e, sid) {
    e.stopPropagation()
    try {
      await deleteChatSession(sid, userId)
      setSessions(prev => prev.filter(s => s.session_id !== sid))
      if (sessionId === sid) {
        handleNewSession()
      }
    } catch {
      // Ignore
    }
  }

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
      refreshSessions()
      setTimeout(refreshMemories, 2000)
      setTimeout(refreshMemories, 5000)
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

  async function handleAddMemory(e) {
    e.preventDefault()
    if (!memoryInput.trim() || savingMemory) return
    try {
      setSavingMemory(true)
      const res = await addMemory(memoryInput.trim(), memoryType, userId)
      if (res?.memory) {
        setMemories(prev => [res.memory, ...prev])
        setMemoryInput('')
      }
    } finally {
      setSavingMemory(false)
    }
  }

  async function handleDeleteMemory(memoryId) {
    try {
      await deleteMemory(memoryId, userId)
      setMemories(prev => prev.filter(m => m.memory_id !== memoryId))
    } catch {
      // Ignore
    }
  }

  async function handleClearMemories() {
    try {
      await clearAllMemories(userId)
      setMemories([])
    } catch {
      // Ignore
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
            The Google ADK agent autonomously selects between <code>hybrid_search</code>, <code>vector_search</code> (Neon pgvector), <code>graph_search</code>, <code>get_entity_relationships</code> (Neo4j), and <code>load_memory</code> (Persistent Memory).
          </p>
        </div>
        <div className={styles.headerActions}>
          <button
            className={`btn btn-secondary btn-sm`}
            onClick={() => setShowHistory(prev => !prev)}
            id="toggle-history-btn"
            title="Toggle persistent conversation history"
          >
            <History size={14} style={{ marginRight: '4px' }} />
            History {sessions.length > 0 ? `(${sessions.length})` : ''}
          </button>
          <button
            className={`btn btn-secondary btn-sm`}
            onClick={() => { refreshMemories(); setShowMemoryModal(true) }}
            id="open-memory-btn"
            title="Inspect and manage long-term agent memory"
          >
            <Brain size={14} style={{ marginRight: '4px' }} />
            Memory ({memories.length})
          </button>
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

      {/* Chat shell: optional History Sidebar + Chat Area */}
      <div className={styles.chatShell}>
        {showHistory && (
          <aside className={`glass-card ${styles.historySidebar}`} id="chat-history-sidebar">
            <div className={styles.historyHeader}>
              <span>Saved Sessions</span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleNewSession}
                title="Start new conversation"
                style={{ padding: '2px 8px', fontSize: '0.72rem' }}
              >
                <Plus size={12} /> New
              </button>
            </div>
            <div className={styles.historyList}>
              {loadingHistory && sessions.length === 0 ? (
                <div className={styles.historyEmpty}>Loading sessions...</div>
              ) : sessions.length === 0 ? (
                <div className={styles.historyEmpty}>No saved conversations yet.</div>
              ) : (
                sessions.map(s => (
                  <div
                    key={s.session_id}
                    className={`${styles.sessionItem} ${s.session_id === sessionId ? styles.sessionItemActive : ''}`}
                    onClick={() => handleSelectSession(s.session_id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && handleSelectSession(s.session_id)}
                  >
                    <div className={styles.sessionInfo}>
                      <div className={styles.sessionTitle}>{s.title}</div>
                      <div className={styles.sessionMeta}>
                        {s.message_count} {s.message_count === 1 ? 'turn' : 'turns'}
                      </div>
                    </div>
                    <button
                      type="button"
                      className={styles.sessionDelBtn}
                      onClick={(e) => handleDeleteSession(e, s.session_id)}
                      aria-label={`Delete session ${s.title}`}
                      title="Delete session"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </aside>
        )}

        {/* Chat area */}
        <div className={`glass-card ${styles.chatArea}`}>
          {messages.length === 0 ? (
            <div className={styles.emptyChat}>
              <div className={styles.emptyChatIconWrap}>
                <MessageSquare size={30} />
              </div>
              <h3>Ask your Agentic RAG + Knowledge Graph Assistant</h3>
              <p>
                Combines semantic chunk retrieval from <strong>Neon PostgreSQL (pgvector)</strong>, structured entity traversal in <strong>Neo4j</strong>, and persistent cross-session <strong>Agent Memory</strong>.
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
          User-scoped workspace (<strong>{userId}</strong>). Sessions &amp; memories persist in Neon PostgreSQL. Document citations appear as{' '}
          <code>[Source: filename, chunk N]</code> and graph citations as{' '}
          <code>[Graph: Source -&gt; RELATION -&gt; Target]</code>.
        </p>
      </div>

      {/* Long-Term Memory Manager Modal */}
      {showMemoryModal && (
        <div
          className={styles.memoryModalOverlay}
          onClick={() => setShowMemoryModal(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Long-Term Agent Memory"
          id="agent-memory-modal"
        >
          <div className={styles.memoryModal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.memoryHeader}>
              <div>
                <div className={styles.memoryHeaderTitle}>
                  <Brain size={18} color="#22d3ee" />
                  Long-Term Semantic Memory
                </div>
                <div className={styles.memoryHeaderSub}>
                  Auto-distilled facts &amp; preferences recalled across sessions via <code>load_memory</code>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {memories.length > 0 && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handleClearMemories}
                    id="clear-memories-btn"
                  >
                    <Trash2 size={13} /> Clear All
                  </button>
                )}
                <button
                  type="button"
                  className={styles.sessionDelBtn}
                  onClick={() => setShowMemoryModal(false)}
                  aria-label="Close memory modal"
                  id="close-memory-modal-btn"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className={styles.memoryBody}>
              <form className={styles.memoryAddForm} onSubmit={handleAddMemory}>
                <select
                  className={styles.memorySelect}
                  value={memoryType}
                  onChange={(e) => setMemoryType(e.target.value)}
                  aria-label="Memory type"
                >
                  <option value="preference">Preference</option>
                  <option value="fact">Fact</option>
                  <option value="summary">Summary</option>
                </select>
                <input
                  type="text"
                  className={styles.memoryInput}
                  placeholder="Add a persistent memory (e.g., Always summarize in bullet points)..."
                  value={memoryInput}
                  onChange={(e) => setMemoryInput(e.target.value)}
                  id="add-memory-input"
                />
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={savingMemory || !memoryInput.trim()}
                  id="add-memory-btn"
                >
                  <Plus size={14} /> {savingMemory ? 'Saving...' : 'Save'}
                </button>
              </form>

              <div className={styles.memoryList}>
                {memories.length === 0 ? (
                  <div className={styles.historyEmpty}>
                    No long-term memories stored yet. Chat with the agent or add one above!
                  </div>
                ) : (
                  memories.map(mem => (
                    <div key={mem.memory_id} className={styles.memoryCard}>
                      <div className={styles.memoryCardBody}>
                        <span className={styles.memoryTypeBadge}>{mem.memory_type}</span>
                        <div className={styles.memoryText}>{mem.content}</div>
                      </div>
                      <button
                        type="button"
                        className={styles.sessionDelBtn}
                        onClick={() => handleDeleteMemory(mem.memory_id)}
                        aria-label="Delete memory"
                        title="Forget this memory"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
