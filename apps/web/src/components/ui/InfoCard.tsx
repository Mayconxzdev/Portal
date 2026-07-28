import React from 'react';

interface InfoCardProps {
  icon?: React.ReactNode;
  title: string;
  children: React.ReactNode;
  tone?: 'default' | 'info' | 'success' | 'warning' | 'danger';
}

export const InfoCard: React.FC<InfoCardProps> = ({ icon, title, children, tone = 'default' }) => (
  <section className={`info-card info-card-${tone}`}>
    {icon && <span className="info-card-icon">{icon}</span>}
    <div>
      <h3>{title}</h3>
      <div className="info-card-content">{children}</div>
    </div>
  </section>
);

export default InfoCard;
