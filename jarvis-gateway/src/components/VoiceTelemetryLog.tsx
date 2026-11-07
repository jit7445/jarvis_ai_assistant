import React, { useState } from 'react';
import { CommandLog } from '../types.ts';
import { Terminal, Send, CheckCircle2, AlertCircle, Clock, Sparkles } from 'lucide-react';

interface VoiceTelemetryLogProps {
  logs: CommandLog[];
  onExecuteTextCommand: (text: string) => void;
  isProcessing: boolean;
}

export const VoiceTelemetryLog: React.FC<VoiceTelemetryLogProps> = ({
  logs,
  onExecuteTextCommand,
  isProcessing,
}) => {
  const [textInput, setTextInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || isProcessing) return;
    onExecuteTextCommand(textInput.trim());
    setTextInput('');
  };

  return (
    <div className="w-full hud-panel rounded-xl border border-cyan-500/20 p-4 flex flex-col gap-3">
      {/* Header and Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono font-semibold tracking-wider text-slate-200">
            VOICE DIRECTIVE TELEMETRY LOG
          </span>
          <span className="text-[10px] font-mono text-slate-500">
            ({logs.length} events)
          </span>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          {isExpanded ? 'Collapse Log' : 'Expand History'}
        </button>
      </div>

      {/* Quick Text Command Input (also allows typing voice commands) */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-500 font-mono text-xs">
            ›
          </span>
          <input
            type="text"
            placeholder="Type or speak a directive (e.g. 'Create folder StarkLabs', 'Take screenshot')..."
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            disabled={isProcessing}
            className="w-full pl-7 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-400 font-mono disabled:opacity-50"
          />
        </div>
        <button
          type="submit"
          disabled={isProcessing || !textInput.trim()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors disabled:opacity-50"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Execute</span>
        </button>
      </form>

      {/* Recent or Expanded Log Entries */}
      <div
        className={`flex flex-col gap-2 overflow-y-auto transition-all ${
          isExpanded ? 'max-h-64' : 'max-h-24'
        } pr-1`}
      >
        {logs.length === 0 ? (
          <div className="text-[11px] font-mono text-slate-500 py-1 italic">
            No directives recorded yet. Click the Arc Reactor or speak to issue voice commands.
          </div>
        ) : (
          logs.slice(0, isExpanded ? 50 : 3).map((log) => (
            <div
              key={log.id}
              className="p-2 rounded bg-slate-950/70 border border-slate-850 flex items-start justify-between gap-3 text-xs font-mono"
            >
              <div className="flex items-start gap-2">
                {log.status === 'success' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                ) : log.status === 'error' ? (
                  <AlertCircle className="w-3.5 h-3.5 text-red-400 mt-0.5 shrink-0" />
                ) : (
                  <Clock className="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0 animate-spin" />
                )}

                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] uppercase font-semibold ${
                        log.sender === 'user' ? 'text-slate-400' : 'text-cyan-400'
                      }`}
                    >
                      {log.sender === 'user' ? 'USER DIRECTIVE' : 'J.A.R.V.I.S.'}
                    </span>
                    {log.action && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-900 border border-slate-700 text-cyan-300">
                        {log.action}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-200 text-[11px] mt-0.5 leading-snug">
                    {log.text}
                  </p>
                  {log.details && (
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      {log.details}
                    </p>
                  )}
                </div>
              </div>

              <span className="text-[10px] text-slate-600 shrink-0 tabular-nums">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
