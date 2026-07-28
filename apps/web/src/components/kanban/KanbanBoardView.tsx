import React, { useMemo, useState, useEffect } from 'react';
import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, KeyboardSensor, PointerSensor, closestCorners, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, horizontalListSortingStrategy, sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { Archive, CheckCircle2, Clock, RotateCcw, Users, Filter, Tv, Plus, Settings, Tags, RefreshCw } from 'lucide-react';
import { KanbanBoardSidePanel } from './KanbanBoardSidePanel';
import { BoardFieldsDrawer } from './BoardFieldsDrawer';
import { BoardLabelsDrawer } from './BoardLabelsDrawer';
import { CreateCardModal } from './CreateCardModal';
import { CreateColumnModal } from './CreateColumnModal';
import { KanbanCardDetail } from './KanbanCardDetail';
import { KanbanColumnView } from './KanbanColumnView';
import { KanbanListView } from './KanbanListView';
import { KanbanBoard, KanbanCard, CurrentUser } from './types';
import { accessRank, apiJson } from './kanbanApi';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Checkbox } from '../ui/Checkbox';
import { Badge } from '../ui/Badge';
import { MetricCard } from '../ui/MetricCard';
import { Modal } from '../ui/Modal';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { BoardSwitcher } from './BoardSwitcher';
import { KanbanViewToggle } from './KanbanViewToggle';
import { Drawer } from '../ui/Drawer';
import { ActionOverflowMenu } from '../ui/ActionOverflowMenu';
import { getQueryNumber, getQueryParam, replaceQueryParams } from '../../utils/urlState';

interface Props {
  board: KanbanBoard;
  onReload: () => Promise<void>;
  onArchiveBoard: (restore?: boolean) => Promise<void>;
  currentUser?: CurrentUser;
  boards: KanbanBoard[];
  includeArchived: boolean;
  onIncludeArchivedChange: (value: boolean) => void;
  onSelectBoard: (boardId: number) => void;
  onBackToBoards: () => void;
}

