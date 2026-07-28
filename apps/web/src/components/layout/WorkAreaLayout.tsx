import React from 'react';

interface WorkAreaLayoutProps {
  sidebar?: React.ReactNode;
  children: React.ReactNode;
  details?: React.ReactNode;
  detailsOpen?: boolean;
  className?: string;
}

export const WorkAreaLayout: React.FC<WorkAreaLayoutProps> = ({
  sidebar,
  children,
  details,
  detailsOpen = false,
  className = '',
}) => (
  <section
    className={[
      'focus-work-area',
      sidebar ? 'focus-work-area--with-sidebar' : '',
      details && detailsOpen ? 'focus-work-area--with-details' : '',
      className,
    ].filter(Boolean).join(' ')}
  >
    {sidebar && <aside className="focus-work-area__sidebar">{sidebar}</aside>}
    <main className="focus-work-area__main">{children}</main>
    {details && detailsOpen && <aside className="focus-work-area__details">{details}</aside>}
  </section>
);

export default WorkAreaLayout;
