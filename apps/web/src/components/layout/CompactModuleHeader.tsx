import React from 'react';

interface CompactModuleHeaderProps {
  icon?: React.ReactNode;
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  meta?: React.ReactNode;
}

export const CompactModuleHeader: React.FC<CompactModuleHeaderProps> = ({
  icon,
  eyebrow,
  title,
  description,
  actions,
  meta,
}) => (
  <header className="focus-compact-header">
    <div className="focus-compact-header__main">
      {icon && <span className="focus-compact-header__icon">{icon}</span>}
      <div className="focus-compact-header__copy">
        {eyebrow && <span className="focus-compact-header__eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
        {meta && <div className="focus-compact-header__meta">{meta}</div>}
      </div>
    </div>
    {actions && <div className="focus-compact-header__actions">{actions}</div>}
  </header>
);

export default CompactModuleHeader;
