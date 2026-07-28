import React, { useState } from 'react';
import { Send, Zap, X } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useActionCommands, ActionCommandDraft } from '../../hooks/useActionCommands';
import { ActionCommandCard } from './ActionCommandCard';

interface ActionCommandInputProps {
  onActionSuccess?: (draft: ActionCommandDraft) => void;
  context?: any;
  placeholder?: string;
  className?: string;
}

export const ActionCommandInput: React.FC<ActionCommandInputProps> = ({
  onActionSuccess,
  context = {},
  placeholder = 'O que você quer fazer hoje? (ex: cotar 5 chapas inox...)',
  className = ''
}) => {
  const { parseCommand, confirmCommand, cancelCommand, loading } = useActionCommands();
  const [text, setText] = useState('');
  const [activeDraft, setActiveDraft] = useState<ActionCommandDraft | null>(null);
  const [showCard, setShowCard] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || loading) return;

    try {
      const draft = await parseCommand(text, 'global_bar', context);
      setActiveDraft(draft);
      setShowCard(true);
      setText(''); // limpa input
    } catch (e) {
      console.error('Erro ao analisar comando:', e);
    }
  };

  const handleConfirm = async (draftId: string, overrideData?: any): Promise<ActionCommandDraft> => {
    const result = await confirmCommand(draftId, overrideData);
    setActiveDraft(result);
    if (result.status === 'EXECUTED' && onActionSuccess) {
      onActionSuccess(result);
    }
    return result;
  };

  const handleCancel = async (draftId: string): Promise<ActionCommandDraft> => {
    const result = await cancelCommand(draftId);
    setActiveDraft(null);
    setShowCard(false);
    return result;
  };

  return (
    <div className={`relative w-full max-w-xl ${className}`}>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-grow">
          <span className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
            <Zap size={14} className="text-blue-400" />
          </span>
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={placeholder}
            className="pl-9 pr-4 bg-gray-950 border-gray-800 text-gray-100 placeholder-gray-500 rounded-xl focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-xs w-full py-2.5 h-auto transition-all"
            disabled={loading}
          />
          {text && (
            <button
              type="button"
              onClick={() => setText('')}
              className="absolute inset-y-0 right-3 flex items-center text-gray-500 hover:text-gray-300"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <Button
          type="submit"
          disabled={loading || !text.trim()}
          className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-4 flex items-center justify-center shrink-0 border border-blue-500/20"
        >
          {loading ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Send size={13} />
          )}
        </Button>
      </form>

      {/* Action Preview Card Overlay */}
      {showCard && activeDraft && (
        <div className="absolute left-0 right-0 mt-3 z-50">
          <div className="relative">
            {/* Backdrop clear button to close */}
            <button
              onClick={() => setShowCard(false)}
              className="absolute -top-3 -right-3 bg-gray-900 border border-gray-800 text-gray-400 hover:text-gray-200 rounded-full p-1 shadow-lg z-50"
            >
              <X size={12} />
            </button>
            <ActionCommandCard
              draft={activeDraft}
              onConfirm={handleConfirm}
              onCancel={handleCancel}
              onSuccess={(res) => {
                if (res.status === 'EXECUTED' || res.status === 'FAILED' || res.status === 'APPROVAL_REQUIRED') {
                  // Keep card open to show results, but invoke callback if it succeeded
                  if (res.status === 'EXECUTED' && onActionSuccess) {
                    onActionSuccess(res);
                  }
                }
              }}
              isAdmin={false}
            />
          </div>
        </div>
      )}
    </div>
  );
};
export default ActionCommandInput;
