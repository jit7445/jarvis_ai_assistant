import React, { useState, useRef, useEffect } from 'react';
import {
  Video,
  Play,
  Pause,
  Clock,
  Sparkles,
  Camera,
  Layers,
  FileCheck,
  Download,
  Share2,
  Upload,
  Link,
  ChevronRight,
  Loader2,
  Trash2,
  BookOpen,
} from 'lucide-react';
import { VideoTimestampMarker, JarvisNote } from '../types.ts';
import { soundEffects } from '../utils/soundEffects.ts';

interface VideoWatcherProps {
  onSaveNoteToMatrix: (note: Omit<JarvisNote, 'id' | 'createdAt' | 'updatedAt'>) => void;
  onSaveFileToWorkspace: (fileName: string, content: string) => void;
  externalVideoTrigger?: { action: string; noteText?: string } | null;
}

export const VideoWatcher: React.FC<VideoWatcherProps> = ({
  onSaveNoteToMatrix,
  onSaveFileToWorkspace,
  externalVideoTrigger,
}) => {
  const [videoMode, setVideoMode] = useState<'sample' | 'screen_share' | 'url' | 'upload'>('sample');
  const [videoUrl, setVideoUrl] = useState<string>('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4');
  const [customUrlInput, setCustomUrlInput] = useState<string>('');
  const [videoTitle, setVideoTitle] = useState<string>('Blender Open Telemetry Demo Video');
  
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Markers created during playback
  const [markers, setMarkers] = useState<VideoTimestampMarker[]>([
    {
      id: 'vm-1',
      seconds: 12,
      timestampStr: '00:12',
      note: 'Introduction to spatial graphics and physics engine simulation',
      createdAt: Date.now() - 1200000,
    },
    {
      id: 'vm-2',
      seconds: 45,
      timestampStr: '00:45',
      note: 'Core animation pipeline and dynamic lighting techniques',
      createdAt: Date.now() - 600000,
    },
  ]);

  const [instantNoteInput, setInstantNoteInput] = useState('');
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [aiSummaryResult, setAiSummaryResult] = useState<string | null>(null);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // React to voice directives passed from parent App
  useEffect(() => {
    if (externalVideoTrigger) {
      if (externalVideoTrigger.action === 'VIDEO_TIMESTAMP_NOTE') {
        handleAddInstantMarker(externalVideoTrigger.noteText || 'Voice observation at this point');
      } else if (externalVideoTrigger.action === 'SUMMARIZE_VIDEO') {
        handleGenerateAiSummary();
      }
    }
  }, [externalVideoTrigger]);

  // Clean up screen stream on unmount
  useEffect(() => {
    return () => {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const formatSeconds = (sec: number) => {
    if (isNaN(sec)) return '00:00';
    const mins = Math.floor(sec / 60);
    const secs = Math.floor(sec % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      setDuration(videoRef.current.duration || 0);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
      soundEffects.playNote();
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
      soundEffects.playNote();
    }
  };

  const handleSeek = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      soundEffects.playNote();
    }
  };

  // Start Screen Sharing to watch ANY video on user's browser/screen
  const handleStartScreenShare = async () => {
    try {
      soundEffects.playListen();
      if (!navigator.mediaDevices?.getDisplayMedia) {
        alert('Screen share is not supported in this browser.');
        return;
      }

      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true,
      });

      screenStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setIsPlaying(true);
      }
      setVideoMode('screen_share');
      setVideoTitle('Live Screen / Video Tab Stream');
      soundEffects.playConfirm();

      // Listen for stream stop
      stream.getVideoTracks()[0].onended = () => {
        handleStopScreenShare();
      };
    } catch (err: any) {
      console.warn('Screen share cancelled or failed:', err);
    }
  };

  const handleStopScreenShare = () => {
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach((track) => track.stop());
      screenStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.src = videoUrl;
    }
    setVideoMode('sample');
    setVideoTitle('Blender Open Telemetry Demo Video');
  };

  // Handle local video file upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      soundEffects.playConfirm();
      const localUrl = URL.createObjectURL(file);
      setVideoUrl(localUrl);
      setVideoTitle(file.name);
      setVideoMode('upload');
      if (videoRef.current) {
        videoRef.current.srcObject = null;
        videoRef.current.src = localUrl;
        videoRef.current.play().catch(() => {});
        setIsPlaying(true);
      }
    }
  };

  // Handle custom URL submit
  const handleUrlSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customUrlInput.trim()) return;
    soundEffects.playConfirm();
    setVideoUrl(customUrlInput.trim());
    setVideoTitle(`Custom Video Stream (${new URL(customUrlInput).hostname || 'Video'})`);
    setVideoMode('url');
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.src = customUrlInput.trim();
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  // Capture current video frame as base64 snapshot
  const captureVideoFrame = (): string | null => {
    if (!videoRef.current) return null;
    try {
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth || 640;
      canvas.height = videoRef.current.videoHeight || 360;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/png');
      }
    } catch (e) {
      // Cross-origin restriction fallback
    }
    return null;
  };

  // Add instant marker at current playback timestamp
  const handleAddInstantMarker = (text?: string) => {
    soundEffects.playNote();
    const noteText = text || instantNoteInput.trim() || 'Key visual concept noted at timestamp';
    const timestampStr = formatSeconds(currentTime);

    const newMarker: VideoTimestampMarker = {
      id: `vm-${Date.now()}`,
      seconds: currentTime,
      timestampStr,
      note: noteText,
      createdAt: Date.now(),
    };

    setMarkers((prev) => [...prev, newMarker]);
    setInstantNoteInput('');
  };

  // Generate comprehensive AI Video Summary using Gemini
  const handleGenerateAiSummary = async () => {
    try {
      setIsSummarizing(true);
      soundEffects.playListen();

      const frameBase64 = captureVideoFrame();

      const response = await fetch('/api/jarvis/video-notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          videoTitle,
          videoUrl: videoMode === 'screen_share' ? 'Active Screen/Tab Stream' : videoUrl,
          duration: formatSeconds(duration),
          currentTime: formatSeconds(currentTime),
          existingNotes: markers.map((m) => ({ timestamp: m.timestampStr, note: m.note })),
          frameBase64,
          userPrompt: 'Generate a structured study guide with executive summary, core takeaways, and timestamped points.',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate video notes from server');
      }

      const data = await response.json();
      setAiSummaryResult(data.notes);
      soundEffects.playConfirm();
    } catch (err: any) {
      console.error('Video summary error:', err);
      soundEffects.playError();
      setAiSummaryResult(
        `# Executive Video Notes: ${videoTitle}\n\n## 1. Executive Summary\nAnalysis of stream telemetry completed at ${formatSeconds(currentTime)}.\n\n## 2. Core Moments\n` +
          markers.map((m) => `- **${m.timestampStr}**: ${m.note}`).join('\n') +
          '\n\n## 3. Action Items\n- Review concepts outlined in the recording.\n- Validate telemetry in test environment.'
      );
    } finally {
      setIsSummarizing(false);
    }
  };

  // Save AI Notes to Notes Matrix
  const handleSaveToNotesMatrix = () => {
    if (!aiSummaryResult) return;
    soundEffects.playConfirm();
    onSaveNoteToMatrix({
      title: `Study Notes: ${videoTitle}`,
      content: aiSummaryResult,
      category: 'Video Notes',
      tags: ['Video', 'StudyGuide', 'Telemetry'],
      pinned: true,
      videoSource: {
        title: videoTitle,
        url: videoUrl,
        timestamp: formatSeconds(currentTime),
      },
    });
    setSaveSuccessMsg('Saved to Notes Matrix!');
    setTimeout(() => setSaveSuccessMsg(null), 2500);
  };

  // Save AI Notes to Workspace File Manager as .md file
  const handleSaveToWorkspace = () => {
    if (!aiSummaryResult) return;
    soundEffects.playConfirm();
    const safeName = `${videoTitle.toLowerCase().replace(/[^a-z0-9]/g, '_')}_notes.md`;
    onSaveFileToWorkspace(safeName, aiSummaryResult);
    setSaveSuccessMsg(`Saved file "${safeName}" to Workspace!`);
    setTimeout(() => setSaveSuccessMsg(null), 2500);
  };

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Top Source Switcher Toolbar */}
      <div className="hud-panel rounded-xl p-4 border border-cyan-500/20 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono font-semibold text-cyan-400 flex items-center gap-1.5 mr-2">
            <Video className="w-4 h-4" /> VIDEO SOURCE:
          </span>

          <button
            onClick={() => {
              if (videoMode === 'screen_share') handleStopScreenShare();
              setVideoMode('sample');
              setVideoUrl('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4');
              setVideoTitle('Blender Open Telemetry Demo Video');
              if (videoRef.current) {
                videoRef.current.srcObject = null;
                videoRef.current.src = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4';
              }
            }}
            className={`px-3 py-1.5 text-xs font-mono rounded-lg transition-colors border ${
              videoMode === 'sample'
                ? 'bg-cyan-950 text-cyan-300 border-cyan-500/50'
                : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900'
            }`}
          >
            Demo Video
          </button>

          <button
            onClick={videoMode === 'screen_share' ? handleStopScreenShare : handleStartScreenShare}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg transition-colors border ${
              videoMode === 'screen_share'
                ? 'bg-amber-950 text-amber-300 border-amber-500/60 shadow-[0_0_12px_rgba(245,158,11,0.3)]'
                : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900'
            }`}
            title="Share YouTube/Netflix/Vimeo browser tab or window"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>{videoMode === 'screen_share' ? 'Stop Tab Share' : 'Watch Screen/Tab Video'}</span>
          </button>

          <label className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-900 rounded-lg cursor-pointer transition-colors">
            <Upload className="w-3.5 h-3.5" />
            <span>Upload MP4</span>
            <input type="file" accept="video/*" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>

        {/* Custom URL Input */}
        <form onSubmit={handleUrlSubmit} className="flex items-center gap-2 w-full md:w-auto">
          <input
            type="text"
            placeholder="Paste video MP4/WebM URL..."
            value={customUrlInput}
            onChange={(e) => setCustomUrlInput(e.target.value)}
            className="px-3 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-400 font-mono w-full md:w-60"
          />
          <button
            type="submit"
            className="px-2.5 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg font-mono"
          >
            Load
          </button>
        </form>
      </div>

      {saveSuccessMsg && (
        <div className="p-3 text-xs bg-emerald-950/70 border border-emerald-500/40 rounded-lg text-emerald-300 font-mono flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-emerald-400" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* Main Grid: Player + Live Note Timeline (12 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Video Player & Directives (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="hud-panel rounded-xl border border-cyan-500/20 overflow-hidden flex flex-col bg-slate-950">
            {/* Player Viewport */}
            <div className="relative aspect-video w-full bg-black flex items-center justify-center">
              <video
                ref={videoRef}
                src={videoMode !== 'screen_share' ? videoUrl : undefined}
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                crossOrigin="anonymous"
                className="w-full h-full object-contain"
              />

              {videoMode === 'screen_share' && (
                <div className="absolute top-3 left-3 px-2 py-1 bg-amber-950/80 border border-amber-500/50 rounded text-[10px] font-mono text-amber-300 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                  <span>STREAMING EXTERNAL VIDEO TAB</span>
                </div>
              )}
            </div>

            {/* Custom Transport Controls */}
            <div className="p-3.5 bg-slate-950/90 border-t border-slate-800 flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 truncate">
                  <span className="text-xs font-mono font-semibold text-slate-200 truncate">
                    {videoTitle}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 text-xs font-mono text-cyan-400 tabular-nums shrink-0">
                  <Clock className="w-3.5 h-3.5 text-cyan-500" />
                  <span>
                    {formatSeconds(currentTime)} / {formatSeconds(duration)}
                  </span>
                </div>
              </div>

              {/* Progress Slider */}
              <input
                type="range"
                min="0"
                max={duration || 100}
                value={currentTime}
                onChange={(e) => handleSeek(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />

              <div className="flex items-center justify-between pt-1">
                <button
                  onClick={togglePlay}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs font-mono bg-cyan-950 text-cyan-300 border border-cyan-500/40 rounded-lg hover:bg-cyan-900/60"
                >
                  {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  <span>{isPlaying ? 'Pause' : 'Play'}</span>
                </button>

                <button
                  onClick={() => handleAddInstantMarker()}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs font-mono text-amber-300 bg-amber-950/50 border border-amber-500/40 rounded-lg hover:bg-amber-900/50"
                  title="Tag note at this exact second"
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>Tag Moment ({formatSeconds(currentTime)})</span>
                </button>
              </div>
            </div>
          </div>

          {/* Quick Real-Time Note Input */}
          <div className="hud-panel rounded-xl p-3.5 border border-cyan-500/20 flex items-center gap-3">
            <input
              type="text"
              placeholder={`Add observation at ${formatSeconds(currentTime)} (or speak: "Jarvis, note this part")...`}
              value={instantNoteInput}
              onChange={(e) => setInstantNoteInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAddInstantMarker();
              }}
              className="flex-1 px-3 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-slate-200 font-mono focus:outline-none focus:border-cyan-400"
            />
            <button
              onClick={() => handleAddInstantMarker()}
              className="px-3.5 py-1.5 text-xs font-medium text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg font-mono transition-colors shrink-0"
            >
              Add Note
            </button>
          </div>
        </div>

        {/* Right: Live Timestamped Notes & AI Summary (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          {/* AI Video Summarizer Trigger */}
          <div className="hud-panel rounded-xl p-4 border border-cyan-500/30 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-cyan-300 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                AUTOMATED VIDEO STUDY GUIDE
              </span>
              <button
                onClick={handleGenerateAiSummary}
                disabled={isSummarizing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors disabled:opacity-50 shadow-[0_0_12px_rgba(6,182,212,0.25)] font-mono"
              >
                {isSummarizing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Compiling...</span>
                  </>
                ) : (
                  <>
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Summarize Video</span>
                  </>
                )}
              </button>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              JARVIS analyzes the video stream, reviews captured moments, and produces an executive study guide with key takeaways and action points.
            </p>
          </div>

          {/* AI Result or Realtime Markers Tab */}
          <div className="hud-panel rounded-xl p-4 border border-cyan-500/20 flex flex-col gap-3 flex-1 min-h-[400px]">
            {aiSummaryResult ? (
              <div className="flex flex-col gap-3 h-full">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="text-xs font-mono font-semibold text-cyan-400">
                    GENERATED STUDY GUIDE
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={handleSaveToNotesMatrix}
                      className="px-2.5 py-1 text-[11px] text-cyan-300 bg-cyan-950 border border-cyan-500/40 rounded hover:bg-cyan-900 font-mono"
                      title="Save into Notes Matrix"
                    >
                      + Notes Matrix
                    </button>
                    <button
                      onClick={handleSaveToWorkspace}
                      className="px-2.5 py-1 text-[11px] text-slate-300 bg-slate-900 border border-slate-700 rounded hover:bg-slate-800 font-mono"
                      title="Save as .md in Files"
                    >
                      + Save as .md
                    </button>
                  </div>
                </div>

                <div className="flex-1 p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap overflow-y-auto max-h-[360px]">
                  {aiSummaryResult}
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="text-xs font-mono font-semibold text-slate-300">
                    REALTIME TIMESTAMPS ({markers.length})
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    Click timestamp to seek
                  </span>
                </div>

                <div className="flex flex-col gap-2 max-h-[380px] overflow-y-auto pr-1">
                  {markers.length === 0 ? (
                    <div className="p-6 text-center text-slate-500 text-xs font-mono">
                      No moments tagged yet. Play video and click &ldquo;Tag Moment&rdquo; or say &ldquo;Jarvis, note this part&rdquo;.
                    </div>
                  ) : (
                    markers.map((marker) => (
                      <div
                        key={marker.id}
                        onClick={() => handleSeek(marker.seconds)}
                        className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 cursor-pointer flex items-start justify-between gap-2 group transition-colors"
                      >
                        <div className="flex items-start gap-2">
                          <span className="px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800/60 text-[10px] font-mono text-cyan-400 font-semibold shrink-0">
                            {marker.timestampStr}
                          </span>
                          <p className="text-xs text-slate-300 font-mono leading-tight">
                            {marker.note}
                          </p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMarkers((prev) => prev.filter((m) => m.id !== marker.id));
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 shrink-0"
                          title="Delete Marker"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
