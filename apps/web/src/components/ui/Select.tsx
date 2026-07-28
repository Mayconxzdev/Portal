import React, { useId } from 'react';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helpText?: string;
  options: { value: string | number; label: string }[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, helpText, options, className = '', id, ...props }, ref) => {
    const generatedId = useId();
    const selectId = id || generatedId;
    return (
      <div className={`form-group ${error ? 'has-error' : ''} ${className}`}>
        {label && <label className="form-label" htmlFor={selectId}>{label}</label>}
        <select id={selectId} ref={ref} className="form-select" {...props}>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="select-option">
              {opt.label}
            </option>
          ))}
        </select>
        {helpText && !error && <span className="field-help">{helpText}</span>}
        {error && <span className="error-text">{error}</span>}
      </div>
    );
  }
);

Select.displayName = 'Select';
