import React from 'react';
import { MailOpen } from 'lucide-react';
import { Button } from '../ui/Button';
import { EmptyState } from '../ui/EmptyState';
import { Badge } from '../ui/Badge';
import { Input } from '../ui/Input';

import { EmailPreview } from './types';

interface EmailQuotationPreviewProps {
  emailPreviews: EmailPreview[];
  selectedEmailPreviewId: string | null;
  setSelectedEmailPreviewId: (id: string | null) => void;
  loadingPreviews: boolean;
  loadEmailPreviews: () => void;
  bccOverrides: Record<string, boolean>;
  handleBccToggle: (preview: EmailPreview, checked: boolean) => void | Promise<void>;
  emailDraftEdits: Record<string, { subject?: string; body_text?: string }>;
  setEmailDraftEdits: React.Dispatch<React.SetStateAction<Record<string, { subject?: string; body_text?: string }>>>;
  saveEmailDraft: (preview: EmailPreview) => void | Promise<void>;
  updateEmailMessage: (messageId: string, payload: any) => void;
  sendEmailMessage: (preview: EmailPreview, isTest: boolean) => void | Promise<void>;
  sendingMessageId: string | null;
  setQuoteWizardStep: (step: 'products' | 'suppliers' | 'preview') => void;
}


export const EmailQuotationPreview: React.FC<EmailQuotationPreviewProps> = ({
  emailPreviews,
  selectedEmailPreviewId,
  setSelectedEmailPreviewId,
  loadingPreviews,
  loadEmailPreviews,
  bccOverrides,
  handleBccToggle,
  emailDraftEdits,
  setEmailDraftEdits,
  saveEmailDraft,
  updateEmailMessage,
  sendEmailMessage,
  sendingMessageId,
  setQuoteWizardStep,
}) => {
  const readyPreviewCount = React.useMemo(() => emailPreviews.filter(p => p.can_send).length, [emailPreviews]);
  const blockedPreviewCount = React.useMemo(() => emailPreviews.filter(p => !p.can_send).length, [emailPreviews]);

  const selectedEmailPreview =
    emailPreviews.find(preview => preview.message_id === selectedEmailPreviewId) || emailPreviews[0];


  return (
    <div className="new-quote-panel">
      <div className="new-quote-panel-header">
        <div>
          <h2>Revisar e enviar</h2>
          <p>Revise exatamente o que cada fornecedor receberá antes de liberar o envio.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadEmailPreviews} disabled={loadingPreviews}>
          {loadingPreviews ? 'Gerando...' : 'Atualizar pré-visualização'}
        </Button>
      </div>

      {emailPreviews.length === 0 ? (
        <EmptyState
          title="Nenhuma pré-visualização pronta"
          description="Salve a distribuição dos fornecedores para preparar as mensagens."
        />
      ) : selectedEmailPreview ? (
        (() => {
          const preview = selectedEmailPreview;
          const bccEnabled = bccOverrides[preview.rfq_supplier_id] ?? preview.bcc_enabled;
          const draft = emailDraftEdits[preview.message_id] || {};
          const blockedReason =
            preview.blocked_reason || (!preview.can_send ? 'Configure a conta de envio antes de enviar.' : '');
          return (
            <div className="quote-message-workspace">
              <div className="supplier-message-list">
                {emailPreviews.map((item, index) => (
                  <button
                    key={item.message_id}
                    type="button"
                    className={`supplier-message-card ${item.message_id === preview.message_id ? 'active' : ''}`}
                    onClick={() => setSelectedEmailPreviewId(item.message_id)}
                  >
                    <span>
                      {index + 1} de {emailPreviews.length}
                    </span>
                    <strong>{item.supplier_name}</strong>
                    <small>
                      {item.to_email || 'Sem e-mail'} · {item.sender_email || 'Sem conta'} · {item.can_send ? 'pronto' : 'bloqueado'}
                    </small>
                  </button>
                ))}
              </div>
              <div className="quote-preview-pane">
                <div className="email-preview-head">
                  <div>
                    <strong>{preview.supplier_name}</strong>
                    <span>
                      Para: {preview.to_email || 'contato pendente'} · Conta: {preview.sender_email}
                    </span>
                  </div>
                  <Badge variant={preview.status === 'sent' ? 'success' : preview.can_send ? 'neutral' : 'warning'}>
                    {preview.status === 'sent' ? 'enviada' : preview.can_send ? 'pronta' : 'bloqueada'}
                  </Badge>
                </div>
                {blockedReason && <p className="email-preview-warning">{blockedReason}</p>}
                <label className="bcc-toggle">
                  <input
                    type="checkbox"
                    checked={bccEnabled}
                    onChange={event => handleBccToggle(preview, event.target.checked)}
                  />
                  BCC padrao {bccEnabled ? 'ativo' : 'desativado'} {preview.bcc ? `(${preview.bcc})` : ''}
                </label>
                <Input
                  id={`subject-${preview.message_id}`}
                  label="Assunto"
                  value={draft.subject ?? preview.subject}
                  onChange={event =>
                    setEmailDraftEdits(prev => ({
                      ...prev,
                      [preview.message_id]: { ...(prev[preview.message_id] || {}), subject: event.target.value },
                    }))
                  }
                />
                <label className="email-message-editor" htmlFor={`message-${preview.message_id}`}>
                  Mensagem
                  <textarea
                    id={`message-${preview.message_id}`}
                    value={draft.body_text ?? preview.body_text ?? ''}
                    onChange={event =>
                      setEmailDraftEdits(prev => ({
                        ...prev,
                        [preview.message_id]: { ...(prev[preview.message_id] || {}), body_text: event.target.value },
                      }))
                    }
                    rows={6}
                  />
                </label>
                <div className="email-preview-body-container" style={{ marginTop: 12 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                    Visualização como fornecedor
                  </span>
                  <div className="email-preview-body" dangerouslySetInnerHTML={{ __html: preview.body_html }} />
                </div>
                <div className="quote-step-footer" style={{ gap: 8 }}>
                  <Button variant="secondary" size="sm" onClick={() => saveEmailDraft(preview)}>
                    Salvar mensagem
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      updateEmailMessage(preview.message_id, {
                        sender_account_id: preview.sender_account_id === 'vesper' ? 'ventrio' : 'vesper',
                      })
                    }
                  >
                    Trocar conta
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => sendEmailMessage(preview, true)}
                    disabled={sendingMessageId === preview.message_id}
                  >
                    Enviar de teste
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => sendEmailMessage(preview, false)}
                    disabled={
                      sendingMessageId === preview.message_id ||
                      (!preview.can_send && preview.environment !== 'testing')
                    }
                  >
                    {sendingMessageId === preview.message_id
                      ? 'Enviando...'
                      : preview.status === 'sent'
                      ? 'Reenviar bloqueado'
                      : 'Enviar cotação'}
                  </Button>
                </div>
              </div>
              <aside className="quote-preview-summary">
                <h3>Resumo</h3>
                <div>
                  <strong>{emailPreviews.length}</strong>
                  <span>fornecedores</span>
                </div>
                <div>
                  <strong>{readyPreviewCount}</strong>
                  <span>prontos</span>
                </div>
                <div>
                  <strong>{blockedPreviewCount}</strong>
                  <span>bloqueados</span>
                </div>
              </aside>
            </div>
          );
        })()
      ) : null}

      <div className="quote-step-footer">
        <Button variant="secondary" onClick={() => setQuoteWizardStep('suppliers')}>
          Voltar
        </Button>
        <Button variant="primary" onClick={loadEmailPreviews} disabled={loadingPreviews}>
          Revisar mensagens
        </Button>
      </div>
    </div>
  );
};
