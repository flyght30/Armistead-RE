import React, { useState, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  FileText,
  Clock,
  CheckCircle,
  CalendarDays,
  Plus,
  Search,
  ChevronRight,
} from 'lucide-react';
import apiClient from '../lib/api';
import { Transaction, DashboardStats } from '../types/transaction';
import PageHeader from '../components/ui/PageHeader';
import StatsCard from '../components/ui/StatsCard';
import StatusBadge from '../components/ui/StatusBadge';
import HealthBadge from '../components/ui/HealthBadge';
import DataTable, { Column } from '../components/ui/DataTable';
import Card from '../components/ui/Card';
import { FullPageSpinner } from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';

interface TransactionListResponse {
  items: Transaction[];
  pagination: { page: number; limit: number };
}

const fetchTransactions = async (): Promise<Transaction[]> => {
  const response = await apiClient.get<TransactionListResponse>('/transactions', {
    params: { limit: 100 },
  });
  return response.data.items;
};

const fetchStats = async (): Promise<DashboardStats> => {
  const response = await apiClient.get<DashboardStats>('/stats/dashboard');
  return response.data;
};

const statusFilters = [
  { id: 'all', label: 'All' },
  { id: 'draft', label: 'Draft' },
  { id: 'pending_review', label: 'Pending Review' },
  { id: 'confirmed', label: 'Confirmed' },
];

function formatPrice(price: Record<string, unknown> | null | undefined): string {
  if (!price) return '--';
  const amount = price.amount ?? price.value;
  if (typeof amount === 'number') {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
  }
  return String(amount ?? '--');
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '--';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return '--';
  }
}

function daysUntilClose(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  try {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const close = new Date(dateStr);
    close.setHours(0, 0, 0, 0);
    return Math.ceil((close.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

function DaysToCloseCell({ dateStr }: { dateStr: string | null | undefined }) {
  const days = daysUntilClose(dateStr);
  if (days == null) return <span className="text-gray-400">--</span>;

  let colorClass: string;
  if (days < 0) colorClass = 'text-red-600 font-semibold';
  else if (days <= 7) colorClass = 'text-red-600 font-semibold';
  else if (days <= 14) colorClass = 'text-orange-600 font-medium';
  else if (days <= 30) colorClass = 'text-yellow-600';
  else colorClass = 'text-gray-600';

  const label = days < 0
    ? `${Math.abs(days)}d past`
    : days === 0
    ? 'Today'
    : `${days}d`;

  return <span className={colorClass}>{label}</span>;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchStats,
  });

  const { data: transactions, isLoading: txnLoading } = useQuery({
    queryKey: ['transactions'],
    queryFn: fetchTransactions,
  });

  const filteredTransactions = useMemo(() => {
    if (!transactions) return [];
    return transactions.filter((t) => {
      const matchesFilter = activeFilter === 'all' || t.status === activeFilter;
      const matchesSearch =
        !searchQuery ||
        (t.property_address || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.property_city || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.representation_side || '').toLowerCase().includes(searchQuery.toLowerCase());
      return matchesFilter && matchesSearch;
    });
  }, [transactions, activeFilter, searchQuery]);

  const columns: Column<Transaction>[] = [
    {
      key: 'property_address',
      header: 'Property',
      sortable: true,
      render: (row) => (
        <div>
          <p className="font-medium text-gray-900">{row.property_address || 'Untitled'}</p>
          {row.property_city && (
            <p className="text-xs text-gray-500">
              {row.property_city}, {row.property_state} {row.property_zip}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: 'health_score',
      header: 'Health',
      render: (row) => (
        row.health_score != null ? <HealthBadge score={row.health_score} size="sm" /> : <span className="text-gray-400">--</span>
      ),
    },
    {
      key: 'representation_side',
      header: 'Side',
      sortable: true,
      render: (row) => (
        <span className="capitalize text-gray-700">{row.representation_side}</span>
      ),
    },
    {
      key: 'purchase_price',
      header: 'Price',
      render: (row) => <span className="font-medium">{formatPrice(row.purchase_price)}</span>,
    },
    {
      key: 'closing_date',
      header: 'Closing',
      sortable: true,
      render: (row) => (
        <div className="flex flex-col">
          <span className="text-gray-600">{formatDate(row.closing_date)}</span>
          <DaysToCloseCell dateStr={row.closing_date} />
        </div>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-10',
      render: () => <ChevronRight className="w-4 h-4 text-gray-400" />,
    },
  ];

  if (statsLoading || txnLoading) return <FullPageSpinner />;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Manage your real estate transactions"
        actions={
          <Link
            to="/new"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Transaction
          </Link>
        }
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard
          icon={LayoutDashboard}
          label="Total Transactions"
          value={stats?.total ?? 0}
          color="blue"
        />
        <StatsCard
          icon={CheckCircle}
          label="Active / Confirmed"
          value={stats?.confirmed ?? 0}
          color="green"
        />
        <StatsCard
          icon={Clock}
          label="Pending Review"
          value={stats?.pending_review ?? 0}
          color="yellow"
        />
        <StatsCard
          icon={CalendarDays}
          label="Closing This Month"
          value={stats?.closing_this_month ?? 0}
          color="purple"
        />
      </div>

      {/* Transactions Table */}
      <Card padding={false}>
        {/* Filter Tabs + Search */}
        <div className="px-4 pt-4 pb-3 border-b border-gray-100">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex gap-1">
              {statusFilters.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setActiveFilter(f.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    activeFilter === f.id
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search address, city, side..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none w-full sm:w-64"
              />
            </div>
          </div>
        </div>

        {filteredTransactions.length === 0 && !searchQuery && activeFilter === 'all' ? (
          <EmptyState
            icon={FileText}
            title="No transactions yet"
            description="Create your first transaction to get started."
            action={{ label: 'New Transaction', onClick: () => navigate('/new') }}
          />
        ) : (
          <DataTable
            columns={columns}
            data={filteredTransactions}
            keyExtractor={(row) => row.id}
            onRowClick={(row) => navigate(`/transaction/${row.id}`)}
            emptyMessage={searchQuery ? `No transactions matching "${searchQuery}"` : 'No transactions in this category'}
          />
        )}
      </Card>
    </div>
  );
};

export default Dashboard;
