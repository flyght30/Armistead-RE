import React from 'react';
import { Link } from 'react-router-dom';
import { ActionItem } from '../types/transaction';
import { HealthDot } from './ui/HealthBadge';

interface ActionItemCardProps {
  item: ActionItem;
  transactionAddress?: string;
  healthScore?: number | null;
  onComplete: (id: string) => void;
  onDismiss: (id: string) => void;
}

function getPriorityStyles(priority: string): string {
  switch (priority) {
    case 'critical': return 'border-l-red-500 bg-red-50';
    case 'high': return 'border-l-orange-500 bg-orange-50';
    case 'medium': return 'border-l-yellow-500 bg-yellow-50';
    case 'low': return 'border-l-blue-500 bg-blue-50';
    default: return 'border-l-gray-300 bg-white';
  }
}

function getUrgencyLabel(dueDate: string | null | undefined): { text: string; className: string } {
  if (!dueDate) return { text: 'No date', className: 'text-gray-400' };
  const now = new Date();
  const due = new Date(dueDate);
  const diffMs = due.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return { text: `${Math.abs(diffDays)}d overdue`, className: 'text-red-600 font-semibold' };
  if (diffDays === 0) return { text: 'Due today', className: 'text-yellow-600 font-semibold' };
  if (diffDays === 1) return { text: 'Tomorrow', className: 'text-green-600' };
  return { text: `In ${diffDays}d`, className: 'text-green-600' };
}

export default function ActionItemCard({ item, transactionAddress, healthScore, onComplete, onDismiss }: ActionItemCardProps) {
  const urgency = getUrgencyLabel(item.due_date);

  return (
    <div className={`border-l-4 rounded-lg p-3 shadow-sm ${getPriorityStyles(item.priority)} transition-all hover:shadow-md`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Transaction address link */}
          {transactionAddress && (
            <Link
              to={`/transaction/${item.transaction_id}`}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 mb-1"
            >
              <HealthDot score={healthScore} />
              {transactionAddress}
            </Link>
          )}

          {/* Title */}
          <h4 className="text-sm font-medium text-gray-900 truncate">{item.title}</h4>

          {/* Description */}
          {item.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{item.description}</p>
          )}
        </div>

        {/* Urgency badge */}
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className={`text-xs ${urgency.className}`}>{urgency.text}</span>
          <span className="text-[10px] text-gray-400 uppercase tracking-wider">{item.priority}</span>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200/60">
        <button
          onClick={() => onComplete(item.id)}
          className="text-xs px-2 py-1 rounded bg-green-600 text-white hover:bg-green-700 transition-colors"
        >
          Complete
        </button>
        <button
          onClick={() => onDismiss(item.id)}
          className="text-xs px-2 py-1 rounded border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors"
        >
          Dismiss
        </button>
        <Link
          to={`/transaction/${item.transaction_id}`}
          className="text-xs px-2 py-1 rounded border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors ml-auto"
        >
          View
        </Link>
      </div>
    </div>
  );
}
