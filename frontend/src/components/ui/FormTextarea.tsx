import React from 'react';

interface FormTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  helpText?: string;
}

export default function FormTextarea({ label, error, helpText, id, className = '', ...props }: FormTextareaProps) {
  const textareaId = id || label.toLowerCase().replace(/\s+/g, '-');

  return (
    <div>
      <label htmlFor={textareaId} className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <textarea
        id={textareaId}
        rows={3}
        className={`block w-full rounded-lg border ${
          error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
        } px-3 py-2 text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 transition-colors ${className}`}
        {...props}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      {helpText && !error && <p className="mt-1 text-xs text-gray-500">{helpText}</p>}
    </div>
  );
}
