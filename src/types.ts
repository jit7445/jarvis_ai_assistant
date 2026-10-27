export interface VirtualFile {
  id: string;
  name: string;
  path: string; // e.g. "/Project Stark/app.ts"
  content: string;
  type: 'file' | 'folder';
  parentId: string | null;
  createdAt: number;
  updatedAt: number;
  fileType?: string; // 'ts', 'js', 'py', 'json', 'md', 'txt', 'png'
  size?: number;
}

export interface JarvisNote {
  id: string;
  title: string;
  content: string;
  createdAt: number;
  updatedAt: number;
  category: 'General' | 'Research' | 'Code' | 'Video Notes';
  tags: string[];
  pinned: boolean;
  videoSource?: {
    title?: string;
    url?: string;
    timestamp?: string;
  };
}

export interface ScreenshotItem {
  id: string;
  dataUrl: string;
  timestamp: number;
  title: string;
  analysis?: string;
  savedToFile?: boolean;
}

export interface CommandLog {
  id: string;
  sender: 'user' | 'jarvis';
  text: string;
  timestamp: number;
  action?: string;
  status?: 'success' | 'executing' | 'error';
  details?: string;
}

export interface VideoTimestampMarker {
  id: string;
  seconds: number;
  timestampStr: string;
  note: string;
  createdAt: number;
}
