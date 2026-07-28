import React, { useId } from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helpText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helpText, className = '', id, ...props }, ref) => {
    const generatedId = useId();
    const textareaId = id || generatedId;
    return (
      <div className={`form-group ${error ? 'has-error' : ''} ${className}`}>
        {label && <label className="form-label" htmlFor={textareaId}>{label}</label>}
        <textarea id={textareaId} ref={ref} className="form-textarea" {...props} />
        {helpText && !error && <span className="field-help">{helpText}</span>}
        {error && <span className="error-text">{error}</span>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
