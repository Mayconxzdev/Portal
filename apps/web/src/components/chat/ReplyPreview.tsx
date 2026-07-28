import React from 'react';
import { X } from 'lucide-react';
import { AccessibleIconButton } from '../ui/AccessibleIconButton';

interface ReplyPreviewProps {
  message: any;
  onCancel: () => void;
}

export const ReplyPreview: React.FC<ReplyPreviewProps> = ({ message, onCancel }) => (
  <div className="reply-preview">
    <div>
      <strong>Respondendo {message.sender_username || 'mensagem'}</strong>
      <p>{message.body || 'Mensagem sem texto'}</p>
    </div>
    <AccessibleIconButton label="Cancelar resposta" icon={<X size={14} />} onClick={onCancel} />
  </div>
);

export default ReplyPreview;
