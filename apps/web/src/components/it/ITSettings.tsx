import React, { useState, useEffect } from 'react';
import { Settings, Plus, Play, Calendar, HelpCircle, CheckCircle2 } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Textarea } from '../ui/Textarea';
import { Modal } from '../ui/Modal';
import { itRequest, priorityLabels, categoryLabel, categoryOptions } from './itApi';

export interface ITSettingsProps {
  customFields: any[];
  customCategories: any[];
  customAssetTypes: any[];
  onNewCustomField: () => void;
  onUpdateCategories: (categories: any[]) => void;
  onUpdateAssetTypes: (types: any[]) => void;
}

const ResourceDetailModal: React.FC<{
  type: string;
  item: any;
  endpoint: string;
  onClose: () => void;
  onChanged: () => void;
}> = ({ type, item, endpoint, onClose, onChanged }) => {
  const isEdit = !!item.id;
  const [name, setName] = useState(item.name || item.title || '');
  const [priority, setPriority] = useState(item.priority || 'MEDIA');
  const [category, setCategory] = useState(item.category || '');
  const [responseMinutes, setResponseMinutes] = useState(item.response_minutes ?? 240);
  const [resolutionMinutes, setResolutionMinutes] = useState(item.resolution_minutes ?? 1440);
  const [isActive, setIsActive] = useState(item.is_active ?? true);
  const [itemsText, setItemsText] = useState(Array.isArray(item.items) ? item.items.join('\n') : '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Nome/Título é obrigatório');
      return;
    }
    setError('');
    setSaving(true);
    try {
      let body: any = {};
      if (type === 'sla') {
        body = {
          name,
          priority,
          category: category || null,
          response_minutes: Number(responseMinutes),
          resolution_minutes: Number(resolutionMinutes),
          is_active: isActive,
        };
      } else {
        body = {
          title: name,
          category: category || 'OUTRO',
          items: itemsText.split('\n').map((x: string) => x.trim()).filter(Boolean),
          is_active: isActive,
        };
      }

      if (isEdit) {
        await itRequest(`${endpoint}/${item.id}`, {
          method: 'PATCH',
          body: JSON.stringify(body),
        });
      } else {
        await itRequest(endpoint, {
          method: 'POST',
          body: JSON.stringify(body),
        });
      }
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar recurso');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title={isEdit ? `Editar ${type === 'sla' ? 'Política de SLA' : 'Template'}` : `Criar ${type === 'sla' ? 'Política de SLA' : 'Template'}`} size="md">
      <form onSubmit={handleSubmit} className="space-y-4 text-xs font-bold text-slate-355">
        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500 rounded text-rose-200">
            {error}
          </div>
        )}

        <div className="space-y-1">
          <label className="block text-slate-400">{type === 'sla' ? 'Nome da Política' : 'Título do Template'}</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={type === 'sla' ? 'Ex: SLA Padrão Computador Alta' : 'Ex: Checklist de Instalação'}
            required
          />
        </div>

        {type === 'sla' ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Prioridade"
                value={priority}
                options={[
                  { value: 'BAIXA', label: 'Baixa' },
                  { value: 'MEDIA', label: 'Média' },
                  { value: 'ALTA', label: 'Alta' },
                  { value: 'CRITICA', label: 'Crítica' }
                ]}
                onChange={(e) => setPriority(e.target.value)}
              />
              <Select
                label="Categoria (Opcional)"
                value={category}
                options={[{ value: '', label: 'Nenhuma (Padrão)' }, ...categoryOptions]}
                onChange={(e) => setCategory(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-slate-400">Tempo de Resposta (Minutos)</label>
                <Input
                  type="number"
                  value={responseMinutes}
                  onChange={(e) => setResponseMinutes(Number(e.target.value))}
                  min={1}
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="block text-slate-400">Tempo de Resolução (Minutos)</label>
                <Input
                  type="number"
                  value={resolutionMinutes}
                  onChange={(e) => setResolutionMinutes(Number(e.target.value))}
                  min={1}
                  required
                />
              </div>
            </div>
          </>
        ) : (
          <>
            <Select
              label="Categoria"
              value={category}
              options={categoryOptions}
              onChange={(e) => setCategory(e.target.value)}
            />
            <div className="space-y-1">
              <label className="block text-slate-400">Itens do Checklist (um por linha)</label>
              <Textarea
                value={itemsText}
                onChange={(e) => setItemsText(e.target.value)}
                placeholder="Ex: Verificar RAM&#10;Limpar poeira&#10;Atualizar OS"
                rows={5}
                required
              />
            </div>
          </>
        )}

        <div className="flex items-center gap-2 pt-2">
          <input
            type="checkbox"
            id="is_active_checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
          />
          <label htmlFor="is_active_checkbox" className="text-slate-350 cursor-pointer select-none">Ativo</label>
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={saving}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={saving}
          >
            {saving ? 'Salvando...' : 'Salvar'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

const ResourcePanel: React.FC<{
  type: string;
  title: string;
  icon: React.ReactNode;
  endpoint: string;
  createLabel: string;
  fields: [string, string][];
}> = ({ type, title, icon, endpoint, createLabel, fields }) => {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<any | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const fetchItems = async () => {
    try {
      setLoading(true);
      const res = await itRequest<any[]>(endpoint);
      setItems(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [endpoint]);

  if (loading) {
    return <div className="text-xs text-slate-500 font-bold py-4">Carregando dados...</div>;
  }

  return (
    <div className="space-y-4 text-xs font-bold text-slate-300">
      <div className="flex justify-between items-center">
        {title && <h4 className="font-extrabold text-sm text-slate-400 uppercase flex items-center gap-2">{icon} {title}</h4>}
        <Button
          size="sm"
          variant="primary"
          onClick={() => {
            if (type === 'sla') {
              setSelectedItem({
                name: '',
                priority: 'MEDIA',
                category: '',
                response_minutes: 60,
                resolution_minutes: 240,
                is_active: true
              });
            } else {
              setSelectedItem({
                title: '',
                category: 'OUTRO',
                items: [],
                is_active: true
              });
            }
            setIsDetailOpen(true);
          }}
        >
          {createLabel}
        </Button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/20">
        <table className="w-full border-collapse text-left text-xs font-bold bg-transparent">
          <thead>
            <tr className="bg-slate-900/60 border-b border-slate-800 text-slate-350">
              {fields.map(([key, label]) => (
                <th key={key} className="p-3 border-r border-slate-800/80">{label}</th>
              ))}
              <th className="p-3 border-r border-slate-800/80">Status</th>
              <th className="p-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-slate-900/50 hover:bg-slate-900/20 text-slate-300">
                {fields.map(([key]) => {
                  let val = item[key];
                  if (key === 'priority') val = priorityLabels[val] || val;
                  if (key === 'category') val = categoryLabel(val);
                  if (key === 'items') val = Array.isArray(val) ? `${val.length} itens` : val;
                  return (
                    <td key={key} className="p-3 border-r border-slate-900/50">
                      {val !== null && val !== undefined ? String(val) : '-'}
                    </td>
                  );
                })}
                <td className="p-3 border-r border-slate-900/50">
                  <Badge variant={item.is_active ? 'success' : 'neutral'} className="text-[10px]">
                    {item.is_active ? 'Ativo' : 'Inativo'}
                  </Badge>
                </td>
                <td className="p-3 text-right space-x-1 shrink-0">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setSelectedItem(item);
                      setIsDetailOpen(true);
                    }}
                    className="py-0.5 px-2"
                  >
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    variant={item.is_active ? 'danger' : 'success'}
                    className="py-0.5 px-2"
                    onClick={async () => {
                      try {
                        await itRequest(`${endpoint}/${item.id}`, {
                          method: 'PATCH',
                          body: JSON.stringify({ is_active: !item.is_active }),
                        });
                        fetchItems();
                      } catch (err) {
                        console.error(err instanceof Error ? err.message : 'Erro ao alterar status');
                      }
                    }}
                  >
                    {item.is_active ? 'Desativar' : 'Ativar'}
                  </Button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={fields.length + 2} className="p-4 text-center text-slate-500 font-bold">
                  Nenhum registro cadastrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isDetailOpen && selectedItem && (
        <ResourceDetailModal
          type={type}
          item={selectedItem}
          endpoint={endpoint}
          onClose={() => {
            setIsDetailOpen(false);
            setSelectedItem(null);
          }}
          onChanged={() => {
            setIsDetailOpen(false);
            setSelectedItem(null);
            fetchItems();
          }}
        />
      )}
    </div>
  );
};

export const ITSettings: React.FC<ITSettingsProps> = ({
  customFields,
  customCategories,
  customAssetTypes,
  onNewCustomField,
  onUpdateCategories,
  onUpdateAssetTypes,
}) => {
  const [showNewCatModal, setShowNewCatModal] = useState(false);
  const [newCatName, setNewCatName] = useState('');
  const [showNewTypeModal, setShowNewTypeModal] = useState(false);
  const [newTypeName, setNewTypeName] = useState('');

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
          ⚙️ Configurações Administrativas do TI
        </h2>
        <p className="text-xs text-slate-400 mb-6 font-medium">
          Configuração de campos de ativos, políticas de SLA, checklists padrões e categorias de chamados.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Campos Personalizados de Ativos */}
          <Card className="p-5 bg-slate-950/20 border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                📑 Campos Adicionais de Ativos
              </h3>
              <Button size="sm" variant="primary" onClick={onNewCustomField} leftIcon={<Plus size={12} />}>
                Criar Campo
              </Button>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin">
              {customFields.map((field) => (
                <div key={field.id} className="p-3 rounded-xl border border-slate-800 bg-slate-950/40 flex justify-between items-center hover:border-slate-700 transition-colors text-xs font-semibold text-slate-300">
                  <div>
                    <strong className="text-sm text-white block">{field.name}</strong>
                    <span className="text-xs text-slate-400 font-medium">
                      Tipo: {
                        field.field_type === 'TEXT' ? 'Texto' :
                        field.field_type === 'NUMBER' ? 'Número' :
                        field.field_type === 'DATE' ? 'Data' :
                        field.field_type === 'SELECT' ? 'Lista de Opções' :
                        field.field_type === 'BOOLEAN' ? 'Booleano' : field.field_type
                      }
                    </span>
                  </div>
                  <Badge variant="success" className="text-[10px]">Ativo</Badge>
                </div>
              ))}
              {customFields.length === 0 && <div className="text-xs text-center py-8 text-slate-500 font-bold">Nenhum campo personalizado cadastrado.</div>}
            </div>
          </Card>

          {/* Categorias de Chamados */}
          <Card className="p-5 bg-slate-950/20 border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                🏷️ Categorias de Chamados
              </h3>
              <Button size="sm" variant="primary" onClick={() => {
                setShowNewCatModal(true);
              }} leftIcon={<Plus size={12} />}>
                Adicionar Categoria
              </Button>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin">
              {categoryOptions.map(cat => (
                <div key={cat.value} className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/40 flex justify-between items-center text-xs font-bold text-slate-350">
                  <span>{cat.label}</span>
                  <span className="text-[9px] text-slate-500 font-bold bg-slate-900 border border-slate-850 px-2 py-0.5 rounded-full uppercase">Sistema</span>
                </div>
              ))}
              {customCategories.map((cat, idx) => (
                <div key={cat.value} className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/40 flex justify-between items-center text-xs font-bold text-slate-300 hover:border-slate-700 transition-colors">
                  <span>{cat.label}</span>
                  <Button
                    size="sm"
                    variant={cat.is_active ? 'danger' : 'success'}
                    className="text-[10px] py-0.5 px-2"
                    onClick={() => {
                      const updated = [...customCategories];
                      updated[idx].is_active = !updated[idx].is_active;
                      onUpdateCategories(updated);
                    }}
                  >
                    {cat.is_active ? 'Desativar' : 'Ativar'}
                  </Button>
                </div>
              ))}
            </div>
          </Card>

          {/* Tipos de Ativos */}
          <Card className="p-5 bg-slate-950/20 border-slate-800 space-y-4 col-span-1 lg:col-span-2">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                💻 Tipos de Ativos
              </h3>
              <Button size="sm" variant="primary" onClick={() => {
                setShowNewTypeModal(true);
              }} leftIcon={<Plus size={12} />}>
                Adicionar Tipo
              </Button>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin">
              {[
                { value: 'PC', label: 'Computador/Desktop' },
                { value: 'NOTEBOOK', label: 'Notebook' },
                { value: 'MONITOR', label: 'Monitor' },
                { value: 'IMPRESSORA', label: 'Impressora' },
                { value: 'SERVIDOR', label: 'Servidor' },
                { value: 'ROTEADOR', label: 'Roteador' },
                { value: 'SWITCH', label: 'Switch' },
                { value: 'OUTRO', label: 'Outro' }
              ].map(t => (
                <div key={t.value} className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/40 flex justify-between items-center text-xs font-bold text-slate-350">
                  <span>{t.label}</span>
                  <span className="text-[9px] text-slate-500 font-bold bg-slate-900 border border-slate-850 px-2 py-0.5 rounded-full uppercase">Sistema</span>
                </div>
              ))}
              {customAssetTypes.map((t, idx) => (
                <div key={t.value} className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/40 flex justify-between items-center text-xs font-bold text-slate-300 hover:border-slate-700 transition-colors">
                  <span>{t.label}</span>
                  <Button
                    size="sm"
                    variant={t.is_active ? 'danger' : 'success'}
                    className="text-[10px] py-0.5 px-2"
                    onClick={() => {
                      const updated = [...customAssetTypes];
                      updated[idx].is_active = !updated[idx].is_active;
                      onUpdateAssetTypes(updated);
                    }}
                  >
                    {t.is_active ? 'Desativar' : 'Ativar'}
                  </Button>
                </div>
              ))}
            </div>
          </Card>

          {/* Removido: SLA e Checklist Templates conforme solicitação 11.5 */}
        </div>
      </Card>

      {showNewCatModal && (
        <Modal isOpen={true} onClose={() => setShowNewCatModal(false)} title="Nova Categoria de Chamado" size="sm">
          <div className="space-y-4 text-xs font-bold text-slate-350">
            <p className="text-slate-400">Digite o nome da nova categoria de chamado:</p>
            <input
              type="text"
              value={newCatName}
              onChange={(e) => setNewCatName(e.target.value)}
              placeholder="Ex: Infraestrutura ou Banco de Dados"
              className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-white font-medium outline-none focus:border-sky-500/50"
              autoFocus
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={() => { setShowNewCatModal(false); setNewCatName(''); }}>Cancelar</Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  if (!newCatName.trim()) return;
                  const name = newCatName.trim();
                  const value = name.toUpperCase().replace(/\s+/g, '_');
                  const updated = [...customCategories, { value, label: name, is_active: true }];
                  onUpdateCategories(updated);
                  setNewCatName('');
                  setShowNewCatModal(false);
                }}
              >
                Confirmar
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {showNewTypeModal && (
        <Modal isOpen={true} onClose={() => setShowNewTypeModal(false)} title="Novo Tipo de Ativo" size="sm">
          <div className="space-y-4 text-xs font-bold text-slate-350">
            <p className="text-slate-400">Digite o nome do novo tipo de ativo:</p>
            <input
              type="text"
              value={newTypeName}
              onChange={(e) => setNewTypeName(e.target.value)}
              placeholder="Ex: Smart TV ou Tablet"
              className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-white font-medium outline-none focus:border-sky-500/50"
              autoFocus
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={() => { setShowNewTypeModal(false); setNewTypeName(''); }}>Cancelar</Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  if (!newTypeName.trim()) return;
                  const name = newTypeName.trim();
                  const value = name.toUpperCase().replace(/\s+/g, '_');
                  const updated = [...customAssetTypes, { value, label: name, is_active: true }];
                  onUpdateAssetTypes(updated);
                  setNewTypeName('');
                  setShowNewTypeModal(false);
                }}
              >
                Confirmar
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default ITSettings;
