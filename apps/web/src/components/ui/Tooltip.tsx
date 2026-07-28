import React, { useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { HelpCircle } from 'lucide-react';

export interface TooltipProps {
  text: string;
  children?: React.ReactNode;
  placement?: 'top' | 'bottom' | 'right' | 'left';
}

export const Tooltip: React.FC<TooltipProps> = ({ text, children, placement }) => {
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);
  const [position, setPosition] = useState<{ top: number; left: number; placement: 'top' | 'bottom' | 'right' | 'left' } | null>(null);

  const open = () => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;

    let top = 0;
    let left = 0;
    let finalPlacement = placement;

    if (!finalPlacement) {
      // Auto-placement com base no espaço vertical restante no topo
      finalPlacement = rect.top > 72 ? 'top' : 'bottom';
    }

    if (finalPlacement === 'right') {
      left = rect.right + 8;
      top = rect.top + rect.height / 2;
    } else if (finalPlacement === 'left') {
      left = rect.left - 8;
      top = rect.top + rect.height / 2;
    } else if (finalPlacement === 'bottom') {
      // Evita vazamentos nas bordas horizontais da tela
      left = Math.min(Math.max(rect.left + rect.width / 2, 120), window.innerWidth - 120);
      top = rect.bottom + 8;
    } else { // top
      // Evita vazamentos nas bordas horizontais da tela
      left = Math.min(Math.max(rect.left + rect.width / 2, 120), window.innerWidth - 120);
      top = rect.top - 8;
    }

    setPosition({ top, left, placement: finalPlacement });
  };

  return (
    <span
      ref={ref}
      className="tooltip-container"
      aria-describedby={position ? id : undefined}
      onMouseEnter={open}
      onFocus={open}
      onMouseLeave={() => setPosition(null)}
      onBlur={() => setPosition(null)}
    >
      {children || <HelpCircle className="tooltip-trigger-icon" />}
      {position && createPortal(
        <span
          id={id}
          role="tooltip"
          className={`tooltip-box tooltip-box-portal tooltip-${position.placement}`}
          style={{ top: position.top, left: position.left }}
        >
          {text}
        </span>,
        document.body
      )}
    </span>
  );
};
