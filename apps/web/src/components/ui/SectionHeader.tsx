import React from 'react';

interface SectionHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({ title, description, action }) => (
  <div className="section-header">
    <div>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
    </div>
    {action && <div className="section-header-action">{action}</div>}
  </div>
);

export default SectionHeader;
