import styles from './ChatMessage.module.css'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const isError = message.role === 'error'

  if (isError) {
    return (
      <div className={`${styles.row} ${styles.rowError}`}>
        <div className={`${styles.bubble} ${styles.bubbleError}`}>
          <span>⚠️</span> {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className={`${styles.row} ${isUser ? styles.rowUser : styles.rowAssistant}`}>
      {!isUser && (
        <div className={styles.avatar}>🧠</div>
      )}

      <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleAssistant}`}>
        {/* Format the message: bold [Source:…] references */}
        <MessageContent content={message.content} />

        {/* Timestamp */}
        {message.timestamp && (
          <span className={styles.timestamp}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {isUser && (
        <div className={`${styles.avatar} ${styles.avatarUser}`}>
          {message.userId ? message.userId.charAt(0).toUpperCase() : 'U'}
        </div>
      )}
    </div>
  )
}

/**
 * Renders message content with [Source: …] citations highlighted.
 */
function MessageContent({ content }) {
  if (!content) return null

  // Split on [Source: ...] citations
  const parts = content.split(/(\[Source:[^\]]+\])/g)

  return (
    <p className={styles.content}>
      {parts.map((part, i) =>
        part.startsWith('[Source:') ? (
          <span key={i} className={styles.citation}>{part}</span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </p>
  )
}
