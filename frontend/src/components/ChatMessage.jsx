import { Brain, AlertCircle, User, Wrench } from 'lucide-react'
import styles from './ChatMessage.module.css'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const isError = message.role === 'error'

  if (isError) {
    return (
      <div className={`${styles.row} ${styles.rowError}`}>
        <div className={`${styles.bubble} ${styles.bubbleError}`}>
          <AlertCircle size={18} /> {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className={`${styles.row} ${isUser ? styles.rowUser : styles.rowAssistant}`}>
      {!isUser && (
        <div className={styles.avatarWrap}>
          <Brain size={18} />
        </div>
      )}

      <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleAssistant}`}>
        {/* Show which Agentic RAG / Graph tools the agent invoked */}
        {!isUser && message.toolsUsed && message.toolsUsed.length > 0 && (
          <div className={styles.toolsRow}>
            {message.toolsUsed.map((tool, idx) => (
              <span key={idx} className={styles.toolChip}>
                <Wrench size={11} /> {tool}
              </span>
            ))}
          </div>
        )}

        {/* Format the message: highlight [Source:…] and [Graph:…] references */}
        <MessageContent content={message.content} />

        {/* Timestamp */}
        {message.timestamp && (
          <span className={styles.timestamp}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {isUser && (
        <div className={`${styles.avatarWrap} ${styles.avatarUser}`}>
          {message.userId ? message.userId.charAt(0).toUpperCase() : <User size={18} />}
        </div>
      )}
    </div>
  )
}

/**
 * Renders message content with [Source: …] and [Graph: …] citations highlighted.
 */
function MessageContent({ content }) {
  if (!content) return null

  const parts = content.split(/(\[(?:Source|Graph):[^\]]+\])/g)

  return (
    <p className={styles.content}>
      {parts.map((part, i) => {
        if (part.startsWith('[Source:')) {
          return (
            <span key={i} className={styles.citation}>
              {part}
            </span>
          )
        }
        if (part.startsWith('[Graph:')) {
          return (
            <span key={i} className={styles.graphCitation}>
              {part}
            </span>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </p>
  )
}
