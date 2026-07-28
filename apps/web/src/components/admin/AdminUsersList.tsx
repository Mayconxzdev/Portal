import React, { useEffect, useMemo, useState } from 'react';
import { Search, Shield } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Badge } from '../ui/Badge';
import { UserItem } from './types';

interface AdminUsersListProps {
  users: UserItem[];
  filteredUsers: UserItem[];
  userSearch: string;
  setUserSearch: (val: string) => void;
  userFilterRole: string;
  setUserFilterRole: (val: string) => void;
  userFilterStatus: string;
  setUserFilterStatus: (val: string) => void;
  currentUser: any;
  onEditClick: (user: UserItem) => void;
  onToggleClick: (user: UserItem) => void;
  onDeleteClick: (user: UserItem) => void;
  loading: boolean;
}

const humanizeRole = (role: string | null) => {
  if (!role) return 'Sem papel';
  const dict: Record<string, string> = {
    'ADMIN': 'Administrador',
    'USER': 'Usuário',
    'COLLABORATOR': 'Colaborador',
    'APPROVER': 'Aprovador',
    'IT_TECH': 'Técnico de TI',
    'IT_ADMIN': 'Administrador de TI',
    'MESSIAS': 'Messias',
    'PURCHASER': 'Comprador',
    'SALES': 'Vendedor',
    'MANAGER': 'Gerente',
  };
  return dict[role.toUpperCase()] || role;
};

const moduleAccessSummary = (user: UserItem) => {
  const visible = user.module_permissions
    .filter((permission) => permission.module_code !== 'chat' && permission.permission_level !== 'NO_ACCESS')
    .slice(0, 3)
    .map((permission) => permission.module_name);

  if (visible.length === 0) return 'Apenas Chat global';
  return `${visible.join(', ')}${visible.length < user.module_permissions.length ? ' e mais' : ''}`;
};

const userInitials = (user: UserItem) => {
  const base = user.full_name || user.username;
  const parts = base.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part.charAt(0).toUpperCase()).join('');
};

export const AdminUsersList: React.FC<AdminUsersListProps> = ({
  users,
  filteredUsers,
  userSearch,
  setUserSearch,
  userFilterRole,
  setUserFilterRole,
  userFilterStatus,
  setUserFilterStatus,
  currentUser,
  onEditClick,
  onToggleClick,
  onDeleteClick,
  loading,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 6;

  const roleOptions = useMemo(() => {
    const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
    const roleNames = Array.from(
      new Set(
        users
          .map((user) => user.role_name)
          .filter((roleName): roleName is string => Boolean(roleName) && (isCurrentUserMessias || roleName !== 'MESSIAS')),
      ),
    );
    return roleNames
      .sort((a, b) => humanizeRole(a).localeCompare(humanizeRole(b), 'pt-BR'))
      .map((roleName) => ({ value: roleName, label: humanizeRole(roleName) }));
  }, [users, currentUser]);

  useEffect(() => {
    setCurrentPage(1);
  }, [userSearch, userFilterRole, userFilterStatus]);

  useEffect(() => {
    if (userFilterRole !== 'ALL' && !roleOptions.some((option) => option.value === userFilterRole)) {
      setUserFilterRole('ALL');
    }
  }, [roleOptions, setUserFilterRole, userFilterRole]);

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const paginatedUsers = filteredUsers.slice(startIndex, startIndex + pageSize);
  const visibleStart = filteredUsers.length === 0 ? 0 : startIndex + 1;
  const visibleEnd = Math.min(startIndex + pageSize, filteredUsers.length);

  return (
    <div className="admin-users-list-container">
      <div className="admin-users-list-header">
        <div>
          <h2>Usuários</h2>
          <p>Veja e gerencie os usuários do Portal.</p>
        </div>
      </div>

      <div className="admin-users-filters">
        <div className="admin-users-search">
          <Input
            name="admin-users-list-search"
            autoComplete="off"
            value={userSearch}
            onChange={(e) => setUserSearch(e.target.value)}
            placeholder="Buscar por nome, usuário, e-mail, função ou setor..."
            leftIcon={<Search size={16} />}
            style={{ marginBottom: 0 }}
          />
        </div>
        <div>
          <Select
            value={userFilterRole}
            onChange={(e) => setUserFilterRole(e.target.value)}
            style={{ marginBottom: 0 }}
            options={[
              { value: 'ALL', label: 'Todos os perfis' },
              ...roleOptions,
            ]}
          />
        </div>
        <div>
          <Select
            value={userFilterStatus}
            onChange={(e) => setUserFilterStatus(e.target.value)}
            style={{ marginBottom: 0 }}
            options={[
              { value: 'ALL', label: 'Todos os status' },
              { value: 'ACTIVE', label: 'Ativos' },
              { value: 'INACTIVE', label: 'Inativos' },
            ]}
          />
        </div>
      </div>

      {loading && users.length === 0 ? (
        <div className="admin-empty-state">Carregando usuários...</div>
      ) : filteredUsers.length === 0 ? (
        <div className="admin-empty-state">
          Nenhum usuário encontrado.
        </div>
      ) : (
        <div className="admin-user-card-stack">
          {paginatedUsers.map((user) => {
            const isMessias = user.role_name === 'MESSIAS';
            const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
            const canModify = !isMessias || isCurrentUserMessias;

            return (
              <article
                key={user.id}
                className="admin-user-card"
              >
                <button type="button" className="admin-user-card-main" onClick={() => onEditClick(user)}>
                  <span className="admin-user-avatar">{userInitials(user)}</span>
                  <span className="admin-user-card-copy">
                    <span className="admin-user-card-title">
                      <strong>{user.full_name || user.username}</strong>
                      <Badge variant={user.is_active ? 'success' : 'neutral'}>
                        {user.is_active ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </span>
                    <span className="admin-user-card-meta">
                      <span>{user.username}</span>
                      <span>{user.email || 'Sem e-mail cadastrado'}</span>
                    </span>
                    <span className="admin-user-card-role">
                      <Shield size={11} />
                      <span>{humanizeRole(user.role_name)}</span>
                      {user.department && <span>{user.department}</span>}
                    </span>
                  </span>
                </button>

                <div className="admin-user-card-side">
                  <span>{moduleAccessSummary(user)}</span>
                  <div className="admin-user-card-actions">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEditClick(user)}
                    >
                      Editar
                    </Button>
                    {canModify && (
                      <>
                        <Button
                          variant={user.is_active ? 'ghost' : 'success'}
                          size="sm"
                          onClick={() => onToggleClick(user)}
                          className={user.is_active ? 'admin-text-danger' : undefined}
                        >
                          {user.is_active ? 'Inativar' : 'Ativar'}
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => onDeleteClick(user)}
                        >
                          Excluir
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
          <div className="admin-users-pagination" aria-label="Paginação de usuários">
            <span>
              {visibleStart}-{visibleEnd} de {filteredUsers.length} usuários
            </span>
            {totalPages > 1 && (
              <div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                  disabled={safePage === 1}
                >
                  Anterior
                </Button>
                {Array.from({ length: totalPages }).map((_, index) => {
                  const pageNumber = index + 1;
                  return (
                    <button
                      key={pageNumber}
                      type="button"
                      className={safePage === pageNumber ? 'is-active' : ''}
                      onClick={() => setCurrentPage(pageNumber)}
                      aria-current={safePage === pageNumber ? 'page' : undefined}
                    >
                      {pageNumber}
                    </button>
                  );
                })}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                  disabled={safePage === totalPages}
                >
                  Próxima
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
