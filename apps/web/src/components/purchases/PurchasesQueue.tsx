import React from 'react';
import { Search, List } from 'lucide-react';
import { Button } from '../ui/Button';
import { EmptyState } from '../ui/EmptyState';
import { PurchaseQueueFilter } from './PurchasesIndicators';

interface PurchasesQueueProps {
  queue: any[];
  focusedRequest: any | null;
  searchTerm: string;
  onSearchChange: (val: string) => void;
  onSelectRequest: (req: any) => void;
  purchaseFilter: PurchaseQueueFilter;
  onFilterChange: (key: PurchaseQueueFilter) => void;
  emptyQueueCopy: { title: string; description: string };
  requestDisplayTitle: (req: any) => string;
  purchaseTypeForRequest: (req: any) => string;
  nextPurchaseAction: (req: any) => { label: string; description: string };
  fmtDate: (date: string) => string;
  priorityLabels: Record<string, string>;
}

export const PurchasesQueue: React.FC<PurchasesQueueProps> = ({
  queue,
  focusedRequest,
  searchTerm,
  onSearchChange,
  onSelectRequest,
  purchaseFilter,
  onFilterChange,
  emptyQueueCopy,
  requestDisplayTitle,
  purchaseTypeForRequest,
  nextPurchaseAction,
  fmtDate,
  priorityLabels,
}) => {
  return (
    <aside className="purchase-panel purchase-queue-panel">
      <div className="purchase-panel-header">
        <div>
          <h2>Necessidades</h2>
          <p>Fila compacta do que precisa de compra ou acompanhamento.</p>
        </div>
      </div>
      <div className="purchase-queue-search">
        <Search size={14} />
        <input
          id="queue-search-input"
          value={searchTerm}
          onChange={event => onSearchChange(event.target.value)}
          placeholder="Buscar necessidade..."
        />
      </div>
      <div className="purchase-needs-list">
        {queue.length === 0 ? (
          <EmptyState title={emptyQueueCopy.title} description={emptyQueueCopy.description} />
        ) : (
          queue.map(req => (
            <button
              key={req.id}
              type="button"
              className={`purchase-need-card ${focusedRequest?.id === req.id ? 'active' : ''}`}
              onClick={() => onSelectRequest(req)}
            >
              <strong>{requestDisplayTitle(req)}</strong>
              <span>
                {req.items?.length || 0} item(ns) · Compra {purchaseTypeForRequest(req)}
              </span>
              <small>
                {nextPurchaseAction(req).label} · {fmtDate(req.updated_at)}
              </small>
              <em>{priorityLabels[req.priority] || req.priority}</em>
            </button>
          ))
        )}
      </div>
      {purchaseFilter !== 'all' && (
        <Button variant="secondary" size="sm" onClick={() => onFilterChange('all')}>
          Mostrar todas
        </Button>
      )}
    </aside>
  );
};
