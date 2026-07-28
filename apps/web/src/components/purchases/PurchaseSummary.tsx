import React from 'react';
import { Button } from '../ui/Button';

import { PurchaseRequest, PurchaseAttentionItem } from './types';


interface PurchaseSummaryProps {
  focusedRequest: PurchaseRequest | null;
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
  emptyQueueCopy: { title: string; description: string };
  requestEstimatedValue: (req: PurchaseRequest) => number;
  fmt: (val: number) => string;
  requestDisplayTitle: (req: PurchaseRequest) => string;
}

export const PurchaseSummary: React.FC<PurchaseSummaryProps> = ({
  focusedRequest,
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
  emptyQueueCopy,
  requestEstimatedValue,
  fmt,
  requestDisplayTitle,
}) => {
  return (
    <aside className="purchase-panel purchase-summary-panel">
      <div className="purchase-panel-header">
        <div>
          <h2>Resumo</h2>
          <p>Proxima acao recomendada.</p>
        </div>
      </div>
      
      {focusedRequest && focusedAction ? (
        <div className="purchase-attention-card">
          <strong>{requestDisplayTitle(focusedRequest)}</strong>
          <span>{focusedAction.description}</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 10 }}>
            {focusedRequest.status === 'APPROVED' && !isRegisteringOrder && (
              <Button variant="primary" size="sm" onClick={() => setIsRegisteringOrder(true)}>
                Registrar Compra
              </Button>
            )}
            {focusedRequest.status === 'ORDERED' && !isReceiving && (
              <Button variant="primary" size="sm" onClick={() => {
                setDeliveryItemsState(focusedRequest.items.map(item => ({
                  item_id: item.id,
                  description: item.description || item.free_text_description,
                  quantity_ordered: item.quantity,
                  quantity_received: item.quantity,
                  is_damaged: false,
                  deviation_notes: '',
                  save_in_catalog: !item.stock_catalog_item_id
                })));
                setIsReceiving(true);
              }}>
                Receber Entrega
              </Button>
            )}
            <Button variant="secondary" size="sm" onClick={() => handleOpenRequestRow(focusedRequest)}>
              Abrir Detalhes do Rascunho
            </Button>
          </div>
        </div>
      ) : primaryAttention ? (
        <div className={`purchase-attention-card severity-${primaryAttention.severity}`}>
          <strong>{primaryAttention.title}</strong>
          <span>{primaryAttention.description}</span>
          <Button variant="secondary" size="sm" onClick={() => {
            const request = requests.find(req => req.id === primaryAttention.request_id);
            if (request) handleOpenRequestRow(request);
          }}>
            {primaryAttention.action_label}
          </Button>
        </div>
      ) : (
        <div className="purchase-attention-card">
          <strong>{emptyQueueCopy.title}</strong>
          <span>{emptyQueueCopy.description}</span>
        </div>
      )}
      
      <div className="purchase-summary-facts">
        <div><strong>{focusedRequest ? `Compra ${focusedType}` : 'Nenhum'}</strong><span>tipo</span></div>
        <div><strong>{focusedRequest?.items.length || 0}</strong><span>itens</span></div>
        <div><strong>{focusedRequest ? fmt(requestEstimatedValue(focusedRequest)) : fmt(0)}</strong><span>valor estimado</span></div>
        <div><strong>{focusedRequest?.rfqs?.length || 0}</strong><span>fornecedores/opções</span></div>
      </div>
    </aside>
  );
};
