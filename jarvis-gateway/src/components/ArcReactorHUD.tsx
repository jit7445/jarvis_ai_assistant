import React, { useMemo } from 'react';
import { Mic, Terminal, Activity, Sparkles } from 'lucide-react';

interface ArcReactorHUDProps {
  isListening: boolean;
  isSpeaking: boolean;
  isProcessing: boolean;
  transcript: string;
  jarvisSpeech: string;
  audioLevel: number;
  toggleListening: () => void;
  onQuickCommand: (cmd: string) => void;
}

export const ArcReactorHUD: React.FC<ArcReactorHUDProps> = ({
  isListening,
  isSpeaking,
  isProcessing,
  transcript,
  jarvisSpeech,
  audioLevel,
  toggleListening,
  onQuickCommand,
}) => {
  // Generate 24 animated audio wave bars
  const waveBars = useMemo(() => {
    return Array.from({ length: 20 }).map((_, i) => {
      let height = 6;
      if (isListening || isSpeaking) {
        const factor = Math.sin(i * 0.45 + (isSpeaking ? Date.now() / 200 : 0));
        height = Math.max(6, Math.min(38, Math.round(10 + (audioLevel * 40 + factor * 14))));
      }
      return height;
    });
  }, [isListening, isSpeaking, audioLevel]);

  const statusText = isProcessing
    ? 'ANALYZING VOICE DIRECTIVE...'
    : isSpeaking
    ? 'TRANSMITTING VOCAL TELEMETRY'
    : isListening
    ? 'ONLINE // LISTENING TO VOICE'
    : 'STANDBY // CLICK ARC CORE OR ACTIVATE MIC';

  return (
    <div className="relative w-full rounded-2xl hud-panel p-6 border border-cyan-500/30 overflow-hidden">
      {/* Background radial gradient glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-cyan-900/20 via-slate-950/40 to-transparent pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Left: Arc Reactor Holographic Core */}
        <div className="flex items-center gap-6">
          <div className="relative group cursor-pointer" onClick={toggleListening} title="Click to toggle voice listening">
            {/* Outer concentric decorative ring */}
            <div
              className={`w-28 h-28 rounded-full border border-dashed flex items-center justify-center transition-all duration-700 ${
                isListening
                  ? 'border-cyan-400 rotate-180 shadow-[0_0_25px_rgba(6,182,212,0.5)]'
                  : 'border-slate-700 hover:border-cyan-500/50'
              }`}
            >
              {/* Inner rotating segmented ring */}
              <div
                className={`w-22 h-22 rounded-full border-2 border-cyan-500/40 flex items-center justify-center ${
                  isListening ? 'animate-spin border-t-cyan-400 border-r-cyan-300' : ''
                }`}
                style={{ animationDuration: '6s' }}
              >
                {/* Central Glowing Core */}
                <div
                  className={`w-14 h-14 rounded-full flex flex-col items-center justify-center transition-all ${
                    isListening
                      ? 'bg-cyan-500/30 shadow-[0_0_30px_#22d3ee] scale-105 border border-cyan-300'
                      : isSpeaking
                      ? 'bg-amber-500/30 shadow-[0_0_25px_#f59e0b] border border-amber-300'
                      : 'bg-slate-900/80 border border-slate-700 group-hover:border-cyan-500/60'
                  }`}
                >
                  <Mic
                    className={`w-6 h-6 transition-colors ${
                      isListening
                        ? 'text-cyan-200 animate-pulse'
                        : isSpeaking
                        ? 'text-amber-200 animate-bounce'
                        : 'text-slate-400 group-hover:text-cyan-300'
                    }`}
                  />
                </div>
              </div>
            </div>

            {/* Micro status badge */}
            <span
              className={`absolute -bottom-2 left-1/2 -translate-x-1/2 text-[10px] font-mono px-2 py-0.5 rounded-full border tracking-wider uppercase font-semibold ${
                isListening
                  ? 'bg-cyan-950 text-cyan-300 border-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.4)]'
                  : 'bg-slate-900 text-slate-400 border-slate-800'
              }`}
            >
              {isListening ? 'LIVE' : 'MIC'}
            </span>
          </div>

          {/* Subtitle & Status Information */}
          <div className="flex flex-col gap-1.5 max-w-lg">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono tracking-widest text-cyan-400 font-semibold">
                {statusText}
              </span>
            </div>

            {/* Transcript display */}
            <div className="min-h-12 flex flex-col justify-center">
              {transcript ? (
                <p className="text-sm text-slate-100 font-medium leading-relaxed">
                  <span className="text-cyan-400 font-mono text-xs uppercase mr-2">You:</span>
                  &ldquo;{transcript}&rdquo;
                </p>
              ) : isListening ? (
                <p className="text-xs text-slate-400 italic">
                  Listening... speak naturally (e.g. &ldquo;Jarvis, create folder Stark Projects&rdquo; or &ldquo;Take a screenshot&rdquo;)
                </p>
              ) : (
                <p className="text-xs text-slate-500">
                  Ready. Click the Arc Reactor or speak after activating voice.
                </p>
              )}

              {jarvisSpeech && (
                <p className="text-xs text-cyan-300/90 font-mono mt-1 border-t border-cyan-900/40 pt-1">
                  <span className="text-cyan-500 font-semibold mr-1.5">J.A.R.V.I.S.:</span>
                  {jarvisSpeech}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right: Audio Wave Equalizer & Quick Directives */}
        <div className="flex flex-col items-center md:items-end gap-3 w-full md:w-auto">
          {/* Dynamic Sound Wave Bars */}
          <div className="flex items-end gap-1 h-10 px-3 py-1 bg-slate-950/70 rounded-lg border border-cyan-500/20">
            {waveBars.map((h, idx) => (
              <div
                key={idx}
                className={`w-1 rounded-full transition-all duration-75 ${
                  isListening
                    ? 'bg-cyan-400 shadow-[0_0_6px_#22d3ee]'
                    : isSpeaking
                    ? 'bg-amber-400 shadow-[0_0_6px_#f59e0b]'
                    : 'bg-slate-700'
                }`}
                style={{ height: `${h}px` }}
              />
            ))}
          </div>

          {/* Quick Command Suggestions & Guide Toggle */}
          <div className="flex flex-wrap items-center justify-end gap-1.5 text-[11px] font-mono text-slate-400">
            <span className="text-slate-500 mr-1 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-cyan-400" /> Try saying:
            </span>
            <button
              onClick={() => onQuickCommand('create folder Mark85')}
              className="px-2 py-0.5 rounded bg-slate-900/90 hover:bg-cyan-950 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/40 transition-colors"
              title="Click or say: 'Jarvis, create folder Mark85'"
            >
              &ldquo;Create folder Mark85&rdquo;
            </button>
            <button
              onClick={() => onQuickCommand("create file repulsor.py and write print('Power at 100%')")}
              className="px-2 py-0.5 rounded bg-slate-900/90 hover:bg-cyan-950 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/40 transition-colors"
              title="Click or say: 'Create file repulsor.py and write print(Power at 100%)'"
            >
              &ldquo;Create file repulsor.py and write code&rdquo;
            </button>
            <button
              onClick={() => onQuickCommand('take screenshot')}
              className="px-2 py-0.5 rounded bg-slate-900/90 hover:bg-cyan-950 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/40 transition-colors"
              title="Click or say: 'Jarvis, take a screenshot'"
            >
              📸 &ldquo;Take a screenshot&rdquo;
            </button>
            <button
              onClick={() => onQuickCommand('take note: check arc reactor plasma containment')}
              className="px-2 py-0.5 rounded bg-slate-900/90 hover:bg-cyan-950 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/40 transition-colors"
              title="Click or say: 'Jarvis, take note: ...'"
            >
              📝 &ldquo;Take note: ...&rdquo;
            </button>
            <button
              onClick={() => onQuickCommand('summarize video and capture key moments')}
              className="px-2 py-0.5 rounded bg-slate-900/90 hover:bg-cyan-950 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/40 transition-colors"
              title="Click or say: 'Jarvis, summarize this video'"
            >
              🎬 &ldquo;Summarize this video&rdquo;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
