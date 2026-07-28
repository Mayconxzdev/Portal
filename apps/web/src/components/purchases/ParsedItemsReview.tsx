import React from 'react';
import { Package, ShoppingCart, AlertTriangle } from 'lucide-react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

import { PurchaseRequest, PurchaseItemResponse } from './types';


interface ParsedItemsReviewProps {
  req: PurchaseRequest;
  onRevisarInterno: () => void;
  onPesquisarExterno: (item: PurchaseItemResponse) => void;
  onResolveAmbiguity: (itemId: string, type: string) => Promise<void>;
  onSendToApproval: (reqId: string) => void;
  fmt: (val: number) => string;
}

export const ParsedItemsReview: React.FC<ParsedItemsReviewProps> = ({
  req,
  onRevisarInterno,
  onPesquisarExterno,
  onResolveAmbiguity,
  onSendToApproval,
  fmt,
}) => {
  const internalItems = req.items.filter(i => i.classification === 'INTERNAL');
  const externalItems = req.items.filter(i => i.classification === 'EXTERNAL');
  const ambiguousItems = req.items.filter(
    i => i.classification === 'AMBIGUOUS' || i.match_status === 'needs_confirmation'
  );

  return (
    <div className="purchase-work-scroll" style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 0' }}>
      <div className="purchase-current-task">
        <span>Fase 4 · Confirmação de Itens da Compra</span>
        <strong>Revisar especificações e origens</strong>
        <p>O Portal identificou os itens a partir do seu texto. Confirme os tipos para iniciar aprovação.</p>
      </div>

      {internalItems.length > 0 && (
        <div className="purchase-work-section">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#c4b5fd', fontSize: 13, margin: '0 0 8px 0' }}>
            <Package size={14} /> Itens do Estoque ({internalItems.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {internalItems.map(item => (
              <div
                key={item.id}
                className="purchase-work-item"
                style={{
                  border: '1px solid var(--border-color)',
                  borderRadius: 8,
                  padding: 10,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <strong>{item.description || item.free_text_description}</strong>
                  <span>
                    {item.quantity} {item.unit_of_measure} · Saldo em Estoque: {item.specifications || 'Disponível'}
                  </span>
                  <small style={{ color: '#34d399', fontSize: 11, marginTop: 4, display: 'block' }}>
                    ✨ Encontramos este item no Estoque e fornecedores conhecidos.
                  </small>
                </div>
                <Button variant="secondary" size="sm" onClick={onRevisarInterno}>
                  Revisar
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {externalItems.length > 0 && (
        <div className="purchase-work-section" style={{ marginTop: 8 }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#34d399', fontSize: 13, margin: '0 0 8px 0' }}>
            <ShoppingCart size={14} /> Itens Externos ({externalItems.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {externalItems.map(item => {
              const selectedOpt = item.options?.find(o => o.id === item.selected_option_id);
              return (
                <div
                  key={item.id}
                  className="purchase-work-item"
                  style={{
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                    padding: 10,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <strong>{item.description || item.free_text_description}</strong>
                    <span>
                      {item.quantity} {item.unit_of_measure}
                    </span>
                    {selectedOpt ? (
                      <div style={{ fontSize: 12, color: '#34d399', marginTop: 4 }}>
                        Opção selecionada: {selectedOpt.title} em {selectedOpt.store_name} ({fmt(selectedOpt.total_price)} total)
                      </div>
                    ) : (
                      <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 4 }}>
                        ⚠️ Nenhuma opção selecionada. Pesquise no mercado antes de enviar para aprovação.
                      </div>
                    )}
                  </div>
                  <Button variant="primary" size="sm" onClick={() => onPesquisarExterno(item)}>
                    {selectedOpt ? 'Alterar' : 'Pesquisar'}
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {ambiguousItems.length > 0 && (
        <div className="purchase-work-section" style={{ marginTop: 8 }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#fbbf24', fontSize: 13, margin: '0 0 8px 0' }}>
            <AlertTriangle size={14} /> Itens Ambíguos ({ambiguousItems.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {ambiguousItems.map(item => (
              <div
                key={item.id}
                className="purchase-work-item"
                style={{
                  border: '1px solid rgba(245,158,11,0.3)',
                  background: 'rgba(245,158,11,0.02)',
                  borderRadius: 8,
                  padding: 10,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}
              >
                <div style={{ flex: 1 }}>
                  <strong style={{ color: '#fbbf24' }}>{item.description || item.free_text_description}</strong>
                  <span>
                    {item.quantity} {item.unit_of_measure}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 4 }}>
                    Não temos certeza se este item já existe no estoque ou se deve ser comprado no mercado externo.
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end', width: '100%' }}>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onResolveAmbiguity(item.id, 'EXTERNAL')}
                  >
                    Marcar como Externo
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => onResolveAmbiguity(item.id, 'INTERNAL')}
                  >
                    Confirmar no Estoque
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10, borderTop: '1px solid var(--border-color)', paddingTop: 14 }}>
        <Button
          variant="primary"
          onClick={() => onSendToApproval(req.id)}
          disabled={ambiguousItems.length > 0 || externalItems.some(i => !i.selected_option_id)}
        >
          Enviar para Aprovação
        </Button>
      </div>
    </div>
  );
};
