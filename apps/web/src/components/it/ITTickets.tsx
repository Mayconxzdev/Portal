import React, { useMemo } from 'react';
import { AlertTriangle, CheckCircle2, Clock3, Plus, RotateCcw, Search, UserCheck } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Select } from '../ui/Select';
import { Badge } from '../ui/Badge';
import { EmptyState } from '../ui/EmptyState';
import { ITTicket, statusLabel, priorityLabel } from './itApi';

interface QueueFilters {
  q: string;
  ticket_number: string;
  requester_user_id: string;
  assigned_to_user_id: string;
  status: string;
  category: string;
  priority: string;
  sla_state: string;
  unassigned: boolean;
  assigned_to_me: boolean;
  created_today: boolean;
  recently_updated: boolean;
  has_attachments: boolean;
  has_kanban_card: boolean;
  missing_kanban_card: boolean;
  sort_by: string;
  sort_dir: string;
}

export interface ITTicketsProps {
  tickets: ITTicket[];
  isStaff: boolean;
  currentUser: any;
  queueFilters: QueueFilters;
  onSetQueueFilters: (filters: QueueFilters) => void;
  onOpenTicket: (ticket: ITTicket) => void;
  onCreateTicket: () => void;
  emptyFilters: QueueFilters;
  statusOptions: { value: string; label: string }[];
  priorityOptions: { value: string; label: string }[];
  categoryOptions: { value: string; label: string }[];
}

