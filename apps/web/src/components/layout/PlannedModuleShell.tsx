import React from 'react';
import { LucideIcon, CalendarClock } from 'lucide-react';
import { ModuleHero } from './ModuleHero';
import { ModulePageLayout } from './ModulePageLayout';
import { HelpCard } from './HelpCard';
import { MetricCard } from '../ui/MetricCard';
import { EmptyState } from '../ui/EmptyState';
import { Button } from '../ui/Button';
import { ArrowLeft } from 'lucide-react';

export type PlannedModuleState = 'soon' | 'partial';

export interface PlannedMetric {
  label: string;
  hint: string;
  icon: React.ReactNode;
  iconColor?: 'violet' | 'emerald' | 'amber' | 'rose' | 'cyan';
}

export interface PlannedModuleShellProps {
  title: string;
  description: string;
  state: PlannedModuleState;
  phase: string;
  icon: LucideIcon;
  kodaMessage: string;
  metrics: PlannedMetric[];
  bullets: string[];
  quickActions?: { label: string; hint: string }[];
  onBack?: () => void;
}

export const PlannedModuleShell: React.FC<PlannedModuleShellProps> = ({
  title,
  description,
  state,
  phase,
  icon: Icon,
  kodaMessage,
  metrics,
  bullets,
  quickActions = [],
  onBack,
}) => {
  const stateLabel = state === 'partial' ? 'Base preparada' : 'Em breve';

  const aside = (
    <>
      <div className="glass-card module-side-card">
        <h4 className="dashboard-side-title">Ações rápidas</h4>
        <div className="quick-action-list">
          {(quickActions.length > 0 ? quickActions : [{ label: 'Aguardando backend', hint: phase }]).map((action) => (
            <div key={action.label} className="planned-action-row" aria-disabled>
              <div>
                <strong>{action.label}</strong>
                <span>{action.hint}</span>
              </div>
              <span className="planned-badge">{stateLabel}</span>
            </div>
          ))}
        </div>
      </div>
      <HelpCard
        title={`${title}: ${stateLabel}`}
        description="Este módulo ainda não executa operações reais. Quando o backend estiver pronto, os cards e tabelas passarão a mostrar dados verdadeiros, sem simulação."
        actionLabel="Voltar ao Dashboard"
        onAction={onBack}
      />
    </>
  );

  return (
    <ModulePageLayout aside={aside}>
      <ModuleHero
        icon={<Icon size={28} />}
        title={title}
        description={description}
        eyebrow={phase}
        kodaMessage={kodaMessage}
        actions={
          onBack ? (
            <Button variant="secondary" size="sm" onClick={onBack} leftIcon={<ArrowLeft size={16} />}>
              Voltar ao Dashboard
            </Button>
          ) : undefined
        }
      />

      <div className="metric-grid">
        {metrics.map((metric) => (
          <MetricCard
            key={metric.label}
            label={metric.label}
            value={stateLabel}
            icon={metric.icon}
            iconColor={metric.iconColor}
            tooltipText={metric.hint}
          />
        ))}
      </div>

      <div className="glass-card module-planned-main">
        <EmptyState
          icon={<CalendarClock size={40} />}
          title={stateLabel}
          description={`${phase}. Nenhum dado fictício é exibido nesta tela.`}
        />
        <ul className="module-planned-bullets">
          {bullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </ModulePageLayout>
  );
};

export default PlannedModuleShell;
