import React, { useState } from 'react';
import { ScreenshotItem } from '../types.ts';
import {
  Camera,
  Monitor,
  Download,
  Trash2,
  Sparkles,
  Eye,
  FileCheck,
  Loader2,
  Maximize2,
  X,
  Layers,
} from 'lucide-react';
import { soundEffects } from '../utils/soundEffects.ts';

interface ScreenshotStudioProps {
  screenshots: ScreenshotItem[];
  onAddScreenshot: (item: ScreenshotItem) => void;
  onDeleteScreenshot: (id: string) => void;
  onSaveToFile: (item: ScreenshotItem) => void;
  onAnalyzeScreenshot: (item: ScreenshotItem) => Promise<void>;
  isAnalyzing: boolean;
}

export const ScreenshotStudio: React.FC<ScreenshotStudioProps> = ({
  screenshots,
  onAddScreenshot,
  onDeleteScreenshot,
  onSaveToFile,
  onAnalyzeScreenshot,
  isAnalyzing,
}) => {
  const [selectedItem, setSelectedItem] = useState<ScreenshotItem | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureError, setCaptureError] = useState<string | null>(null);

  // Trigger high-res display capture via Screen Capture API
  const handleCaptureScreen = async () => {
    try {
      setIsCapturing(true);
      setCaptureError(null);
      soundEffects.playListen();

      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        throw new Error('Screen capture API is not supported in this browser environment.');
      }

      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: 'monitor',
        },
        audio: false,
      });

      const video = document.createElement('video');
      video.srcObject = stream;
      video.autoplay = true;

      await new Promise<void>((resolve) => {
        video.onloadedmetadata = () => {
          video.play();
          resolve();
        };
      });

      // Allow 300ms for video stream to stabilize
      await new Promise((r) => setTimeout(r, 300));

      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 1920;
      canvas.height = video.videoHeight || 1080;

      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      }

      // Stop all screen tracks immediately
      stream.getTracks().forEach((track) => track.stop());

      const dataUrl = canvas.toDataURL('image/png');
      soundEffects.playScreenshot();

      const newScreenshot: ScreenshotItem = {
        id: `shot-${Date.now()}`,
        dataUrl,
        timestamp: Date.now(),
        title: `Screen Capture ${new Date().toLocaleTimeString()}`,
      };

      onAddScreenshot(newScreenshot);
      setSelectedItem(newScreenshot);
    } catch (err: any) {
      if (err.name !== 'NotAllowedError') {
        console.error('Screenshot error:', err);
        setCaptureError(err.message || 'Failed to capture screen.');
        soundEffects.playError();
      }
    } finally {
      setIsCapturing(false);
    }
  };

  const handleDownloadImage = (item: ScreenshotItem) => {
    soundEffects.playConfirm();
    const link = document.createElement('a');
    link.href = item.dataUrl;
    link.download = `jarvis_screenshot_${item.timestamp}.png`;
    link.click();
  };

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Top Banner & Trigger Action */}
      <div className="hud-panel rounded-xl p-5 border border-cyan-500/20 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center">
            <Camera className="w-5 h-5 text-cyan-300" />
          </div>
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-slate-100 font-mono">
              SCREENSHOT & MULTIMODAL VISION HUD
            </h3>
            <p className="text-xs text-slate-400">
              Capture your entire display, browser window, or active tab, and let JARVIS inspect and analyze telemetry.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCaptureScreen}
            disabled={isCapturing}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] disabled:opacity-50"
          >
            {isCapturing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Capturing Display...</span>
              </>
            ) : (
              <>
                <Monitor className="w-4 h-4" />
                <span>Capture Screen Now</span>
              </>
            )}
          </button>
        </div>
      </div>

      {captureError && (
        <div className="p-3 text-xs bg-red-950/60 border border-red-500/40 rounded-lg text-red-300">
          Capture notice: {captureError}
        </div>
      )}

      {/* Main Grid: Gallery & Detailed Inspection */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Gallery of Captured Shots (4 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-semibold text-slate-300 tracking-wider">
              CAPTURED REPOSITORY ({screenshots.length})
            </span>
          </div>

          <div className="flex flex-col gap-3 max-h-[620px] overflow-y-auto pr-1">
            {screenshots.length === 0 ? (
              <div className="hud-panel rounded-xl p-8 text-center text-slate-500 border border-slate-800">
                <Camera className="w-8 h-8 mx-auto text-slate-600 mb-2" />
                <p className="text-xs font-mono">No screenshots captured yet.</p>
                <p className="text-[11px] text-slate-600 mt-1">
                  Click &ldquo;Capture Screen Now&rdquo; or voice command: &ldquo;Jarvis, take a screenshot&rdquo;.
                </p>
              </div>
            ) : (
              screenshots.map((item) => (
                <div
                  key={item.id}
                  onClick={() => {
                    soundEffects.playNote();
                    setSelectedItem(item);
                  }}
                  className={`hud-panel rounded-xl p-3 border transition-all cursor-pointer flex gap-3 ${
                    selectedItem?.id === item.id
                      ? 'border-cyan-400 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                      : 'border-slate-800 hover:border-cyan-500/40'
                  }`}
                >
                  <div className="w-24 h-16 rounded overflow-hidden bg-slate-900 shrink-0 border border-slate-800 relative">
                    <img
                      src={item.dataUrl}
                      alt={item.title}
                      className="w-full h-full object-cover"
                      referrerPolicy="no-referrer"
                    />
                  </div>

                  <div className="flex-1 min-w-0 flex flex-col justify-between py-0.5">
                    <div>
                      <h4 className="text-xs font-mono text-slate-200 truncate font-semibold">
                        {item.title}
                      </h4>
                      <span className="text-[10px] font-mono text-slate-500 tabular-nums">
                        {new Date(item.timestamp).toLocaleTimeString()} · PNG Frame
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-1">
                      {item.analysis && (
                        <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1">
                          <Sparkles className="w-3 h-3" /> Analyzed
                        </span>
                      )}
                      {item.savedToFile && (
                        <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                          <FileCheck className="w-3 h-3" /> Saved to Files
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteScreenshot(item.id);
                    }}
                    className="p-1.5 text-slate-500 hover:text-red-400 self-start"
                    title="Delete Screenshot"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Selected Screenshot Preview & Gemini Vision Analysis (7 cols) */}
        <div className="lg:col-span-7 hud-panel rounded-xl border border-cyan-500/20 p-5 flex flex-col gap-4 min-h-[500px]">
          {selectedItem ? (
            <>
              {/* Image Preview Container */}
              <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-slate-950 max-h-[340px] flex items-center justify-center">
                <img
                  src={selectedItem.dataUrl}
                  alt={selectedItem.title}
                  className="max-h-[340px] w-auto object-contain"
                  referrerPolicy="no-referrer"
                />
              </div>

              {/* Action Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-y border-slate-800 py-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onAnalyzeScreenshot(selectedItem)}
                    disabled={isAnalyzing}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors disabled:opacity-50 shadow-[0_0_12px_rgba(6,182,212,0.25)]"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Analyzing Vision...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Ask JARVIS to Analyze Screen</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => onSaveToFile(selectedItem)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-300 hover:text-cyan-300 bg-slate-900 border border-slate-700 hover:border-cyan-500/40 rounded-lg transition-colors font-mono"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Save to Virtual Files</span>
                  </button>
                </div>

                <button
                  onClick={() => handleDownloadImage(selectedItem)}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-300 hover:text-cyan-300 bg-slate-900 border border-slate-700 hover:border-cyan-500/40 rounded-lg transition-colors font-mono"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PNG</span>
                </button>
              </div>

              {/* AI Vision Analysis Output */}
              <div className="flex-1 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold text-cyan-400 flex items-center gap-1.5">
                    <Eye className="w-4 h-4" /> JARVIS MULTIMODAL TELEMETRY REPORT
                  </span>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap max-h-[220px] overflow-y-auto">
                  {selectedItem.analysis ? (
                    selectedItem.analysis
                  ) : (
                    <span className="text-slate-500 italic">
                      Click &ldquo;Ask JARVIS to Analyze Screen&rdquo; to run neural vision analysis on this frame. JARVIS will summarize code, inspect UI layout, diagnose errors, and speak key observations.
                    </span>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
              <Monitor className="w-12 h-12 text-slate-700 mb-3" />
              <h4 className="text-sm font-semibold text-slate-300 font-mono">No Screenshot Selected</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Capture a screenshot above or select an existing frame to review telemetry and AI vision analysis.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
