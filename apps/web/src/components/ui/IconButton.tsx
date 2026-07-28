import React from 'react';

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  icon: React.ReactNode;
  variant?: 'default' | 'primary' | 'danger';
}

export const IconButton: React.FC<IconButtonProps> = ({
  label,
  icon,
  variant = 'default',
  className = '',
  type = 'button',
  ...props
}) => (
  <button
    type={type}
    aria-label={label}
    title={label}
    className={`icon-button icon-button-${variant} ${className}`}
    {...props}
  >
    {icon}
  </button>
);

export default IconButton;
