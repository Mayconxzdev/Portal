import React, { useEffect, useState } from 'react';
import { ChevronDown, Play, Zap } from 'lucide-react';
import { Button } from '../ui/Button';
import { useActionCommands, AvailableAction, ActionCommandDraft } from '../../hooks/useActionCommands';

interface EntityQuickActionsProps {
  moduleName: string;
  entityType?: string;
  entityId?: string;
  initialData?: Record<string, any>;
  onActionPrepared: (draft: ActionCommandDraft) => void;
  variant?: 'buttons' | 'dropdown';
  className?: string;
}

export const EntityQuickActions: React.FC<EntityQuickActionsProps> = ({
  moduleName,
  entityType,
  entityId,
  initialData = {},
  onActionPrepared,
  variant = 'buttons',
  className = ''
}) => {
  const { fetchAvailableActions, prepareCommand, loading, error } = useActionCommands();
  const [actions, setActions] = useState<AvailableAction[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    let active = true;
    const loadActions = async () => {
      try {
        const available = await fetchAvailableActions(moduleName, entityType);
        if (active) {
          setActions(available);
        }
      } catch (e) {
        console.error('Erro ao buscar ações rápidas contextuais:', e);
      }
    };
    loadActions();
    return () => {
      active = false;
    };
  }, [moduleName, entityType, fetchAvailableActions]);

  const handleActionClick = async (actionKey: string) => {
    setDropdownOpen(false);
    try {
      // Une dados contextuais
      const mergedData = { ...initialData };
      if (entityType && entityId) {
        // Mapeia IDs conhecidos
        if (entityType === 'product_item') {
          mergedData.product_item_id = entityId;
        } else if (entityType === 'supplier') {
          mergedData.supplier_id = entityId;
        } else if (entityType === 'customer') {
          mergedData.customer_id = entityId;
        }
      }
      
      const draft = await prepareCommand(
        actionKey,
        'module_button',
        moduleName,
        entityType,
        entityId,
        mergedData
      );
      onActionPrepared(draft);
    } catch (e) {
      console.error('Erro ao preparar comando de ação:', e);
    }
  };

  if (actions.length === 0) return null;

  if (variant === 'dropdown') {
    return (
      <div className={`relative inline-block text-left ${className}`}>
        <Button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="bg-gray-900 border border-gray-800 text-gray-200 hover:bg-gray-800 flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg shadow-sm"
          disabled={loading}
        >
          <Zap size={13} className="text-blue-400" />
          Ações Rápidas
          <ChevronDown size={12} className="text-gray-500" />
        </Button>
        {dropdownOpen && (
          <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-xl shadow-2xl bg-[#0f111a] border border-gray-800 ring-1 ring-black ring-opacity-5 focus:outline-none z-50 overflow-hidden">
            <div className="py-1">
              {actions.map((act) => (
                <button
                  key={act.action_key}
                  onClick={() => handleActionClick(act.action_key)}
                  className="w-full text-left px-4 py-2.5 text-xs text-gray-300 hover:bg-gray-900 hover:text-white flex items-center gap-2 border-b border-gray-900 last:border-0 transition-colors"
                >
                  <Play size={10} className="text-blue-500 shrink-0" />
                  <div>
                    <div className="font-bold text-gray-200">{act.title}</div>
                    <div className="text-[10px] text-gray-500 leading-normal line-clamp-1">{act.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Buttons variant
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {actions.map((act) => (
        <Button
          key={act.action_key}
          onClick={() => handleActionClick(act.action_key)}
          disabled={loading}
          className="bg-[#121422] border border-blue-900/30 text-blue-300 hover:bg-blue-950/20 flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg shadow-sm transition-all duration-300"
        >
          <Zap size={11} className="text-blue-400 shrink-0" />
          {act.title}
        </Button>
      ))}
    </div>
  );
};
