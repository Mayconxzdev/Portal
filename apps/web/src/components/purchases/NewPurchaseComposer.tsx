import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { PurchaseInputMode, SmartPurchaseInput } from './SmartPurchaseInput';

import { ParsedQuoteLine as ParsedLine } from './types';


interface NewPurchaseComposerProps {
  pastedListText: string;
  onPastedListTextChange: (val: string) => void;
  purchaseMode: PurchaseInputMode;
  onPurchaseModeChange: (val: PurchaseInputMode) => void;
  parsingList: boolean;
  onParseNeedList: () => void;
  parsedLines: ParsedLine[];
  setParsedLines: React.Dispatch<React.SetStateAction<ParsedLine[]>>;
  parsedLineStatusText: (line: ParsedLine) => string;
  handleCreateIntelligentNeed: () => void;
  savingRequest: boolean;
  linkImportUrl: string;
  onLinkImportUrlChange: (val: string) => void;
  importingLink: boolean;
  handleImportLink: (url: string) => void;
  cartImportUrl: string;
  onCartImportUrlChange: (val: string) => void;
  importingCart: boolean;
  handleImportCart: (url: string) => void;
  setShowPrivateCartModal: (val: boolean) => void;

  // Detalhes adicionais gerenciados no estado pai
  reqTitle: string;
  setReqTitle: (val: string) => void;
  reqPriority: string;
  setReqPriority: (val: string) => void;
  reqDepartment: string;
  setReqDepartment: (val: string) => void;
  reqNeededBy: string;
  setReqNeededBy: (val: string) => void;
  reqDesc: string;
  setReqDesc: (val: string) => void;
  reqJustify: string;
  setReqJustify: (val: string) => void;
}

