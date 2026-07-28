import React, { useCallback, useEffect, useState } from 'react';
import { Paperclip, Send, Ticket, UploadCloud, X } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Select } from '../ui/Select';
import { Textarea } from '../ui/Textarea';
import { categoryOptions, itRequest, ITTicket } from './itApi';

interface CreateTicketModalProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (ticket: ITTicket) => void;
}

export const CreateTicketModal: React.FC<CreateTicketModalProps> = ({ open, onClose, onCreated }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('OUTRO');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    setFiles((current) => {
      const next = [...current];
      Array.from(incoming).forEach((file) => {
        if (!next.some((existing) => existing.name === file.name && existing.size === file.size)) {
          next.push(file);
        }
      });
      return next;
    });
  }, []);

  useEffect(() => {
    if (!open) return;
    const onPaste = (event: ClipboardEvent) => {
      const pasted = Array.from(event.clipboardData?.files || []);
      if (pasted.length) {
        addFiles(pasted);
      }
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  }, [open, addFiles]);

  const reset = () => {
    setTitle('');
    setDescription('');
    setCategory('OUTRO');
    setFiles([]);
    setError('');
  };

  const submit = async () => {
    if (!title.trim() || !description.trim()) {
      setError('Informe um titulo e descreva o problema.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const ticket = await itRequest<ITTicket>('/tickets', {
        method: 'POST',
        body: JSON.stringify({ title, description, category }),
      });
      for (const file of files) {
        const form = new FormData();
        form.append('upload', file);
        await itRequest(`/tickets/${ticket.id}/attachments`, { method: 'POST', body: form });
      }
      reset();
      onCreated?.(ticket);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Nao foi possivel abrir o chamado.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      title="Abrir chamado de TI"
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button onClick={submit} isLoading={saving} leftIcon={<Send size={16} />}>Enviar chamado</Button>
        </>
      }
    >
      <div className="it-ticket-form">
        <div className="it-ticket-form-intro">
          <Ticket size={22} />
          <div>
            <strong>Conte o problema de forma simples.</strong>
            <span>A prioridade sera definida pela TI. Voce pode colar print com Ctrl+V, arrastar arquivo ou selecionar do computador.</span>
          </div>
        </div>
        <Input label="Titulo" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ex: Internet caindo no setor de producao" />
        <Select label="Categoria" value={category} onChange={(event) => setCategory(event.target.value)} options={categoryOptions} />
        <Textarea label="O que está acontecendo?" value={description} onChange={(event) => setDescription(event.target.value)} rows={5} placeholder="Explique o problema de forma simples: quando começou, o que você estava fazendo e quem foi afetado." />
        <div
          className="it-dropzone"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            addFiles(event.dataTransfer.files);
          }}
        >
          <UploadCloud size={22} />
          <span>Arraste arquivos aqui, cole print com Ctrl+V ou selecione manualmente.</span>
          <label className="btn btn-secondary btn-sm">
            <span className="btn-text"><Paperclip size={14} /> Selecionar arquivo</span>
            <input type="file" multiple hidden onChange={(event) => event.target.files && addFiles(event.target.files)} />
          </label>
        </div>
        {files.length > 0 && (
          <div className="it-attachment-list">
            {files.map((file) => (
              <span key={`${file.name}-${file.size}`} className="it-attachment-chip">
                {file.name}
                <button type="button" onClick={() => setFiles((current) => current.filter((item) => item !== file))}>
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        {error && <div className="form-error-banner">{error}</div>}
      </div>
    </Modal>
  );
};
