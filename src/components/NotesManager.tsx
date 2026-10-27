import React, { useState } from 'react';
import { JarvisNote } from '../types.ts';
import {
  FileText,
  Plus,
  Search,
  Pin,
  Trash2,
  Download,
  Tag,
  Calendar,
  Sparkles,
  Video,
  Clock,
  Check,
} from 'lucide-react';
import { soundEffects } from '../utils/soundEffects.ts';

interface NotesManagerProps {
  notes: JarvisNote[];
  onAddNote: (note: Omit<JarvisNote, 'id' | 'createdAt' | 'updatedAt'>) => void;
  onUpdateNote: (id: string, updates: Partial<JarvisNote>) => void;
  onDeleteNote: (id: string) => void;
}

export const NotesManager: React.FC<NotesManagerProps> = ({
  notes,
  onAddNote,
  onUpdateNote,
  onDeleteNote,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [isCreating, setIsCreating] = useState(false);
  const [activeNoteId, setActiveNoteId] = useState<string | null>(notes[0]?.id || null);

  // New Note State
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState<'General' | 'Research' | 'Code' | 'Video Notes'>('General');
  const [tagsInput, setTagsInput] = useState('');

  const categories = ['All', 'General', 'Research', 'Video Notes', 'Code'];

  const filteredNotes = notes.filter((n) => {
    const matchesCategory = selectedCategory === 'All' || n.category === selectedCategory;
    const matchesSearch =
      n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      n.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      n.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  // Sort: pinned first, then newest
  const sortedNotes = [...filteredNotes].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return b.updatedAt - a.updatedAt;
  });

  const activeNote = notes.find((n) => n.id === activeNoteId);

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() && !content.trim()) return;

    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    onAddNote({
      title: title.trim() || 'Untitled Voice Note',
      content: content.trim(),
      category,
      tags,
      pinned: false,
    });

    soundEffects.playNote();
    setTitle('');
    setContent('');
    setTagsInput('');
    setIsCreating(false);
  };

  const handleTogglePin = (id: string, current: boolean) => {
    soundEffects.playConfirm();
    onUpdateNote(id, { pinned: !current });
  };

  const handleExportNote = (note: JarvisNote) => {
    soundEffects.playConfirm();
    const textData = `# ${note.title}\nCategory: ${note.category}\nDate: ${new Date(note.createdAt).toLocaleString()}\nTags: ${note.tags.join(', ')}\n\n${note.content}`;
    const blob = new Blob([textData], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${note.title.toLowerCase().replace(/\s+/g, '_')}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Top Bar with Category Filter, Search and Add */}
      <div className="hud-panel rounded-xl p-4 border border-cyan-500/20 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => {
                soundEffects.playNote();
                setSelectedCategory(cat);
              }}
              className={`px-3 py-1.5 text-xs font-mono font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 ${
                selectedCategory === cat
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search & New Note CTA */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search notes or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-900/90 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-cyan-400 font-mono"
            />
          </div>

          <button
            onClick={() => {
              soundEffects.playNote();
              setIsCreating(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors whitespace-nowrap shrink-0 shadow-[0_0_12px_rgba(6,182,212,0.25)]"
          >
            <Plus className="w-4 h-4" />
            <span>New Note</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Notes List & Note Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Notes List Column (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-3">
          {isCreating && (
            <form onSubmit={handleCreateSubmit} className="hud-panel rounded-xl p-4 border border-cyan-400/50 flex flex-col gap-3">
              <span className="text-xs font-mono font-semibold text-cyan-300 flex items-center gap-1.5">
                <Plus className="w-4 h-4" /> CREATE NEW NOTE
              </span>
              <input
                type="text"
                autoFocus
                placeholder="Note Title (e.g. Arc Plasma Containment)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-1.5 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-cyan-400 font-mono"
              />
              <div className="flex gap-2">
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as any)}
                  className="px-2.5 py-1 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-200 font-mono focus:outline-none focus:border-cyan-400"
                >
                  <option value="General">General</option>
                  <option value="Research">Research</option>
                  <option value="Video Notes">Video Notes</option>
                  <option value="Code">Code</option>
                </select>
                <input
                  type="text"
                  placeholder="Tags (comma separated, e.g. physics, stark)"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  className="flex-1 px-3 py-1 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:outline-none focus:border-cyan-400"
                />
              </div>
              <textarea
                placeholder="Write your note contents or markdown..."
                rows={4}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:outline-none focus:border-cyan-400"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="px-3 py-1 text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1 text-xs bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg"
                >
                  Save Note
                </button>
              </div>
            </form>
          )}

          <div className="flex flex-col gap-2.5 max-h-[620px] overflow-y-auto pr-1">
            {sortedNotes.length === 0 ? (
              <div className="hud-panel rounded-xl p-8 text-center text-slate-500 border border-slate-800">
                <FileText className="w-8 h-8 mx-auto text-slate-600 mb-2" />
                <p className="text-xs font-mono">No notes found in this view.</p>
                <p className="text-[11px] text-slate-600 mt-1">
                  Say &ldquo;Jarvis, take note: [your thoughts]&rdquo; to create instant voice notes.
                </p>
              </div>
            ) : (
              sortedNotes.map((note) => (
                <div
                  key={note.id}
                  onClick={() => {
                    soundEffects.playNote();
                    setActiveNoteId(note.id);
                  }}
                  className={`hud-panel rounded-xl p-3.5 border transition-all cursor-pointer flex flex-col gap-2 ${
                    activeNoteId === note.id
                      ? 'border-cyan-400 bg-cyan-950/30 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                      : 'border-slate-800 hover:border-cyan-500/30'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 truncate">
                      {note.category === 'Video Notes' ? (
                        <Video className="w-4 h-4 text-amber-400 shrink-0" />
                      ) : (
                        <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                      )}
                      <h4 className="text-xs font-mono font-semibold text-slate-200 truncate">
                        {note.title}
                      </h4>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTogglePin(note.id, note.pinned);
                        }}
                        className={`p-1 rounded ${
                          note.pinned ? 'text-amber-400' : 'text-slate-600 hover:text-slate-400'
                        }`}
                        title={note.pinned ? 'Unpin' : 'Pin Note'}
                      >
                        <Pin className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteNote(note.id);
                        }}
                        className="p-1 text-slate-600 hover:text-red-400 rounded"
                        title="Delete Note"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {note.content}
                  </p>

                  <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1 border-t border-slate-900">
                    <span className="text-slate-400">{note.category}</span>
                    <span className="tabular-nums">
                      {new Date(note.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Note Detail Column (7 cols) */}
        <div className="lg:col-span-7 hud-panel rounded-xl border border-cyan-500/20 p-5 flex flex-col gap-4 min-h-[500px]">
          {activeNote ? (
            <>
              {/* Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                <div className="flex flex-col gap-1">
                  <h3 className="text-base font-semibold text-slate-100 font-mono">
                    {activeNote.title}
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                    <span className="text-cyan-400">{activeNote.category}</span>
                    <span>·</span>
                    <span className="tabular-nums">
                      {new Date(activeNote.createdAt).toLocaleDateString()} at{' '}
                      {new Date(activeNote.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleExportNote(activeNote)}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs text-slate-300 hover:text-cyan-300 bg-slate-900 border border-slate-700 hover:border-cyan-500/40 rounded-lg transition-colors font-mono"
                    title="Export Markdown"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export .md</span>
                  </button>
                </div>
              </div>

              {/* Tags */}
              {activeNote.tags.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <Tag className="w-3.5 h-3.5 text-slate-500" />
                  {activeNote.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="text-[11px] font-mono text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Video reference if available */}
              {activeNote.videoSource && (
                <div className="p-3 bg-amber-950/20 border border-amber-500/30 rounded-lg flex items-center justify-between text-xs text-amber-300 font-mono">
                  <div className="flex items-center gap-2">
                    <Video className="w-4 h-4 text-amber-400" />
                    <span>Source: {activeNote.videoSource.title || 'Video Stream'}</span>
                  </div>
                  {activeNote.videoSource.timestamp && (
                    <span className="flex items-center gap-1 text-amber-200">
                      <Clock className="w-3 h-3" /> {activeNote.videoSource.timestamp}
                    </span>
                  )}
                </div>
              )}

              {/* Content Editable Area */}
              <div className="flex-1">
                <textarea
                  value={activeNote.content}
                  onChange={(e) => onUpdateNote(activeNote.id, { content: e.target.value })}
                  className="w-full h-full min-h-[300px] p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 text-xs leading-relaxed font-mono focus:outline-none focus:border-cyan-400/60 resize-none selection:bg-cyan-500/30"
                  placeholder="Note content..."
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-500">
              <FileText className="w-12 h-12 text-slate-700 mb-3" />
              <h4 className="text-sm font-semibold text-slate-300 font-mono">No Note Selected</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Select a note from the left or speak &ldquo;Jarvis, take a note&rdquo; to dictate new items.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
