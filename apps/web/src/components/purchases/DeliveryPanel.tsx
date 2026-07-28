import React from 'react';
import { Button } from '../ui/Button';

interface DeliveryItemState {
  item_id: string;
  description: string;
  quantity_ordered: number;
  quantity_received: number;
  is_damaged: boolean;
  deviation_notes: string;
  save_in_catalog: boolean;
}

import { PurchaseRequest } from './types';


interface DeliveryPanelProps {
  req: PurchaseRequest;
  deliveryItemsState: DeliveryItemState[];
  setDeliveryItemsState: React.Dispatch<React.SetStateAction<DeliveryItemState[]>>;
  deliveryNotes: string;
  setDeliveryNotes: (val: string) => void;
  onSubmit: () => Promise<void>;
  onCancel: () => void;
}

export const DeliveryPanel: React.FC<DeliveryPanelProps> = ({
  req,
  deliveryItemsState,
  setDeliveryItemsState,
  deliveryNotes,
  setDeliveryNotes,
  onSubmit,
  onCancel,
}) => {
  return (
    <div className="purchase-work-scroll" style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 0' }}>
      <div className="purchase-current-task">
        <span>Fase 16 · Recebimento de Entrega</span>
        <strong>Registrar entrada no Estoque</strong>
        <p>Confirme os itens recebidos e avarias detectadas para dar entrada automática no inventário.</p>
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {deliveryItemsState.map((item, idx) => (
          <div key={item.item_id} className="glass-card" style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 10, border: '1px solid var(--border-color)', borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: 13 }}>{item.description}</strong>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Pedido: {item.quantity_ordered} un</span>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Qtd Recebida</label>
                <input
                  type="number"
                  style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13 }}
                  value={item.quantity_received}
                  onChange={e => {
                    const val = parseFloat(e.target.value) || 0;
                    setDeliveryItemsState(prev => {
                      const next = [...prev];
                      next[idx] = { ...next[idx], quantity_received: val };
                      return next;
                    });
                  }}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 18 }}>
                <input
                  type="checkbox"
                  id={`damage-${item.item_id}`}
                  checked={item.is_damaged}
                  onChange={e => {
                    const checked = e.target.checked;
                    setDeliveryItemsState(prev => {
                      const next = [...prev];
                      next[idx] = { ...next[idx], is_damaged: checked };
                      return next;
                    });
                  }}
                />
                <label htmlFor={`damage-${item.item_id}`} style={{ fontSize: 12, color: '#f87171', cursor: 'pointer' }}>Item avariado / com defeito</label>
              </div>
            </div>
            
            {item.quantity_received !== item.quantity_ordered && (
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Motivo da divergência de quantidade</label>
                <input
                  type="text"
                  placeholder="Ex: Entrega parcial acordada com fornecedor"
                  style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                  value={item.deviation_notes}
                  onChange={e => {
                    const val = e.target.value;
                    setDeliveryItemsState(prev => {
                      const next = [...prev];
                      next[idx] = { ...next[idx], deviation_notes: val };
                      return next;
                    });
                  }}
                />
              </div>
            )}
            
            {!req.items[idx]?.stock_catalog_item_id && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input
                  type="checkbox"
                  id={`save-cat-${item.item_id}`}
                  checked={item.save_in_catalog}
                  onChange={e => {
                    const checked = e.target.checked;
                    setDeliveryItemsState(prev => {
                      const next = [...prev];
                      next[idx] = { ...next[idx], save_in_catalog: checked };
                      return next;
                    });
                  }}
                />
                <label htmlFor={`save-cat-${item.item_id}`} style={{ fontSize: 12, color: 'var(--text-muted)', cursor: 'pointer' }}>Salvar este produto no Catálogo de Estoque</label>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div>
        <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Observações gerais de recebimento</label>
        <textarea
          rows={3}
          placeholder="Observações ou notas fiscais vinculadas..."
          style={{ width: '100%', padding: '8px 12px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 8, color: 'var(--text-primary)', fontSize: 13 }}
          value={deliveryNotes}
          onChange={e => setDeliveryNotes(e.target.value)}
        />
      </div>
      
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 10 }}>
        <Button variant="secondary" size="sm" onClick={onCancel}>Voltar</Button>
        <Button variant="primary" size="sm" onClick={onSubmit}>Confirmar Recebimento e Entrada</Button>
      </div>
    </div>
  );
};
