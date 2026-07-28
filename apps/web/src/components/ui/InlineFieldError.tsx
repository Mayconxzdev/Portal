import React from 'react';

interface InlineFieldErrorProps {
  message?: string | null;
}

export const InlineFieldError: React.FC<InlineFieldErrorProps> = ({ message }) => {
  if (!message) return null;
  return <span className="error-text">{message}</span>;
};

export default InlineFieldError;
