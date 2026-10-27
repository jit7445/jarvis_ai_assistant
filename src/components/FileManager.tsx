import React, { useState } from 'react';
import { VirtualFile } from '../types.ts';
import {
  Folder,
  FolderPlus,
  FileCode,
  FilePlus,
  Trash2,
  Download,
  Save,
  Check,
  FileText,
  Code2,
  ChevronRight,
  ChevronDown,
  Info,
  Sparkles,
} from 'lucide-react';
import { soundEffects } from '../utils/soundEffects.ts';

interface FileManagerProps {
  files: VirtualFile[];
  activeFileId: string | null;
  setActiveFileId: (id: string | null) => void;
  onCreateFolder: (name: string, parentId?: string | null) => void;
  onCreateFile: (name: string, content?: string, parentId?: string | null) => void;
  onUpdateFileContent: (fileId: string, newContent: string) => void;
  onDeleteFile: (fileId: string) => void;
  lastVoiceAction?: string | null;
}

export const FileManager: React.FC<FileManagerProps> = ({
  files,
  activeFileId,
  setActiveFileId,
  onCreateFolder,
  onCreateFile,
  onUpdateFileContent,
  onDeleteFile,
  lastVoiceAction,
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    'folder-projects': true,
    'folder-research': true,
    'folder-screenshots': true,
  });

  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileInitialContent, setNewFileInitialContent] = useState('');
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);

  const [editorContent, setEditorContent] = useState<string>('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Active file details
  const activeFile = files.find((f) => f.id === activeFileId && f.type === 'file');

  // Sync editor when active file changes
  React.useEffect(() => {
    if (activeFile) {
      setEditorContent(activeFile.content);
      setHasUnsavedChanges(false);
    }
  }, [activeFileId, activeFile?.updatedAt]);

  const toggleFolder = (folderId: string) => {
    soundEffects.playNote();
    setExpandedFolders((prev) => ({
      ...prev,
      [folderId]: !prev[folderId],
    }));
  };

  const handleSelectFile = (file: VirtualFile) => {
    soundEffects.playNote();
    setActiveFileId(file.id);
  };

  const handleSave = () => {
    if (!activeFile) return;
    onUpdateFileContent(activeFile.id, editorContent);
    soundEffects.playConfirm();
    setHasUnsavedChanges(false);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  const handleDownload = () => {
    if (!activeFile) return;
    soundEffects.playConfirm();
    const blob = new Blob([activeFile.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = activeFile.name;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleCreateFolderSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    onCreateFolder(newFolderName.trim(), selectedFolderId);
    setNewFolderName('');
    setIsCreatingFolder(false);
  };

  const handleCreateFileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim()) return;
    onCreateFile(newFileName.trim(), newFileInitialContent, selectedFolderId);
    setNewFileName('');
    setNewFileInitialContent('');
    setIsCreatingFile(false);
  };

  // Get file icon based on extension
  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.py') || fileName.endsWith('.ts') || fileName.endsWith('.js') || fileName.endsWith('.json')) {
      return <Code2 className="w-4 h-4 text-cyan-400" />;
    }
    return <FileText className="w-4 h-4 text-slate-400" />;
  };

  // Hierarchy rendering
  const rootFolders = files.filter((f) => f.type === 'folder' && !f.parentId);
  const rootFiles = files.filter((f) => f.type === 'file' && !f.parentId);

  const renderFolderItems = (folderId: string) => {
    const childFolders = files.filter((f) => f.type === 'folder' && f.parentId === folderId);
    const childFiles = files.filter((f) => f.type === 'file' && f.parentId === folderId);

    return (
      <div className="pl-4 space-y-1 mt-1 border-l border-slate-800">
        {childFolders.map((subFolder) => (
          <div key={subFolder.id}>
            <div
              onClick={() => toggleFolder(subFolder.id)}
              className="flex items-center justify-between group px-2 py-1.5 rounded-lg hover:bg-slate-900 cursor-pointer text-xs"
            >
              <div className="flex items-center gap-1.5 text-slate-300">
                {expandedFolders[subFolder.id] ? (
                  <ChevronDown className="w-3.5 h-3.5 text-cyan-400" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                )}
                <Folder className="w-3.5 h-3.5 text-amber-400/90" />
                <span className="font-mono">{subFolder.name}</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteFile(subFolder.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400"
                title="Delete Folder"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
            {expandedFolders[subFolder.id] && renderFolderItems(subFolder.id)}
          </div>
        ))}

        {childFiles.map((file) => (
          <div
            key={file.id}
            onClick={() => handleSelectFile(file)}
            className={`flex items-center justify-between group px-2 py-1.5 rounded-lg cursor-pointer text-xs transition-colors ${
              activeFileId === file.id
                ? 'bg-cyan-950/60 text-cyan-200 border border-cyan-500/40 shadow-[0_0_10px_rgba(6,182,212,0.15)]'
                : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
            }`}
          >
            <div className="flex items-center gap-2 truncate">
              {getFileIcon(file.name)}
              <span className="font-mono truncate">{file.name}</span>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteFile(file.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400"
              title="Delete File"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    );
  };

  const lineCount = (editorContent || '').split('\n').length;

  return (
    <div className="w-full flex flex-col lg:flex-row gap-6">
      {/* Left Sidebar: File Tree & Actions */}
      <div className="w-full lg:w-80 shrink-0 flex flex-col gap-4">
        <div className="hud-panel rounded-xl p-4 flex flex-col gap-4 border border-cyan-500/20">
          {/* Header & Quick Action Buttons */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Folder className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold tracking-wide text-slate-200 font-mono">
                WORKSPACE FILES
              </h3>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => {
                  setIsCreatingFolder(true);
                  setIsCreatingFile(false);
                }}
                className="p-1.5 text-slate-400 hover:text-cyan-300 hover:bg-slate-900 rounded-md transition-colors"
                title="Create Folder"
              >
                <FolderPlus className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  setIsCreatingFile(true);
                  setIsCreatingFolder(false);
                }}
                className="p-1.5 text-slate-400 hover:text-cyan-300 hover:bg-slate-900 rounded-md transition-colors"
                title="Create File"
              >
                <FilePlus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Create Folder Inline Form */}
          {isCreatingFolder && (
            <form onSubmit={handleCreateFolderSubmit} className="flex flex-col gap-2 p-2.5 bg-slate-900/90 rounded-lg border border-cyan-500/30">
              <span className="text-[11px] font-mono text-cyan-400 flex items-center gap-1">
                <FolderPlus className="w-3 h-3" /> New Folder Name
              </span>
              <input
                type="text"
                autoFocus
                placeholder="e.g. Avionics"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                className="w-full px-2.5 py-1 text-xs bg-slate-950 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
              />
              <div className="flex justify-end gap-1.5 mt-1">
                <button
                  type="button"
                  onClick={() => setIsCreatingFolder(false)}
                  className="px-2 py-0.5 text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-2.5 py-0.5 text-xs bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium"
                >
                  Create
                </button>
              </div>
            </form>
          )}

          {/* Create File Inline Form */}
          {isCreatingFile && (
            <form onSubmit={handleCreateFileSubmit} className="flex flex-col gap-2 p-2.5 bg-slate-900/90 rounded-lg border border-cyan-500/30">
              <span className="text-[11px] font-mono text-cyan-400 flex items-center gap-1">
                <FilePlus className="w-3 h-3" /> New File Name
              </span>
              <input
                type="text"
                autoFocus
                placeholder="e.g. telemetry.py"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                className="w-full px-2.5 py-1 text-xs bg-slate-950 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
              />
              <textarea
                placeholder="Initial content (optional)"
                rows={2}
                value={newFileInitialContent}
                onChange={(e) => setNewFileInitialContent(e.target.value)}
                className="w-full px-2.5 py-1 text-xs bg-slate-950 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
              />
              <div className="flex justify-end gap-1.5 mt-1">
                <button
                  type="button"
                  onClick={() => setIsCreatingFile(false)}
                  className="px-2 py-0.5 text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-2.5 py-0.5 text-xs bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium"
                >
                  Create File
                </button>
              </div>
            </form>
          )}

          {/* File Tree List */}
          <div className="flex flex-col space-y-1 max-h-[380px] overflow-y-auto pr-1">
            {rootFolders.map((folder) => (
              <div key={folder.id}>
                <div
                  onClick={() => toggleFolder(folder.id)}
                  className="flex items-center justify-between group px-2 py-1.5 rounded-lg hover:bg-slate-900 cursor-pointer text-xs transition-colors"
                >
                  <div className="flex items-center gap-2 text-slate-200">
                    {expandedFolders[folder.id] ? (
                      <ChevronDown className="w-3.5 h-3.5 text-cyan-400" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                    )}
                    <Folder className="w-4 h-4 text-cyan-400/80" />
                    <span className="font-mono font-medium">{folder.name}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteFile(folder.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400"
                    title="Delete Folder"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
                {expandedFolders[folder.id] && renderFolderItems(folder.id)}
              </div>
            ))}

            {rootFiles.map((file) => (
              <div
                key={file.id}
                onClick={() => handleSelectFile(file)}
                className={`flex items-center justify-between group px-2 py-1.5 rounded-lg cursor-pointer text-xs transition-colors ${
                  activeFileId === file.id
                    ? 'bg-cyan-950/60 text-cyan-200 border border-cyan-500/40 shadow-[0_0_10px_rgba(6,182,212,0.15)]'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {getFileIcon(file.name)}
                  <span className="font-mono truncate">{file.name}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteFile(file.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400"
                  title="Delete File"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Voice Control Assistance Guide for Files */}
        <div className="hud-panel rounded-xl p-3.5 border border-cyan-500/20 text-xs">
          <div className="flex items-center gap-1.5 text-cyan-400 font-mono font-semibold mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>VOICE FILE COMMANDS</span>
          </div>
          <ul className="space-y-1.5 text-slate-400 font-mono text-[11px]">
            <li className="flex items-start gap-1">
              <span className="text-cyan-500">›</span>
              <span>&ldquo;Create folder [name]&rdquo;</span>
            </li>
            <li className="flex items-start gap-1">
              <span className="text-cyan-500">›</span>
              <span>&ldquo;Create file [name] and write [content]&rdquo;</span>
            </li>
            <li className="flex items-start gap-1">
              <span className="text-cyan-500">›</span>
              <span>&ldquo;Write in file [name]: [content]&rdquo;</span>
            </li>
            <li className="flex items-start gap-1">
              <span className="text-cyan-500">›</span>
              <span>&ldquo;Open file [name]&rdquo;</span>
            </li>
            <li className="flex items-start gap-1">
              <span className="text-cyan-500">›</span>
              <span>&ldquo;Delete file [name]&rdquo;</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Right Area: Code / Document Editor */}
      <div className="flex-1 hud-panel rounded-xl border border-cyan-500/20 flex flex-col min-h-[500px]">
        {activeFile ? (
          <>
            {/* Editor Top Bar */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 bg-slate-950/80">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-mono font-semibold text-slate-200">
                  {activeFile.path || `/${activeFile.name}`}
                </span>
                {hasUnsavedChanges && (
                  <span className="text-[10px] text-amber-400 font-mono px-1.5 py-0.5 rounded bg-amber-950/60 border border-amber-800/40">
                    UNSAVED
                  </span>
                )}
                {saveSuccess && (
                  <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-0.5">
                    <Check className="w-3 h-3" /> SAVED
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-slate-500 tabular-nums">
                  {lineCount} lines · {editorContent.length} chars
                </span>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs text-slate-300 hover:text-cyan-300 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded transition-colors font-mono"
                  title="Download File"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export</span>
                </button>
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1 px-3 py-1 text-xs text-white bg-cyan-600 hover:bg-cyan-500 rounded font-medium transition-colors shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Save</span>
                </button>
              </div>
            </div>

            {/* Editor Area with Line Numbers */}
            <div className="relative flex-1 flex bg-slate-950/95 font-mono text-xs">
              {/* Line numbers column */}
              <div className="select-none py-3 px-3 text-right text-slate-600 border-r border-slate-800 bg-slate-950/50 w-12 shrink-0 tabular-nums">
                {Array.from({ length: Math.max(1, lineCount) }).map((_, idx) => (
                  <div key={idx} className="leading-5">
                    {idx + 1}
                  </div>
                ))}
              </div>

              {/* Textarea Code Editor */}
              <textarea
                value={editorContent}
                onChange={(e) => {
                  setEditorContent(e.target.value);
                  setHasUnsavedChanges(true);
                }}
                spellCheck={false}
                className="w-full h-full p-3 bg-transparent text-slate-200 font-mono text-xs leading-5 resize-none focus:outline-none selection:bg-cyan-500/30 selection:text-white"
                placeholder="Type or voice-dictate file contents here..."
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
            <div className="w-12 h-12 rounded-full border border-dashed border-slate-700 flex items-center justify-center mb-3">
              <FileCode className="w-6 h-6 text-slate-600" />
            </div>
            <h4 className="text-sm font-semibold text-slate-300 mb-1 font-mono">No File Selected</h4>
            <p className="text-xs text-slate-500 max-w-sm mb-4">
              Select a file from the workspace tree or speak a voice command like &ldquo;Jarvis, create file neural.py and write code&rdquo;.
            </p>
            <button
              onClick={() => {
                setIsCreatingFile(true);
                setIsCreatingFolder(false);
              }}
              className="px-3 py-1.5 text-xs text-cyan-300 bg-cyan-950/60 border border-cyan-500/40 rounded-lg hover:bg-cyan-900/60 font-mono"
            >
              + Create First File
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
