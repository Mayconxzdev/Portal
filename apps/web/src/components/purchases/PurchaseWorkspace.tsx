import React from 'react';
import { Plus } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { PurchasesQueue } from './PurchasesQueue';
import { PurchaseSummary } from './PurchaseSummary';

import { PurchaseRequest, PurchaseAttentionItem } from './types';


interface PurchaseWorkspaceProps {
  // Queue Props
  queue: PurchaseRequest[];
  focusedRequest: PurchaseRequest | null;
  searchTerm: string;
  onSearchChange: (val: string) => void;
  onSelectRequest: (req: PurchaseRequest) => void;
  purchaseFilter: 'all' | 'attention' | 'suppliers' | 'approval' | 'ready' | 'delivery';
  onFilterChange: (key: 'all' | 'attention' | 'suppliers' | 'approval' | 'ready' | 'delivery') => void;
  emptyQueueCopy: { title: string; description: string };
  requestDisplayTitle: (req: PurchaseRequest) => string;
  purchaseTypeForRequest: (req: PurchaseRequest) => string;
  nextPurchaseAction: (req: PurchaseRequest) => { label: string; description: string };
  fmtDate: (date: string) => string;
  priorityLabels: Record<string, string>;

  // Center Work Panel Render helper
  renderIntelligentWorkContent: (req: PurchaseRequest) => React.ReactNode;
  STATUS_LABELS: Record<string, string>;

  // Right Summary Panel Props
  focusedAction: { label: string; description: string } | null;
  focusedType: string | null;
  isRegisteringOrder: boolean;
  setIsRegisteringOrder: (val: boolean) => void;
  isReceiving: boolean;
  setIsReceiving: (val: boolean) => void;
  setDeliveryItemsState: (items: any[]) => void;
  handleOpenRequestRow: (req: PurchaseRequest) => void;
  primaryAttention: PurchaseAttentionItem | undefined;
  requests: PurchaseRequest[];
  requestEstimatedValue: (req: PurchaseRequest) => number;
  fmt: (val: number) => string;

  // Global actions
  onNewPurchaseClick: () => void;
}

export const PurchaseWorkspace: React.FC<PurchaseWorkspaceProps> = ({
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
  renderIntelligentWorkContent,
  STATUS_LABELS,
  focusedAction,
  focusedType,
  isRegisteringOrder,
  setIsRegisteringOrder,
  isReceiving,
  setIsReceiving,
  setDeliveryItemsState,
  handleOpenRequestRow,
  primaryAttention,
  requests,
  requestEstimatedValue,
  fmt,
  onNewPurchaseClick,
}) => {
  return (
    <div className="purchases-adaptive-workspace">
      {/* 1. Painel Esquerdo — Fila de Necessidades */}
      <PurchasesQueue
        queue={queue}
        focusedRequest={focusedRequest}
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        onSelectRequest={onSelectRequest}
        purchaseFilter={purchaseFilter}
        onFilterChange={onFilterChange}
        emptyQueueCopy={emptyQueueCopy}
        requestDisplayTitle={requestDisplayTitle}
        purchaseTypeForRequest={purchaseTypeForRequest}
        nextPurchaseAction={nextPurchaseAction}
        fmtDate={fmtDate}
        priorityLabels={priorityLabels}
      />

      {/* 2. Painel Central — Conteúdo de Trabalho Adaptativo */}
      <section className="purchase-panel purchase-work-panel">
        {focusedRequest ? (
          <>
            <div className="purchase-panel-header">
              <div>
                <h2>{focusedAction?.label}</h2>
                <p>{focusedAction?.description}</p>
              </div>
              <Badge
                variant={
                  focusedRequest.status === 'APPROVED'
                    ? 'success'
                    : focusedRequest.status === 'PENDING_APPROVAL'
                    ? 'warning'
                    : 'neutral'
                }
              >
                {STATUS_LABELS[focusedRequest.status] || focusedRequest.status}
              </Badge>
            </div>
            {renderIntelligentWorkContent(focusedRequest)}
          </>
        ) : (
          <div className="purchase-empty-workspace">
            <h2>Informe o que precisa comprar</h2>
            <p>O Portal classifica como compra interna, externa ou mista antes de criar a necessidade.</p>
            <Button
              variant="primary"
              leftIcon={<Plus size={15} />}
              onClick={onNewPurchaseClick}
            >
              Nova compra
            </Button>
          </div>
        )}
      </section>

      {/* 3. Painel Direito — Resumo e Ação Recomendada */}
      <PurchaseSummary
        focusedRequest={focusedRequest}
        focusedAction={focusedAction}
        focusedType={focusedType}
        isRegisteringOrder={isRegisteringOrder}
        setIsRegisteringOrder={setIsRegisteringOrder}
        isReceiving={isReceiving}
        setIsReceiving={setIsReceiving}
        setDeliveryItemsState={setDeliveryItemsState}
        handleOpenRequestRow={handleOpenRequestRow}
        primaryAttention={primaryAttention}
        requests={requests}
        emptyQueueCopy={emptyQueueCopy}
        requestEstimatedValue={requestEstimatedValue}
        fmt={fmt}
        requestDisplayTitle={requestDisplayTitle}
      />
    </div>
  );
};
