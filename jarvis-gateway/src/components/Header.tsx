import React from 'react';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';

interface HeaderProps {
  activeTab: 'files' | 'screenshots' | 'notes' | 'video';
  setActiveTab: (tab: 'files' | 'screenshots' | 'notes' | 'video') => void;
  isListening: boolean;
  toggleListening: () => void;
  isMuted: boolean;
  toggleMute: () => void;
  isProcessing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  isListening,
  toggleListening,
  isMuted,
  toggleMute,
}) => {
  return (
    <header className="flex items-center justify-between gap-8 px-6 py-3.5 bg-slate-950/90 backdrop-blur-md border-b border-cyan-500/20 sticky top-0 z-40">
      {/* Zone 1: Single text element wordmark */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="relative flex items-center justify-center w-8 h-8 rounded-full border border-cyan-400/40 bg-cyan-950/40">
          <div className="w-3 h-3 rounded-full bg-cyan-400 shadow-[0_0_10px_#22d3ee] animate-pulse" />
        </div>
        <span className="font-bold tracking-widest text-base text-cyan-300 font-mono whitespace-nowrap">
          J.A.R.V.I.S.
        </span>
      </div>

      {/* Zone 2: 4 clean single-line text navigation links */}
      <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab('files')}
          className={`transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'files'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200 border-transparent'
          }`}
        >
          Files & Workspace
        </button>
        <button
          onClick={() => setActiveTab('screenshots')}
          className={`transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'screenshots'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200 border-transparent'
          }`}
        >
          Screen Capture & Vision
        </button>
        <button
          onClick={() => setActiveTab('notes')}
          className={`transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'notes'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200 border-transparent'
          }`}
        >
          Notes Matrix
        </button>
        <button
          onClick={() => setActiveTab('video')}
          className={`transition-colors whitespace-nowrap shrink-0 py-1 border-b-2 ${
            activeTab === 'video'
              ? 'text-cyan-300 border-cyan-400 font-semibold'
              : 'text-slate-400 hover:text-slate-200 border-transparent'
          }`}
        >
          Video Watcher HUD
        </button>
      </nav>

      {/* Zone 3: 1 primary action / audio controls */}
      <div className="flex items-center gap-2.5 shrink-0">
        <button
          onClick={toggleMute}
          title={isMuted ? 'Unmute Audio Voice' : 'Mute Audio Voice'}
          className="p-2 text-slate-400 hover:text-cyan-300 bg-slate-900 border border-slate-800 rounded-lg transition-colors"
        >
          {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
        </button>

        <button
          onClick={toggleListening}
          className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all whitespace-nowrap shrink-0 border ${
            isListening
              ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.4)]'
              : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-cyan-500/50 hover:text-cyan-300'
          }`}
        >
          {isListening ? (
            <>
              <Mic className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>Voice Active</span>
            </>
          ) : (
            <>
              <MicOff className="w-3.5 h-3.5 text-slate-400" />
              <span>Start Voice</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