export const NewPurchaseComposer: React.FC<NewPurchaseComposerProps> = ({
  pastedListText,
  onPastedListTextChange,
  purchaseMode,
  onPurchaseModeChange,
  parsingList,
  onParseNeedList,
  parsedLines,
  setParsedLines,
  parsedLineStatusText,
  handleCreateIntelligentNeed,
  savingRequest,
  linkImportUrl,
  onLinkImportUrlChange,
  importingLink,
  handleImportLink,
  cartImportUrl,
  onCartImportUrlChange,
  importingCart,
  handleImportCart,
  setShowPrivateCartModal,
  reqTitle,
  setReqTitle,
  reqPriority,
  setReqPriority,
  reqDepartment,
  setReqDepartment,
  reqNeededBy,
  setReqNeededBy,
  reqDesc,
  setReqDesc,
  reqJustify,
  setReqJustify,
}) => {
  const [isAddingDetails, setIsAddingDetails] = useState(false);

  return (
    <div className="new-purchase-start" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
      <section className="new-quote-panel" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="new-quote-panel-header">
          <div>
            <h2>Nova compra</h2>
            <p>Informe o que precisa comprar de forma simples. O Portal interpreta quantidades, limites e destinos automaticamente.</p>
          </div>
        </div>

        <div className="pasted-list-box" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label htmlFor="need-pasted-list" style={{ fontSize: 12, fontWeight: 'bold' }}>
            O que você precisa comprar?
          </label>
          <SmartPurchaseInput
            value={pastedListText}
            onChange={onPastedListTextChange}
            mode={purchaseMode}
            onModeChange={onPurchaseModeChange}
            rows={4}
          />
          <div className="quote-actions-line" style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <Button
              variant="primary"
              size="sm"
              onClick={onParseNeedList}
              disabled={parsingList || !pastedListText.trim()}
            >
              {parsingList ? 'Analisando...' : 'Analisar antes de criar'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onPastedListTextChange('');
                setParsedLines([]);
              }}
              disabled={parsingList && !parsedLines.length}
            >
              Limpar
            </Button>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>O Portal analisa sem criar a compra definitiva.</span>
          </div>
        </div>

        {parsedLines.length > 0 && (
          <div className="quote-review-list" style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 10 }}>
            <h3 style={{ fontSize: 13, fontWeight: 'bold', borderBottom: '1px solid var(--border-color)', paddingBottom: 6 }}>
              Revisar Itens Interpretados
            </h3>

            {parsedLines.map((line, index) => (
              <div
                key={index}
                className="glass-card"
                style={{ padding: 12, border: '1px solid var(--border-color)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 8 }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 11, color: line.confidence === 'high' ? '#34d399' : '#fbbf24', fontWeight: 'bold' }}>
                      Confiança: {line.confidence === 'high' ? 'Alta' : 'Média/Baixa'}
                    </span>
                    <Badge variant={line.purchase_type === 'internal' ? 'success' : line.purchase_type === 'ambiguous' ? 'warning' : 'neutral'}>
                      {line.purchase_type === 'internal' ? 'Item do Estoque' : line.purchase_type === 'ambiguous' ? 'Ambíguo' : 'Compra externa'}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setParsedLines(prev => prev.filter((_, itemIndex) => itemIndex !== index))}
                  >
                    Remover
                  </Button>
                </div>
                <small style={{ color: 'var(--text-muted)', lineHeight: 1.35 }}>{parsedLineStatusText(line)}</small>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 0.8fr 0.8fr 1fr', gap: 8 }}>
                  <div>
                    <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Produto / Descrição</label>
                    <input
                      type="text"
                      className="form-control"
                      style={{ width: '100%', padding: '4px 8px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                      value={line.description}
                      onChange={e => {
                        const val = e.target.value;
                        setParsedLines(prev => {
                          const next = [...prev];
                          next[index] = { ...next[index], description: val };
                          return next;
                        });
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Qtd</label>
                    <input
                      type="number"
                      className="form-control"
                      style={{ width: '100%', padding: '4px 8px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                      value={line.quantity}
                      onChange={e => {
                        const val = parseFloat(e.target.value) || 1;
                        setParsedLines(prev => {
                          const next = [...prev];
                          next[index] = { ...next[index], quantity: val };
                          return next;
                        });
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Unidade</label>
                    <input
                      type="text"
                      className="form-control"
                      style={{ width: '100%', padding: '4px 8px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                      value={line.unit_of_measure || 'un'}
                      onChange={e => {
                        const val = e.target.value || 'un';
                        setParsedLines(prev => {
                          const next = [...prev];
                          next[index] = { ...next[index], unit_of_measure: val };
                          return next;
                        });
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Orçamento Limite</label>
                    <input
                      type="number"
                      className="form-control"
                      style={{ width: '100%', padding: '4px 8px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                      value={line.budget_limit || ''}
                      onChange={e => {
                        const val = e.target.value === '' ? undefined : parseFloat(e.target.value);
                        setParsedLines(prev => {
                          const next = [...prev];
                          next[index] = { ...next[index], budget_limit: val };
                          return next;
                        });
                      }}
                      placeholder="Sem limite"
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Destino / Local entrega</label>
                    <input
                      type="text"
                      className="form-control"
                      style={{ width: '100%', padding: '4px 8px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 11 }}
                      value={line.destination || ''}
                      onChange={e => {
                        const val = e.target.value;
                        setParsedLines(prev => {
                          const next = [...prev];
                          next[index] = { ...next[index], destination: val };
                          return next;
                        });
                      }}
                      placeholder="Ex: PC de um colaborador"
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 14 }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Classificação:</span>
                    <select
                      style={{ padding: '3px 6px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 11 }}
                      value={line.purchase_type}
                      onChange={e => {
                        const val = e.target.value as any;
                        setParsedLines(prev => {
                          const next = [...prev];
                          next[index] = { ...next[index], purchase_type: val };
                          return next;
                        });
                      }}
                    >
                      <option value="internal">Interno</option>
                      <option value="external">Externo</option>
                      <option value="ambiguous">Ambíguo</option>
                    </select>
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-primary)', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={Boolean(line.requires_approval)}
                    onChange={e => {
                      const checked = e.target.checked;
                      setParsedLines(prev => {
                        const next = [...prev];
                        next[index] = { ...next[index], requires_approval: checked };
                        return next;
                      });
                    }}
                  />
                  Pedir aprovação para este item
                </label>
              </div>
            ))}

            {/* Accordion de Detalhes Avançados */}
            <div style={{ border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden', background: 'rgba(255,255,255,0.01)' }}>
              <button
                type="button"
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'var(--surface-elevated)',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontSize: 12,
                  fontWeight: 'bold',
                  display: 'flex',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                }}
                onClick={() => setIsAddingDetails(!isAddingDetails)}
              >
                <span>{isAddingDetails ? 'Ocultar detalhes avançados' : 'Adicionar detalhes avançados (opcional)'}</span>
                <span>{isAddingDetails ? '▲' : '▼'}</span>
              </button>

              {isAddingDetails && (
                <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 12, borderTop: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <div className="form-group">
                      <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Título da Compra</label>
                      <input
                        type="text"
                        className="form-control"
                        style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                        placeholder="Ex: Manutenção do PC de um colaborador"
                        value={reqTitle}
                        onChange={e => setReqTitle(e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Prioridade</label>
                      <select
                        style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                        value={reqPriority}
                        onChange={e => setReqPriority(e.target.value)}
                      >
                        <option value="LOW">Baixa</option>
                        <option value="NORMAL">Normal</option>
                        <option value="HIGH">Alta</option>
                        <option value="URGENT">Urgente</option>
                      </select>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    <div className="form-group">
                      <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Departamento</label>
                      <input
                        type="text"
                        className="form-control"
                        style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                        placeholder="Ex: TI, Financeiro"
                        value={reqDepartment}
                        onChange={e => setReqDepartment(e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Data Limite</label>
                      <input
                        type="date"
                        className="form-control"
                        style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                        value={reqNeededBy}
                        onChange={e => setReqNeededBy(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="form-group">
                    <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Descrição / Escopo</label>
                    <textarea
                      className="form-control"
                      style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                      placeholder="Detalhes ou especificações adicionais..."
                      value={reqDesc}
                      onChange={e => setReqDesc(e.target.value)}
                      rows={3}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Justificativa comercial</label>
                    <textarea
                      className="form-control"
                      style={{ width: '100%', padding: '6px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                      placeholder="Justificativa da compra..."
                      value={reqJustify}
                      onChange={e => setReqJustify(e.target.value)}
                      rows={2}
                    />
                  </div>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
              <Button variant="primary" onClick={handleCreateIntelligentNeed} disabled={savingRequest}>
                {savingRequest ? 'Criando...' : 'Criar compra'}
              </Button>
            </div>
          </div>
        )}
      </section>

      <aside className="new-quote-context" style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>
        <div className="glass-card" style={{ padding: 16, border: '1px solid var(--border-color)', borderRadius: 8, minWidth: 0 }}>
          <h3 style={{ fontSize: 13, fontWeight: 'bold', margin: '0 0 10px 0', lineHeight: 1.25 }}>Como o Portal decide</h3>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, margin: '0 0 12px 0', maxWidth: '100%' }}>
            Itens com correspondência exata no estoque viram <strong>compra interna</strong>. Produtos de mercado viram{' '}
            <strong>compra externa</strong>. Termos desconhecidos viram <strong>ambíguos</strong>.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 10 }}>
              <span>Itens Internos</span>
              <strong>{parsedLines.filter(line => line.purchase_type === 'internal').length}</strong>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 10 }}>
              <span>Itens Externos</span>
              <strong>{parsedLines.filter(line => line.purchase_type === 'external').length}</strong>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 10 }}>
              <span>Itens Ambíguos</span>
              <strong>{parsedLines.filter(line => line.purchase_type === 'ambiguous').length}</strong>
            </div>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 16, border: '1px solid var(--border-color)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h3 style={{ fontSize: 13, fontWeight: 'bold', margin: 0 }}>Importação Assistida</h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Importar link de produto</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                type="text"
                style={{ flex: 1, padding: '4px 8px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 11 }}
                value={linkImportUrl}
                onChange={e => onLinkImportUrlChange(e.target.value)}
                placeholder="Cole link do produto"
              />
              <Button variant="secondary" size="sm" onClick={() => handleImportLink(linkImportUrl)} disabled={importingLink}>
                {importingLink ? 'Importando...' : 'Importar'}
              </Button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Importar link de carrinho</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                type="text"
                style={{ flex: 1, padding: '4px 8px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 11 }}
                value={cartImportUrl}
                onChange={e => onCartImportUrlChange(e.target.value)}
                placeholder="Cole link do carrinho"
              />
              <Button variant="secondary" size="sm" onClick={() => handleImportCart(cartImportUrl)} disabled={importingCart}>
                {importingCart ? 'Importando...' : 'Importar'}
              </Button>
            </div>
          </div>

          <Button variant="secondary" size="sm" onClick={() => setShowPrivateCartModal(true)} style={{ marginTop: 4 }}>
            Colar carrinho privado (texto)
          </Button>
        </div>
      </aside>
    </div>
  );
};
