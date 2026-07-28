import React from 'react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { PurchaseRequest } from './types';

interface ApprovalSelectionPanelProps {
  req: PurchaseRequest;
  onSelectOption: (itemId: string, optionId: string) => Promise<void>;
  onSendToApproval: (reqId: string) => void;
  onNavigate?: (moduleCode: string, options?: any) => void;
  loadRequestDetail: (reqId: string) => void;
  fmt: (val: number) => string;
  statusLabels: Record<string, string>;
}

export const ApprovalSelectionPanel: React.FC<ApprovalSelectionPanelProps> = ({
  req,
  onSelectOption,
  onSendToApproval,
  onNavigate,
  loadRequestDetail,
  fmt,
  statusLabels,
}) => {
  const isPendingDecision = req.status === 'PENDING_APPROVAL';

  if (isPendingDecision) {
    const revisionItems = req.items.filter(item => item.approval_status === 'REVISION_REQUESTED');
    return (
      <div className="purchase-work-scroll" style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 0' }}>
        <div className="purchase-current-task">
          <span>Aprovação</span>
          <strong>Aguardando decisão</strong>
          <p>A compra já foi enviada para a Central de Aprovações. Quando houver decisão, ela volta automaticamente para esta fila.</p>
        </div>

        <div className="purchase-work-section">
          <h3>Itens enviados</h3>
          {req.items.map(item => {
            const selectedOpt = item.options?.find(option => option.id === item.selected_option_id);
            return (
              <div key={item.id} className="purchase-work-item" style={{ border: '1px solid var(--border-color)', borderRadius: 8, padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <div>
                  <strong>{item.description || item.free_text_description}</strong>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 2 }}>
                    {item.quantity} {item.unit_of_measure} ·{' '}
                    {selectedOpt
                      ? `${selectedOpt.title} em ${selectedOpt.store_name || selectedOpt.seller_name || 'fornecedor'}`
                      : 'sem opção selecionada'}
                  </span>
                </div>
                <Badge
                  variant={
                    item.approval_status === 'APPROVED'
                      ? 'success'
                      : item.approval_status === 'REVISION_REQUESTED'
                      ? 'warning'
                      : 'neutral'
                  }
                >
                  {item.approval_status === 'APPROVED' ? 'Aprovado' : item.approval_status === 'REVISION_REQUESTED' ? 'Revisar' : 'Aguardando'}
                </Badge>
              </div>
            );
          })}
        </div>

        {revisionItems.length > 0 && (
          <div className="purchase-attention-card severity-warning">
            <strong>Chefia pediu ajuste</strong>
            <span>Revise os itens marcados antes de reenviar para aprovação.</span>
          </div>
        )}

        <div className="purchase-panel-footer" style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          {req.approval_id ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => onNavigate?.('approvals', { search: { approval: req.approval_id }, replace: false })}
            >
              Abrir aprovação
            </Button>
          ) : (
            <Button variant="secondary" size="sm" onClick={() => loadRequestDetail(req.id)}>
              Atualizar status
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Se req.status === 'APPROVAL_REQUIRED'
  return (
    <div className="purchase-work-scroll" style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 0' }}>
      <div className="purchase-current-task">
        <span>Fase 14 · Aprovação por Item e Opção</span>
        <strong>Revisar opções para autorização</strong>
        <p>O Portal organizou as ofertas para cada item. Selecione a melhor opção para aprovação.</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {req.items.map(item => (
          <div
            key={item.id}
            className="glass-card"
            style={{ padding: 12, border: '1px solid var(--border-color)', borderRadius: 8 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
              <div>
                <strong style={{ fontSize: 13 }}>{item.description || item.free_text_description}</strong>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Quantidade: {item.quantity} un · Limite orçamentário: {fmt(item.budget_limit || 0)}
                </div>
              </div>
              <Badge variant={item.approval_status === 'APPROVED' ? 'success' : 'warning'}>
                {item.approval_status === 'APPROVED' ? 'Aprovado' : 'Aguardando'}
              </Badge>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {item.options && item.options.length > 0 ? (
                item.options.map(opt => (
                  <div
                    key={opt.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '8px 10px',
                      background: opt.selected ? 'rgba(52,211,153,0.06)' : 'rgba(255,255,255,0.01)',
                      border: `1px solid ${opt.selected ? '#34d399' : 'var(--border-color)'}`,
                      borderRadius: 6,
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 'bold' }}>
                        {opt.title} · <span style={{ color: 'var(--text-muted)' }}>{opt.store_name || opt.seller_name}</span>
                      </div>
                      <div style={{ fontSize: 11, color: '#34d399' }}>
                        Total: {fmt(opt.total_price)} (Preço: {fmt(opt.unit_price)} + Frete: {fmt(opt.shipping_price || 0)})
                      </div>
                    </div>
                    <Button
                      variant={opt.selected ? 'primary' : 'secondary'}
                      size="sm"
                      onClick={() => onSelectOption(item.id, opt.id)}
                    >
                      {opt.selected ? 'Selecionado' : 'Selecionar'}
                    </Button>
                  </div>
                ))
              ) : (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Nenhuma opção comercial carregada para este item ainda.
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
        <Button variant="primary" onClick={() => onSendToApproval(req.id)}>
          Enviar Decisão Consolidada para Aprovação
        </Button>
      </div>
    </div>
  );
};
