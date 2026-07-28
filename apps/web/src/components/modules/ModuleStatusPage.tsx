import React from 'react';
import { ArrowLeft, CalendarClock, CheckCircle2, Construction, LucideIcon } from 'lucide-react';
import { Button } from '../ui/Button';
import { KodaMascot } from '../ui/KodaMascot';

export type ModuleState = 'complete' | 'partial' | 'soon';

interface ModuleStatusPageProps {
  title: string;
  description: string;
  state: ModuleState;
  phase?: string;
  icon?: LucideIcon;
  bullets?: string[];
  onBack?: () => void;
}

const stateText: Record<ModuleState, { label: string; title: string; icon: LucideIcon }> = {
  complete: { label: 'Operacional', title: 'Módulo disponível', icon: CheckCircle2 },
  partial: { label: 'Base preparada', title: 'Implementação parcial', icon: Construction },
  soon: { label: 'Em breve', title: 'Planejado para próxima fase', icon: CalendarClock },
};

export const ModuleStatusPage: React.FC<ModuleStatusPageProps> = ({
  title,
  description,
  state,
  phase,
  icon,
  bullets = [],
  onBack,
}) => {
  const status = stateText[state];
  const StatusIcon = icon || status.icon;

  return (
    <div className="module-status-page">
      <div className="module-status-card">
        <div className="module-status-visual">
          <div className={`module-status-icon ${state}`}>
            <StatusIcon size={34} />
          </div>
          <KodaMascot size="sm" mood={state === 'soon' ? 'thinking' : 'hello'} />
        </div>
        <span className={`module-status-badge ${state}`}>{status.label}</span>
        <h1>{title}</h1>
        <h2>{status.title}</h2>
        <p>{description}</p>
        {phase && <span className="module-status-phase">{phase}</span>}

        {bullets.length > 0 && (
          <div className="module-status-list">
            {bullets.map((item) => (
              <div key={item} className="module-status-list-item">
                <CheckCircle2 size={14} />
                <span>{item}</span>
              </div>
            ))}
          </div>
        )}

        {onBack && (
          <Button variant="secondary" onClick={onBack} leftIcon={<ArrowLeft size={16} />}>
            Voltar ao Dashboard
          </Button>
        )}
      </div>
    </div>
  );
};

export default ModuleStatusPage;
