import React, { useEffect, useMemo, useState } from 'react';
import { Save, Search, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { humanizeApiError } from '../../lib/apiErrors';

interface UserOption {
  id: number;
  username: string;
  email?: string | null;
  role_name?: string | null;
}

interface BoardOption {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  is_archived: boolean;
}

interface BoardPermissionItem {
  board_id: number;
  board_name: string;
  board_slug: string;
  access_level: string;
  permission_id?: number | null;
}

interface PermissionMatrix {
  user_id: number;
  username: string;
  email?: string | null;
  role_name?: string | null;
  permissions: BoardPermissionItem[];
}

const accessOptions = [
  { value: 'NO_ACCESS', label: 'Sem acesso' },
  { value: 'READ_ONLY', label: 'Somente leitura' },
  { value: 'NORMAL', label: 'Uso normal' },
  { value: 'MANAGER', label: 'Gestor' },
  { value: 'ADMIN', label: 'Admin' },
];

const accessLabels: Record<string, string> = Object.fromEntries(accessOptions.map((item) => [item.value, item.label]));
const displayEmail = (email?: string | null) => email || 'E-mail nao informado';

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(humanizeApiError(data, 'Nao foi possivel concluir a operacao.', response.status));
  return data as T;
}

export const AdminKanbanPermissions: React.FC = () => {
  const [query, setQuery] = useState('');
  const [users, setUsers] = useState<UserOption[]>([]);
  const [boards, setBoards] = useState<BoardOption[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserOption | null>(null);
  const [matrix, setMatrix] = useState<PermissionMatrix | null>(null);
  const [boardFilter, setBoardFilter] = useState('ALL');
  const [levelFilter, setLevelFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const searchUsers = async (term = query) => {
    setError(null);
    setUsers(await api<UserOption[]>(`/api/v1/admin/users/search?q=${encodeURIComponent(term)}`));
  };

  const loadBoards = async () => {
    setBoards(await api<BoardOption[]>('/api/v1/admin/kanban/boards'));
  };

  const loadMatrix = async (user: UserOption) => {
    setLoading(true);
    setError(null);
    try {
      setMatrix(await api<PermissionMatrix>(`/api/v1/admin/kanban/board-permissions?user_id=${user.id}`));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBoards().catch((err) => setError(err.message));
    searchUsers('').catch((err) => setError(err.message));
  }, []);

  const chooseUser = async (user: UserOption) => {
    setSelectedUser(user);
    setMessage(null);
    await loadMatrix(user);
  };

  const updateLevel = (boardId: number, accessLevel: string) => {
    if (!matrix) return;
    setMatrix({
      ...matrix,
      permissions: matrix.permissions.map((item) => item.board_id === boardId ? { ...item, access_level: accessLevel } : item),
    });
  };

  const applyAll = (level: string) => {
    if (!matrix) return;
    setMatrix({ ...matrix, permissions: matrix.permissions.map((item) => ({ ...item, access_level: level })) });
  };

  const applyOnly = (boardId: number) => {
    if (!matrix) return;
    setMatrix({
      ...matrix,
      permissions: matrix.permissions.map((item) => ({ ...item, access_level: item.board_id === boardId ? 'NORMAL' : 'NO_ACCESS' })),
    });
  };

  const save = async () => {
    if (!matrix) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await api<PermissionMatrix>('/api/v1/admin/kanban/board-permissions/bulk', {
        method: 'PUT',
        body: JSON.stringify({
          user_id: matrix.user_id,
          permissions: matrix.permissions.map((item) => ({ board_id: item.board_id, access_level: item.access_level })),
        }),
      });
      setMatrix(saved);
      setMessage('Permissoes dos quadros salvas com sucesso.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredPermissions = useMemo(() => {
    if (!matrix) return [];
    return matrix.permissions.filter((item) => {
      if (boardFilter !== 'ALL' && String(item.board_id) !== boardFilter) return false;
      if (levelFilter !== 'ALL' && item.access_level !== levelFilter) return false;
      return true;
    });
  }, [matrix, boardFilter, levelFilter]);

  return (
    <div style={{ display: 'grid', gap: 18 }}>
      <Card variant="glass" style={{ padding: 18 }}>
        <h3 style={{ color: 'var(--admin-title)', margin: '0 0 6px' }}>Permissoes por Kanban / Quadros</h3>
        <p style={{ color: 'var(--admin-muted)', margin: '0 0 16px' }}>
          Escolha um usuario e defina quais quadros ele pode ver ou editar. A permissao do modulo Kanban continua controlando se o modulo aparece na sidebar.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, 1fr) auto', gap: 10, alignItems: 'end' }}>
          <Input label="Buscar usuario" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nome, usuario ou e-mail" leftIcon={<Search size={16} />} />
          <Button onClick={() => searchUsers()}>Buscar</Button>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
          {users.map((user) => (
            <button
              key={user.id}
              className={`tab-btn ${selectedUser?.id === user.id ? 'active' : ''}`}
              onClick={() => chooseUser(user)}
              style={{ border: '1px solid var(--border-color)', borderRadius: 8 }}
            >
              <strong>{user.username}</strong>
              <span style={{ marginLeft: 8, color: 'var(--admin-muted)' }}>{displayEmail(user.email)}</span>
            </button>
          ))}
          {users.length === 0 && <span className="text-muted">Nenhum usuario encontrado.</span>}
        </div>
      </Card>

      {error && <div className="admin-inline-alert admin-inline-alert--danger">{error}</div>}
      {message && <div className="admin-inline-alert admin-inline-alert--success">{message}</div>}

      {matrix && (
        <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: 18, borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <h3 style={{ color: 'var(--admin-title)', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                <ShieldCheck size={18} /> {matrix.username}
              </h3>
              <p style={{ color: 'var(--admin-muted)', margin: '4px 0 0' }}>{displayEmail(matrix.email)}{matrix.role_name ? ` · ${matrix.role_name}` : ''}</p>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button size="sm" variant="secondary" onClick={() => applyAll('READ_ONLY')}>Todos como leitura</Button>
              <Button size="sm" variant="secondary" onClick={() => applyAll('NO_ACCESS')}>Remover todos</Button>
              <Button size="sm" onClick={save} disabled={loading} leftIcon={<Save size={14} />}>{loading ? 'Salvando...' : 'Salvar'}</Button>
            </div>
          </div>
          <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <Select label="Filtrar por quadro" value={boardFilter} onChange={(event) => setBoardFilter(event.target.value)} options={[
              { value: 'ALL', label: 'Todos os quadros' },
              ...boards.map((board) => ({ value: String(board.id), label: board.name })),
            ]} />
            <Select label="Filtrar por acesso" value={levelFilter} onChange={(event) => setLevelFilter(event.target.value)} options={[
              { value: 'ALL', label: 'Todos os acessos' },
              ...accessOptions,
            ]} />
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderTop: '1px solid var(--border-color)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={th}>Quadro</th>
                  <th style={th}>Acesso atual</th>
                  <th style={th}>Atalho</th>
                </tr>
              </thead>
              <tbody>
                {filteredPermissions.map((item) => (
                  <tr key={item.board_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={td}>
                      <strong style={{ color: 'var(--admin-title)' }}>{item.board_name}</strong>
                      <div style={{ color: 'var(--admin-muted)', fontSize: 12 }}>{item.board_slug}</div>
                    </td>
                    <td style={td}>
                      <Select
                        value={item.access_level}
                        onChange={(event) => updateLevel(item.board_id, event.target.value)}
                        options={accessOptions}
                        style={{ marginBottom: 0, minWidth: 180 }}
                      />
                      <span style={{ color: 'var(--admin-muted)', fontSize: 12 }}>{accessLabels[item.access_level]}</span>
                    </td>
                    <td style={td}>
                      <Button size="sm" variant="ghost" onClick={() => applyOnly(item.board_id)}>
                        Dar acesso so a este quadro
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

const th: React.CSSProperties = { textAlign: 'left', padding: 12, color: 'var(--admin-muted)', fontSize: 12, textTransform: 'uppercase' };
const td: React.CSSProperties = { padding: 12, color: 'var(--admin-secondary)', verticalAlign: 'middle' };
