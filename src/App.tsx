import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from './components/Header.tsx';
import { ArcReactorHUD } from './components/ArcReactorHUD.tsx';
import { FileManager } from './components/FileManager.tsx';
import { ScreenshotStudio } from './components/ScreenshotStudio.tsx';
import { NotesManager } from './components/NotesManager.tsx';
import { VideoWatcher } from './components/VideoWatcher.tsx';
import { VoiceTelemetryLog } from './components/VoiceTelemetryLog.tsx';
import { VirtualFile, JarvisNote, ScreenshotItem, CommandLog } from './types.ts';
import { INITIAL_FILES, INITIAL_NOTES } from './utils/initialData.ts';
import { soundEffects } from './utils/soundEffects.ts';
import { jarvisSpeaker } from './utils/speechEngine.ts';

export default function App() {
  // Navigation State
  const [activeTab, setActiveTab] = useState<'files' | 'screenshots' | 'notes' | 'video'>('files');

  // Persistence State
  const [files, setFiles] = useState<VirtualFile[]>(() => {
    try {
      const saved = localStorage.getItem('jarvis_files');
      return saved ? JSON.parse(saved) : INITIAL_FILES;
    } catch {
      return INITIAL_FILES;
    }
  });

  const [activeFileId, setActiveFileId] = useState<string | null>('file-arc-reactor');

  const [notes, setNotes] = useState<JarvisNote[]>(() => {
    try {
      const saved = localStorage.getItem('jarvis_notes');
      return saved ? JSON.parse(saved) : INITIAL_NOTES;
    } catch {
      return INITIAL_NOTES;
    }
  });

  const [screenshots, setScreenshots] = useState<ScreenshotItem[]>(() => {
    try {
      const saved = localStorage.getItem('jarvis_screenshots');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [logs, setLogs] = useState<CommandLog[]>([]);

  // Speech & Audio HUD State
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [jarvisSpeech, setJarvisSpeech] = useState('');
  const [audioLevel, setAudioLevel] = useState(0);

  // Video external trigger
  const [videoTrigger, setVideoTrigger] = useState<{ action: string; noteText?: string } | null>(null);
  const [isAnalyzingScreenshot, setIsAnalyzingScreenshot] = useState(false);

  // Audio Context & Recognition references
  const recognitionRef = useRef<any>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Sync to LocalStorage
  useEffect(() => {
    try {
      localStorage.setItem('jarvis_files', JSON.stringify(files));
    } catch (e) {
      console.warn('LocalStorage save failed:', e);
    }
  }, [files]);

  useEffect(() => {
    try {
      localStorage.setItem('jarvis_notes', JSON.stringify(notes));
    } catch (e) {
      console.warn('LocalStorage save failed:', e);
    }
  }, [notes]);

  useEffect(() => {
    try {
      localStorage.setItem('jarvis_screenshots', JSON.stringify(screenshots));
    } catch (e) {
      console.warn('LocalStorage save failed:', e);
    }
  }, [screenshots]);

  // Audio mute sync
  const toggleMute = () => {
    const next = !isMuted;
    setIsMuted(next);
    soundEffects.setMuted(next);
    if (next) {
      jarvisSpeaker.stopSpeaking();
    }
  };

  // Add Log Entry helper
  const addLog = (
    sender: 'user' | 'jarvis',
    text: string,
    action?: string,
    status: 'success' | 'executing' | 'error' = 'success',
    details?: string
  ) => {
    const newLog: CommandLog = {
      id: `log-${Date.now()}-${Math.random()}`,
      sender,
      text,
      timestamp: Date.now(),
      action,
      status,
      details,
    };
    setLogs((prev) => [newLog, ...prev.slice(0, 99)]);
  };

  // Speak JARVIS response helper
  const speakJarvis = (text: string) => {
    setJarvisSpeech(text);
    if (isMuted) return;
    setIsSpeaking(true);
    jarvisSpeaker.speak(
      text,
      () => setIsSpeaking(true),
      () => setIsSpeaking(false)
    );
  };

  // --- Virtual File Operations ---
  const handleCreateFolder = useCallback((name: string, parentId: string | null = null) => {
    const newFolder: VirtualFile = {
      id: `folder-${Date.now()}`,
      name,
      path: parentId ? `/${name}` : `/${name}`,
      content: '',
      type: 'folder',
      parentId: parentId || null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setFiles((prev) => [...prev, newFolder]);
    soundEffects.playConfirm();
    return newFolder;
  }, []);

  const handleCreateFile = useCallback(
    (name: string, content: string = '', parentId: string | null = null) => {
      const ext = name.split('.').pop() || 'txt';
      const newFile: VirtualFile = {
        id: `file-${Date.now()}`,
        name,
        path: `/${name}`,
        content,
        type: 'file',
        parentId: parentId || null,
        fileType: ext,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      setFiles((prev) => [...prev, newFile]);
      setActiveFileId(newFile.id);
      soundEffects.playConfirm();
      return newFile;
    },
    []
  );

  const handleUpdateFileContent = useCallback((fileId: string, newContent: string) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === fileId ? { ...f, content: newContent, updatedAt: Date.now() } : f))
    );
  }, []);

  const handleDeleteFile = useCallback((fileId: string) => {
    soundEffects.playError();
    setFiles((prev) => prev.filter((f) => f.id !== fileId && f.parentId !== fileId));
    setActiveFileId((current) => (current === fileId ? null : current));
  }, []);

  // --- Note Operations ---
  const handleAddNote = useCallback((noteData: Omit<JarvisNote, 'id' | 'createdAt' | 'updatedAt'>) => {
    const newNote: JarvisNote = {
      ...noteData,
      id: `note-${Date.now()}`,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setNotes((prev) => [newNote, ...prev]);
    soundEffects.playNote();
    return newNote;
  }, []);

  const handleUpdateNote = useCallback((id: string, updates: Partial<JarvisNote>) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, ...updates, updatedAt: Date.now() } : n))
    );
  }, []);

  const handleDeleteNote = useCallback((id: string) => {
    soundEffects.playError();
    setNotes((prev) => prev.filter((n) => n.id !== id));
  }, []);

  // --- Screenshot Operations ---
  const handleAddScreenshot = useCallback((item: ScreenshotItem) => {
    setScreenshots((prev) => [item, ...prev]);
    addLog('jarvis', 'Screenshot captured successfully, sir.', 'TAKE_SCREENSHOT', 'success');
  }, []);

  const handleDeleteScreenshot = useCallback((id: string) => {
    soundEffects.playError();
    setScreenshots((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const handleSaveScreenshotToFile = useCallback(
    (item: ScreenshotItem) => {
      const fileName = `screenshot_${new Date(item.timestamp).toISOString().replace(/[:.]/g, '_')}.png`;
      const screenshotsFolder = files.find((f) => f.type === 'folder' && f.name.toLowerCase() === 'screenshots');
      const parentId = screenshotsFolder ? screenshotsFolder.id : null;

      const newFile: VirtualFile = {
        id: `file-${Date.now()}`,
        name: fileName,
        path: `/Screenshots/${fileName}`,
        content: item.dataUrl,
        type: 'file',
        parentId,
        fileType: 'png',
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      setFiles((prev) => [...prev, newFile]);
      setScreenshots((prev) =>
        prev.map((s) => (s.id === item.id ? { ...s, savedToFile: true } : s))
      );
      soundEffects.playConfirm();
      addLog('jarvis', `Screenshot saved to /Screenshots/${fileName}`, 'WRITE_FILE', 'success');
    },
    [files]
  );

  const handleAnalyzeScreenshot = useCallback(
    async (item: ScreenshotItem) => {
      try {
        setIsAnalyzingScreenshot(true);
        soundEffects.playListen();

        const response = await fetch('/api/jarvis/analyze-screenshot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            imageBase64: item.dataUrl,
            prompt: 'Analyze this screenshot in detail: identify code, UI elements, errors, or diagrams.',
          }),
        });

        if (!response.ok) throw new Error('Analysis failed');
        const data = await response.json();

        setScreenshots((prev) =>
          prev.map((s) => (s.id === item.id ? { ...s, analysis: data.analysis } : s))
        );

        soundEffects.playConfirm();
        speakJarvis(data.speechSummary || 'Display telemetry analyzed, sir.');
        addLog('jarvis', data.speechSummary || 'Screenshot analyzed', 'ANALYZE_SCREENSHOT', 'success');
      } catch (err: any) {
        console.error('Screenshot analysis error:', err);
        soundEffects.playError();
        speakJarvis('Apologies sir, I could not complete the visual analysis.');
      } finally {
        setIsAnalyzingScreenshot(false);
      }
    },
    [speakJarvis]
  );

  // --- Voice Command Execution Brain ---
  const executeVoiceDirective = useCallback(
    async (userInput: string) => {
      if (!userInput.trim()) return;
      setIsProcessing(true);
      addLog('user', userInput);

      try {
        // Fast client-side regexes for immediate execution
        const cleanInput = userInput.trim().toLowerCase();

        // 1. Create Folder
        const createFolderMatch = cleanInput.match(/(?:create|make)\s+folder\s+([a-zA-Z0-9_\-\s]+)/i);
        if (createFolderMatch && !cleanInput.includes('file')) {
          const folderName = createFolderMatch[1].trim();
          handleCreateFolder(folderName);
          setActiveTab('files');
          const reply = `Folder '${folderName}' created in workspace, sir.`;
          speakJarvis(reply);
          addLog('jarvis', reply, 'CREATE_FOLDER', 'success');
          setIsProcessing(false);
          return;
        }

        // 2. Create File & Write in file
        const createFileWriteMatch = cleanInput.match(
          /(?:create|make)\s+file\s+([a-zA-Z0-9_\-.]+)(?:\s+(?:and\s+)?write\s+(?:in\s+file\s+)?(?:that\s+)?(.+))?/i
        );
        if (createFileWriteMatch) {
          const fileName = createFileWriteMatch[1].trim();
          const initialContent = createFileWriteMatch[2] ? createFileWriteMatch[2].trim() : '';
          handleCreateFile(fileName, initialContent);
          setActiveTab('files');
          const reply = initialContent
            ? `File '${fileName}' created with your content, sir.`
            : `File '${fileName}' initialized in workspace, sir.`;
          speakJarvis(reply);
          addLog('jarvis', reply, 'CREATE_FILE', 'success', `File: ${fileName}`);
          setIsProcessing(false);
          return;
        }

        // 3. Write in existing file
        const writeInFileMatch = cleanInput.match(
          /(?:write|append)\s+(?:in|to)\s+(?:file\s+)?([a-zA-Z0-9_\-.]+)(?:\s*:\s*|\s+content\s+|\s+)(.+)/i
        );
        if (writeInFileMatch) {
          const targetName = writeInFileMatch[1].trim();
          const appendContent = writeInFileMatch[2].trim();
          const targetFile = files.find(
            (f) => f.type === 'file' && f.name.toLowerCase() === targetName.toLowerCase()
          );

          if (targetFile) {
            const updated = `${targetFile.content}\n${appendContent}`;
            handleUpdateFileContent(targetFile.id, updated);
            setActiveFileId(targetFile.id);
            setActiveTab('files');
            const reply = `Updated content written to ${targetFile.name}, sir.`;
            speakJarvis(reply);
            addLog('jarvis', reply, 'WRITE_FILE', 'success');
            setIsProcessing(false);
            return;
          }
        }

        // 4. Take Screenshot
        if (cleanInput.includes('screenshot') || cleanInput.includes('capture screen') || cleanInput.includes('take screen shot')) {
          setActiveTab('screenshots');
          const reply = 'Display capture mode activated, sir. Please confirm the screen area.';
          speakJarvis(reply);
          addLog('jarvis', reply, 'TAKE_SCREENSHOT', 'executing');
          setIsProcessing(false);
          return;
        }

        // 5. Take Note
        const noteMatch = cleanInput.match(/(?:take\s+note|create\s+note|note\s+down)(?:\s*:\s*|\s+titled\s+|\s+)(.+)/i);
        if (noteMatch) {
          const noteText = noteMatch[1].trim();
          const title = noteText.length > 30 ? `${noteText.substring(0, 30)}...` : noteText;
          handleAddNote({
            title: `Voice Note: ${title}`,
            content: noteText,
            category: 'General',
            tags: ['Voice', 'Jarvis'],
            pinned: false,
          });
          setActiveTab('notes');
          const reply = 'Voice note recorded and archived in your matrix, sir.';
          speakJarvis(reply);
          addLog('jarvis', reply, 'CREATE_NOTE', 'success', noteText);
          setIsProcessing(false);
          return;
        }

        // 6. Video Directives
        if (cleanInput.includes('video') && (cleanInput.includes('summarize') || cleanInput.includes('study guide') || cleanInput.includes('notes of this video'))) {
          setActiveTab('video');
          setVideoTrigger({ action: 'SUMMARIZE_VIDEO' });
          const reply = 'Compiling executive telemetry and study notes for this video session, sir.';
          speakJarvis(reply);
          addLog('jarvis', reply, 'SUMMARIZE_VIDEO', 'executing');
          setIsProcessing(false);
          return;
        }

        if (cleanInput.includes('video') || cleanInput.includes('timestamp') || cleanInput.includes('note this part') || cleanInput.includes('note this moment')) {
          setActiveTab('video');
          setVideoTrigger({ action: 'VIDEO_TIMESTAMP_NOTE', noteText: userInput });
          const reply = 'Video timestamp marker anchored, sir.';
          speakJarvis(reply);
          addLog('jarvis', reply, 'VIDEO_TIMESTAMP_NOTE', 'success');
          setIsProcessing(false);
          return;
        }

        // 7. General Server-Side Gemini Intelligence Parser
        const response = await fetch('/api/jarvis/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            input: userInput,
            context: {
              activeTab,
              fileNames: files.map((f) => f.name),
              noteCount: notes.length,
            },
          }),
        });

        if (!response.ok) throw new Error('Command parsing failed');
        const data = await response.json();

        // Execute action returned by Gemini
        if (data.action === 'CREATE_FOLDER' && data.parameters?.folderName) {
          handleCreateFolder(data.parameters.folderName);
          setActiveTab('files');
        } else if (data.action === 'CREATE_FILE' && data.parameters?.fileName) {
          handleCreateFile(data.parameters.fileName, data.parameters.fileContent || '');
          setActiveTab('files');
        } else if (data.action === 'WRITE_FILE' && data.parameters?.fileName) {
          const target = files.find(
            (f) => f.name.toLowerCase() === data.parameters.fileName.toLowerCase()
          );
          if (target) {
            handleUpdateFileContent(
              target.id,
              data.parameters.mode === 'overwrite'
                ? data.parameters.fileContent
                : `${target.content}\n${data.parameters.fileContent}`
            );
            setActiveFileId(target.id);
            setActiveTab('files');
          }
        } else if (data.action === 'TAKE_SCREENSHOT') {
          setActiveTab('screenshots');
        } else if (data.action === 'CREATE_NOTE' && data.parameters?.title) {
          handleAddNote({
            title: data.parameters.title,
            content: data.parameters.content || data.parameters.title,
            category: (data.parameters.category as any) || 'General',
            tags: data.parameters.tags || ['Voice'],
            pinned: false,
          });
          setActiveTab('notes');
        } else if (data.action === 'SUMMARIZE_VIDEO') {
          setActiveTab('video');
          setVideoTrigger({ action: 'SUMMARIZE_VIDEO' });
        } else if (data.action === 'VIDEO_TIMESTAMP_NOTE') {
          setActiveTab('video');
          setVideoTrigger({ action: 'VIDEO_TIMESTAMP_NOTE', noteText: data.parameters?.note || userInput });
        }

        const spoken = data.speechResponse || data.fullAnswer || 'Instruction received, sir.';
        speakJarvis(spoken);
        addLog('jarvis', spoken, data.action, 'success', data.fullAnswer);
      } catch (err: any) {
        console.error('Command execution error:', err);
        soundEffects.playError();
        const errReply = 'I encountered a minor calculation variance, sir. Please repeat your instruction.';
        speakJarvis(errReply);
        addLog('jarvis', errReply, 'ERROR', 'error', err.message);
      } finally {
        setIsProcessing(false);
      }
    },
    [
      files,
      notes,
      activeTab,
      handleCreateFolder,
      handleCreateFile,
      handleUpdateFileContent,
      handleAddNote,
      speakJarvis,
    ]
  );

  // --- Web Speech Recognition Initializer ---
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const hasGreetedRef = useRef(false);

  const startListening = async () => {
    soundEffects.playListen();
    setIsListening(true);

    if (!hasGreetedRef.current) {
      hasGreetedRef.current = true;
      soundEffects.playStartup();
      speakJarvis("Good day, sir. All subsystems are online and standing by for your directive.");
      addLog("jarvis", "All subsystems online. Voice telemetry operational.", "STARTUP", "success");
    }

    // Audio Visualizer setup via microphone AnalyserNode
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        const audioCtx = new AudioCtx();
        audioContextRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        const updateAudio = () => {
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length / 255;
          setAudioLevel(avg);
          animFrameRef.current = requestAnimationFrame(updateAudio);
        };
        updateAudio();
      }
    } catch (err) {
      console.warn('Microphone energy visualizer stream unavailable:', err);
    }

    // Web Speech Recognition
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert('Speech recognition is not natively supported in this browser. You can still type directives in the prompt bar.');
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          currentTranscript += item[0].transcript;
          if (item.isFinal) {
            const finalStr = item[0].transcript.trim();
            setTranscript(finalStr);
            executeVoiceDirective(finalStr);
          }
        }
        setTranscript(currentTranscript);
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition status:', event.error);
        if (event.error === 'not-allowed') {
          setIsListening(false);
        }
      };

      recognition.onend = () => {
        // Automatically restart if user hasn't explicitly toggled off
        if (isListening && recognitionRef.current) {
          try {
            recognition.start();
          } catch (e) {
            // Ignore
          }
        }
      };

      recognition.start();
      recognitionRef.current = recognition;
    } catch (err) {
      console.error('Speech recognition start failed:', err);
      setIsListening(false);
    }
  };

  const stopListening = () => {
    setIsListening(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    setAudioLevel(0);
    soundEffects.playNote();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans hud-grid-pattern selection:bg-cyan-500 selection:text-slate-950">
      {/* Top Bar Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isListening={isListening}
        toggleListening={toggleListening}
        isMuted={isMuted}
        toggleMute={toggleMute}
        isProcessing={isProcessing}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 md:px-6 py-6 flex flex-col gap-6">
        {/* Holographic Arc Reactor HUD and Voice State */}
        <ArcReactorHUD
          isListening={isListening}
          isSpeaking={isSpeaking}
          isProcessing={isProcessing}
          transcript={transcript}
          jarvisSpeech={jarvisSpeech}
          audioLevel={audioLevel}
          toggleListening={toggleListening}
          onQuickCommand={(cmd) => executeVoiceDirective(cmd)}
        />

        {/* Viewport Workspace Sections based on Active Tab */}
        <div className="flex-1">
          {activeTab === 'files' && (
            <FileManager
              files={files}
              activeFileId={activeFileId}
              setActiveFileId={setActiveFileId}
              onCreateFolder={handleCreateFolder}
              onCreateFile={handleCreateFile}
              onUpdateFileContent={handleUpdateFileContent}
              onDeleteFile={handleDeleteFile}
            />
          )}

          {activeTab === 'screenshots' && (
            <ScreenshotStudio
              screenshots={screenshots}
              onAddScreenshot={handleAddScreenshot}
              onDeleteScreenshot={handleDeleteScreenshot}
              onSaveToFile={handleSaveScreenshotToFile}
              onAnalyzeScreenshot={handleAnalyzeScreenshot}
              isAnalyzing={isAnalyzingScreenshot}
            />
          )}

          {activeTab === 'notes' && (
            <NotesManager
              notes={notes}
              onAddNote={handleAddNote}
              onUpdateNote={handleUpdateNote}
              onDeleteNote={handleDeleteNote}
            />
          )}

          {activeTab === 'video' && (
            <VideoWatcher
              onSaveNoteToMatrix={handleAddNote}
              onSaveFileToWorkspace={(name, content) => {
                handleCreateFile(name, content);
                setActiveTab('files');
              }}
              externalVideoTrigger={videoTrigger}
            />
          )}
        </div>

        {/* Bottom Voice Directive Telemetry Log */}
        <VoiceTelemetryLog
          logs={logs}
          onExecuteTextCommand={(text) => executeVoiceDirective(text)}
          isProcessing={isProcessing}
        />
      </main>
    </div>
  );
}
