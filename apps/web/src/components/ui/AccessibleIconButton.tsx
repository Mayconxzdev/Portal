import React from 'react';
import { Tooltip } from './Tooltip';

interface AccessibleIconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  icon: React.ReactNode;
  tone?: 'default' | 'primary' | 'danger' | 'success';
  tooltipPlacement?: 'top' | 'right' | 'bottom' | 'left';
}

export const AccessibleIconButton: React.FC<AccessibleIconButtonProps> = ({
  label,
  icon,
  tone = 'default',
  tooltipPlacement = 'top',
  className = '',
  type = 'button',
  ...props
}) => (
  <Tooltip text={label} placement={tooltipPlacement}>
    <button
      type={type}
      aria-label={label}
      title={label}
      className={`accessible-icon-button accessible-icon-button--${tone} ${className}`}
      {...props}
    >
      {icon}
    </button>
  </Tooltip>
);

export default AccessibleIconButton;
