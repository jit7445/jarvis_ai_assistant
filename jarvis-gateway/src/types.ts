export interface CommandLog {
  id: string;
  sender: 'user' | 'jarvis';
  text: string;
  timestamp: number;
  action?: string;
  status?: 'success' | 'executing' | 'error';
  details?: string;
}

/** One state change from jarvis-core, relayed by the gateway. */
export interface CoreEvent {
  at: number;
  state: string;
  text: string;
}
