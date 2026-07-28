import React from 'react';
import { Copy, Forward, MessageSquareReply, MoreVertical, Pencil, Pin, Trash2 } from 'lucide-react';
import { AccessibleIconButton } from '../ui/AccessibleIconButton';

interface MessageActionToolbarProps {
  canEdit?: boolean;
  canDelete?: boolean;
  onReply: () => void;
  onForward: () => void;
  onCopy: () => void;
  onEdit?: () => void;
  onDelete: () => void;
  onPin?: () => void;
}

export const MessageActionToolbar: React.FC<MessageActionToolbarProps> = ({
  canEdit = false,
  canDelete = false,
  onReply,
  onForward,
  onCopy,
  onEdit,
  onDelete,
  onPin,
}) => (
  <div className="message-action-toolbar" aria-label="Ações da mensagem">
    <AccessibleIconButton label="Responder" icon={<MessageSquareReply size={14} />} onClick={onReply} />
    <AccessibleIconButton label="Encaminhar" icon={<Forward size={14} />} onClick={onForward} />
    <AccessibleIconButton label="Copiar texto" icon={<Copy size={14} />} onClick={onCopy} />
    {onPin && <AccessibleIconButton label="Fixar mensagem" icon={<Pin size={14} />} onClick={onPin} />}
    {canEdit && onEdit && <AccessibleIconButton label="Editar mensagem" icon={<Pencil size={14} />} onClick={onEdit} />}
    {canDelete ? (
      <AccessibleIconButton label="Apagar mensagem" tone="danger" icon={<Trash2 size={14} />} onClick={onDelete} />
    ) : (
      <AccessibleIconButton label="Mais ações" icon={<MoreVertical size={14} />} disabled />
    )}
  </div>
);

export default MessageActionToolbar;
