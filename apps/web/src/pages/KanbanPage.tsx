import React, { useEffect, useState } from 'react';
import { Plus, RefreshCw, Kanban, Archive, Tv } from 'lucide-react';
import { KanbanBoardView } from '../components/kanban/KanbanBoardView';
import { apiJson } from '../components/kanban/kanbanApi';
import { CurrentUser, KanbanBoard } from '../components/kanban/types';
import { ModuleHero } from '../components/ui/ModuleHero';
import { FooterStatusBar } from '../components/ui/FooterStatusBar';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { Checkbox } from '../components/ui/Checkbox';
import { BoardSwitcher } from '../components/kanban/BoardSwitcher';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { getQueryNumber, replaceQueryParams } from '../utils/urlState';

interface KanbanPageProps {
  currentUser: CurrentUser;
  onNavigate?: (
    moduleCode: string,
    options?: { search?: Record<string, string | number | boolean | undefined | null> | URLSearchParams | string }
  ) => void;
}

export const KanbanPage: React.FC<KanbanPageProps> = ({ currentUser, onNavigate }) => {
  const [boards, setBoards] = useState<KanbanBoard[]>([]);
  const [selectedBoard, setSelectedBoard] = useState<KanbanBoard | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newBoardName, setNewBoardName] = useState('');
  const [newBoardDescription, setNewBoardDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchBoards = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiJson<KanbanBoard[]>(`/api/v1/kanban/boards?include_archived=${includeArchived}`);
      setBoards(data);
      if (selectedBoard) {
        const refreshed = data.find((board) => board.id === selectedBoard.id);
        if (refreshed) setSelectedBoard(refreshed);
      }
    } catch (err: any) {
      setError(err.message || 'Falha ao carregar quadros do Kanban.');
    } finally {
      setLoading(false);
    }
  };

  const fetchBoardDetail = async (boardId: number, options: { updateUrl?: boolean } = { updateUrl: true }) => {
    setLoading(true);
    try {
      const board = await apiJson<KanbanBoard>(`/api/v1/kanban/boards/${boardId}`);
      setSelectedBoard(board);
      if (options.updateUrl !== false) {
        replaceQueryParams({ board: boardId });
      }
    } catch (err: any) {
      setError(err.message || 'Você não tem acesso a este quadro.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBoards();
  }, [includeArchived]);

  useEffect(() => {
    const pending = localStorage.getItem('vesper.kanban.openBoardId');
    if (pending) {
      localStorage.removeItem('vesper.kanban.openBoardId');
      fetchBoardDetail(Number(pending));
      return;
    }
    const boardId = getQueryNumber('board');
    if (boardId) {
      fetchBoardDetail(boardId, { updateUrl: false });
    }
  }, []);

  useEffect(() => {
    if (!selectedBoard) return;
    let closed = false;
    let retryTimer: number | undefined;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = new WebSocket(`${protocol}://${window.location.host}/api/v1/ws/kanban?board_id=${selectedBoard.id}`);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'kanban_event' && !closed) {
          window.clearTimeout(retryTimer);
          retryTimer = window.setTimeout(() => fetchBoardDetail(selectedBoard.id), 450);
        }
      } catch {
        /* noop */
      }
    };
    socket.onerror = () => {
      window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(() => fetchBoardDetail(selectedBoard.id), 5000);
    };
    return () => {
      closed = true;
      window.clearTimeout(retryTimer);
      socket.close();
    };
  }, [selectedBoard?.id]);

  const handleCreateBoardSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newBoardName.trim()) return;
    setIsSubmitting(true);
    try {
      const board = await apiJson<KanbanBoard>('/api/v1/kanban/boards', {
        method: 'POST',
        body: JSON.stringify({ name: newBoardName, description: newBoardDescription || undefined, preset: 'custom' }),
      });
      setNewBoardName('');
      setNewBoardDescription('');
      setCreateModalOpen(false);
      await fetchBoards();
      setSelectedBoard(board);
      replaceQueryParams({ board: board.id, card: null });
    } catch (err: any) {
      setError(err.message || 'Não foi possível criar o quadro.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const [archiveConfirmOpen, setArchiveConfirmOpen] = useState(false);

  const proceedArchiveBoard = async (restore: boolean) => {
    if (!selectedBoard) return;
    try {
      const board = await apiJson<KanbanBoard>(`/api/v1/kanban/boards/${selectedBoard.id}/${restore ? 'restore' : 'archive'}`, { method: 'POST' });
      setSelectedBoard(board);
      await fetchBoards();
    } catch (err: any) {
      setError(err.message || 'Não foi possível arquivar o quadro.');
    }
  };

  const archiveBoard = async (restore = false) => {
    if (!selectedBoard) return;
    if (!restore) {
      setArchiveConfirmOpen(true);
    } else {
      await proceedArchiveBoard(true);
    }
  };

  const getBoardStats = (board: KanbanBoard) => {
    let openCards = 0;
    let overdueCards = 0;
    const assignees = new Set<string>();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    board.columns?.forEach((col) => {
      if (col.is_archived || col.is_done_column) return;
      col.cards?.forEach((card) => {
        if (card.is_archived) return;
        openCards++;
        if (card.due_date) {
          const dueDate = new Date(card.due_date);
          dueDate.setHours(0, 0, 0, 0);
          if (dueDate < today) overdueCards++;
        }
        card.assignees?.forEach((ass) => {
          if (ass.user?.username) assignees.add(ass.user.username);
        });
      });
    });

    return { openCards, overdueCards, assigneesCount: assignees.size };
  };

  return (
    <div className="kanban-page module-page">
      {!selectedBoard && (
        <ModuleHero
          icon={<Kanban size={28} />}
          title="Kanban"
          description="Acompanhe tarefas, produção e pendências em quadros visuais."
          compact={true}
          showKoda={false}
          actions={
            <>
              {currentUser.role === 'ADMIN' && onNavigate && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    onNavigate('admin', { search: { tab: 'permissions', subtab: 'kanban' } });
                  }}
                >
                  Permissões na Administração
                </Button>
              )}
              <Button variant="secondary" size="sm" onClick={fetchBoards} leftIcon={<RefreshCw size={16} className={loading ? 'spin-anim' : ''} />}>
                Atualizar
              </Button>
              <Button variant="primary" size="sm" onClick={() => setCreateModalOpen(true)} leftIcon={<Plus size={16} />}>
                Novo quadro
              </Button>
            </>
          }
        />
      )}

      {error && <ErrorState message={error} onRetry={fetchBoards} />}

      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, height: '100%' }}>
        {loading && !selectedBoard ? (
          <LoadingState text="Carregando quadros..." />
        ) : selectedBoard ? (
          <KanbanBoardView
            board={selectedBoard}
            onReload={() => fetchBoardDetail(selectedBoard.id, { updateUrl: false })}
            onArchiveBoard={archiveBoard}
            currentUser={currentUser}
            boards={boards}
            includeArchived={includeArchived}
            onIncludeArchivedChange={setIncludeArchived}
            onSelectBoard={(boardId) => fetchBoardDetail(boardId)}
            onBackToBoards={() => {
              setSelectedBoard(null);
              replaceQueryParams({ board: null, card: null, view: null });
            }}
          />
        ) : (
          <div>
            {boards.length === 0 ? (
              <EmptyState
                icon={<Kanban size={48} />}
                title="Nenhum quadro ainda"
                description="Crie um quadro para organizar tarefas e acompanhar a produção."
                actionText="Criar quadro"
                onAction={() => setCreateModalOpen(true)}
              />
            ) : (
              <div>
                <div className="kanban-board-picker-header">
                  <h3>Selecione um Quadro de Trabalho</h3>
                  <Checkbox label="Exibir quadros arquivados" checked={includeArchived} onChange={(e) => setIncludeArchived(e.currentTarget.checked)} style={{ marginBottom: 0 }} />
                </div>
                <div className="kanban-boards-grid">
                  {boards.map((board) => {
                    const stats = getBoardStats(board);
                    return (
                      <Card
                        key={board.id}
                        variant="interactive"
                        className="kanban-board-picker-card"
                      >
                        <div className="kanban-board-picker-card__content">
                          <div className="flex justify-between items-start">
                            <h3 className="kanban-board-picker-card__title">{board.name}</h3>
                            {board.is_archived && (
                              <span className="kanban-board-picker-card__badge">
                                Arquivado
                              </span>
                            )}
                          </div>
                          <p className="kanban-board-picker-card__description">
                            {board.description ? (
                              board.description
                            ) : (
                              <span className="kanban-board-picker-card__description-empty">Quadro sem descrição cadastrada</span>
                            )}
                          </p>
                        </div>

                        <div className="kanban-board-picker-card__footer">
                          <div className="kanban-board-picker-card__stats">
                            <div className="kanban-board-picker-card__stat kanban-board-picker-card__stat--open">
                              <span className="kanban-board-picker-card__dot"></span>
                              <span>{stats.openCards} Abertos</span>
                            </div>
                            {stats.overdueCards > 0 && (
                              <div className="kanban-board-picker-card__stat kanban-board-picker-card__stat--overdue">
                                <span className="kanban-board-picker-card__dot"></span>
                                <span>{stats.overdueCards} Atrasados</span>
                              </div>
                            )}
                          </div>

                          <div className="kanban-board-picker-card__actions">
                            <Button
                              variant="primary"
                              size="sm"
                              className="kanban-board-picker-card__action"
                              onClick={() => fetchBoardDetail(board.id)}
                            >
                              Abrir quadro
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              leftIcon={<Tv size={14} />}
                              className="kanban-board-picker-card__action kanban-board-picker-card__action--tv"
                              onClick={() => window.open(`/kanban/tv/${board.id}?mode=external`, '_blank')}
                            >
                              Modo TV
                            </Button>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <FooterStatusBar
        items={[
          'Dados exibidos a partir do backend local',
          'Ambiente de produção',
          'Nenhum card usa pendências simuladas',
          'Variação 5 • Premium Dark Glass',
        ]}
      />

      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Criar novo quadro"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setCreateModalOpen(false)} disabled={isSubmitting}>
              Cancelar
            </Button>
            <Button variant="primary" onClick={handleCreateBoardSubmit} isLoading={isSubmitting}>
              Criar quadro
            </Button>
          </>
        }
      >
        <form onSubmit={handleCreateBoardSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Input label="Nome do quadro" value={newBoardName} onChange={(e) => setNewBoardName(e.currentTarget.value)} required />
          <Textarea label="Descrição" value={newBoardDescription} onChange={(e) => setNewBoardDescription(e.currentTarget.value)} rows={3} />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={archiveConfirmOpen}
        onClose={() => setArchiveConfirmOpen(false)}
        onConfirm={async () => {
          setArchiveConfirmOpen(false);
          await proceedArchiveBoard(false);
        }}
        title="Arquivar Quadro"
        message="Deseja arquivar este quadro? Todos os dados serão preservados."
        confirmText="Arquivar"
        cancelText="Cancelar"
        variant="warning"
      />
    </div>
  );
};

export default KanbanPage;
