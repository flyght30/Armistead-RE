import React from 'react';

const colorMap: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending_review: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-green-100 text-green-800',
  active: 'bg-green-100 text-green-800',
  deleted: 'bg-red-100 text-red-700',
  overdue: 'bg-red-100 text-red-700',
  completed: 'bg-green-100 text-green-800',
  sent: 'bg-blue-100 text-blue-700',
  pending: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-blue-100 text-blue-700',
  not_started: 'bg-gray-100 text-gray-700',
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-700',
  critical: 'bg-red-200 text-red-900',
  buyer: 'bg-blue-100 text-blue-700',
  seller: 'bg-purple-100 text-purple-700',
  buyer_agent: 'bg-indigo-100 text-indigo-700',
  seller_agent: 'bg-pink-100 text-pink-700',
  attorney: 'bg-amber-100 text-amber-700',
  lender: 'bg-teal-100 text-teal-700',
  inspector: 'bg-orange-100 text-orange-700',
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const colors = colorMap[status.toLowerCase()] || 'bg-gray-100 text-gray-700';
  const label = status.replace(/_/g, ' ');

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${colors} ${className}`}
    >
      {label}
    </span>
  );
}
