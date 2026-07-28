import React from 'react';
import { FooterStatusBar } from '../ui/FooterStatusBar';

export interface ModulePageLayoutProps {
  children: React.ReactNode;
  aside?: React.ReactNode;
  footerItems?: string[];
  className?: string;
}

const defaultFooter = [
  'Dados exibidos a partir do backend local',
  'Ambiente de produção',
  'Nenhum card usa pendências simuladas',
  'Variação 5 • Premium Dark Glass',
];

export const ModulePageLayout: React.FC<ModulePageLayoutProps> = ({
  children,
  aside,
  footerItems = defaultFooter,
  className = '',
}) => (
  <div className={`module-page ${className}`.trim()}>
    <div className={aside ? 'module-page-body module-page-body--with-aside' : 'module-page-body'}>
      <div className="module-page-main">{children}</div>
      {aside && <aside className="module-page-aside">{aside}</aside>}
    </div>
    <FooterStatusBar items={footerItems} />
  </div>
);

export default ModulePageLayout;
