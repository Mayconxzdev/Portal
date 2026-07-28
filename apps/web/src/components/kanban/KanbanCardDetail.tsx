import React, { useEffect, useState } from 'react';
import { Download, Paperclip, Plus, Save, X, Calendar, User, Clock, AlertTriangle, FileText, CheckCircle2 } from 'lucide-react';
import { Activity, CardAttachment, CardComment, Checklist, KanbanBoard, KanbanCard, CurrentUser } from './types';
import { activityLabel, apiJson, priorityLabels } from './kanbanApi';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Textarea } from '../ui/Textarea';
import { Checkbox } from '../ui/Checkbox';
import { Badge } from '../ui/Badge';
import { PriorityBadge } from '../ui/PriorityBadge';

interface Props {
  board: KanbanBoard;
  card: KanbanCard;
  canEdit: boolean;
  onClose: () => void;
  onChanged: () => void;
  currentUser?: CurrentUser;
}

export const KanbanCardDetail: React.FC<Props> = ({ board, card, canEdit, onClose, onChanged, currentUser }) => {
  const [activeTab, setActiveTab] = useState<'details' | 'checklist' | 'comments' | 'attachments' | 'activity'>('details');
  const [draft, setDraft] = useState({
    title: card.title,
    description: card.description || '',
    priority: card.priority,
    due_date: card.due_date?.slice(0, 10) || '',
    custom_fields: card.custom_fields || {}
  });
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [comments, setComments] = useState<CardComment[]>([]);
  const [attachments, setAttachments] = useState<CardAttachment[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [newChecklist, setNewChecklist] = useState('');
  const [newItem, setNewItem] = useState<Record<number, string>>({});
  const [newComment, setNewComment] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [allUsers, setAllUsers] = useState<any[]>([]);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const users = await apiJson<any[]>('/api/v1/kanban/users');
        setAllUsers(users || []);
      } catch (err) {
        console.error("Falha ao buscar usuários para atribuição:", err);
      }
    };
    fetchUsers();
  }, []);

  const handleAddLabel = async (labelId: number) => {
    if (!labelId) return;
    try {
      setError(null);
      await apiJson(`/api/v1/kanban/cards/${card.id}/labels/${labelId}`, { method: 'POST' });
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao adicionar etiqueta.');
    }
  };

  const handleRemoveLabel = async (labelId: number) => {
    try {
      setError(null);
      await apiJson(`/api/v1/kanban/cards/${card.id}/labels/${labelId}`, { method: 'DELETE' });
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao remover etiqueta.');
    }
  };

  const handleAddAssignee = async (userId: number) => {
    if (!userId) return;
    try {
      setError(null);
      await apiJson(`/api/v1/kanban/cards/${card.id}/assignees/${userId}`, { method: 'POST' });
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao adicionar responsável.');
    }
  };

  const handleRemoveAssignee = async (userId: number) => {
    try {
      setError(null);
      await apiJson(`/api/v1/kanban/cards/${card.id}/assignees/${userId}`, { method: 'DELETE' });
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao remover responsável.');
    }
  };

  const reload = async () => {
    const [checklistData, commentData, attachmentData, activityData] = await Promise.all([
      apiJson<Checklist[]>(`/api/v1/kanban/cards/${card.id}/checklists`),
      apiJson<CardComment[]>(`/api/v1/kanban/cards/${card.id}/comments`),
      apiJson<CardAttachment[]>(`/api/v1/kanban/cards/${card.id}/attachments`),
      apiJson<Activity[]>(`/api/v1/kanban/cards/${card.id}/activity`),
    ]);
    setChecklists(checklistData);
    setComments(commentData);
    setAttachments(attachmentData);
    setActivity(activityData);
  };

  useEffect(() => {
    reload().catch((err) => setError(err.message));
  }, [card.id]);

  useEffect(() => {
    setDraft({
      title: card.title,
      description: card.description || '',
      priority: card.priority,
      due_date: card.due_date?.slice(0, 10) || '',
      custom_fields: card.custom_fields || {}
    });
  }, [card]);

  const saveDetails = async () => {
    try {
      setError(null);
      setSuccessMsg(null);
      const activeFieldKeys = new Set((board.custom_fields || []).filter((field) => field.is_active).map((field) => field.key));
      const activeCustomFields = Object.fromEntries(
        Object.entries(draft.custom_fields || {}).filter(([key]) => activeFieldKeys.has(key))
      );
      await apiJson(`/api/v1/kanban/cards/${card.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          title: draft.title,
          description: draft.description,
          priority: draft.priority,
          due_date: draft.due_date ? new Date(draft.due_date).toISOString() : null,
          custom_fields: activeCustomFields,
        }),
      });
      setSuccessMsg('Informações salvas com sucesso!');
      setTimeout(() => setSuccessMsg(null), 3000);
      onChanged();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const createChecklist = async () => {
    if (!newChecklist.trim()) return;
    try {
      await apiJson(`/api/v1/kanban/cards/${card.id}/checklists`, { method: 'POST', body: JSON.stringify({ title: newChecklist }) });
      setNewChecklist('');
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const getInsumoStatusBadge = (itemText: string, isDone: boolean) => {
    if (isDone) {
      return <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>OK</span>;
    }
    
    const warningItems = ['Flanges', 'Junta Flexível', 'Motor'];
    const delayedItems = ['Beneficiamento Externo', 'Pintura'];
    
    if (warningItems.some(name => itemText.toLowerCase().includes(name.toLowerCase()))) {
      return <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold', backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' }}>ATENÇÃO</span>;
    }
    if (delayedItems.some(name => itemText.toLowerCase().includes(name.toLowerCase()))) {
      return <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>ATRASADO</span>;
    }
    
    return <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold', backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>OK</span>;
  };

  const handleGenerateFactoryChecklist = async () => {
    try {
      setError(null);
      const checklist = await apiJson<any>(`/api/v1/kanban/cards/${card.id}/checklists`, {
        method: 'POST',
        body: JSON.stringify({ title: 'Insumos de Fábrica' })
      });
      
      const factoryItems = [
        'Desenho',
        'Motor',
        'Hélice/Rotor',
        'Fabricação de Peças',
        'Tambor/Voluta',
        'Base do Motor',
        'Suporte/Estrutura',
        'Flanges',
        'Junta Flexível',
        'Acessórios do Exaustor',
        'Acessórios Avulsos',
        'Beneficiamento Externo',
        'Pintura',
        'Montagem',
        'Inspeção Final'
      ];
      
      for (const itemText of factoryItems) {
        await apiJson(`/api/v1/kanban/checklists/${checklist.id}/items`, {
          method: 'POST',
          body: JSON.stringify({ text: itemText })
        });
      }
      
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao gerar o checklist canônico.');
    }
  };

  const createItem = async (checklistId: number) => {
    if (!newItem[checklistId]?.trim()) return;
    try {
      await apiJson(`/api/v1/kanban/checklists/${checklistId}/items`, { method: 'POST', body: JSON.stringify({ text: newItem[checklistId] }) });
      setNewItem({ ...newItem, [checklistId]: '' });
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const toggleItem = async (itemId: number, isDone: boolean) => {
    try {
      await apiJson(`/api/v1/kanban/checklist-items/${itemId}`, { method: 'PATCH', body: JSON.stringify({ is_done: !isDone }) });
      await reload();
      onChanged();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const createComment = async () => {
    if (!newComment.trim()) return;
    try {
      await apiJson(`/api/v1/kanban/cards/${card.id}/comments`, { method: 'POST', body: JSON.stringify({ comment: newComment }) });
      setNewComment('');
      await reload();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const uploadAttachment = async (file?: File) => {
    if (!file) return;
    try {
      setError(null);
      const data = new FormData();
      data.append('upload', file);
      await apiJson(`/api/v1/kanban/cards/${card.id}/attachments`, { method: 'POST', body: data });
      await reload();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const op = card.custom_fields?.op as string | undefined;

  return (
    <div style={overlayStyle}>
      <aside style={panelStyle} className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, borderBottom: '1px solid var(--border-color)', paddingBottom: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <Badge variant="info">{board.name}</Badge>
              <Badge variant="neutral">Card #{card.id}</Badge>
              {op && <Badge variant="primary">OP: {op}</Badge>}
            </div>
            <h2 style={{ color: 'var(--text-primary)', margin: '12px 0 4px', fontSize: '20px', fontWeight: 700 }}>{card.title}</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', fontSize: '12px' }}>
              <Clock size={13} />
              <span>Criado em {new Date(card.created_at).toLocaleString('pt-BR')}</span>
            </div>
          </div>
          <button className="close-btn" onClick={onClose} style={{ background: 'var(--surface-control)', border: '1px solid var(--semantic-border)', borderRadius: 8, cursor: 'pointer', padding: 8, color: 'var(--icon-strong)' }}>
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="offline-banner" style={{ marginTop: 12 }}>
            <div>
              <div className="offline-banner-title">Ops! Ocorreu um erro</div>
              <div className="offline-banner-text">{error}</div>
            </div>
          </div>
        )}

        {successMsg && (
          <div style={{ color: '#a7f3d0', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: 8, padding: 10, marginTop: 12, fontSize: 13 }}>
            {successMsg}
          </div>
        )}

        <div className="tabs-header" style={{ margin: '16px 0 20px', display: 'flex', gap: 4, overflowX: 'auto', borderBottom: '1px solid var(--border-color)' }}>
          {([
            { id: 'details', label: 'Detalhes' },
            { id: 'checklist', label: 'Checklist' },
            { id: 'comments', label: 'Comentários' },
            { id: 'attachments', label: 'Anexos' },
            { id: 'activity', label: 'Histórico' }
          ] as const).map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '8px 16px' }}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div style={{ paddingBottom: 40 }}>
          {activeTab === 'details' && (
            <section style={{ display: 'grid', gap: 16 }}>
              <Input
                label="Título da Tarefa"
                disabled={!canEdit}
                value={draft.title}
                onChange={(event) => setDraft({ ...draft, title: event.target.value })}
              />

              <Textarea
                label="Descrição"
                disabled={!canEdit}
                rows={5}
                value={draft.description}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                placeholder="Insira os detalhes e objetivos desta tarefa..."
              />

              <div style={gridStyle}>
                <Input
                  label="Prazo de Conclusão"
                  disabled={!canEdit}
                  type="date"
                  value={draft.due_date}
                  onChange={(event) => setDraft({ ...draft, due_date: event.target.value })}
                  helpText="Selecione a data limite"
                />
              </div>

              {board.custom_fields && board.custom_fields.some((field) => field.is_active) && (
                <div style={{ marginTop: 8, borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                  <h4 style={{ fontSize: 14, color: 'var(--text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <FileText size={15} style={{ color: 'var(--color-primary)' }} />
                    Campos Personalizados do Quadro
                  </h4>
                  <div style={{ display: 'grid', gap: 14 }}>
                    {board.custom_fields.filter((field) => field.is_active).map((field) => {
                      const value = (draft.custom_fields as Record<string, any>)[field.key] ?? '';
                      const handleChange = (val: any) => {
                        setDraft(prev => ({
                          ...prev,
                          custom_fields: {
                            ...prev.custom_fields,
                            [field.key]: val
                          }
                        }));
                      };

                      if (field.field_type === 'BOOLEAN') {
                        return (
                          <Checkbox
                            key={field.id}
                            label={field.name}
                            disabled={!canEdit}
                            checked={!!value}
                            onChange={(e) => handleChange(e.target.checked)}
                          />
                        );
                      }

                      if (field.field_type === 'SELECT') {
                        const choices = (field.options?.choices as string[]) || [];
                        const selectOpts = [
                          { value: '', label: 'Selecione uma opção...' },
                          ...choices.map(c => ({ value: c, label: c }))
                        ];
                        return (
                          <Select
                            key={field.id}
                            label={field.name}
                            disabled={!canEdit}
                            value={value as string}
                            options={selectOpts}
                            onChange={(e) => handleChange(e.target.value)}
                          />
                        );
                      }

                      if (field.field_type === 'NUMBER') {
                        return (
                          <Input
                            key={field.id}
                            label={field.name}
                            type="number"
                            disabled={!canEdit}
                            value={value}
                            onChange={(e) => handleChange(e.target.value === '' ? '' : Number(e.target.value))}
                          />
                        );
                      }

                      if (field.field_type === 'DATE') {
                        return (
                          <Input
                            key={field.id}
                            label={field.name}
                            type="date"
                            disabled={!canEdit}
                            value={(value as string)?.slice(0, 10) || ''}
                            onChange={(e) => handleChange(e.target.value)}
                            helpText="Data do setor"
                          />
                        );
                      }

                      return (
                        <Input
                          key={field.id}
                          label={field.name}
                          type="text"
                          disabled={!canEdit}
                          value={value as string}
                          onChange={(e) => handleChange(e.target.value)}
                        />
                      );
                    })}
                  </div>
                </div>
              )}

              <div style={{ marginTop: 8, display: 'grid', gap: 14, borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                <div>
                  <span style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Etiquetas</span>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    {card.labels.map((label) => (
                      <span 
                        key={label.id} 
                        className="badge" 
                        style={{ 
                          borderColor: label.color, 
                          color: label.color, 
                          background: `${label.color}15`,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6
                        }}
                      >
                        {label.name}
                        {canEdit && (
                          <button 
                            type="button"
                            onClick={() => handleRemoveLabel(label.id)}
                            style={{ background: 'none', border: 0, padding: 0, color: label.color, cursor: 'pointer', display: 'flex', alignItems: 'center', fontWeight: 'bold', fontSize: 11 }}
                          >
                            ×
                          </button>
                        )}
                      </span>
                    ))}
                    {card.labels.length === 0 && <span style={{ fontSize: 12, color: '#475569', fontStyle: 'italic' }}>Nenhuma etiqueta</span>}
                    
                    {canEdit && (
                      <select 
                        aria-label="Adicionar etiqueta"
                        className="form-input" 
                        style={{ margin: 0, height: 28, padding: '2px 8px', fontSize: 11, width: 'auto', minWidth: 120 }}
                        value="" 
                        onChange={(e) => {
                          handleAddLabel(Number(e.target.value));
                          e.target.value = "";
                        }}
                      >
                        <option value="">+ Add Etiqueta...</option>
                        {(board.labels || [])
                          .filter(l => !card.labels.some(cl => cl.id === l.id))
                          .map(l => (
                            <option key={l.id} value={l.id}>{l.name}</option>
                          ))
                        }
                      </select>
                    )}
                  </div>
                </div>

                <div>
                  <span style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Responsáveis</span>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    {card.assignees.map((item) => (
                      <span 
                        key={item.id} 
                        className="badge" 
                        style={{ 
                          display: 'inline-flex', 
                          alignItems: 'center', 
                          gap: 6 
                        }}
                      >
                        <User size={10} />
                        {item.user?.username || `Usuário ${item.user_id}`}
                        {canEdit && (
                          <button 
                            type="button"
                            onClick={() => handleRemoveAssignee(item.user_id)}
                            style={{ background: 'none', border: 0, padding: 0, color: 'var(--color-danger)', cursor: 'pointer', display: 'flex', alignItems: 'center', fontWeight: 'bold', fontSize: 11 }}
                          >
                            ×
                          </button>
                        )}
                      </span>
                    ))}
                    {card.assignees.length === 0 && <span style={{ fontSize: 12, color: '#475569', fontStyle: 'italic' }}>Sem responsáveis atribuídos</span>}
                    
                    {canEdit && (
                      <select 
                        aria-label="Adicionar responsável"
                        className="form-input" 
                        style={{ margin: 0, height: 28, padding: '2px 8px', fontSize: 11, width: 'auto', minWidth: 140 }}
                        value="" 
                        onChange={(e) => {
                          handleAddAssignee(Number(e.target.value));
                          e.target.value = "";
                        }}
                      >
                        <option value="">+ Add Responsável...</option>
                        {allUsers
                          .filter(u => !card.assignees.some(ca => ca.user_id === u.id))
                          .filter(u => {
                            const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
                            if (isCurrentUserMessias) return true;
                            return u.role_name !== 'MESSIAS' && u.role !== 'MESSIAS' && u.username !== 'MESSIAS';
                          })
                          .map(u => (
                            <option key={u.id} value={u.id}>{u.username}</option>
                          ))
                        }
                      </select>
                    )}
                  </div>
                </div>
              </div>

              {canEdit && (
                <Button variant="primary" onClick={saveDetails} style={{ marginTop: 12 }} leftIcon={<Save size={15} />}>
                  Salvar Alterações
                </Button>
              )}
            </section>
          )}

          {activeTab === 'checklist' && (
            <section style={{ display: 'grid', gap: 16 }}>
              {canEdit && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <Input
                      label="Criar Nova Lista de Verificação"
                      value={newChecklist}
                      onChange={(event) => setNewChecklist(event.target.value)}
                      placeholder="Nome da lista (ex: Etapas de Montagem...)"
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Button variant="secondary" onClick={createChecklist} style={{ height: 42 }}>
                      <Plus size={16} />
                    </Button>
                    <Button 
                      variant="primary" 
                      onClick={handleGenerateFactoryChecklist} 
                      style={{ height: 42, backgroundColor: '#10b981', borderColor: '#10b981' }}
                    >
                      Gerar Checklist de Insumos (15 Itens)
                    </Button>
                  </div>
                </div>
              )}

              {checklists.length === 0 && (
                <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-secondary)' }}>
                  <CheckCircle2 size={32} style={{ margin: '0 auto 8px', color: 'var(--icon-muted)' }} />
                  <p style={{ fontSize: 14 }}>Nenhuma lista de verificação criada para este card.</p>
                </div>
              )}

              {checklists.map((checklist) => (
                <div key={checklist.id} style={boxStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>{checklist.title}</strong>
                    <Badge variant={checklist.items.length > 0 && checklist.items.every(i => i.is_done) ? 'success' : 'neutral'}>
                      {checklist.items.filter((item) => item.is_done).length}/{checklist.items.length} concluídos
                    </Badge>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, margin: '12px 0' }}>
                    {checklist.items.map((item) => {
                      const isFactoryChecklist = checklist.title.toLowerCase().includes('insumo') || checklist.title.toLowerCase().includes('fábrica');
                      return (
                        <div key={item.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: item.is_done ? 'var(--text-muted)' : 'var(--text-primary)', cursor: 'pointer', fontSize: 13, flex: 1 }}>
                            <input
                              type="checkbox"
                              className="form-checkbox"
                              disabled={!canEdit}
                              checked={item.is_done}
                              onChange={() => toggleItem(item.id, item.is_done)}
                            />
                            <span style={{ textDecoration: item.is_done ? 'line-through' : 'none' }}>{item.text}</span>
                          </label>
                          {isFactoryChecklist && getInsumoStatusBadge(item.text, item.is_done)}
                        </div>
                      );
                    })}
                  </div>

                  {canEdit && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                      <div style={{ flex: 1 }}>
                        <Input
                          placeholder="Adicionar item..."
                          value={newItem[checklist.id] || ''}
                          onChange={(event) => setNewItem({ ...newItem, [checklist.id]: event.target.value })}
                        />
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => createItem(checklist.id)} style={{ height: 38 }}>
                        Adicionar
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </section>
          )}

          {activeTab === 'comments' && (
            <section style={{ display: 'grid', gap: 16 }}>
              <div className="comment-list" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {comments.length === 0 && (
                  <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '20px 0', fontSize: 14 }}>
                    Nenhum comentário feito ainda.
                  </p>
                )}
                {comments.map((comment) => (
                  <div key={comment.id} className="comment-card" style={{ marginBottom: 12 }}>
                    <div className="comment-header">
                      <span>Usuário #{comment.user_id}</span>
                      <span>{new Date(comment.created_at).toLocaleString('pt-BR')}{comment.edited_at ? ' · editado' : ''}</span>
                    </div>
                    <p className="comment-body">{comment.comment}</p>
                  </div>
                ))}
              </div>

              {canEdit && (
                <div style={{ display: 'grid', gap: 8, borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                  <Textarea
                    label="Novo Comentário"
                    rows={3}
                    value={newComment}
                    onChange={(event) => setNewComment(event.target.value)}
                    placeholder="Escreva um comentário amigável ou notas de atualização..."
                  />
                  <Button variant="primary" onClick={createComment} style={{ justifySelf: 'end' }}>
                    Enviar Comentário
                  </Button>
                </div>
              )}
            </section>
          )}

          {activeTab === 'attachments' && (
            <section style={{ display: 'grid', gap: 16 }}>
              {canEdit && (
                <div style={{ border: '1px dashed var(--border-color)', borderRadius: 'var(--border-radius-md)', padding: 16, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, background: 'var(--surface-panel-soft)' }}>
                  <Paperclip size={24} style={{ color: 'var(--icon-muted)' }} />
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Selecione um arquivo de seu dispositivo</span>
                  <input
                    type="file"
                    style={{ display: 'block', fontSize: 12, color: 'var(--text-secondary)' }}
                    onChange={(event) => uploadAttachment(event.target.files?.[0]).catch((err) => setError(err.message))}
                  />
                </div>
              )}

              <div style={{ display: 'grid', gap: 10 }}>
                {attachments.length === 0 && (
                  <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '20px 0', fontSize: 14 }}>
                    Nenhum anexo enviado.
                  </p>
                )}
                {attachments.map((attachment) => (
                  <div key={attachment.id} style={{ ...boxStyle, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <Paperclip size={14} style={{ color: 'var(--icon-muted)' }} />
                      {attachment.file?.original_filename || 'Arquivo Anexo'}
                    </span>
                    <a
                      className="btn btn-ghost btn-sm"
                      style={{ padding: 6 }}
                      href={`/api/v1/kanban/card-attachments/${attachment.id}/download`}
                      title="Download do anexo"
                    >
                      <Download size={14} />
                    </a>
                  </div>
                ))}
              </div>
            </section>
          )}

          {activeTab === 'activity' && (
            <section>
              <div className="timeline">
                {activity.length === 0 && (
                  <p style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
                    Nenhum histórico registrado.
                  </p>
                )}
                {activity.map((item) => (
                  <div key={item.id} className="timeline-item">
                    <div className="timeline-dot" />
                    <div className="timeline-content">
                      <strong style={{ color: 'var(--text-primary)' }}>{activityLabel(item.action)}</strong>
                      <div className="timeline-time">{new Date(item.created_at).toLocaleString('pt-BR')}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </aside>
    </div>
  );
};

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(2, 6, 23, 0.72)',
  zIndex: 1000,
  display: 'flex',
  justifyContent: 'flex-end',
  backdropFilter: 'blur(4px)'
};

const panelStyle: React.CSSProperties = {
  width: 'min(700px, 100vw)',
  height: '100vh',
  overflowY: 'auto',
  borderRadius: 0,
  borderLeft: '1px solid var(--border-color)',
  padding: 24,
  boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
  display: 'flex',
  flexDirection: 'column',
  animation: 'slideLeft 0.3s ease-out'
};

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 16
};

const boxStyle: React.CSSProperties = {
  border: '1px solid var(--border-color)',
  borderRadius: 8,
  padding: 14,
  background: 'var(--surface-panel-soft)'
};
