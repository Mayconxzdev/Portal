import React from 'react';

export interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className={`switch-group ${error ? 'has-error' : ''} ${className}`}>
        <label className="switch-label">
          <div className="switch-wrapper">
            <input ref={ref} type="checkbox" className="form-switch" {...props} />
            <div className="switch-slider"></div>
          </div>
          {label && <span className="switch-text">{label}</span>}
        </label>
        {error && <span className="error-text">{error}</span>}
      </div>
    );
  }
);

Switch.displayName = 'Switch';
