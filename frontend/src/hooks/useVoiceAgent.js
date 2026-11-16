import { useCallback, useEffect, useRef, useState } from 'react'
import { getStoredAuth } from '../api.js'

function buildVoiceWsUrl(token, sessionId) {
  const apiBase = import.meta.env.VITE_API_URL
  if (apiBase && apiBase.startsWith('http')) {
    const wsBase = apiBase.replace(/^http/, 'ws').replace(/\/$/, '')
    return `${wsBase}/ws/voice?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(sessionId)}`
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/ws/voice?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(sessionId)}`
}

export function useVoiceAgent({ sessionId, onTurnComplete } = {}) {
  const [status, setStatus] = useState('idle') // idle | connecting | listening | thinking | speaking | error
  const [muted, setMuted] = useState(false)
  const [inputLevel, setInputLevel] = useState(0)
  const [outputLevel, setOutputLevel] = useState(0)
  const [transcripts, setTranscripts] = useState([])
  const [activeTools, setActiveTools] = useState([])
  const [error, setError] = useState(null)
  const [voiceInfo, setVoiceInfo] = useState(null)

  const wsRef = useRef(null)
  const audioCtxRef = useRef(null)
  const captureNodeRef = useRef(null)
  const playbackNodeRef = useRef(null)
  const streamRef = useRef(null)
  const pendingToolsRef = useRef([])
  const onTurnCompleteRef = useRef(onTurnComplete)

  useEffect(() => {
    onTurnCompleteRef.current = onTurnComplete
  }, [onTurnComplete])

  const cleanupAudioAndSocket = useCallback(() => {
    if (wsRef.current) {
      try {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'close' }))
        }
        wsRef.current.close()
      } catch {
        // Ignore close errors
      }
      wsRef.current = null
    }
    if (captureNodeRef.current) {
      try { captureNodeRef.current.disconnect() } catch { /* ignore */ }
      captureNodeRef.current = null
    }
    if (playbackNodeRef.current) {
      try { playbackNodeRef.current.disconnect() } catch { /* ignore */ }
      playbackNodeRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (audioCtxRef.current) {
      try { audioCtxRef.current.close() } catch { /* ignore */ }
      audioCtxRef.current = null
    }
    setInputLevel(0)
    setOutputLevel(0)
    setActiveTools([])
    pendingToolsRef.current = []
  }, [])

  useEffect(() => {
    return () => cleanupAudioAndSocket()
  }, [cleanupAudioAndSocket])

  const upsertTranscript = useCallback((role, text, finished = false) => {
    const raw = text || ''
    const clean = raw.trim()
    if (!clean) return
    setTranscripts(prev => {
      const last = prev[prev.length - 1]
      if (last && last.role === role && !last.finished) {
        let nextText
        const normClean = clean.replace(/\s+/g, '')
        const normLast = last.text.replace(/\s+/g, '')
        if (finished && (normClean.includes(normLast) || normClean.length >= normLast.length * 0.6)) {
          nextText = clean
        } else if (normClean.includes(normLast)) {
          nextText = clean
        } else if (normLast.includes(normClean)) {
          nextText = last.text
        } else {
          // Preserve token spacing from streaming deltas without extra spaces before punctuation
          const joiner = raw.startsWith(' ') || /^[,.;:!?']/.test(clean) ? '' : ' '
          nextText = `${last.text}${joiner}${clean}`.replace(/\s+/g, ' ').trim()
        }
        const updated = {
          ...last,
          text: nextText,
          finished,
          toolsUsed: role === 'assistant' ? [...pendingToolsRef.current] : last.toolsUsed,
        }
        return [...prev.slice(0, -1), updated]
      }
      if (last && last.role === role && last.finished && last.text.replace(/\s+/g, '') === clean.replace(/\s+/g, '')) {
        return prev
      }
      return [
        ...prev,
        {
          id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          role,
          text: clean,
          finished,
          toolsUsed: role === 'assistant' ? [...pendingToolsRef.current] : [],
        },
      ]
    })
  }, [])

  const startVoice = useCallback(async (overrideSessionId) => {
    const { token } = getStoredAuth()
    if (!token) {
      setError('Authentication required to start voice session.')
      setStatus('error')
      return
    }

    cleanupAudioAndSocket()
    setError(null)
    setStatus('connecting')

    const rawSid = overrideSessionId || sessionId
    const sid = (!rawSid || rawSid === 'null' || rawSid === 'undefined')
      ? (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `voice-${Date.now()}`)
      : rawSid

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      streamRef.current = stream

      const AudioCtx = window.AudioContext || window.webkitAudioContext
      const audioCtx = new AudioCtx()
      audioCtxRef.current = audioCtx
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume()
      }

      await audioCtx.audioWorklet.addModule('/pcm-processor.js')

      const source = audioCtx.createMediaStreamSource(stream)
      const captureNode = new AudioWorkletNode(audioCtx, 'pcm-capture-processor')
      const playbackNode = new AudioWorkletNode(audioCtx, 'pcm-playback-processor')

      // Connect capture silently through a 0-gain sink so AudioWorklet keeps running
      const zeroGain = audioCtx.createGain()
      zeroGain.gain.value = 0
      source.connect(captureNode)
      captureNode.connect(zeroGain)
      zeroGain.connect(audioCtx.destination)

      playbackNode.connect(audioCtx.destination)

      captureNodeRef.current = captureNode
      playbackNodeRef.current = playbackNode

      const ws = new WebSocket(buildVoiceWsUrl(token, sid))
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      captureNode.port.onmessage = (e) => {
        const msg = e.data
        if (!msg) return
        if (typeof msg.level === 'number') {
          setInputLevel(msg.level)
        }
        if (msg.type === 'audio' && msg.pcm && ws.readyState === WebSocket.OPEN) {
          ws.send(msg.pcm)
        }
      }

      playbackNode.port.onmessage = (e) => {
        const msg = e.data
        if (!msg) return
        if (typeof msg.level === 'number') {
          setOutputLevel(msg.level)
          if (msg.playing) {
            setStatus('speaking')
          } else {
            setStatus(prev => (prev === 'speaking' ? 'listening' : prev))
          }
        }
      }

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          playbackNode.port.postMessage(
            { type: 'audio', buffer: event.data },
            [event.data]
          )
          return
        }

        try {
          const data = JSON.parse(event.data)
          if (data.type === 'ready') {
            setVoiceInfo({ model: data.model, voice: data.voice })
            setStatus('listening')
          } else if (data.type === 'input_transcript') {
            upsertTranscript('user', data.text, data.finished)
          } else if (data.type === 'output_transcript') {
            upsertTranscript('assistant', data.text, data.finished)
          } else if (data.type === 'tool_call' && data.name) {
            setStatus('thinking')
            if (!pendingToolsRef.current.includes(data.name)) {
              pendingToolsRef.current = [...pendingToolsRef.current, data.name]
              setActiveTools([...pendingToolsRef.current])
            }
          } else if (data.type === 'interrupted') {
            playbackNode.port.postMessage({ type: 'interrupt' })
            setOutputLevel(0)
            setStatus('listening')
          } else if (data.type === 'turn_complete') {
            pendingToolsRef.current = []
            setActiveTools([])
            setTranscripts(prev => prev.map(t => ({ ...t, finished: true })))
            onTurnCompleteRef.current?.()
          } else if (data.type === 'error') {
            setError(data.detail || 'Voice stream error')
            setStatus('error')
          }
        } catch {
          // Ignore non-JSON text frames
        }
      }

      ws.onerror = () => {
        setError('Voice WebSocket connection error.')
        setStatus('error')
      }

      ws.onclose = () => {
        setStatus(prev => (prev === 'error' ? 'error' : 'idle'))
      }
    } catch (err) {
      cleanupAudioAndSocket()
      setError(err?.message || 'Microphone permission denied or audio setup failed.')
      setStatus('error')
    }
  }, [cleanupAudioAndSocket, sessionId, upsertTranscript])

  const stopVoice = useCallback(() => {
    cleanupAudioAndSocket()
    setStatus('idle')
  }, [cleanupAudioAndSocket])

  const toggleMute = useCallback(() => {
    setMuted(prev => {
      const next = !prev
      captureNodeRef.current?.port.postMessage({ type: 'mute', muted: next })
      if (next) setInputLevel(0)
      return next
    })
  }, [])

  const interruptPlayback = useCallback(() => {
    playbackNodeRef.current?.port.postMessage({ type: 'interrupt' })
    setOutputLevel(0)
    setStatus('listening')
  }, [])

  const sendTextToVoice = useCallback((text) => {
    if (!text?.trim() || wsRef.current?.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'text', text: text.trim() }))
    upsertTranscript('user', text.trim(), true)
  }, [upsertTranscript])

  return {
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
    sendTextToVoice,
    clearTranscripts: () => setTranscripts([]),
  }
}