export const KanbanBoardView: React.FC<Props> = ({
  board,
  onReload,
  onArchiveBoard,
  currentUser,
  boards,
  includeArchived,
  onIncludeArchivedChange,
  onSelectBoard,
  onBackToBoards,
}) => {
  const [selectedCard, setSelectedCard] = useState<KanbanCard | null>(null);
  const [cardToArchive, setCardToArchive] = useState<KanbanCard | null>(null);
  const [activeDragCard, setActiveDragCard] = useState<KanbanCard | null>(null);
  const [viewMode, setViewMode] = useState<'board' | 'list'>(() => getQueryParam('view') === 'list' ? 'list' : 'board');
  const [modal, setModal] = useState<null | 'card' | 'column' | 'fields' | 'labels' | 'import' | 'tvChoice' | 'tvConfig'>(null);
  const [filters, setFilters] = useState({ text: '', overdue: false, high: false, unassigned: false, archived: false, labelId: 0 });
  const [showFilters, setShowFilters] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  const boardAccess = board.access_level || 'READ_ONLY';
  const canEditCards = (accessRank[boardAccess] || 0) >= accessRank.NORMAL;
  const canEditStructure = (accessRank[boardAccess] || 0) >= accessRank.MANAGER;

  // Sincroniza selectedCard com o board quando o board é recarregado
  useEffect(() => {
    if (selectedCard) {
      const updatedCard = board.columns
        .flatMap((col) => col.cards)
        .find((c) => c.id === selectedCard.id);
      if (updatedCard) {
        setSelectedCard(updatedCard);
      }
    }
  }, [board, selectedCard?.id]);

  useEffect(() => {
    const cardId = getQueryNumber('card');
    if (!cardId || selectedCard) return;
    const card = board.columns.flatMap((col) => col.cards).find((item) => item.id === cardId);
    if (card) setSelectedCard(card);
  }, [board, selectedCard]);

  const selectViewMode = (mode: 'board' | 'list') => {
    setViewMode(mode);
    replaceQueryParams({ view: mode === 'board' ? null : mode });
  };

  const openCard = (card: KanbanCard) => {
    setSelectedCard(card);
    replaceQueryParams({ card: card.id });
  };

  const closeCard = () => {
    setSelectedCard(null);
    replaceQueryParams({ card: null });
  };

  const filteredColumns = useMemo(() => {
    const now = new Date();
    return board.columns.filter((column) => !column.is_archived).map((column) => ({
      ...column,
      cards: column.cards.filter((card) => {
        if (!filters.archived && card.is_archived) return false;
        if (filters.text && !`${card.title} ${card.description || ''}`.toLowerCase().includes(filters.text.toLowerCase())) return false;
        if (filters.overdue && (!card.due_date || new Date(card.due_date) >= now)) return false;
        if (filters.high && !['HIGH', 'URGENT'].includes(card.priority) && !card.labels.some((l) => ['alta', 'urgente'].includes(l.name.toLowerCase()))) return false;
        if (filters.unassigned && card.assignees.length > 0) return false;
        if (filters.labelId && !card.labels.some((label) => label.id === filters.labelId)) return false;
        return true;
      }),
    }));
  }, [board, filters]);

  const summaryCards = board.columns.flatMap((column) => column.cards).filter((card) => !card.is_archived);
  const openCards = summaryCards.filter((card) => !board.columns.find((column) => column.id === card.column_id)?.is_done_column).length;
  const overdueCards = summaryCards.filter((card) => card.due_date && new Date(card.due_date) < new Date()).length;
  const urgentCards = summaryCards.filter((card) => card.priority === 'URGENT' || card.labels?.some((l) => l.name.toLowerCase() === 'urgente')).length;

  const assigneeSet = new Set<string>();
  summaryCards.forEach((card) => {
    card.assignees?.forEach((a) => {
      if (a.user?.username) assigneeSet.add(a.user.username);
    });
  });

  const totalCardsCount = summaryCards.length;
  
  const concluidosCardsCount = summaryCards.filter((card) => {
    const col = board.columns.find((c) => c.id === card.column_id);
    return col?.is_done_column;
  }).length;

  const atrasadosCardsCount = summaryCards.filter((card) => {
    if (!card.due_date) return false;
    const isDone = board.columns.find((c) => c.id === card.column_id)?.is_done_column;
    if (isDone) return false;
    const dDate = new Date(card.due_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    dDate.setHours(0, 0, 0, 0);
    return dDate < today;
  }).length;

  const hojeCardsCount = summaryCards.filter((card) => {
    if (!card.due_date) return false;
    const isDone = board.columns.find((c) => c.id === card.column_id)?.is_done_column;
    if (isDone) return false;
    const dDate = new Date(card.due_date);
    const today = new Date();
    return dDate.getFullYear() === today.getFullYear() &&
           dDate.getMonth() === today.getMonth() &&
           dDate.getDate() === today.getDate();
  }).length;

  const proximos7DiasCardsCount = summaryCards.filter((card) => {
    if (!card.due_date) return false;
    const isDone = board.columns.find((c) => c.id === card.column_id)?.is_done_column;
    if (isDone) return false;
    const dDate = new Date(card.due_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    dDate.setHours(0, 0, 0, 0);
    const limit = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    return dDate > today && dDate <= limit;
  }).length;

  const progressPercentage = totalCardsCount > 0 ? Math.round((concluidosCardsCount / totalCardsCount) * 100) : 0;


  const moveCard = async (card: KanbanCard, columnId: number, position = 0) => {
    await apiJson(`/api/v1/kanban/cards/${card.id}/move`, { method: 'POST', body: JSON.stringify({ to_column_id: columnId, new_position: position }) });
    await onReload();
  };

  const handleDragStart = (event: DragStartEvent) => {
    if (event.active.data.current?.type === 'card') {
      setActiveDragCard(event.active.data.current.card as KanbanCard);
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const activeType = event.active.data.current?.type;
    setActiveDragCard(null);
    if (!event.over || !canEditCards) return;
    if (activeType === 'card') {
      const card = event.active.data.current?.card as KanbanCard;
      const overId = String(event.over.id);
      const targetCard = board.columns.flatMap((column) => column.cards).find((item) => `card-${item.id}` === overId);
      const targetColumn = targetCard ? board.columns.find((column) => column.id === targetCard.column_id) : board.columns.find((column) => `column-${column.id}` === overId);
      if (!targetColumn) return;
      const position = targetCard ? targetColumn.cards.filter((item) => !item.is_archived).findIndex((item) => item.id === targetCard.id) : targetColumn.cards.length;
      await moveCard(card, targetColumn.id, Math.max(position, 0));
    }
    if (activeType === 'column' && canEditStructure) {
      const activeColumn = event.active.data.current?.column;
      const overColumn = board.columns.find((column) => `column-${column.id}` === String(event.over?.id));
      if (!activeColumn || !overColumn || activeColumn.id === overColumn.id) return;
      const ordered = [...board.columns].filter((column) => !column.is_archived);
      const from = ordered.findIndex((column) => column.id === activeColumn.id);
      const to = ordered.findIndex((column) => column.id === overColumn.id);
      const [moved] = ordered.splice(from, 1);
      ordered.splice(to, 0, moved);
      await apiJson(`/api/v1/kanban/boards/${board.id}/columns/reorder`, {
        method: 'POST',
        body: JSON.stringify({ columns: ordered.map((column, index) => ({ column_id: column.id, position: index })) }),
      });
      await onReload();
    }
  };

  const createColumn = async (payload: Record<string, unknown>) => {
    await apiJson(`/api/v1/kanban/boards/${board.id}/columns`, { method: 'POST', body: JSON.stringify(payload) });
    await onReload();
  };

  const createCard = async (payload: Record<string, unknown>) => {
    await apiJson(`/api/v1/kanban/boards/${board.id}/cards`, { method: 'POST', body: JSON.stringify(payload) });
    await onReload();
  };

  const proceedArchiveCard = async (card: KanbanCard) => {
    await apiJson(`/api/v1/kanban/cards/${card.id}/archive`, { method: 'POST' });
    await onReload();
  };

  const archiveCard = async (card: KanbanCard) => {
    setCardToArchive(card);
  };

  const duplicateCard = async (card: KanbanCard) => {
    await apiJson(`/api/v1/kanban/cards/${card.id}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({ title: `Cópia - ${card.title}`, copy_checklist: true, copy_labels: true, copy_assignees: true, copy_custom_fields: true }),
    });
    await onReload();
  };

  return (
    <div className="kanban-board-layout" style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0, gap: '10px' }}>
      <section className="operational-command-surface">
        <div className="command-surface-left">
          <Button variant="ghost" size="sm" onClick={onBackToBoards}>
            ← Voltar
          </Button>
          <BoardSwitcher
            boards={boards}
            selectedBoard={board}
            includeArchived={includeArchived}
            onIncludeArchivedChange={onIncludeArchivedChange}
            onSelectBoard={onSelectBoard}
          />
          <span className="divider">|</span>
          <KanbanViewToggle value={viewMode} onChange={selectViewMode} />
          {canEditCards && (
            <Button size="sm" variant="primary" onClick={() => setModal('card')} leftIcon={<Plus size={14} />}>
              Nova tarefa
            </Button>
          )}
        </div>
        
        <div className="command-surface-right">
          <Button size="sm" variant={showFilters ? 'primary' : 'secondary'} onClick={() => setShowFilters(!showFilters)} leftIcon={<Filter size={14} />}>
            Filtros
          </Button>
          <Button size="sm" variant={panelOpen ? 'primary' : 'secondary'} onClick={() => setPanelOpen(!panelOpen)} leftIcon={<Clock size={14} />}>
            Atividades & Resumo
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setModal('tvChoice')} leftIcon={<Tv size={14} />}>
            Modo TV
          </Button>
          <Button size="sm" variant="ghost" onClick={onReload} leftIcon={<RefreshCw size={14} />}>
            Atualizar
          </Button>
          
          <ActionOverflowMenu
            label="Ações do quadro"
            items={[
              canEditStructure ? { key: 'columns', label: 'Gerenciar colunas', onSelect: () => setModal('column'), icon: <Settings size={14} /> } : null,
              canEditStructure ? { key: 'fields', label: 'Campos personalizados', onSelect: () => setModal('fields'), icon: <Settings size={14} /> } : null,
              canEditStructure ? { key: 'labels', label: 'Etiquetas', onSelect: () => setModal('labels'), icon: <Tags size={14} /> } : null,
              canEditStructure ? { key: 'archive', label: board.is_archived ? 'Restaurar quadro' : 'Arquivar quadro', onSelect: () => onArchiveBoard(board.is_archived), tone: 'danger', icon: <Archive size={14} /> } : null,
            ].filter(Boolean) as any}
          />
        </div>
      </section>

      {showFilters && (
        <section className="glass-card" style={{ padding: 12, marginTop: 4 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr repeat(4, auto) 180px', gap: 12, alignItems: 'center' }}>
            <Input placeholder="Buscar por título ou descrição..." value={filters.text} onChange={(event) => setFilters({ ...filters, text: event.target.value })} style={{ margin: 0 }} />
            <Checkbox label="Atrasados" checked={filters.overdue} onChange={(event) => setFilters({ ...filters, overdue: event.target.checked })} />
            <Checkbox label="Alta prioridade" checked={filters.high} onChange={(event) => setFilters({ ...filters, high: event.target.checked })} />
            <Checkbox label="Sem responsável" checked={filters.unassigned} onChange={(event) => setFilters({ ...filters, unassigned: event.target.checked })} />
            <Checkbox label="Arquivados" checked={filters.archived} onChange={(event) => setFilters({ ...filters, archived: event.target.checked })} />
            <Select value={filters.labelId} onChange={(event) => setFilters({ ...filters, labelId: Number(event.target.value) })} options={[
              { value: 0, label: 'Todas etiquetas' },
              ...board.labels.map((label) => ({ value: label.id, label: label.name })),
            ]} style={{ margin: 0 }} />
          </div>
        </section>
      )}

      <main className="kanban-board-main" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>      {viewMode === 'list' ? (
        <KanbanListView board={board} onOpenCard={openCard} />
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={handleDragStart} onDragCancel={() => setActiveDragCard(null)} onDragEnd={handleDragEnd}>
          <SortableContext items={filteredColumns.map((column) => `column-${column.id}`)} strategy={horizontalListSortingStrategy}>
            <section className="kanban-board-work-surface">
              {filteredColumns.map((column) => (
                <KanbanColumnView
                  key={column.id}
                  column={column}
                  columns={board.columns}
                  canEditCards={canEditCards}
                  onOpenCard={openCard}
                  onMoveCard={(card, columnId) => moveCard(card, columnId)}
                  onArchiveCard={archiveCard}
                  onDuplicateCard={duplicateCard}
                />
              ))}
            </section>
          </SortableContext>
          <DragOverlay dropAnimation={null} zIndex={10000}>
            {activeDragCard ? (
              <div style={{
                background: 'var(--surface-panel)',
                border: '1px solid var(--color-primary)',
                borderRadius: 8,
                padding: 12,
                boxShadow: 'var(--shadow-dropdown)',
                width: 280,
                color: 'var(--text-primary)',
                zIndex: 9999,
                pointerEvents: 'none',
              }}>
                <strong>{activeDragCard.title}</strong>
                {activeDragCard.description && <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: '6px 0 0' }}>{activeDragCard.description}</p>}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

      <CreateCardModal board={board} isOpen={modal === 'card'} onClose={() => setModal(null)} onCreate={createCard} />
      <CreateColumnModal board={board} isOpen={modal === 'column'} onClose={() => setModal(null)} onChanged={onReload} />
      <BoardFieldsDrawer board={board} isOpen={modal === 'fields'} onClose={() => setModal(null)} onChanged={onReload} />
      <BoardLabelsDrawer board={board} isOpen={modal === 'labels'} onClose={() => setModal(null)} onChanged={onReload} />
      <TVOpenModal board={board} isOpen={modal === 'tvChoice'} onClose={() => setModal(null)} onConfigure={() => setModal('tvConfig')} />
      <TVConfigModal board={board} isOpen={modal === 'tvConfig'} onClose={() => setModal(null)} />
      {selectedCard && <KanbanCardDetail board={board} card={selectedCard} canEdit={canEditCards} onClose={closeCard} onChanged={onReload} currentUser={currentUser} />}
      <ConfirmDialog
        isOpen={cardToArchive !== null}
        onClose={() => setCardToArchive(null)}
        onConfirm={async () => {
          if (cardToArchive) {
            const card = cardToArchive;
            setCardToArchive(null);
            await proceedArchiveCard(card);
          }
        }}
        title="Arquivar tarefa"
        message={`Deseja arquivar a tarefa "${cardToArchive?.title}"?`}
        confirmText="Arquivar"
        cancelText="Cancelar"
        variant="warning"
      />
      </main>

      <Drawer
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        title="Informações do Quadro"
        description="Métricas de progresso, prazos e histórico de atividades recentes."
      >
        <KanbanBoardSidePanel
          board={board}
          summary={{
            total: totalCardsCount,
            open: openCards,
            overdue: atrasadosCardsCount,
            urgent: urgentCards,
            done: concluidosCardsCount,
            assignees: assigneeSet.size,
          }}
        />
      </Drawer>
    </div>
  );
};

const tvLayouts = [
  { value: 'COLUMNS', label: 'Quadro' },
  { value: 'TV_LIST', label: 'Lista' },
  { value: 'PRODUCTION_LIST', label: 'Produção Lista' },
  { value: 'PRODUCTION', label: 'Produção Cards' },
];

const openTv = (boardId: number, mode: 'external' | 'meeting', layout: string, remember: boolean) => {
  if (remember) {
    localStorage.setItem(`vesper.kanban.tv.preference.${boardId}`, JSON.stringify({ mode, layout }));
  }
  window.location.assign(`/kanban/tv/${boardId}?mode=${mode}&layout=${layout}`);
};

const TVOpenModal: React.FC<{ board: KanbanBoard; isOpen: boolean; onClose: () => void; onConfigure: () => void }> = ({ board, isOpen, onClose, onConfigure }) => {
  const saved = (() => {
    try { return JSON.parse(localStorage.getItem(`vesper.kanban.tv.preference.${board.id}`) || '{}'); } catch { return {}; }
  })();
  const [layout, setLayout] = useState(saved.layout || 'PRODUCTION_LIST');
  const [remember, setRemember] = useState(true);
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Como deseja abrir o painel?" size="md" footer={<Button variant="ghost" onClick={onClose}>Cancelar</Button>}>
      <div style={{ display: 'grid', gap: 14 }}>
        <Select label="Visual" value={layout} onChange={(event) => setLayout(event.target.value)} options={tvLayouts} />
        <Checkbox label="Lembrar essa escolha para este quadro" checked={remember} onChange={(event) => setRemember(event.target.checked)} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          <button className="glass-card" style={tvChoiceCard} onClick={() => openTv(board.id, 'external', layout, remember)}>
            <strong style={{ color: 'var(--text-primary)', fontSize: 16 }}>TV Externa</strong>
            <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Modo limpo para deixar em uma TV ou monitor da produção.</span>
          </button>
          <button className="glass-card" style={tvChoiceCard} onClick={() => openTv(board.id, 'meeting', layout, remember)}>
            <strong style={{ color: 'var(--text-primary)', fontSize: 16 }}>Apresentação / Reunião</strong>
            <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Modo completo para supervisão, análise e explicação.</span>
          </button>
        </div>
        <Button variant="secondary" onClick={onConfigure}>Configurar TV/Foco</Button>
      </div>
    </Modal>
  );
};

const TVConfigModal: React.FC<{ board: KanbanBoard; isOpen: boolean; onClose: () => void }> = ({ board, isOpen, onClose }) => {
  const [configMode, setConfigMode] = useState<'meeting' | 'external'>('meeting');

  const [meetingConfig, setMeetingConfig] = useState({
    layoutType: 'COLUMNS',
    showClock: true,
    showBoardName: true,
    showKpis: true,
    showRanking: true,
    showExitButton: true,
    visibleRows: 'auto',
    fontScale: 'large',
    density: 'comfortable',
    autoScroll: false,
  });

  const [externalConfig, setExternalConfig] = useState({
    layoutType: 'PRODUCTION_LIST',
    showClock: false,
    showBoardName: false,
    showKpis: false,
    showRanking: false,
    showExitButton: false,
    visibleRows: '16',
    fontScale: 'large',
    density: 'factory',
    autoScroll: true,
  });

  // Novos estados para a configuracao de colunas e larguras
  const [meetingColumns, setMeetingColumns] = useState<string[]>([]);
  const [externalColumns, setExternalColumns] = useState<string[]>([]);
  const [meetingVisible, setMeetingVisible] = useState<string[]>([]);
  const [externalVisible, setExternalVisible] = useState<string[]>([]);
  const [meetingWidths, setMeetingWidths] = useState<Record<string, number>>({});
  const [externalWidths, setExternalWidths] = useState<Record<string, number>>({});

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const loadConfig = async () => {
      try {
        const config = await apiJson<any>(`/api/v1/kanban/boards/${board.id}/tv-config?_=${Date.now()}`);
        const activeCustomKeys = (board.custom_fields || []).filter(f => f.is_active).map(f => f.key);
        const allKeys = ['title', ...activeCustomKeys, 'due_date'];

        if (config) {
          setMeetingConfig({
            layoutType: config.layout_type || 'COLUMNS',
            showClock: config.display_options?.show_clock !== false,
            showBoardName: config.display_options?.show_board_name !== false,
            showKpis: config.kpi_options?.show_kpis !== false,
            showRanking: config.layout_options?.show_ranking !== false,
            showExitButton: config.display_options?.show_exit_button !== false,
            visibleRows: config.layout_options?.visible_rows === 'auto' ? 'auto' : String(config.layout_options?.visible_rows || '16'),
            fontScale: config.layout_options?.font_scale || 'large',
            density: config.layout_options?.density || 'comfortable',
            autoScroll: config.layout_options?.auto_scroll !== false,
          });

          // Carrega as colunas e larguras da Reunião
          let meetVis = config.visible_custom_fields || [];
          if (!meetVis.includes('title')) meetVis = ['title', ...meetVis];
          if (!meetVis.includes('due_date')) meetVis = [...meetVis, 'due_date'];
          meetVis = meetVis.filter((k: string) => allKeys.includes(k));
          
          const meetColOrder = [...meetVis, ...allKeys.filter(k => !meetVis.includes(k))];
          setMeetingColumns(meetColOrder);
          setMeetingVisible(meetVis);
          setMeetingWidths(config.layout_options?.column_widths || {});

          const ext = config.external_mode_options || {};
          setExternalConfig({
            layoutType: ext.layout_type || 'PRODUCTION_LIST',
            showClock: ext.display_options ? ext.display_options.show_clock === true : false,
            showBoardName: ext.display_options ? ext.display_options.show_board_name === true : false,
            showKpis: ext.kpi_options ? ext.kpi_options.show_kpis === true : false,
            showRanking: ext.layout_options ? ext.layout_options.show_ranking === true : false,
            showExitButton: ext.display_options ? ext.display_options.show_exit_button === true : false,
            visibleRows: ext.layout_options?.visible_rows === 'auto' ? 'auto' : String(ext.layout_options?.visible_rows || '16'),
            fontScale: ext.layout_options?.font_scale || 'large',
            density: ext.layout_options?.density || 'factory',
            autoScroll: ext.layout_options?.auto_scroll !== false,
          });

          // Carrega as colunas e larguras da Externa
          let extVis = ext.visible_custom_fields || [];
          if (!extVis.includes('title')) extVis = ['title', ...extVis];
          if (!extVis.includes('due_date')) extVis = [...extVis, 'due_date'];
          extVis = extVis.filter((k: string) => allKeys.includes(k));
          
          const extColOrder = [...extVis, ...allKeys.filter(k => !extVis.includes(k))];
          setExternalColumns(extColOrder);
          setExternalVisible(extVis);
          setExternalWidths(ext.layout_options?.column_widths || {});
        } else {
          setMeetingColumns(allKeys);
          setMeetingVisible(allKeys);
          setMeetingWidths({});
          
          setExternalColumns(allKeys);
          setExternalVisible(allKeys);
          setExternalWidths({});
        }
      } catch (err) {
        console.error("Falha ao carregar configuracao de TV:", err);
      }
    };
    loadConfig();
  }, [isOpen, board.id, board.custom_fields]);

  const save = async () => {
    setSaving(true);
    try {
      await apiJson(`/api/v1/kanban/boards/${board.id}/tv-config`, {
        method: 'PATCH',
        body: JSON.stringify({
          layout_type: meetingConfig.layoutType,
          display_options: {
            show_board_name: meetingConfig.showBoardName,
            show_clock: meetingConfig.showClock,
            show_exit_button: meetingConfig.showExitButton,
            show_layout_name: true,
            show_connection: true,
            show_last_update: true,
          },
          kpi_options: { show_kpis: meetingConfig.showKpis, visible: meetingConfig.showKpis ? ['total_active_cards', 'critical_cards', 'overdue_cards', 'due_today_cards', 'unassigned_cards'] : [] },
          layout_options: {
            density: meetingConfig.density,
            font_scale: meetingConfig.fontScale,
            visible_rows: meetingConfig.visibleRows === 'auto' ? 'auto' : Number(meetingConfig.visibleRows),
            show_ranking: meetingConfig.showRanking,
            ranking_limit: meetingConfig.showRanking ? 8 : 0,
            auto_scroll: meetingConfig.autoScroll,
            auto_scroll_seconds: 18,
            short_labels: { tensao: 'V', quantidade: 'Qtd', qtd: 'Qtd', inicio: 'Início', entrada: 'Início', pendencia: 'Pend.' },
            column_widths: meetingWidths,
          },
          visible_custom_fields: meetingColumns.filter(k => meetingVisible.includes(k)),
          external_mode_options: {
            layout_type: externalConfig.layoutType,
            visible_custom_fields: externalColumns.filter(k => externalVisible.includes(k)),
            display_options: {
              show_board_name: externalConfig.showBoardName,
              show_clock: externalConfig.showClock,
              show_exit_button: externalConfig.showExitButton,
              show_layout_name: false,
              show_connection: false,
              show_last_update: false,
            },
            kpi_options: { show_kpis: externalConfig.showKpis, visible: externalConfig.showKpis ? ['total_active_cards', 'critical_cards', 'overdue_cards', 'due_today_cards', 'unassigned_cards'] : [] },
            layout_options: {
              density: externalConfig.density,
              font_scale: externalConfig.fontScale,
              visible_rows: externalConfig.visibleRows === 'auto' ? 'auto' : Number(externalConfig.visibleRows),
              show_ranking: externalConfig.showRanking,
              ranking_limit: externalConfig.showRanking ? 8 : 0,
              auto_scroll: externalConfig.autoScroll,
              auto_scroll_seconds: 18,
              short_labels: { tensao: 'V', quantidade: 'Qtd', qtd: 'Qtd', inicio: 'Início', entrada: 'Início', pendencia: 'Pend.' },
              column_widths: externalWidths,
            },
          },
        }),
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const currentVal = configMode === 'meeting' ? meetingConfig : externalConfig;
  const updateCurrent = (key: string, value: any) => {
    if (configMode === 'meeting') {
      setMeetingConfig((prev) => ({ ...prev, [key]: value }));
    } else {
      setExternalConfig((prev) => ({ ...prev, [key]: value }));
    }
  };

  // Metodos auxiliares de gerenciamento de colunas locais
  const moveColumn = (index: number, direction: 'up' | 'down') => {
    const isMeeting = configMode === 'meeting';
    const cols = isMeeting ? meetingColumns : externalColumns;
    const setCols = isMeeting ? setMeetingColumns : setExternalColumns;
    
    const next = [...cols];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= next.length) return;
    
    [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
    setCols(next);
  };

  const currentColumns = configMode === 'meeting' ? meetingColumns : externalColumns;
  const currentVisible = configMode === 'meeting' ? meetingVisible : externalVisible;
  const currentWidths = configMode === 'meeting' ? meetingWidths : externalWidths;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configurar Visualização / TV" size="lg" footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button onClick={save} disabled={saving}>{saving ? 'Salvando...' : 'Salvar configuração'}</Button></>}>
      <div style={{ display: 'grid', gap: 16 }}>
        {/* Abas para escolher o modo */}
        <div style={{ display: 'flex', gap: 8, borderBottom: '1px solid var(--border-color)', paddingBottom: 10 }}>
          <button
            type="button"
            className={`tab-btn ${configMode === 'meeting' ? 'active' : ''}`}
            onClick={() => setConfigMode('meeting')}
            style={{ padding: '8px 16px', background: configMode === 'meeting' ? 'color-mix(in srgb, var(--color-primary) 22%, transparent)' : 'transparent', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', borderRadius: 4, fontWeight: 600 }}
          >
            Apresentação / Reunião
          </button>
          <button
            type="button"
            className={`tab-btn ${configMode === 'external' ? 'active' : ''}`}
            onClick={() => setConfigMode('external')}
            style={{ padding: '8px 16px', background: configMode === 'external' ? 'color-mix(in srgb, var(--color-primary) 22%, transparent)' : 'transparent', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', borderRadius: 4, fontWeight: 600 }}
          >
            TV Externa (Chão de Fábrica)
          </button>
        </div>

        <div style={tvConfigGroup}>
          <strong>Aparência ({configMode === 'meeting' ? 'Reunião' : 'Externa'})</strong>
          <div style={tvConfigGrid}>
            <Select label="Densidade" value={currentVal.density} onChange={(event) => updateCurrent('density', event.target.value)} options={[{ value: 'compact', label: 'Compacta' }, { value: 'factory', label: 'Fábrica' }, { value: 'comfortable', label: 'Confortável' }]} />
            <Select label="Escala da fonte" value={currentVal.fontScale} onChange={(event) => updateCurrent('fontScale', event.target.value)} options={[{ value: 'small', label: 'Pequena' }, { value: 'medium', label: 'Média' }, { value: 'large', label: 'Grande' }, { value: 'xlarge', label: 'Extra grande' }]} />
            <Select label="Linhas visíveis" value={currentVal.visibleRows} onChange={(event) => updateCurrent('visibleRows', event.target.value)} options={['10', '12', '14', '16', '18', '20', 'auto'].map((value) => ({ value, label: value === 'auto' ? 'Automático' : value }))} />
          </div>
        </div>

        <div style={tvConfigGroup}>
          <strong>Informações exibidas ({configMode === 'meeting' ? 'Reunião' : 'Externa'})</strong>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <Checkbox label="Nome do quadro" checked={currentVal.showBoardName} onChange={(event) => updateCurrent('showBoardName', event.target.checked)} />
            <Checkbox label="Relógio" checked={currentVal.showClock} onChange={(event) => updateCurrent('showClock', event.target.checked)} />
            <Checkbox label="KPIs" checked={currentVal.showKpis} onChange={(event) => updateCurrent('showKpis', event.target.checked)} />
            <Checkbox label="Ranking crítico" checked={currentVal.showRanking} onChange={(event) => updateCurrent('showRanking', event.target.checked)} />
            <Checkbox label="Botão sair" checked={currentVal.showExitButton} onChange={(event) => updateCurrent('showExitButton', event.target.checked)} />
            <Checkbox label="Auto-scroll" checked={currentVal.autoScroll} onChange={(event) => updateCurrent('autoScroll', event.target.checked)} />
          </div>
        </div>

        <div style={tvConfigGroup}>
          <strong>Colunas e Larguras ({configMode === 'meeting' ? 'Reunião' : 'Externa'})</strong>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Marque as colunas que devem aparecer, ordene-as com as setas ↑ ↓ e defina a largura em pixels (deixe em branco ou 0 para automático).
          </span>
          <div style={{ display: 'grid', gap: 8, marginTop: 8, maxHeight: 320, overflowY: 'auto', paddingRight: 6 }}>
            {currentColumns.map((colKey, index) => {
              const isSystem = colKey === 'title' || colKey === 'due_date';
              const name = colKey === 'title' ? 'Tarefa' : colKey === 'due_date' ? 'Prazo' : (board.custom_fields?.find(cf => cf.key === colKey)?.name || colKey);
              const isChecked = currentVisible.includes(colKey);
              const widthVal = currentWidths[colKey] || '';
              
              return (
                <div 
                  key={colKey} 
                  style={{ 
                    display: 'grid', 
                    gridTemplateColumns: '24px 1.5fr auto auto 100px', 
                    gap: 12, 
                    alignItems: 'center', 
                    padding: '8px 12px', 
                    background: 'var(--surface-control)', 
                    border: '1px solid var(--semantic-border)', 
                    borderRadius: 6 
                  }}
                >
                  <input
                    aria-label={`Selecionar coluna ${name}`}
                    type="checkbox"
                    checked={isChecked}
                    onChange={(e) => {
                      const next = e.target.checked 
                        ? [...currentVisible, colKey] 
                        : currentVisible.filter(k => k !== colKey);
                      if (configMode === 'meeting') {
                        setMeetingVisible(next);
                      } else {
                        setExternalVisible(next);
                      }
                    }}
                    style={{ cursor: 'pointer' }}
                  />
                  <span style={{ color: isChecked ? 'var(--text-primary)' : 'var(--text-muted)', fontSize: 13, fontWeight: isChecked ? 600 : 400 }}>
                    {name} {isSystem && <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 4 }}>(Sistema)</span>}
                  </span>
                  
                  <button
                    type="button"
                    disabled={index === 0}
                    onClick={() => moveColumn(index, 'up')}
                    className="btn btn-ghost btn-sm"
                    style={{ padding: '2px 8px', color: 'var(--text-muted)' }}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    disabled={index === currentColumns.length - 1}
                    onClick={() => moveColumn(index, 'down')}
                    className="btn btn-ghost btn-sm"
                    style={{ padding: '2px 8px', color: 'var(--text-muted)' }}
                  >
                    ↓
                  </button>
                  
                  <Input
                    aria-label={`Largura de ${name}`}
                    type="number"
                    min={0}
                    placeholder="Auto"
                    value={widthVal}
                    onChange={(e) => {
                      const val = e.target.value === '' ? 0 : Number(e.target.value);
                      const nextWidths = { ...currentWidths, [colKey]: val };
                      if (configMode === 'meeting') {
                        setMeetingWidths(nextWidths);
                      } else {
                        setExternalWidths(nextWidths);
                      }
                    }}
                    style={{ margin: 0, height: 32, padding: '4px 8px', fontSize: 12 }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Modal>
  );
};

const tvChoiceCard: React.CSSProperties = { padding: 16, display: 'grid', gap: 8, textAlign: 'left', border: '1px solid var(--border-color)', borderRadius: 8, cursor: 'pointer' };
const tvConfigGroup: React.CSSProperties = { display: 'grid', gap: 10, padding: 14, border: '1px solid var(--border-color)', borderRadius: 8 };
const tvConfigGrid: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 };
