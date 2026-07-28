import React, { useEffect, useRef, useState } from 'react';
import { MoreVertical } from 'lucide-react';
import { AccessibleIconButton } from './AccessibleIconButton';

export interface ActionOverflowItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  tone?: 'default' | 'danger';
  disabled?: boolean;
  disabledReason?: string;
  onSelect: () => void;
}

interface ActionOverflowMenuProps {
  label?: string;
  items: ActionOverflowItem[];
  align?: 'left' | 'right';
}

export const ActionOverflowMenu: React.FC<ActionOverflowMenuProps> = ({
  label = 'Mais ações',
  items,
  align = 'right',
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, []);

  return (
    <div className="action-overflow" ref={ref}>
      <AccessibleIconButton
        label={label}
        icon={<MoreVertical size={18} />}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      />
      {open && (
        <div className={`action-overflow__menu action-overflow__menu--${align}`} role="menu">
          {items.map((item) => (
            <button
              key={item.key}
              type="button"
              role="menuitem"
              className={`action-overflow__item ${item.tone === 'danger' ? 'action-overflow__item--danger' : ''}`}
              disabled={item.disabled}
              title={item.disabled ? item.disabledReason : item.label}
              onClick={() => {
                if (item.disabled) return;
                setOpen(false);
                item.onSelect();
              }}
            >
              {item.icon && <span>{item.icon}</span>}
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActionOverflowMenu;
