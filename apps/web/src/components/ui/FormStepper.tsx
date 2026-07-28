import React from 'react';
import { Button } from './Button';

interface FormStepperStep {
  key: string;
  title: string;
  description?: string;
}

interface FormStepperProps {
  steps: FormStepperStep[];
  currentStep: number;
  children: React.ReactNode;
  canContinue?: boolean;
  isSubmitting?: boolean;
  submitLabel?: string;
  onBack: () => void;
  onNext: () => void;
  onCancel?: () => void;
}

export const FormStepper: React.FC<FormStepperProps> = ({
  steps,
  currentStep,
  children,
  canContinue = true,
  isSubmitting = false,
  submitLabel = 'Enviar',
  onBack,
  onNext,
  onCancel,
}) => {
  const isLast = currentStep >= steps.length;

  return (
    <div className="form-stepper">
      <ol className="form-stepper__steps" aria-label="Etapas do formulário">
        {steps.map((step, index) => {
          const number = index + 1;
          return (
            <li
              key={step.key}
              className={[
                'form-stepper__step',
                number === currentStep ? 'active' : '',
                number < currentStep ? 'done' : '',
              ].filter(Boolean).join(' ')}
            >
              <span>{number}</span>
              <div>
                <strong>{step.title}</strong>
                {step.description && <small>{step.description}</small>}
              </div>
            </li>
          );
        })}
      </ol>
      <div className="form-stepper__body">{children}</div>
      <footer className="form-stepper__footer">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        )}
        <div className="form-stepper__footer-actions">
          <Button type="button" variant="secondary" onClick={onBack} disabled={currentStep === 1 || isSubmitting}>
            Voltar
          </Button>
          <Button type="button" variant="primary" onClick={onNext} disabled={!canContinue || isSubmitting} isLoading={isSubmitting}>
            {isLast ? submitLabel : 'Continuar'}
          </Button>
        </div>
      </footer>
    </div>
  );
};

export default FormStepper;