export const ITTickets: React.FC<ITTicketsProps> = ({
  tickets,
  isStaff,
  queueFilters,
  onSetQueueFilters,
  onOpenTicket,
  onCreateTicket,
  emptyFilters,
  statusOptions,
  priorityOptions,
  categoryOptions,
}) => {
  const withEmpty = (options: { value: string; label: string }[], label = 'Todos') => [
    { value: '', label },
    ...options,
  ];

  const activeQuickFilter = useMemo(() => {
    if (queueFilters.assigned_to_me) return 'mine';
    if (queueFilters.unassigned) return 'unassigned';
    if (queueFilters.status === 'ABERTO') return 'open';
    if (queueFilters.status === 'EM_ATENDIMENTO') return 'progress';
    if (queueFilters.status === 'FECHADO') return 'closed';
    return 'all';
  }, [queueFilters]);

  const handleQuickFilter = (type: 'all' | 'mine' | 'unassigned' | 'open' | 'progress' | 'closed') => {
    const base = { ...emptyFilters };
    if (type === 'mine') base.assigned_to_me = true;
    if (type === 'unassigned') base.unassigned = true;
    if (type === 'open') base.status = 'ABERTO';
    if (type === 'progress') base.status = 'EM_ATENDIMENTO';
    if (type === 'closed') base.status = 'FECHADO';
    onSetQueueFilters(base);
  };

  const categoryName = (ticket: ITTicket) =>
    categoryOptions.find((cat) => cat.value === ticket.category)?.label || ticket.category || 'Sem categoria';

  return (
    <div className="space-y-6">
      <div className="section-card it-product-header">
        <div>
          <span className="product-eyebrow">Central de atendimento</span>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">Chamados de TI</h2>
          <p className="text-xs text-slate-400">
            Acompanhe incidentes, dúvidas e solicitações sem termos técnicos desnecessários.
          </p>
        </div>
        <Button variant="primary" size="sm" onClick={onCreateTicket} leftIcon={<Plus size={16} />}>
          Abrir chamado
        </Button>
      </div>

      <div className="product-chip-row" aria-label="Filtros rápidos de chamados">
        {[
          ['all', 'Todos'],
          ...(isStaff ? [['mine', 'Meus chamados'], ['unassigned', 'Sem responsável']] : []),
          ['open', 'Abertos'],
          ['progress', 'Em atendimento'],
          ['closed', 'Resolvidos'],
        ].map(([type, label]) => (
          <button
            key={type}
            type="button"
            onClick={() => handleQuickFilter(type as any)}
            className={`product-chip ${activeQuickFilter === type ? 'active' : ''}`}
          >
            {label}
          </button>
        ))}
      </div>

      {isStaff && (
        <Card className="p-4 space-y-4 product-filter-card">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="product-search-box">
              <Search size={16} className="text-slate-400" />
              <input
                type="text"
                value={queueFilters.q}
                onChange={(e) => onSetQueueFilters({ ...queueFilters, q: e.target.value })}
                placeholder="Buscar por número, título, pessoa ou categoria..."
                className="w-full bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 py-1.5"
              />
            </div>
            <Select
              label=""
              value={queueFilters.status}
              options={withEmpty(statusOptions, 'Todos os status')}
              onChange={(e) => onSetQueueFilters({ ...queueFilters, status: e.target.value })}
              className="!min-h-[38px] text-xs"
            />
            <Select
              label=""
              value={queueFilters.priority}
              options={withEmpty(priorityOptions, 'Todas as prioridades')}
              onChange={(e) => onSetQueueFilters({ ...queueFilters, priority: e.target.value })}
              className="!min-h-[38px] text-xs"
            />
            <Select
              label=""
              value={queueFilters.category}
              options={withEmpty(categoryOptions, 'Todas as categorias')}
              onChange={(e) => onSetQueueFilters({ ...queueFilters, category: e.target.value })}
              className="!min-h-[38px] text-xs"
            />
          </div>

          <div className="flex justify-between items-center text-xs text-slate-400 font-bold border-t border-slate-800/40 pt-3">
            <span>{tickets.length} {tickets.length === 1 ? 'chamado encontrado' : 'chamados encontrados'}</span>
            <button
              type="button"
              onClick={() => onSetQueueFilters(emptyFilters)}
              className="text-red-400 hover:text-red-300 flex items-center gap-1.5 transition-colors"
            >
              <RotateCcw size={13} /> Limpar filtros
            </button>
          </div>
        </Card>
      )}

      <div className="data-card-grid">
        {tickets.map((ticket) => {
          const isUrgent = ticket.priority === 'CRITICA' || ticket.priority === 'ALTA';
          return (
            <Card
              key={ticket.id}
              variant="interactive"
              className={`ticket-product-card ${isUrgent ? 'ticket-product-card--urgent' : ''}`}
            >
              <div className="space-y-2">
                <div className="flex justify-between items-start gap-2">
                  <Badge className="ticket-number-chip">{ticket.ticket_number}</Badge>
                  <div className="flex gap-1.5">
                    <span className={`status-mini status-mini--${ticket.status.toLowerCase()}`}>
                      {statusLabel(ticket.status)}
                    </span>
                    <span className={`priority-mini priority-mini--${ticket.priority.toLowerCase()}`}>
                      {priorityLabel(ticket.priority)}
                    </span>
                  </div>
                </div>
                <h4 className="text-base font-bold text-white line-clamp-1">{ticket.title}</h4>
                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{ticket.description}</p>
              </div>

              <div className="ticket-product-meta">
                <div className="ticket-meta-pill">
                  <UserCheck size={13} />
                  <span>{ticket.requester_name || 'Usuário'}</span>
                </div>
                <div className="ticket-meta-pill">
                  {ticket.status === 'FECHADO' ? <CheckCircle2 size={13} /> : isUrgent ? <AlertTriangle size={13} /> : <Clock3 size={13} />}
                  <span>{categoryName(ticket)}</span>
                </div>
              </div>

              <div className="flex justify-between items-center pt-3 border-t border-white/5 text-[11px] font-bold text-slate-400">
                <span>{ticket.assignee_name ? `Responsável: ${ticket.assignee_name}` : 'Sem responsável definido'}</span>
                <Button variant="secondary" size="sm" onClick={() => onOpenTicket(ticket)}>
                  Abrir
                </Button>
              </div>
            </Card>
          );
        })}

        {tickets.length === 0 && (
          <div className="col-span-2 py-12">
            <EmptyState
              icon={<Search size={48} />}
              title="Nenhum chamado encontrado"
              description="Nenhum chamado corresponde aos filtros aplicados ou sua fila está vazia."
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ITTickets;
