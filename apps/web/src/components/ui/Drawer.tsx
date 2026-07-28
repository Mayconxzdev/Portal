import React, { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { IconButton } from './IconButton';

interface DrawerProps {
  open: boolean;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  onClose: () => void;
  className?: string;
  headerContent?: React.ReactNode;
}

export const Drawer: React.FC<DrawerProps> = ({ open, title, description, children, footer, onClose, className = '', headerContent }) => {
  const titleId = useId();
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    requestAnimationFrame(() => panelRef.current?.focus());
    return () => previousFocus?.focus();
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="drawer-overlay" role="presentation" onClick={onClose}>
      <aside
        ref={panelRef}
        className={`drawer-panel ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headerContent ? undefined : titleId}
        aria-label={headerContent ? title : undefined}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="drawer-header">
          {headerContent || (
            <div>
              <h2 id={titleId}>{title}</h2>
              {description && <p>{description}</p>}
            </div>
          )}
          <IconButton label="Fechar" icon={<X size={18} />} onClick={onClose} />
        </header>
        <div className="drawer-content">{children}</div>
        {footer && <footer className="drawer-footer">{footer}</footer>}
      </aside>
    </div>,
    document.body
  );
};

export default Drawer;
