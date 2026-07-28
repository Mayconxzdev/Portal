import React from 'react';
import { Button } from '../ui/Button';

import { PurchaseRequest } from './types';


interface PurchaseRegistrationPanelProps {
  req: PurchaseRequest;
  finalValue: number | '';
  setFinalValue: (val: number | '') => void;
  shippingPrice: number | '';
  setShippingPrice: (val: number | '') => void;
  orderNumber: string;
  setOrderNumber: (val: string) => void;
  paymentMethod: string;
  setPaymentMethod: (val: string) => void;
  orderNotes: string;
  setOrderNotes: (val: string) => void;
  onSubmit: () => Promise<void>;
  onCancel: () => void;
  fmt: (val: number) => string;
}

export const PurchaseRegistrationPanel: React.FC<PurchaseRegistrationPanelProps> = ({
  req,
  finalValue,
  setFinalValue,
  shippingPrice,
  setShippingPrice,
  orderNumber,
  setOrderNumber,
  paymentMethod,
  setPaymentMethod,
  orderNotes,
  setOrderNotes,
  onSubmit,
  onCancel,
  fmt,
}) => {
  return (
    <div className="purchase-work-scroll" style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 0' }}>
      <div className="purchase-current-task">
        <span>Fase 15 · Registro da Compra</span>
        <strong>Registrar pedido de compra efetuado</strong>
        <p>O orçamento foi autorizado. Efetue a compra no link do mercado ou confirme o pedido interno.</p>
      </div>
      
      <div className="purchase-work-section">
        <h3>Itens Aprovados</h3>
        {req.items.map(item => {
          const selectedOpt = item.options?.find(o => o.id === item.selected_option_id);
          return (
            <div key={item.id} className="purchase-work-item" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 10, marginBottom: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{item.description || item.free_text_description}</strong>
                <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block' }}>{item.quantity} {item.unit_of_measure}</span>
                {selectedOpt && (
                  <div style={{ fontSize: 12, color: '#34d399', marginTop: 4 }}>
                    Opção: {selectedOpt.title} em {selectedOpt.store_name || selectedOpt.seller_name} ({fmt(selectedOpt.unit_price)} un + {fmt(selectedOpt.shipping_price || 0)} frete)
                  </div>
                )}
              </div>
              {selectedOpt?.product_url && (
                <Button variant="secondary" size="sm" onClick={() => window.open(selectedOpt.product_url, '_blank')}>
                  Abrir produto
                </Button>
              )}
            </div>
          );
        })}
      </div>
      
      <div className="glass-card" style={{ padding: 16, border: '1px solid var(--border-color)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h4 style={{ fontSize: 13, fontWeight: 'bold', margin: '0 0 10px 0' }}>Dados do Pedido Realizado</h4>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Valor Final Pago *</label>
            <input
              type="number"
              style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13 }}
              value={finalValue}
              onChange={e => setFinalValue(e.target.value === '' ? '' : parseFloat(e.target.value))}
              placeholder="Ex: 1450.00"
            />
          </div>
          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Valor do Frete Final</label>
            <input
              type="number"
              style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13 }}
              value={shippingPrice}
              onChange={e => setShippingPrice(e.target.value === '' ? '' : parseFloat(e.target.value))}
              placeholder="Ex: 20.00"
            />
          </div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Número do Pedido / Cód. Rastreio</label>
            <input
              type="text"
              style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13 }}
              value={orderNumber}
              onChange={e => setOrderNumber(e.target.value)}
              placeholder="Ex: PED-123456"
            />
          </div>
          <div>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Forma de Pagamento</label>
            <select
              style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13 }}
              value={paymentMethod}
              onChange={e => setPaymentMethod(e.target.value)}
            >
              <option value="Boleto">Boleto</option>
              <option value="Pix">Pix</option>
              <option value="Cartão Corporativo">Cartão Corporativo</option>
              <option value="Faturamento">Faturamento</option>
            </select>
          </div>
        </div>
        
        <div style={{ marginTop: 8 }}>
          <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Notas adicionais da compra</label>
          <input
            type="text"
            style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13 }}
            value={orderNotes}
            onChange={e => setOrderNotes(e.target.value)}
            placeholder="Ex: Comprovante anexado no slack"
          />
        </div>
      </div>
      
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 10 }}>
        <Button variant="secondary" size="sm" onClick={onCancel}>Voltar</Button>
        <Button variant="primary" size="sm" onClick={onSubmit}>Registrar Compra Efetuada</Button>
      </div>
    </div>
  );
};
