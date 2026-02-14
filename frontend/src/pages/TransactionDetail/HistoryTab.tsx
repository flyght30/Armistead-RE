import React from 'react';
import { History, ArrowRight } from 'lucide-react';
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

function formatValue(val: unknown): string {
  if (val == null) return '(empty)';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
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
                Fields changed: {amendment.field_changed}
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
              <div className="flex-1">
                <p className="text-xs text-gray-500 mb-1">Old Value</p>
                <code className="text-xs text-red-700 bg-red-50 px-2 py-1 rounded block overflow-x-auto">
                  {formatValue(amendment.old_value)}
                </code>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-xs text-gray-500 mb-1">New Value</p>
                <code className="text-xs text-green-700 bg-green-50 px-2 py-1 rounded block overflow-x-auto">
                  {formatValue(amendment.new_value)}
                </code>
              </div>
            </div>
          )}

          <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
            {amendment.notification_sent && <span>Notification sent</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
