import React from 'react';

interface Option {
  value: string;
  label: string;
}

interface FormSelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label: string;
  options: Option[];
  error?: string;
  placeholder?: string;
}

export default function FormSelect({ label, options, error, placeholder, id, className = '', ...props }: FormSelectProps) {
  const selectId = id || label.toLowerCase().replace(/\s+/g, '-');

  return (
    <div>
      <label htmlFor={selectId} className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <select
        id={selectId}
        className={`block w-full rounded-lg border ${
          error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
        } px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 transition-colors ${className}`}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}
