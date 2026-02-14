import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../lib/api';
import { TodayViewData, ActionItem, Transaction } from '../types/transaction';
import ActionItemCard from '../components/ActionItemCard';
import PipelineSidebar from '../components/PipelineSidebar';
import PageHeader from '../components/ui/PageHeader';
import { FullPageSpinner } from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../components/ui/ToastContext';

export default function TodayView() {
  const [data, setData] = useState<TodayViewData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (selectedTxnId) params.transaction_id = selectedTxnId;

      const [todayRes, txnRes] = await Promise.all([
        apiClient.get('/today', { params }),
        apiClient.get('/transactions'),
      ]);

      setData(todayRes.data);
      setTransactions(txnRes.data.items || []);
    } catch (err) {
      console.error('Failed to load Today View:', err);
      toast('error', 'Failed to load Today View');
    } finally {
      setLoading(false);
    }
  }, [selectedTxnId, toast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleComplete = async (id: string) => {
    try {
      await apiClient.patch(`/action-items/${id}`, { status: 'completed' });
      toast('success', 'Item completed');
      fetchData();
    } catch {
      toast('error', 'Failed to complete item');
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      await apiClient.patch(`/action-items/${id}`, { status: 'dismissed' });
      toast('info', 'Item dismissed');
      fetchData();
    } catch {
      toast('error', 'Failed to dismiss item');
    }
  };

  const handleSelectTransaction = (id: string) => {
    setSelectedTxnId(prev => prev === id ? null : id);
  };

  // Helper to find transaction address for an action item
  const getTransactionInfo = (item: ActionItem) => {
    const txn = transactions.find(t => t.id === item.transaction_id);
    return {
      address: txn?.property_address || undefined,
      healthScore: txn?.health_score,
    };
  };

  if (loading) return <FullPageSpinner />;

  const totalItems =
    (data?.summary.overdue_count || 0) +
    (data?.summary.due_today_count || 0) +
    (data?.summary.coming_up_count || 0) +
    (data?.summary.this_week_count || 0);

  return (
    <div className="flex h-full">
      {/* Pipeline sidebar — hidden on mobile */}
      <div className="hidden lg:block flex-shrink-0">
        <PipelineSidebar
          transactions={transactions}
          selectedId={selectedTxnId}
          onSelect={handleSelectTransaction}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <PageHeader
            title="Today"
            subtitle={totalItems > 0 ? `${totalItems} items need your attention` : 'All caught up!'}
            actions={
              <button
                onClick={() => navigate('/new')}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                + New Transaction
              </button>
            }
          />

          {/* Summary counts */}
          <div className="grid grid-cols-4 gap-3 mb-6">
            <SummaryPill label="Overdue" count={data?.summary.overdue_count || 0} color="red" />
            <SummaryPill label="Due Today" count={data?.summary.due_today_count || 0} color="yellow" />
            <SummaryPill label="Coming Up" count={data?.summary.coming_up_count || 0} color="green" />
            <SummaryPill label="This Week" count={data?.summary.this_week_count || 0} color="gray" />
          </div>

          {/* Filter indicator */}
          {selectedTxnId && (
            <div className="mb-4 flex items-center gap-2 text-sm text-indigo-600 bg-indigo-50 px-3 py-2 rounded-lg">
              <span>Filtered to: {transactions.find(t => t.id === selectedTxnId)?.property_address || 'Selected transaction'}</span>
              <button onClick={() => setSelectedTxnId(null)} className="ml-auto text-indigo-500 hover:text-indigo-700 text-xs font-medium">
                Clear filter
              </button>
            </div>
          )}

          {totalItems === 0 ? (
            <EmptyState
              title="You're all caught up!"
              description="No action items need your attention right now. Great job staying on top of your deals."
            />
          ) : (
            <div className="space-y-6">
              {/* Overdue section */}
              <ActionSection
                title="Overdue"
                items={data?.overdue || []}
                bgAccent="bg-red-50"
                borderAccent="border-red-200"
                transactions={transactions}
                onComplete={handleComplete}
                onDismiss={handleDismiss}
                getTransactionInfo={getTransactionInfo}
              />

              {/* Due Today section */}
              <ActionSection
                title="Due Today"
                items={data?.due_today || []}
                bgAccent="bg-yellow-50"
                borderAccent="border-yellow-200"
                transactions={transactions}
                onComplete={handleComplete}
                onDismiss={handleDismiss}
                getTransactionInfo={getTransactionInfo}
              />

              {/* Coming Up section */}
              <ActionSection
                title="Coming Up"
                items={data?.coming_up || []}
                bgAccent="bg-green-50"
                borderAccent="border-green-200"
                transactions={transactions}
                onComplete={handleComplete}
                onDismiss={handleDismiss}
                getTransactionInfo={getTransactionInfo}
              />

              {/* This Week section */}
              <ActionSection
                title="This Week"
                items={data?.this_week || []}
                bgAccent="bg-gray-50"
                borderAccent="border-gray-200"
                transactions={transactions}
                onComplete={handleComplete}
                onDismiss={handleDismiss}
                defaultCollapsed
                getTransactionInfo={getTransactionInfo}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Sub-components ---

function SummaryPill({ label, count, color }: { label: string; count: number; color: string }) {
  const colorMap: Record<string, string> = {
    red: 'bg-red-100 text-red-700 border-red-200',
    yellow: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    green: 'bg-green-100 text-green-700 border-green-200',
    gray: 'bg-gray-100 text-gray-700 border-gray-200',
  };

  return (
    <div className={`rounded-lg border px-3 py-2 text-center ${colorMap[color] || colorMap.gray}`}>
      <div className="text-xl font-bold">{count}</div>
      <div className="text-xs font-medium">{label}</div>
    </div>
  );
}

interface ActionSectionProps {
  title: string;
  items: ActionItem[];
  bgAccent: string;
  borderAccent: string;
  transactions: Transaction[];
  onComplete: (id: string) => void;
  onDismiss: (id: string) => void;
  getTransactionInfo: (item: ActionItem) => { address?: string; healthScore?: number | null };
  defaultCollapsed?: boolean;
}

function ActionSection({
  title,
  items,
  bgAccent,
  borderAccent,
  onComplete,
  onDismiss,
  getTransactionInfo,
  defaultCollapsed = false,
}: ActionSectionProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed && items.length > 5);

  if (items.length === 0) return null;

  return (
    <div className={`rounded-xl border ${borderAccent} overflow-hidden`}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={`w-full flex items-center justify-between px-4 py-2.5 ${bgAccent}`}
      >
        <h3 className="text-sm font-semibold text-gray-800">
          {title} <span className="text-gray-500 font-normal">({items.length})</span>
        </h3>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${collapsed ? '' : 'rotate-180'}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {!collapsed && (
        <div className="p-3 space-y-2">
          {items.map(item => {
            const info = getTransactionInfo(item);
            return (
              <ActionItemCard
                key={item.id}
                item={item}
                transactionAddress={info.address}
                healthScore={info.healthScore}
                onComplete={onComplete}
                onDismiss={onDismiss}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
