import React, { useEffect, useMemo, useState } from 'react';
import { Activity, Clock3, ListFilter, Users } from 'lucide-react';
import { apiJson } from './kanbanApi';
import { KanbanBoard } from './types';
import { KodaCard } from '../ui/KodaCard';
import { Drawer } from '../ui/Drawer';
import { Button } from '../ui/Button';
import { humanizeEventAction } from '../../utils/humanizeEvents';

interface BoardActivity {
  id: number;
  action: string;
  created_at: string;
  username?: string;
  metadata?: Record<string, unknown>;
}

interface KanbanBoardSidePanelProps {
  board: KanbanBoard;
  summary: {
    total: number;
    open: number;
    overdue: number;
    urgent: number;
    done: number;
    assignees: number;
  };
}

const relativeTime = (iso: string) => {
  if (!iso) return 'Recentemente';
  const formattedIso = iso.includes(' ') && !iso.includes('T') ? iso.replace(' ', 'T') : iso;
  const parsedDate = new Date(formattedIso);
  if (isNaN(parsedDate.getTime())) return 'Recentemente';
  const diff = Date.now() - parsedDate.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Agora';
  if (mins < 60) return `Há ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `Há ${hours} h`;
  return parsedDate.toLocaleDateString('pt-BR');
};

export const KanbanBoardSidePanel: React.FC<KanbanBoardSidePanelProps> = ({ board, summary }) => {
  const [activities, setActivities] = useState<BoardActivity[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    apiJson<BoardActivity[]>(`/api/v1/kanban/boards/${board.id}/activity?limit=40`)
      .then(setActivities)
      .catch(() => setActivities([]));
  }, [board.id]);

  const statusSlices = useMemo(() => {
    const openCount = summary.open;
    const doneCount = summary.done;
    const total = Math.max(openCount + doneCount, 1);
    return [
      { label: 'Em andamento', value: openCount, pct: Math.round((openCount / total) * 100), color: '#38bdf8' },
      { label: 'Concluídos', value: doneCount, pct: Math.round((doneCount / total) * 100), color: '#34d399' },
    ];
  }, [summary]);

  const recentActivities = activities.slice(0, 12);

  const renderActivity = (item: BoardActivity) => (
    <li key={item.id} className="kanban-activity-item">
      <span className="kanban-activity-icon"><Activity size={13} /></span>
      <span className="kanban-activity-copy">
        <span className="kanban-activity-action">{humanizeEventAction(item.action)}</span>
        <span className="kanban-activity-meta">
          {item.username || 'Sistema'} · {relativeTime(item.created_at)}
        </span>
      </span>
    </li>
  );

  return (
    <aside className="kanban-board-aside">
      <div className="glass-card module-side-card">
        <h4 className="dashboard-side-title">Resumo do quadro</h4>
        <div className="kanban-donut-legend">
          {statusSlices.map((slice) => (
            <div key={slice.label} className="kanban-donut-row">
              <span className="kanban-donut-dot" style={{ background: slice.color }} />
              <span>{slice.label}</span>
              <strong>{slice.value}</strong>
              <span className="text-muted">{slice.pct}%</span>
            </div>
          ))}
        </div>
        <div className="kanban-mini-metrics">
          <div><span>Total</span><strong>{summary.total}</strong></div>
          <div><span>Atrasados</span><strong className="text-danger">{summary.overdue}</strong></div>
          <div><span>Urgentes</span><strong className="text-warning">{summary.urgent}</strong></div>
          <div><span>Responsáveis</span><strong><Users size={14} /> {summary.assignees}</strong></div>
        </div>
      </div>

      <div className="glass-card module-side-card">
        <div className="module-side-card-header">
          <h4 className="dashboard-side-title">Atividades recentes</h4>
          <Activity size={16} />
        </div>
        {activities.length === 0 ? (
          <p className="text-muted" style={{ fontSize: 13 }}>Nenhuma atividade recente neste quadro.</p>
        ) : (
          <>
            <ul className="kanban-activity-list kanban-activity-list--bounded">
              {recentActivities.map(renderActivity)}
            </ul>
            <Button
              variant="secondary"
              size="sm"
              className="kanban-history-button"
              onClick={() => setHistoryOpen(true)}
              leftIcon={<Clock3 size={14} />}
            >
              Abrir histórico completo
            </Button>
          </>
        )}
      </div>

      <KodaCard
        compact
        title="Koda no Kanban"
        description={summary.overdue > 0 ? 'Revise primeiro os cards atrasados antes de abrir novas demandas.' : 'Use o Modo TV para acompanhar a produção sem abrir o painel completo.'}
      />

      <Drawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        title="Histórico do quadro"
        description="Eventos recentes humanizados, sem códigos técnicos."
      >
        <div className="kanban-history-drawer">
          <div className="kanban-history-filter">
            <ListFilter size={15} />
            <span>Mostrando os últimos {activities.length} eventos registrados neste quadro.</span>
          </div>
          <ul className="kanban-activity-list kanban-activity-list--drawer">
            {activities.map(renderActivity)}
          </ul>
        </div>
      </Drawer>
    </aside>
  );
};

export default KanbanBoardSidePanel;
