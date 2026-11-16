/* AudioWorklet processors for 16 kHz PCM mic capture and 24 kHz PCM speaker playback */

class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._buffer = []
    this._targetRate = 16000
    this._chunkSamples = 1024 // ~64ms at 16kHz
    this._muted = false
    this.port.onmessage = (e) => {
      if (e.data?.type === 'mute') {
        this._muted = Boolean(e.data.muted)
      }
    }
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input[0] || input[0].length === 0) return true
    if (this._muted) {
      this.port.postMessage({ type: 'level', level: 0 })
      return true
    }

    const channel = input[0]
    const ratio = sampleRate / this._targetRate

    // Downsample to 16 kHz
    for (let i = 0; i < channel.length; i += ratio) {
      const idx = Math.floor(i)
      const s = Math.max(-1, Math.min(1, channel[idx]))
      this._buffer.push(s)
    }

    while (this._buffer.length >= this._chunkSamples) {
      const slice = this._buffer.splice(0, this._chunkSamples)
      const pcm = new Int16Array(slice.length)
      let sumSq = 0
      for (let i = 0; i < slice.length; i++) {
        const v = slice[i]
        sumSq += v * v
        pcm[i] = v < 0 ? v * 0x8000 : v * 0x7fff
      }
      const rms = Math.min(1, Math.sqrt(sumSq / slice.length) * 4.2)
      this.port.postMessage(
        { type: 'audio', pcm: pcm.buffer, level: rms },
        [pcm.buffer]
      )
    }
    return true
  }
}

class PcmPlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._queue = new Float32Array(24000 * 30) // 30s ring buffer at 24kHz
    this._writeIdx = 0
    this._readIdx = 0
    this._count = 0
    this._inputRate = 24000
    this._srcPos = 0
    this._frameCounter = 0

    this.port.onmessage = (e) => {
      const msg = e.data
      if (!msg) return
      if (msg.type === 'interrupt') {
        this._readIdx = 0
        this._writeIdx = 0
        this._count = 0
        this._srcPos = 0
        this.port.postMessage({ type: 'level', level: 0, playing: false })
        return
      }
      if (msg.type === 'audio' && msg.buffer) {
        const int16 = new Int16Array(msg.buffer)
        const cap = this._queue.length
        for (let i = 0; i < int16.length; i++) {
          if (this._count >= cap) {
            this._readIdx = (this._readIdx + 1) % cap
            this._count--
          }
          this._queue[this._writeIdx] = int16[i] / 32768
          this._writeIdx = (this._writeIdx + 1) % cap
          this._count++
        }
      }
    }
  }

  process(_inputs, outputs) {
    const out = outputs[0]?.[0]
    if (!out) return true

    const cap = this._queue.length
    const step = this._inputRate / sampleRate
    let sumSq = 0
    let played = false

    for (let i = 0; i < out.length; i++) {
      if (this._count <= 1) {
        out[i] = 0
        continue
      }
      played = true
      const s0 = this._queue[this._readIdx]
      const s1 = this._queue[(this._readIdx + 1) % cap]
      const frac = this._srcPos
      const sample = s0 + (s1 - s0) * frac
      out[i] = sample
      sumSq += sample * sample

      this._srcPos += step
      while (this._srcPos >= 1 && this._count > 0) {
        this._readIdx = (this._readIdx + 1) % cap
        this._count--
        this._srcPos -= 1
      }
    }

    this._frameCounter++
    if (this._frameCounter % 4 === 0) {
      const rms = played ? Math.min(1, Math.sqrt(sumSq / out.length) * 3.8) : 0
      this.port.postMessage({ type: 'level', level: rms, playing: played })
    }

    return true
  }
}

registerProcessor('pcm-capture-processor', PcmCaptureProcessor)
registerProcessor('pcm-playback-processor', PcmPlaybackProcessor)
