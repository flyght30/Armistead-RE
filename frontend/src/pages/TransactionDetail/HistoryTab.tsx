import React from 'react';
import { History, ArrowRight, Bell } from 'lucide-react';
import { Amendment } from '../../types/transaction';
import EmptyState from '../../components/ui/EmptyState';

interface HistoryTabProps {
  amendments: Amendment[];
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

function formatFieldName(field: string): string {
  return field
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Smart value formatting — detect currency, dates, booleans, etc.
function formatValue(val: unknown, fieldName: string): string {
  if (val == null) return '(empty)';

  // JSON object with "amount" key → currency
  if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
    const obj = val as Record<string, unknown>;
    if ('amount' in obj && typeof obj.amount === 'number') {
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(obj.amount);
    }
    // Other JSON objects — format nicely
    const entries = Object.entries(obj).filter(([, v]) => v != null);
    if (entries.length === 0) return '(empty)';
    return entries.map(([k, v]) => `${k}: ${v}`).join(', ');
  }

  if (Array.isArray(val)) {
    if (val.length === 0) return '(empty)';
    return val.join(', ');
  }

  const s = String(val);

  // Boolean values
  if (s === 'true') return 'Yes';
  if (s === 'false') return 'No';

  // Date-like strings (ISO format)
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
    try {
      return new Date(s).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      // fall through
    }
  }

  // Status values — capitalize
  const lowerField = fieldName.toLowerCase();
  if (lowerField.includes('status') || lowerField.includes('side') || lowerField.includes('type')) {
    return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  return s;
}

export default function HistoryTab({ amendments }: HistoryTabProps) {
  if (amendments.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No amendment history"
        description="Changes to transaction fields will be logged here automatically."
      />
    );
  }

  const sorted = [...amendments].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-4 max-w-3xl">
      {sorted.map((amendment) => (
        <div
          key={amendment.id}
          className="bg-white rounded-xl border border-gray-200 p-5"
        >
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-sm font-semibold text-gray-900">
                {formatFieldName(amendment.field_changed)}
              </p>
              {amendment.reason && (
                <p className="text-sm text-gray-500 mt-0.5">{amendment.reason}</p>
              )}
            </div>
            <time className="text-xs text-gray-400 whitespace-nowrap">
              {formatDate(amendment.created_at)}
            </time>
          </div>

          {(amendment.old_value != null || amendment.new_value != null) && (
            <div className="bg-gray-50 rounded-lg p-3 flex items-center gap-3 text-sm">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-500 mb-1">Before</p>
                <p className="text-sm text-red-700 bg-red-50 px-2 py-1 rounded break-words">
                  {formatValue(amendment.old_value, amendment.field_changed)}
                </p>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-500 mb-1">After</p>
                <p className="text-sm text-green-700 bg-green-50 px-2 py-1 rounded break-words">
                  {formatValue(amendment.new_value, amendment.field_changed)}
                </p>
              </div>
            </div>
          )}

          {amendment.notification_sent && (
            <div className="flex items-center gap-1.5 mt-3 text-xs text-gray-400">
              <Bell className="w-3 h-3" />
              <span>Notification sent</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
