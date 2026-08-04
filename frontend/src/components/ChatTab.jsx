import { useEffect, useRef, useState } from 'react'
import { sendMessage } from '../api.js'
import ChatMessage from './ChatMessage.jsx'
import styles from './ChatTab.module.css'

const SUGGESTED_QUESTIONS = [
  'What are the main topics covered in my documents?',
  'Summarize the key findings from my uploaded documents.',
  'What technical skills are mentioned?',
  'What are the conclusions or recommendations?',
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
          <h2 className={styles.title}>Chat with your Documents</h2>
          <p className={styles.sub}>
            Ask questions about your uploaded documents. The ADK agent searches ChromaDB and answers using the most relevant chunks.
          </p>
        </div>
        <div className={styles.headerActions}>
          {sessionId && (
            <span className="badge badge-teal" title={`Session: ${sessionId}`}>
              🔗 Session active
            </span>
          )}
          {messages.length > 0 && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleNewSession}
              id="new-session-btn"
            >
              🔄 New session
            </button>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className={`glass-card ${styles.chatArea}`}>
        {messages.length === 0 ? (
          <div className={styles.emptyChat}>
            <span className={styles.emptyChatIcon}>💬</span>
            <h3>Ask a question</h3>
            <p>Your answers are grounded in your uploaded documents only.</p>

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
                <div className={styles.typingAvatar}>🧠</div>
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
          placeholder="Ask a question about your documents… (Enter to send, Shift+Enter for new line)"
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
          id="send-btn"
        >
          {loading ? <span className="spinner" /> : <span>Send ↑</span>}
        </button>
      </div>

      {/* Info footer */}
      <p className={styles.infoFooter}>
        🔒 Answers are user-scoped — only your documents are searched (user: <strong>{userId}</strong>).
        Citations appear as <code>[Source: filename, chunk N]</code>.
      </p>
    </div>
  )
}
