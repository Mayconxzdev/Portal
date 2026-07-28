import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { 
  Search, 
  X, 
  Plus, 
  LayoutGrid, 
  Kanban, 
  ClipboardList, 
  Tv, 
  FileCheck, 
  Zap, 
  Ticket, 
  CornerDownLeft,
  Info,
  Building,
  Package,
  ShieldCheck,
  FileText,
  HardDrive
} from 'lucide-react';
import { apiJson } from './kanban/kanbanApi';
import { SearchResult } from './kanban/types';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Badge } from './ui/Badge';
import { Card } from './ui/Card';

interface Props {
  open: boolean;
  onClose: () => void;
  onNavigate: (moduleCode: string) => void;
  onOpenBoard: (boardId: number) => void;
}

export const CommandPalette: React.FC<Props> = ({ open, onClose, onNavigate, onOpenBoard }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [quickText, setQuickText] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        const data = await apiJson<{ results: SearchResult[] }>(`/api/v1/search/global?q=${encodeURIComponent(query)}`);
        setResults(data.results || []);
      } catch (err) {
        console.error('Erro na busca global:', err);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => window.clearTimeout(timer);
  }, [query, open]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setQuickText('');
    setMessage(null);
  }, [open]);

  // Registra ou escuta teclado para fechar no ESC
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  const execute = (item: SearchResult) => {
    if (item.type === 'module') onNavigate(String(item.id));
    if (item.type === 'board') {
      onNavigate('kanban');
      onOpenBoard(Number(item.id));
    }
    if (item.type === 'tv') window.location.assign(`/kanban/tv/${item.id}`);
    if (item.type === 'approval') onNavigate('approvals');
    if (item.type === 'supplier') onNavigate('purchases');
    if (item.type === 'product') onNavigate('purchases');
    if (item.type === 'it_ticket') onNavigate('it');
    if (item.type === 'it_asset') onNavigate('it');
    if (item.type === 'credential') onNavigate('it');
    if (item.type === 'proposal') onNavigate('proposals');
    if (item.type === 'nas_file') onNavigate('files');
    onClose();
  };

  const createQuickCard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickText.trim()) return;
    try {
      const res = await apiJson<any>('/api/v1/kanban/quick-card', { method: 'POST', body: JSON.stringify({ text: quickText, confirm: true }) });
      setMessage(`Tarefa "${res.card?.title || 'criada'}" adicionada com sucesso.`);
      setQuickText('');
      // Recarrega resultados se estiver buscando
      if (query.trim()) {
        const data = await apiJson<{ results: SearchResult[] }>(`/api/v1/search/global?q=${encodeURIComponent(query)}`);
        setResults(data.results || []);
      }
      setTimeout(() => setMessage(null), 4000);
    } catch (err: any) {
      setMessage('Erro ao processar criação rápida: ' + (err.message || err));
      setTimeout(() => setMessage(null), 5000);
    }
  };

  // Agrupa os resultados por categoria
  const groupedResults = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {
      module: [],
      board: [],
      card: [],
      tv: [],
      approval: [],
      supplier: [],
      product: [],
      credential: [],
      it_ticket: [],
      it_asset: [],
      proposal: [],
      nas_file: [],
    };

    results.forEach((item) => {
      const t = item.type;
      if (groups[t]) {
        groups[t].push(item);
      } else {
        if (!groups[t]) groups[t] = [];
        groups[t].push(item);
      }
    });

    return groups;
  }, [results]);

  const staticActions = [
    { id: 'nav-kanban', type: 'action', title: 'Acessar Kanban / Produção', subtitle: 'Visualizar quadros de tarefas e etapas de produção', icon: <Kanban size={16} />, execute: () => { onNavigate('kanban'); onClose(); } },
    { id: 'nav-approvals', type: 'action', title: 'Central de Aprovações', subtitle: 'Verificar solicitações pendentes e registrar decisões', icon: <FileCheck size={16} />, execute: () => { onNavigate('approvals'); onClose(); } },
    { id: 'action-ti', type: 'action', title: 'Abrir TI / Meus chamados', subtitle: 'Acompanhar chamados e abrir solicitacoes de suporte', icon: <Ticket size={16} />, execute: () => { onNavigate('it'); onClose(); } },
  ];

  const getCategoryLabel = (type: string) => {
    const dict: Record<string, string> = {
      module: 'Módulos do Portal',
      board: 'Quadros de Kanban',
      card: 'Cartões / Tarefas',
      tv: 'Modo TV / Produção',
      approval: 'Central de Aprovações',
      supplier: 'Fornecedores (Master Data)',
      product: 'Produtos / Insumos',
      it_ticket: 'Chamados de TI',
      it_asset: 'Ativos de TI',
      credential: 'Cofre de TI (Senhas)',
      proposal: 'Propostas Comerciais',
      nas_file: 'Arquivos / Templates (NAS)',
    };
    return dict[type] || type.toUpperCase();
  };

  const getCategoryIcon = (type: string) => {
    switch (type) {
      case 'module': return <LayoutGrid size={16} style={{ color: 'var(--color-primary)' }} />;
      case 'board': return <Kanban size={16} style={{ color: 'var(--color-success)' }} />;
      case 'card': return <ClipboardList size={16} style={{ color: 'var(--color-info)' }} />;
      case 'tv': return <Tv size={16} style={{ color: 'var(--color-danger)' }} />;
      case 'approval': return <FileCheck size={16} style={{ color: 'var(--color-warning)' }} />;
      case 'supplier': return <Building size={16} style={{ color: '#fb7185' }} />;
      case 'product': return <Package size={16} style={{ color: '#38bdf8' }} />;
      case 'credential': return <ShieldCheck size={16} style={{ color: '#34d399' }} />;
      case 'it_ticket': return <Ticket size={16} style={{ color: '#fbbf24' }} />;
      case 'it_asset': return <HardDrive size={16} style={{ color: '#a78bfa' }} />;
      case 'proposal': return <FileText size={16} style={{ color: '#f472b6' }} />;
      case 'nas_file': return <FileText size={16} style={{ color: '#94a3b8' }} />;
      default: return <Zap size={16} style={{ color: 'var(--text-muted)' }} />;
    }
  };

  if (!open) return null;

  return createPortal(
    <div style={overlayStyle} onClick={onClose}>
      <div style={paletteStyle} onClick={(e) => e.stopPropagation()}>
        {/* Barra de Busca Superior */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, borderBottom: '1px solid var(--border-color)', paddingBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
            <Search size={18} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <input 
              autoFocus 
              className="form-input" 
              value={query} 
              onChange={(event) => setQuery(event.target.value)} 
              placeholder="Buscar por módulo, quadro de kanban, tarefa ou aprovação..." 
              style={{
                background: 'transparent',
                border: 'none',
                padding: 0,
                fontSize: 15,
                color: 'var(--text-primary)',
                outline: 'none',
                width: '100%',
                boxShadow: 'none'
              }}
            />
          </div>
          <Badge variant="neutral" style={{ fontSize: 10, fontFamily: 'monospace', padding: '2px 6px', color: 'var(--text-muted)' }}>ESC</Badge>
          <button className="close-btn" style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }} onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Resultados / Ações */}
        <div style={{ maxHeight: 340, overflowY: 'auto', paddingRight: 4, marginTop: 14 }} className="custom-scroll">
          {loading && (
            <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              Buscando na base de dados...
            </div>
          )}

          {!loading && query.trim() !== '' && results.length === 0 && (
            <div style={{ padding: '30px 10px', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, margin: 0, fontWeight: 500 }}>Nenhum resultado encontrado</p>
              <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 6, margin: 0 }}>
                Nada encontrado. Tente buscar por nome do board, card ou módulo.
              </p>
            </div>
          )}

          {/* Se query estiver vazia, exibe Ações Rápidas e atalhos comuns */}
          {!loading && query.trim() === '' && (
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <span style={categoryHeaderStyle}>Ações Rápidas</span>
                <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
                  {staticActions.map((action) => (
                    <button key={action.id} style={menuItemStyle} onClick={action.execute} className="command-palette-item">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div style={{ background: 'var(--bg-tertiary)', padding: 8, borderRadius: 6, display: 'flex' }}>
                          {action.icon}
                        </div>
                        <div style={{ textAlign: 'left' }}>
                          <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 500 }}>{action.title}</div>
                          <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>{action.subtitle}</div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Badge variant="neutral" style={{ fontSize: 9, padding: '2px 4px' }}>Ação</Badge>
                        <CornerDownLeft size={12} style={{ color: 'var(--text-muted)' }} />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Exibição dos resultados agrupados se houver query */}
          {!loading && query.trim() !== '' && results.length > 0 && (
            <div style={{ display: 'grid', gap: 16 }}>
              {Object.entries(groupedResults).map(([type, items]) => {
                if (items.length === 0) return null;
                return (
                  <div key={type}>
                    <span style={categoryHeaderStyle}>{getCategoryLabel(type)}</span>
                    <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
                      {items.map((item) => (
                        <button key={`${item.type}-${item.id}`} style={menuItemStyle} onClick={() => execute(item)} className="command-palette-item">
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <div style={{ background: 'var(--bg-tertiary)', padding: 8, borderRadius: 6, display: 'flex' }}>
                              {getCategoryIcon(item.type)}
                            </div>
                            <div style={{ textAlign: 'left' }}>
                              <div style={{ color: 'var(--text-primary)', fontSize: 13, fontWeight: 500 }}>{item.title}</div>
                              {item.subtitle && <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>{item.subtitle}</div>}
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Badge variant="neutral" style={{ fontSize: 9, padding: '2px 4px' }}>
                              {item.type === 'tv' ? 'Monitor TV' : item.type}
                            </Badge>
                            <CornerDownLeft size={12} style={{ color: 'var(--text-muted)' }} />
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Criação Rápida de Tarefa no Rodapé */}
        <div style={{ borderTop: '1px solid var(--border-color)', marginTop: 16, paddingTop: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-primary)', fontSize: 13, fontWeight: 600 }}>
            <Plus size={15} style={{ color: 'var(--color-primary)' }} />
            <span>Criar cartão de tarefa rápido</span>
          </div>
          
          <form onSubmit={createQuickCard} style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <input 
              className="form-input" 
              value={quickText} 
              onChange={(event) => setQuickText(event.target.value)} 
              placeholder="Ex: producao: Revisar folga do torno OP#105" 
              style={{ flex: 1, fontSize: 13, color: 'var(--text-primary)', background: 'var(--glass-bg)', border: '1px solid var(--border-color)' }}
            />
            <Button variant="primary" size="sm" type="submit" disabled={!quickText.trim()}>
              Criar
            </Button>
          </form>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
            <p style={{ color: 'var(--text-muted)', fontSize: 11, margin: 0, display: 'flex', alignItems: 'center', gap: 4 }}>
              <Info size={12} />
              <span>Sintaxe: <strong>board: título da tarefa</strong>. Requer confirmação.</span>
            </p>
            {message && <p style={{ color: 'var(--color-success)', fontSize: 11, margin: 0, fontWeight: 500 }}>{message}</p>}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

const overlayStyle: React.CSSProperties = { 
  position: 'fixed', 
  inset: 0, 
  background: 'color-mix(in srgb, var(--bg-primary) 84%, transparent)', 
  zIndex: 1000, 
  display: 'flex', 
  justifyContent: 'center', 
  alignItems: 'flex-start', 
  paddingTop: 80,
  backdropFilter: 'blur(4px)'
};

const paletteStyle: React.CSSProperties = { 
  width: 'min(640px, calc(100vw - 32px))', 
  background: 'var(--surface-glass-strong)', 
  border: '1px solid var(--border-color)', 
  borderRadius: 12, 
  padding: 16, 
  boxShadow: 'var(--shadow-modal)' 
};

const categoryHeaderStyle: React.CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  display: 'block',
  marginTop: 10
};

const menuItemStyle: React.CSSProperties = {
  width: '100%',
  background: 'transparent',
  border: 'none',
  padding: '8px 10px',
  borderRadius: 8,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  cursor: 'pointer',
  transition: 'background-color 0.15s, transform 0.1s',
};



