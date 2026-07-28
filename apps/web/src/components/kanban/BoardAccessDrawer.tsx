import React, { useEffect, useMemo, useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Select } from '../ui/Select';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { BoardPermission, KanbanBoard, RoleOption, UserOption } from './types';
import { apiJson } from './kanbanApi';

interface Props {
  board: KanbanBoard;
  isOpen: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

const accessOptions = [
  { value: 'NO_ACCESS', label: 'Sem acesso' },
  { value: 'READ_ONLY', label: 'Somente leitura' },
  { value: 'NORMAL', label: 'Uso normal' },
  { value: 'MANAGER', label: 'Gestor' },
  { value: 'ADMIN', label: 'Admin' },
];

const accessLabel = Object.fromEntries(accessOptions.map((item) => [item.value, item.label]));

const personName = (item: BoardPermission) => item.username || item.user_email || 'Usuário sem nome cadastrado';
const roleName = (item: BoardPermission) => item.role_name || 'Perfil sem nome cadastrado';

export const BoardAccessDrawer: React.FC<Props> = ({ board, isOpen, onClose, onChanged }) => {
  const [items, setItems] = useState<BoardPermission[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [usersFound, setUsersFound] = useState<UserOption[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserOption | null>(null);
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState('');
  const [accessLevel, setAccessLevel] = useState('READ_ONLY');
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingPerm, setDeletingPerm] = useState<BoardPermission | null>(null);

  const selectedRole = useMemo(
    () => roles.find((role) => String(role.id) === selectedRoleId),
    [roles, selectedRoleId]
  );

  const loadPermissions = async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await apiJson<BoardPermission[]>(`/api/v1/kanban/boards/${board.id}/permissions`));
    } catch (err: any) {
      setError(err.message || 'Não foi possível carregar os acessos deste quadro.');
    } finally {
      setLoading(false);
    }
  };

  const loadRoles = async () => {
    try {
      setRoles(await apiJson<RoleOption[]>(`/api/v1/kanban/roles?board_id=${board.id}`));
    } catch (err: any) {
      setError(err.message || 'Não foi possível carregar os perfis disponíveis.');
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    loadPermissions();
    loadRoles();
    setSearchQuery('');
    setUsersFound([]);
    setSelectedUser(null);
    setSelectedRoleId('');
    setAccessLevel('READ_ONLY');
    setError(null);
  }, [isOpen, board.id]);

  const handleSearchUsers = async () => {
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setError(null);
    try {
      setUsersFound(await apiJson<UserOption[]>(`/api/v1/kanban/users?board_id=${board.id}&search=${encodeURIComponent(searchQuery)}`));
    } catch (err: any) {
      setError(err.message || 'Não foi possível buscar usuários.');
    } finally {
      setSearchLoading(false);
    }
  };

  const saveAccess = async () => {
    if (!selectedUser && !selectedRoleId) return;
    setError(null);
    try {
      await apiJson(`/api/v1/kanban/boards/${board.id}/permissions`, {
        method: 'POST',
        body: JSON.stringify({
          user_id: selectedUser ? selectedUser.id : undefined,
          role_id: selectedRoleId ? Number(selectedRoleId) : undefined,
          access_level: accessLevel,
        }),
      });
      setSelectedUser(null);
      setSelectedRoleId('');
      setSearchQuery('');
      setUsersFound([]);
      await loadPermissions();
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Não foi possível salvar o acesso.');
    }
  };

  const updateAccessLevel = async (permission: BoardPermission, level: string) => {
    setError(null);
    try {
      await apiJson(`/api/v1/kanban/boards/${board.id}/permissions`, {
        method: 'POST',
        body: JSON.stringify({
          user_id: permission.user_id,
          role_id: permission.role_id,
          access_level: level,
        }),
      });
      await loadPermissions();
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Não foi possível alterar o nível de acesso.');
    }
  };

  const handleDeleteAccess = async () => {
    if (!deletingPerm) return;
    setError(null);
    try {
      await apiJson(`/api/v1/kanban/boards/${board.id}/permissions/${deletingPerm.id}`, { method: 'DELETE' });
      setDeletingPerm(null);
      await loadPermissions();
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Não foi possível remover o acesso.');
    }
  };

  const pendingTarget = selectedUser
    ? `${selectedUser.username}${selectedUser.email ? ` (${selectedUser.email})` : ''}`
    : selectedRole
      ? `Perfil ${selectedRole.name}`
      : 'Escolha um usuário ou perfil';

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title={`Acessos do quadro - ${board.name}`} size="lg" footer={<Button variant="ghost" onClick={onClose}>Fechar</Button>}>
        <div style={{ display: 'grid', gap: 18 }}>
          {error && (
            <div className="offline-banner">
              <div>
                <div className="offline-banner-title">Não foi possível concluir a ação</div>
                <div className="offline-banner-text">{error}</div>
              </div>
            </div>
          )}

          <div className="glass-card" style={{ padding: 16, display: 'grid', gap: 12, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 12 }}>
            <strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>Conceder novo acesso</strong>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 1.2fr) minmax(180px, 1fr) 150px auto', gap: 10, alignItems: 'end' }}>
              <div style={{ position: 'relative' }}>
                <span className="form-label" style={{ display: 'block', marginBottom: 4, fontSize: 12 }}>Buscar usuário</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <Input
                    aria-label="Buscar usuário"
                    placeholder="Nome, usuário ou e-mail"
                    value={selectedUser ? `${selectedUser.username}${selectedUser.email ? ` (${selectedUser.email})` : ''}` : searchQuery}
                    disabled={!!selectedUser}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') handleSearchUsers();
                    }}
                    style={{ marginBottom: 0 }}
                  />
                  {selectedUser ? (
                    <Button variant="secondary" size="sm" onClick={() => { setSelectedUser(null); setSearchQuery(''); setUsersFound([]); }} style={{ padding: '0 8px' }}>Limpar</Button>
                  ) : (
                    <Button onClick={handleSearchUsers} disabled={searchLoading || !searchQuery.trim()}>{searchLoading ? 'Buscando...' : 'Buscar'}</Button>
                  )}
                </div>

                {!selectedUser && usersFound.length > 0 && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, background: 'var(--surface-panel)', border: '1px solid var(--semantic-border)', borderRadius: 8, boxShadow: 'var(--shadow-lg)', maxHeight: 180, overflowY: 'auto', marginTop: 4 }}>
                    {usersFound.map((user) => (
                      <button
                        key={user.id}
                        type="button"
                        onClick={() => { setSelectedUser(user); setSelectedRoleId(''); setUsersFound([]); }}
                        style={{ width: '100%', textAlign: 'left', padding: '8px 12px', cursor: 'pointer', fontSize: 13, border: 0, borderBottom: '1px solid var(--semantic-border)', color: 'var(--text-primary)', background: 'transparent' }}
                      >
                        <strong>{user.username}</strong>
                        {user.email && <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}> - {user.email}</span>}
                      </button>
                    ))}
                  </div>
                )}

                {!selectedUser && searchQuery && usersFound.length === 0 && !searchLoading && (
                  <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, padding: '8px 12px', background: 'var(--surface-panel)', border: '1px solid var(--semantic-border)', borderRadius: 8, fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                    Nenhum usuário ativo encontrado.
                  </div>
                )}
              </div>

              <Select
                label="Ou por perfil"
                value={selectedRoleId}
                disabled={!!selectedUser}
                onChange={(event) => { setSelectedRoleId(event.target.value); setSelectedUser(null); }}
                options={[
                  { value: '', label: 'Selecione um perfil' },
                  ...roles.map((role) => ({ value: String(role.id), label: role.name })),
                ]}
                style={{ marginBottom: 0 }}
              />

              <Select label="Nível" value={accessLevel} onChange={(event) => setAccessLevel(event.target.value)} options={accessOptions} style={{ marginBottom: 0 }} />
              <Button variant="primary" disabled={!selectedUser && !selectedRoleId} onClick={saveAccess}>Adicionar</Button>
            </div>
            <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Destino selecionado: {pendingTarget}</span>
          </div>

          <div style={{ display: 'grid', gap: 10 }}>
            <h4 style={{ margin: 0, color: 'var(--text-primary)', fontSize: 14 }}>Membros e permissões atuais</h4>
            {loading ? (
              <p className="text-muted" style={{ fontSize: 13 }}>Carregando permissões...</p>
            ) : items.length === 0 ? (
              <p className="text-muted" style={{ fontSize: 13 }}>Nenhuma permissão especial configurada. Apenas administradores globais e regras internas têm acesso.</p>
            ) : (
              <div style={{ display: 'grid', gap: 8 }}>
                {items.map((item) => {
                  const isUser = Boolean(item.user_id);
                  const title = isUser ? personName(item) : roleName(item);
                  return (
                    <div key={item.id} className="glass-card" style={{ padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: 10, gap: 12 }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                        <strong style={{ color: 'var(--text-primary)', fontSize: 13.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</strong>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                          {isUser ? (item.user_email || 'Usuário sem e-mail cadastrado') : 'Acesso concedido a todos os membros deste perfil'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <Select
                          aria-label={`Nível de acesso de ${title}`}
                          value={item.access_level}
                          onChange={(event) => updateAccessLevel(item, event.target.value)}
                          options={accessOptions}
                          style={{ marginBottom: 0, width: 150, padding: '4px 8px', fontSize: 12.5 }}
                        />
                        <span className="badge badge-neutral" style={{ minWidth: 110, textAlign: 'center' }}>{accessLabel[item.access_level]}</span>
                        <Button size="sm" variant="danger" onClick={() => setDeletingPerm(item)}>Remover</Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </Modal>

      {deletingPerm && (
        <ConfirmDialog
          isOpen
          title="Remover acesso"
          message={`Deseja remover o acesso de "${deletingPerm.user_id ? personName(deletingPerm) : roleName(deletingPerm)}" deste quadro?`}
          confirmText="Sim, remover"
          cancelText="Cancelar"
          onConfirm={handleDeleteAccess}
          onClose={() => setDeletingPerm(null)}
          variant="danger"
        />
      )}
    </>
  );
};
