// Speech Synthesis and Audio Visualizer Utilities for JARVIS

export class JarvisSpeechSynthesis {
  private synth: SpeechSynthesis | null = null;
  private jarvisVoice: SpeechSynthesisVoice | null = null;
  private currentAudioElement: HTMLAudioElement | null = null;

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.synth = window.speechSynthesis;
      this.loadVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  private loadVoices() {
    if (!this.synth) return;
    const voices = this.synth.getVoices();
    // Prefer British English, refined male voices matching JARVIS
    const preferred = voices.find(
      (v) =>
        v.lang.includes('en-GB') ||
        v.name.toLowerCase().includes('british') ||
        v.name.toLowerCase().includes('daniel') ||
        v.name.toLowerCase().includes('george') ||
        v.name.toLowerCase().includes('uk english male')
    );
    this.jarvisVoice = preferred || voices.find((v) => v.lang.startsWith('en')) || voices[0] || null;
  }

  public stopSpeaking() {
    if (this.synth && this.synth.speaking) {
      this.synth.cancel();
    }
    if (this.currentAudioElement) {
      this.currentAudioElement.pause();
      this.currentAudioElement = null;
    }
  }

  public speak(
    text: string,
    onStart?: () => void,
    onEnd?: () => void,
    fallbackToBrowser: boolean = true
  ): Promise<void> {
    return new Promise(async (resolve) => {
      this.stopSpeaking();

      // Attempt high quality Gemini TTS from server if available
      try {
        const response = await fetch('/api/jarvis/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, voice: 'Fenrir' }),
        });

        if (response.ok) {
          const data = await response.json();
          if (data.audioBase64) {
            const audio = new Audio(`data:${data.mimeType || 'audio/wav'};base64,${data.audioBase64}`);
            this.currentAudioElement = audio;

            audio.onplay = () => {
              if (onStart) onStart();
            };
            audio.onended = () => {
              this.currentAudioElement = null;
              if (onEnd) onEnd();
              resolve();
            };
            audio.onerror = () => {
              this.fallbackBrowserSpeech(text, onStart, onEnd, resolve);
            };

            await audio.play();
            return;
          }
        }
      } catch (err) {
        // Fall back to Web Speech API
      }

      if (fallbackToBrowser) {
        this.fallbackBrowserSpeech(text, onStart, onEnd, resolve);
      } else {
        if (onEnd) onEnd();
        resolve();
      }
    });
  }

  private fallbackBrowserSpeech(
    text: string,
    onStart?: () => void,
    onEnd?: () => void,
    resolve?: () => void
  ) {
    if (!this.synth) {
      if (onEnd) onEnd();
      if (resolve) resolve();
      return;
    }

    const cleanText = text.replace(/[*#`_]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);

    if (this.jarvisVoice) {
      utterance.voice = this.jarvisVoice;
    }
    utterance.rate = 1.0;
    utterance.pitch = 0.95;

    utterance.onstart = () => {
      if (onStart) onStart();
    };
    utterance.onend = () => {
      if (onEnd) onEnd();
      if (resolve) resolve();
    };
    utterance.onerror = () => {
      if (onEnd) onEnd();
      if (resolve) resolve();
    };

    this.synth.speak(utterance);
  }
}

export const jarvisSpeaker = new JarvisSpeechSynthesis();
