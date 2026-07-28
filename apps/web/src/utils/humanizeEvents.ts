export const humanizeEventAction = (action?: string) => {
  if (!action) return 'Evento registrado';

  const normalized = action.replace(/_/g, '.').toLowerCase();
  const labels: Record<string, string> = {
    'board.created': 'Quadro criado',
    'board.updated': 'Quadro atualizado',
    'board.archived': 'Quadro arquivado',
    'board.restored': 'Quadro restaurado',
    'card.created': 'Card criado',
    'card.updated': 'Card atualizado',
    'card.moved': 'Card movido',
    'card.archived': 'Card arquivado',
    'card.restored': 'Card restaurado',
    'card.duplicated': 'Card duplicado',
    'column.created': 'Coluna criada',
    'column.updated': 'Coluna atualizada',
    'column.reordered': 'Coluna reordenada',
    'label.created': 'Etiqueta criada',
    'label.updated': 'Etiqueta atualizada',
    'label.applied': 'Etiqueta aplicada',
    'label.removed': 'Etiqueta removida',
    'custom.field.created': 'Campo personalizado criado',
    'custom.field.updated': 'Campo personalizado atualizado',
    'custom.field.disabled': 'Campo personalizado desativado',
    'custom_field.created': 'Campo personalizado criado',
    'custom_field.updated': 'Campo personalizado atualizado',
    'custom_field.disabled': 'Campo personalizado desativado',
    'tv.config.updated': 'Configuração do Modo TV atualizada',
    'tv_config.updated': 'Configuração do Modo TV atualizada',
    'view.updated': 'Visualização atualizada',
    'view.default.changed': 'Visualização padrão alterada',
    'view.default_changed': 'Visualização padrão alterada',
    'import.previewed': 'Importação pré-visualizada',
    'attachment.uploaded': 'Anexo enviado',
    'attachment.deleted': 'Anexo removido',
    'comment.created': 'Comentário criado',
    'comment.updated': 'Comentário atualizado',
    'checklist.created': 'Checklist criado',
    'checklist.item.checked': 'Item de checklist concluído',
    'checklist.item.unchecked': 'Item de checklist reaberto',
    'assignee.added': 'Responsável adicionado',
    'assignee.removed': 'Responsável removido',
  };

  return labels[action] || labels[normalized] || action
    .split(/[._]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

export const humanizeEntityType = (type?: string) => {
  const labels: Record<string, string> = {
    board: 'Quadro',
    card: 'Card',
    column: 'Coluna',
    label: 'Etiqueta',
    custom_field: 'Campo personalizado',
    tv_config: 'Modo TV',
    view: 'Visualização',
    import: 'Importação',
    ticket: 'Chamado',
    asset: 'Ativo',
    credential: 'Credencial',
    certificate: 'Certificado',
    user: 'Usuário',
  };
  return type ? labels[type] || humanizeEventAction(type) : 'Registro';
};
