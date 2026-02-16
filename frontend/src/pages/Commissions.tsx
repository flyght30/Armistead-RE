import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DollarSign,
  TrendingUp,
  Clock,
  CheckCircle,
  Download,
  ChevronRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../lib/api';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import StatsCard from '../components/ui/StatsCard';
import { FullPageSpinner } from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';

interface PipelineItem {
  transaction_id: string;
  property_address: string;
  status: string;
  purchase_price: number;
  gross_commission: number;
  agent_net: number;
  commission_status: string;
  closing_date: string | null;
}

interface PipelineSummary {
  total_gross: number;
  total_net: number;
  pending_amount: number;
  paid_amount: number;
  items: PipelineItem[];
}

function formatCurrency(amount: number | null | undefined): string {
  if (amount == null) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '--';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return '--';
  }
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  paid: 'bg-green-100 text-green-700',
  processing: 'bg-blue-100 text-blue-700',
};

export default function Commissions() {
  const navigate = useNavigate();
  const [filterStatus, setFilterStatus] = useState('all');

  const { data: pipeline, isLoading } = useQuery({
    queryKey: ['pipeline'],
    queryFn: async () => {
      const res = await apiClient.get('/pipeline');
      return res.data as PipelineSummary;
    },
  });

  const handleExport = async () => {
    try {
      const res = await apiClient.get('/pipeline/export', {
        responseType: 'blob',
        params: filterStatus !== 'all' ? { status: filterStatus } : undefined,
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'pipeline_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      // handle silently
    }
  };

  if (isLoading) return <FullPageSpinner />;

  const items = pipeline?.items ?? [];
  const filtered = filterStatus === 'all'
    ? items
    : items.filter((i) => i.commission_status === filterStatus);

  return (
    <div>
      <PageHeader
        title="Commissions"
        subtitle="Track your earnings across all transactions"
        actions={
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard
          icon={DollarSign}
          label="Total Gross"
          value={formatCurrency(pipeline?.total_gross)}
          color="blue"
        />
        <StatsCard
          icon={TrendingUp}
          label="Agent Net"
          value={formatCurrency(pipeline?.total_net)}
          color="green"
        />
        <StatsCard
          icon={Clock}
          label="Pending"
          value={formatCurrency(pipeline?.pending_amount)}
          color="yellow"
        />
        <StatsCard
          icon={CheckCircle}
          label="Paid"
          value={formatCurrency(pipeline?.paid_amount)}
          color="green"
        />
      </div>

      {/* Pipeline Table */}
      <Card padding={false}>
        <div className="px-4 pt-4 pb-3 border-b border-gray-100">
          <div className="flex gap-1">
            {['all', 'pending', 'processing', 'paid'].map((s) => (
              <button
                key={s}
                onClick={() => setFilterStatus(s)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${
                  filterStatus === s
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={DollarSign}
            title="No commission records"
            description="Commission data will appear here once transactions have commissions configured."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Property</th>
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Status</th>
                  <th className="text-right text-xs font-medium text-gray-500 px-4 py-3">Purchase Price</th>
                  <th className="text-right text-xs font-medium text-gray-500 px-4 py-3">Gross</th>
                  <th className="text-right text-xs font-medium text-gray-500 px-4 py-3">Net</th>
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Closing</th>
                  <th className="w-8 px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr
                    key={item.transaction_id}
                    onClick={() => navigate(`/transaction/${item.transaction_id}`)}
                    className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {item.property_address || 'Untitled'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[item.commission_status] || 'bg-gray-100 text-gray-600'}`}>
                        {item.commission_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 text-right">{formatCurrency(item.purchase_price)}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 text-right">{formatCurrency(item.gross_commission)}</td>
                    <td className="px-4 py-3 text-sm font-medium text-green-600 text-right">{formatCurrency(item.agent_net)}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{formatDate(item.closing_date)}</td>
                    <td className="px-4 py-3">
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
