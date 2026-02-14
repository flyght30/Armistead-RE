import React from 'react';
import { Link } from 'react-router-dom';
import { Transaction } from '../types/transaction';
import { HealthDot } from './ui/HealthBadge';

interface PipelineSidebarProps {
  transactions: Transaction[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'No date';
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getDaysToClose(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  const days = Math.ceil((new Date(dateStr).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (days < 0) return `${Math.abs(days)}d past`;
  if (days === 0) return 'Today';
  return `${days}d`;
}

export default function PipelineSidebar({ transactions, selectedId, onSelect }: PipelineSidebarProps) {
  const active = transactions.filter(t => t.status !== 'draft' && t.status !== 'deleted');
  const drafts = transactions.filter(t => t.status === 'draft');

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-full overflow-hidden">
      <div className="p-3 border-b border-gray-200">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Pipeline</h3>
        <p className="text-xs text-gray-400 mt-0.5">{active.length} active deals</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Active transactions */}
        {active.map(txn => (
          <button
            key={txn.id}
            onClick={() => onSelect?.(txn.id)}
            className={`w-full text-left px-3 py-2.5 border-b border-gray-100 hover:bg-indigo-50 transition-colors ${
              selectedId === txn.id ? 'bg-indigo-50 border-l-2 border-l-indigo-500' : ''
            }`}
          >
            <div className="flex items-center gap-2">
              <HealthDot score={txn.health_score} />
              <span className="text-sm font-medium text-gray-900 truncate flex-1">
                {txn.property_address || 'No address'}
              </span>
            </div>
            <div className="flex items-center justify-between mt-1 ml-5">
              <span className="text-xs text-gray-500">{formatDate(txn.closing_date)}</span>
              <span className="text-xs text-gray-400">{getDaysToClose(txn.closing_date)}</span>
            </div>
          </button>
        ))}

        {/* Draft section */}
        {drafts.length > 0 && (
          <>
            <div className="px-3 py-2 bg-gray-50">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                Drafts ({drafts.length})
              </span>
            </div>
            {drafts.map(txn => (
              <Link
                key={txn.id}
                to={`/transaction/${txn.id}`}
                className="w-full text-left px-3 py-2 border-b border-gray-100 hover:bg-gray-50 transition-colors block"
              >
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-gray-300" />
                  <span className="text-sm text-gray-500 truncate">{txn.property_address || 'Incomplete draft'}</span>
                </div>
              </Link>
            ))}
          </>
        )}
      </div>
    </aside>
  );
}
