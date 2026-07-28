import React from 'react';

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className={`checkbox-group ${error ? 'has-error' : ''} ${className}`}>
        <label className="checkbox-label">
          <input ref={ref} type="checkbox" className="form-checkbox" {...props} />
          <span className="checkbox-text">{label}</span>
        </label>
        {error && <span className="error-text">{error}</span>}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';
