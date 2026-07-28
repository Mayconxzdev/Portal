import React, { useState, useMemo } from 'react';
import { StickyNote, Plus, Archive, Edit2, Search, Pin, Tag } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { KodaEmptyState } from '../ui/KodaEmptyState';

export interface ITNotesProps {
  notes: any[];
  onNew: () => void;
  onEdit: (note: any) => void;
  onArchive: (id: number) => void;
  onDelete: (note: any) => void;
}

export const ITNotes: React.FC<ITNotesProps> = ({
  notes,
  onNew,
  onEdit,
  onArchive,
  onDelete,
}) => {
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  const activeNotes = useMemo(() => notes.filter(n => !n.is_archived), [notes]);

  // Extract all unique tags
  const allTags = useMemo(() => {
    const tagsSet = new Set<string>();
    activeNotes.forEach(note => {
      const tagsList = Array.isArray(note.tags)
        ? note.tags
        : typeof note.tags === 'string'
        ? note.tags.split(',').map((t: string) => t.trim())
        : [];
      tagsList.forEach((t: string) => {
        if (t) tagsSet.add(t.toLowerCase());
      });
    });
    return Array.from(tagsSet);
  }, [activeNotes]);

  // Filter notes based on search query and tag selection
  const filteredNotes = useMemo(() => {
    return activeNotes.filter(note => {
      const matchSearch =
        note.title?.toLowerCase().includes(search.toLowerCase()) ||
        note.content?.toLowerCase().includes(search.toLowerCase());

      const noteTagsList = Array.isArray(note.tags)
        ? note.tags.map((t: string) => t.toLowerCase())
        : typeof note.tags === 'string'
        ? note.tags.split(',').map((t: string) => t.trim().toLowerCase())
        : [];

      const matchTag = !selectedTag || noteTagsList.includes(selectedTag.toLowerCase());

      return matchSearch && matchTag;
    });
  }, [activeNotes, search, selectedTag]);

  // Sort notes: pinned ones first, then by created_at (newest first)
  const sortedNotes = useMemo(() => {
    return [...filteredNotes].sort((a, b) => {
      if (a.is_pinned && !b.is_pinned) return -1;
      if (!a.is_pinned && b.is_pinned) return 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [filteredNotes]);

  return (
    <div className="space-y-6">
      <Card className="p-6">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              📌 Notas Rápidas / Sticky Notes
            </h2>
            <p className="text-xs text-slate-400 mt-1 font-medium">
              Lembretes, tarefas voláteis, recados rápidos e avisos técnicos compartilhados na equipe de TI.
            </p>
          </div>
          <Button size="sm" variant="primary" onClick={onNew} leftIcon={<Plus size={14} />}>
            Adicionar Lembrete
          </Button>
        </div>

        {/* Filters and Search Bar */}
        <div className="flex flex-col sm:flex-row gap-3 justify-between items-stretch sm:items-center mb-6">
          <div className="relative flex-1 max-w-md">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-550">
              <Search size={16} />
            </span>
            <input
              type="text"
              placeholder="Buscar lembretes por título ou conteúdo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-slate-950/40 border border-slate-800 text-slate-200 placeholder-slate-550 focus:outline-none focus:border-sky-500/50 transition-colors"
            />
          </div>

          {/* Tags list */}
          {allTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 items-center">
              <span className="text-[10px] text-slate-500 font-bold flex items-center gap-1 mr-1.5 uppercase tracking-wider">
                <Tag size={10} /> Filtrar:
              </span>
              <button
                onClick={() => setSelectedTag(null)}
                className={`px-2.5 py-0.5 text-[10px] rounded-full border font-bold transition-all ${
                  selectedTag === null
                    ? 'bg-sky-500/20 text-sky-400 border-sky-500/30 shadow-[0_0_8px_rgba(14,165,233,0.15)]'
                    : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                }`}
              >
                Todas
              </button>
              {allTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                  className={`px-2.5 py-0.5 text-[10px] rounded-full border font-bold transition-all uppercase ${
                    selectedTag === tag
                      ? 'bg-sky-500/20 text-sky-400 border-sky-500/30 shadow-[0_0_8px_rgba(14,165,233,0.15)]'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Sticky Notes Grid */}
        {sortedNotes.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {sortedNotes.map((note) => {
              // Color schemes using transparent glassy look and glowing borders
              let noteStyle = 'bg-yellow-500/5 border-yellow-500/20 text-yellow-100 hover:border-yellow-500/40 hover:bg-yellow-500/10 shadow-[0_4px_16px_rgba(234,179,8,0.02)]';
              let pinColor = 'text-yellow-400';
              let tagStyle = 'bg-yellow-500/10 text-yellow-300 border-yellow-500/20';

              if (note.color === 'blue') {
                noteStyle = 'bg-sky-500/5 border-sky-500/20 text-sky-100 hover:border-sky-500/40 hover:bg-sky-500/10 shadow-[0_4px_16px_rgba(14,165,233,0.02)]';
                pinColor = 'text-sky-400';
                tagStyle = 'bg-sky-500/10 text-sky-300 border-sky-500/20';
              } else if (note.color === 'green') {
                noteStyle = 'bg-emerald-500/5 border-emerald-500/20 text-emerald-100 hover:border-emerald-500/40 hover:bg-emerald-500/10 shadow-[0_4px_16px_rgba(16,185,129,0.02)]';
                pinColor = 'text-emerald-400';
                tagStyle = 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20';
              } else if (note.color === 'pink') {
                noteStyle = 'bg-rose-500/5 border-rose-500/20 text-rose-100 hover:border-rose-500/40 hover:bg-rose-500/10 shadow-[0_4px_16px_rgba(244,63,94,0.02)]';
                pinColor = 'text-rose-400';
                tagStyle = 'bg-rose-500/10 text-rose-300 border-rose-500/20';
              } else if (note.color === 'orange') {
                noteStyle = 'bg-amber-500/5 border-amber-500/20 text-amber-100 hover:border-amber-500/40 hover:bg-amber-500/10 shadow-[0_4px_16px_rgba(245,158,11,0.02)]';
                pinColor = 'text-amber-400';
                tagStyle = 'bg-amber-500/10 text-amber-300 border-amber-500/20';
              } else if (note.color === 'purple') {
                noteStyle = 'bg-violet-500/5 border-violet-500/20 text-violet-100 hover:border-violet-500/40 hover:bg-violet-500/10 shadow-[0_4px_16px_rgba(139,92,246,0.02)]';
                pinColor = 'text-violet-400';
                tagStyle = 'bg-violet-500/10 text-violet-300 border-violet-500/20';
              }

              // Extract tag array
              const noteTags = Array.isArray(note.tags)
                ? note.tags
                : typeof note.tags === 'string'
                ? note.tags.split(',').map((t: string) => t.trim())
                : [];

              return (
                <div
                  key={note.id}
                  className={`p-5 rounded-2xl border flex flex-col justify-between min-h-[180px] ${noteStyle} transition-all duration-300 hover:-translate-y-1 relative group`}
                >
                  <div>
                    <div className="flex justify-between items-start gap-2 mb-3">
                      <div className="flex items-center gap-1.5 min-w-0">
                        {note.is_pinned && <Pin size={12} className={`${pinColor} shrink-0 fill-current`} />}
                        <h4 className="font-extrabold text-sm text-white truncate">{note.title || "Nota"}</h4>
                      </div>
                      <div className="flex gap-1.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <button
                          onClick={() => onEdit(note)}
                          className="p-1 rounded bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white"
                          title="Editar"
                        >
                          <Edit2 size={11} />
                        </button>
                        <button
                          onClick={() => onArchive(note.id)}
                          className="p-1 rounded bg-slate-900 border border-slate-800 hover:border-rose-900 hover:bg-rose-950/20 text-slate-350 hover:text-rose-400"
                          title="Arquivar"
                        >
                          <Archive size={11} />
                        </button>
                        <button
                          onClick={() => onDelete(note)}
                          className="p-1 rounded bg-slate-900 border border-slate-800 hover:border-rose-900 hover:bg-rose-950/20 text-red-400 hover:text-red-300"
                          title="Excluir Permanentemente"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-trash-2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                        </button>
                      </div>
                    </div>
                    
                    <p className="text-[11px] text-slate-300 whitespace-pre-line font-medium leading-relaxed">
                      {note.content}
                    </p>

                    {noteTags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {noteTags.map((tag: string, idx: number) => (
                          <span
                            key={idx}
                            className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${tagStyle}`}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex justify-between items-center pt-3 mt-4 border-t border-slate-900/60 text-[9px] font-bold text-slate-500">
                    <span>Criado em {new Date(note.created_at).toLocaleDateString('pt-BR')}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-12">
            <KodaEmptyState
              title={search || selectedTag ? "Nenhum lembrete encontrado" : "Nenhum lembrete ativo"}
              description={
                search || selectedTag
                  ? "Tente mudar os filtros de busca ou tags para encontrar o que procura."
                  : "Escreva notas rápidas, tarefas voláteis e avisos técnicos compartilhados."
              }
              variant="guide"
              action={
                <Button size="sm" variant="secondary" onClick={onNew} leftIcon={<Plus size={12} />}>
                  Criar Nota Adesiva
                </Button>
              }
            />
          </div>
        )}
      </Card>
    </div>
  );
};

export default ITNotes;
