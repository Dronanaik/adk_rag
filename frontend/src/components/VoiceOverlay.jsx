import { useEffect, useRef } from 'react'
import { MessageSquare, Mic, MicOff, Phone, PhoneOff, Volume2, Wrench } from 'lucide-react'
import styles from './VoiceOverlay.module.css'

const STATUS_LABELS = {
  idle: 'Ready — Tap Orb or Start Voice',
  connecting: 'Connecting to Gemini Live...',
  listening: 'Listening...',
  thinking: 'Searching Knowledge & Memory...',
  speaking: 'Speaking...',
  error: 'Connection Error',
}

export default function VoiceOverlay({
  voice,
  onSwitchToText,
}) {
  const {
    status,
    muted,
    inputLevel,
    outputLevel,
    transcripts,
    activeTools,
    error,
    voiceInfo,
    startVoice,
    stopVoice,
    toggleMute,
    interruptPlayback,
  } = voice

  const transcriptEndRef = useRef(null)

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcripts])

  const isLive = status === 'listening' || status === 'thinking' || status === 'speaking' || status === 'connecting'
  const activeLevel = status === 'speaking' ? outputLevel : inputLevel

  // Dynamic "blowing up" expansion driven by live RMS audio energy
  const orbScale = isLive ? 1 + activeLevel * 0.42 : 1
  const ring1Scale = isLive ? 1.05 + activeLevel * 0.65 : 1
  const ring2Scale = isLive ? 1.02 + activeLevel * 0.45 : 1
  const ring3Scale = isLive ? 1.0 + activeLevel * 0.28 : 1
  const glowSpread = Math.round(36 + activeLevel * 68)

  const orbClasses = [
    styles.bigOrb,
    status === 'idle' ? styles.bigOrb_idle : '',
    status === 'thinking' ? styles.bigOrb_thinking : '',
    status === 'speaking' ? styles.bigOrb_speaking : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={styles.voiceStage} id="voice-agent-stage">
      {/* Top status bar */}
      <div className={styles.voiceTopBar}>
        <div className={styles.statusBadge} id="voice-status-badge">
          <span className={`${styles.statusDot} ${styles[`statusDot_${status}`] || ''}`} />
          <span>{STATUS_LABELS[status] || status}</span>
        </div>

        <div className={styles.voiceMeta}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              if (isLive) stopVoice()
              onSwitchToText?.()
            }}
            id="switch-to-text-btn"
          >
            <MessageSquare size={14} /> Text Chat
          </button>
        </div>
      </div>

      {error && <div className={styles.errorBanner}>{error}</div>}

      {/* Center Big Round Blowing-Up Speaker Orb */}
      <div className={styles.orbStage}>
        <div className={styles.orbContainer}>
          <div
            className={`${styles.shockRing} ${styles.ringOuter}`}
            style={{
              transform: `scale(${ring1Scale.toFixed(3)})`,
              opacity: isLive ? 0.25 + activeLevel * 0.7 : 0.14,
            }}
          />
          <div
            className={`${styles.shockRing} ${styles.ringMid}`}
            style={{
              transform: `scale(${ring2Scale.toFixed(3)})`,
              opacity: isLive ? 0.35 + activeLevel * 0.65 : 0.18,
            }}
          />
          <div
            className={`${styles.shockRing} ${styles.ringInner}`}
            style={{
              transform: `scale(${ring3Scale.toFixed(3)})`,
              opacity: isLive ? 0.4 + activeLevel * 0.6 : 0.22,
            }}
          />

          <button
            type="button"
            className={orbClasses}
            id="voice-big-orb"
            onClick={() => (isLive ? toggleMute() : startVoice())}
            style={
              isLive
                ? {
                    transform: `scale(${orbScale.toFixed(3)})`,
                    boxShadow: `0 0 ${glowSpread}px ${
                      status === 'speaking'
                        ? 'rgba(52, 211, 153, 0.55)'
                        : status === 'thinking'
                          ? 'rgba(251, 191, 36, 0.48)'
                          : 'rgba(34, 211, 238, 0.48)'
                    }, inset 0 0 32px rgba(103, 232, 249, 0.28)`,
                  }
                : undefined
            }
            aria-label={isLive ? (muted ? 'Unmute microphone' : 'Mute microphone') : 'Start voice conversation'}
          >
            {status === 'speaking' ? (
              <Volume2 size={48} strokeWidth={1.75} />
            ) : muted ? (
              <MicOff size={48} strokeWidth={1.75} />
            ) : (
              <Mic size={48} strokeWidth={1.75} />
            )}
            <span className={styles.orbLabel}>
              {!isLive ? 'Tap to Speak' : muted ? 'Muted' : status === 'speaking' ? 'Speaking' : 'Live'}
            </span>
          </button>
        </div>

        {/* Active ADK Tools */}
        <div className={styles.toolRow}>
          {activeTools.map((tool) => (
            <span key={tool} className={styles.toolPill}>
              <Wrench size={12} /> {tool}
            </span>
          ))}
        </div>

        {/* Controls */}
        <div className={styles.controlsRow}>
          {!isLive ? (
            <button
              type="button"
              className={`${styles.controlBtn} ${styles.startBtn}`}
              onClick={() => startVoice()}
              id="start-voice-btn"
            >
              <Phone size={16} /> Start Voice Agent
            </button>
          ) : (
            <>
              <button
                type="button"
                className={`${styles.controlBtn} ${muted ? styles.muteActive : ''}`}
                onClick={toggleMute}
                id="mute-voice-btn"
              >
                {muted ? <MicOff size={16} /> : <Mic size={16} />}
                {muted ? 'Unmute' : 'Mute'}
              </button>

              {status === 'speaking' && (
                <button
                  type="button"
                  className={styles.controlBtn}
                  onClick={interruptPlayback}
                  id="interrupt-voice-btn"
                >
                  Interrupt
                </button>
              )}

              <button
                type="button"
                className={`${styles.controlBtn} ${styles.endBtn}`}
                onClick={stopVoice}
                id="end-voice-btn"
              >
                <PhoneOff size={16} /> End Call
              </button>
            </>
          )}
        </div>
      </div>

      {/* Live Transcript */}
      <div className={styles.transcriptBox} id="voice-transcript-box">
        {transcripts.length === 0 ? (
          <div className={styles.transcriptEmpty}>
            Live captions and tool citations will appear here as you speak with the agent.
          </div>
        ) : (
          transcripts.map((t) => (
            <div key={t.id} className={styles.transcriptItem}>
              <span
                className={`${styles.transcriptRole} ${
                  t.role === 'user' ? styles.roleUser : styles.roleAssistant
                }`}
              >
                {t.role === 'user' ? 'You' : 'ADK Voice Agent'}
                {t.toolsUsed?.length ? ` · ${t.toolsUsed.join(', ')}` : ''}
              </span>
              <span className={styles.transcriptText}>{t.text}</span>
            </div>
          ))
        )}
        <div ref={transcriptEndRef} />
      </div>
    </div>
  )
}
