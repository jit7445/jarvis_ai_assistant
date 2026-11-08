import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArcReactorHUD } from './components/ArcReactorHUD.tsx';
import { Header, type Status } from './components/Header.tsx';
import { VoiceTelemetryLog } from './components/VoiceTelemetryLog.tsx';
import type { CommandLog, CoreEvent } from './types.ts';

const MAX_LOGS = 100;

/** Core's states, as the HUD understands them. */
function toLog(event: CoreEvent, index: number): CommandLog | null {
  const id = `${event.at}-${index}`;
  switch (event.state) {
    case 'heard':
    case 'typed':
      return { id, sender: 'user', text: event.text, timestamp: event.at };
    case 'done':
      return { id, sender: 'jarvis', text: event.text, timestamp: event.at, status: 'success' };
    case 'failed':
      return { id, sender: 'jarvis', text: event.text, timestamp: event.at, status: 'error' };
    case 'confirming':
      return { id, sender: 'jarvis', text: event.text, timestamp: event.at, status: 'executing' };
    default:
      return null;
  }
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [logs, setLogs] = useState<CommandLog[]>([]);
  const [state, setState] = useState<CoreEvent | null>(null);
  const [sending, setSending] = useState(false);
  const counter = useRef(0);

  const addEvent = useCallback((event: CoreEvent) => {
    setState(event);
    const log = toLog(event, counter.current++);
    if (log) setLogs((current) => [...current, log].slice(-MAX_LOGS));
  }, []);

  useEffect(() => {
    fetch('/history')
      .then((r) => r.json())
      .then((events: CoreEvent[]) => events.forEach(addEvent))
      .catch(() => {});
  }, [addEvent]);

  useEffect(() => {
    const load = () => fetch('/status').then((r) => r.json()).then(setStatus).catch(() => setStatus(null));
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout>;
    const connect = () => {
      socket = new WebSocket(`ws://${location.host}/live`);
      socket.onmessage = (message) => {
        const data = JSON.parse(message.data);
        if (data.type === 'state') addEvent(data);
      };
      socket.onclose = () => { retry = setTimeout(connect, 2000); };
    };
    connect();
    return () => { clearTimeout(retry); socket?.close(); };
  }, [addEvent]);

  const send = useCallback(async (text: string) => {
    if (!text.trim()) return;
    setSending(true);
    try {
      const response = await fetch('/command', {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text }),
      });
      const { reply } = await response.json();
      if (!response.ok) addEvent({ at: Date.now(), state: 'failed', text: reply });
    } catch {
      addEvent({ at: Date.now(), state: 'failed', text: "The gateway didn't answer." });
    } finally {
      setSending(false);
    }
  }, [addEvent]);

  const now = state?.state ?? 'idle';
  const listening = now === 'listening';
  const thinking = sending || now === 'thinking' || now === 'heard';
  const lastHeard = [...logs].reverse().find((l) => l.sender === 'user')?.text ?? '';
  const lastSaid = [...logs].reverse().find((l) => l.sender === 'jarvis')?.text ?? '';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <Header status={status} isListening={listening} />
      <main className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
        <section className="lg:col-span-2">
          <ArcReactorHUD
            isListening={listening}
            isSpeaking={['done', 'failed', 'confirming'].includes(now)}
            isProcessing={thinking}
            transcript={lastHeard}
            jarvisSpeech={lastSaid}
            audioLevel={listening ? 0.6 : thinking ? 0.3 : 0.1}
            toggleListening={() => {}}
            onQuickCommand={send}
          />
        </section>
        <aside>
          <VoiceTelemetryLog logs={logs} onExecuteTextCommand={send} isProcessing={sending} />
        </aside>
      </main>
    </div>
  );
}
