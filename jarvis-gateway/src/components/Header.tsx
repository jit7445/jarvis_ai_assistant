import React from 'react';
import { Mic, MicOff } from 'lucide-react';

export interface Status {
  core: { ok: boolean; whisper: string } | null;
  gemini: boolean;
}

interface HeaderProps {
  status: Status | null;
  isListening: boolean;
}

const Chip: React.FC<{ on: boolean; label: string }> = ({ on, label }) => (
  <span
    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-mono whitespace-nowrap ${
      on ? 'text-cyan-300 border-cyan-500/40 bg-cyan-950/30' : 'text-slate-500 border-slate-800 bg-slate-900'
    }`}
  >
    <span className={`w-1.5 h-1.5 rounded-full ${on ? 'bg-cyan-400 shadow-[0_0_6px_#22d3ee]' : 'bg-slate-600'}`} />
    {label}
  </span>
);

export const Header: React.FC<HeaderProps> = ({ status, isListening }) => {
  const core = status?.core;
  return (
    <header className="flex items-center justify-between gap-8 px-6 py-3.5 bg-slate-950/90 backdrop-blur-md border-b border-cyan-500/20 sticky top-0 z-40">
      <div className="flex items-center gap-3 shrink-0">
        <div className="relative flex items-center justify-center w-8 h-8 rounded-full border border-cyan-400/40 bg-cyan-950/40">
          <div className="w-3 h-3 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee] animate-pulse" />
        </div>
        <span className="font-bold tracking-widest text-base text-cyan-300 font-mono whitespace-nowrap">
          J.A.R.V.I.S.
        </span>
      </div>

      <nav className="hidden md:flex items-center gap-2">
        <Chip on={Boolean(core?.ok)} label={core?.ok ? 'Core online' : 'Core offline'} />
        <Chip on={core?.whisper === 'loaded'} label={core?.whisper === 'loaded' ? 'Whisper loaded' : 'Whisper on demand'} />
        <Chip on={Boolean(status?.gemini)} label={status?.gemini ? 'Gemini on' : 'Gemini off'} />
      </nav>

      <div
        className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap shrink-0 border ${
          isListening
            ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.4)]'
            : 'bg-slate-900 text-slate-300 border-slate-700'
        }`}
        title='Jarvis listens through the Mac microphone: say "Jarvis" or hold right Option'
      >
        {isListening ? <Mic className="w-3.5 h-3.5 text-cyan-400 animate-pulse" /> : <MicOff className="w-3.5 h-3.5 text-slate-400" />}
        <span>{isListening ? 'Listening' : 'Say "Jarvis"'}</span>
      </div>
    </header>
  );
};
