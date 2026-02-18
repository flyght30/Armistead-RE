import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DollarSign,
  TrendingUp,
  Building2,
  Pencil,
  Save,
  X,
  Plus,
  CheckCircle,
  Clock,
  PieChart,
} from 'lucide-react';
import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import Spinner from '../../components/ui/Spinner';
import FormInput from '../../components/ui/FormInput';
import FormSelect from '../../components/ui/FormSelect';
import { useToast } from '../../components/ui/ToastContext';
import apiClient from '../../lib/api';

interface CommissionsTabProps {
  transactionId: string;
  purchasePrice: number | null;
}

interface CommissionSplit {
  id: string;
  split_type: string;
  recipient_name: string;
  is_percentage: boolean;
  percentage: number | null;
  flat_amount: number | null;
  calculated_amount: number | null;
}

interface TransactionCommission {
  id: string;
  transaction_id: string;
  agent_id: string;
  commission_type: string;
  rate: number | null;
  flat_amount: number | null;
  gross_commission: number | null;
  projected_net: number | null;
  actual_net: number | null;
  actual_gross: number | null;
  status: string;
  is_dual_agency: boolean;
  is_manual_override: boolean;
  notes: string | null;
  splits: CommissionSplit[];
  created_at: string;
  updated_at: string;
}

function formatCurrency(amount: number | null | undefined): string {
  if (amount == null) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatPercent(rate: number | null | undefined): string {
  if (rate == null) return '0%';
  return `${(rate * 100).toFixed(2)}%`;
}

function statusColor(status: string): string {
  switch (status) {
    case 'paid': return 'bg-green-100 text-green-700';
    case 'pending': return 'bg-yellow-100 text-yellow-700';
    default: return 'bg-blue-100 text-blue-700';
  }
}

function CommissionDonut({
  gross,
  brokerAmount,
  agentNet,
}: {
  gross: number;
  brokerAmount: number;
  agentNet: number;
}) {
  if (gross <= 0) return null;
  const brokerPct = (brokerAmount / gross) * 100;
  const agentPct = (agentNet / gross) * 100;

  // SVG donut chart
  const size = 120;
  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const agentDash = (agentPct / 100) * circumference;
  const brokerDash = (brokerPct / 100) * circumference;

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Agent portion (green) */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#22c55e"
          strokeWidth={strokeWidth}
          strokeDasharray={`${agentDash} ${circumference}`}
          strokeLinecap="round"
        />
        {/* Broker portion (blue) */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#6366f1"
          strokeWidth={strokeWidth}
          strokeDasharray={`${brokerDash} ${circumference}`}
          strokeDashoffset={-agentDash}
          strokeLinecap="round"
        />
      </svg>
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-sm text-gray-600">Agent ({agentPct.toFixed(0)}%)</span>
          <span className="text-sm font-semibold text-gray-900">{formatCurrency(agentNet)}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-indigo-500" />
          <span className="text-sm text-gray-600">Broker ({brokerPct.toFixed(0)}%)</span>
          <span className="text-sm font-semibold text-gray-900">{formatCurrency(brokerAmount)}</span>
        </div>
      </div>
    </div>
  );
}

export default function CommissionsTab({ transactionId, purchasePrice }: CommissionsTabProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [formRate, setFormRate] = useState('');
  const [formStatus, setFormStatus] = useState('');
  const [formNotes, setFormNotes] = useState('');

  const { data: commission, isLoading, isError } = useQuery({
    queryKey: ['commission', transactionId],
    queryFn: async () => {
      try {
        const res = await apiClient.get(`/transactions/${transactionId}/commission`);
        return res.data as TransactionCommission;
      } catch (err: unknown) {
        const axiosErr = err as { response?: { status?: number } };
        if (axiosErr?.response?.status === 404) return null;
        throw err;
      }
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const rate = parseFloat(formRate) / 100; // Convert from percentage display to decimal
      const res = await apiClient.post(`/transactions/${transactionId}/commission`, {
        commission_type: 'percentage',
        rate,
        splits: [
          {
            split_type: 'broker',
            recipient_name: 'Brokerage',
            is_percentage: true,
            percentage: 0.2, // 20% to broker
          },
        ],
      });
      return res.data;
    },
    onSuccess: () => {
      toast('success', 'Commission created');
      queryClient.invalidateQueries({ queryKey: ['commission', transactionId] });
      setEditing(false);
    },
    onError: () => toast('error', 'Failed to create commission'),
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {};
      if (formRate) body.rate = parseFloat(formRate) / 100;
      if (formStatus) body.status = formStatus;
      if (formNotes !== (commission?.notes ?? '')) body.notes = formNotes || null;
      const res = await apiClient.patch(`/transactions/${transactionId}/commission`, body);
      return res.data;
    },
    onSuccess: () => {
      toast('success', 'Commission updated');
      queryClient.invalidateQueries({ queryKey: ['commission', transactionId] });
      setEditing(false);
    },
    onError: () => toast('error', 'Failed to update commission'),
  });

  function startEdit() {
    if (commission) {
      setFormRate(commission.rate ? (commission.rate * 100).toFixed(2) : '3.00');
      setFormStatus(commission.status);
      setFormNotes(commission.notes ?? '');
    } else {
      setFormRate('3.00');
      setFormStatus('projected');
      setFormNotes('');
    }
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
  }

  function handleSave() {
    if (commission) {
      updateMutation.mutate();
    } else {
      createMutation.mutate();
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  // No commission yet
  if (!commission && !editing) {
    return (
      <div className="space-y-6">
        <EmptyState
          icon={DollarSign}
          title="No commission configured"
          description="Set up the commission for this transaction with your rate and broker/agent split."
          action={{ label: 'Configure Commission', onClick: startEdit }}
        />
      </div>
    );
  }

  // Editing / Creating form
  if (editing) {
    const previewRate = parseFloat(formRate) / 100 || 0;
    const previewGross = (purchasePrice || 0) * previewRate;
    const previewBroker = previewGross * 0.20;
    const previewNet = previewGross - previewBroker;

    return (
      <div className="space-y-6 max-w-2xl">
        <Card title={commission ? 'Edit Commission' : 'Configure Commission'}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormInput
                label="Commission Rate (%)"
                type="number"
                min="0"
                max="100"
                step="0.01"
                value={formRate}
                onChange={(e) => setFormRate(e.target.value)}
                placeholder="3.00"
              />
              {commission && (
                <FormSelect
                  label="Status"
                  value={formStatus}
                  onChange={(e) => setFormStatus(e.target.value)}
                  options={[
                    { value: 'projected', label: 'Projected' },
                    { value: 'pending', label: 'Pending' },
                    { value: 'paid', label: 'Paid' },
                  ]}
                />
              )}
            </div>

            <FormInput
              label="Notes"
              value={formNotes}
              onChange={(e) => setFormNotes(e.target.value)}
              placeholder="Optional notes about this commission..."
            />

            {/* Live Preview */}
            {purchasePrice && (
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Preview</p>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-gray-500">Gross Commission</p>
                    <p className="text-lg font-bold text-gray-900">{formatCurrency(previewGross)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Broker (20%)</p>
                    <p className="text-lg font-semibold text-indigo-600">{formatCurrency(previewBroker)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Agent Net (80%)</p>
                    <p className="text-lg font-bold text-green-600">{formatCurrency(previewNet)}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-200">
              <button
                onClick={cancelEdit}
                className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={createMutation.isPending || updateMutation.isPending || !formRate}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
              >
                {(createMutation.isPending || updateMutation.isPending) ? (
                  <Spinner size="sm" className="text-white" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {commission ? 'Save Changes' : 'Create Commission'}
              </button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // Display commission data
  const gross = commission!.gross_commission ?? 0;
  const brokerSplit = commission!.splits.find((s) => s.split_type === 'broker');
  const brokerAmount = brokerSplit?.calculated_amount ?? 0;
  const agentNet = commission!.projected_net ?? 0;
  const brokerPct = brokerSplit?.percentage ?? 0;
  const agentPct = 1 - brokerPct;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium capitalize ${statusColor(commission!.status)}`}>
            {commission!.status === 'paid' && <CheckCircle className="w-3 h-3" />}
            {commission!.status === 'pending' && <Clock className="w-3 h-3" />}
            {commission!.status}
          </span>
          <span className="text-sm text-gray-500">
            {formatPercent(commission!.rate)} commission rate
          </span>
        </div>
        <button
          onClick={startEdit}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          <Pencil className="w-4 h-4" />
          Edit
        </button>
      </div>

      {/* Commission Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Gross Commission</p>
              <p className="text-xl font-bold text-gray-900">{formatCurrency(gross)}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Broker ({(brokerPct * 100).toFixed(0)}%)</p>
              <p className="text-xl font-bold text-indigo-700">{formatCurrency(brokerAmount)}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Agent Net ({(agentPct * 100).toFixed(0)}%)</p>
              <p className="text-xl font-bold text-green-700">{formatCurrency(agentNet)}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Visual Split */}
      <Card title="Commission Split" action={<PieChart className="w-4 h-4 text-gray-400" />}>
        <div className="flex flex-col md:flex-row items-start gap-6">
          <CommissionDonut gross={gross} brokerAmount={brokerAmount} agentNet={agentNet} />

          <div className="flex-1 space-y-4">
            {/* Split breakdown table */}
            <div className="bg-gray-50 rounded-lg divide-y divide-gray-200">
              <div className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">Purchase Price</p>
                  <p className="text-xs text-gray-500">Contract amount</p>
                </div>
                <p className="text-sm font-semibold text-gray-900">{formatCurrency(purchasePrice)}</p>
              </div>
              <div className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">Commission Rate</p>
                  <p className="text-xs text-gray-500">{formatPercent(commission!.rate)} of purchase price</p>
                </div>
                <p className="text-sm font-semibold text-gray-900">{formatCurrency(gross)}</p>
              </div>
              {commission!.splits.map((split) => (
                <div key={split.id} className="px-4 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{split.recipient_name}</p>
                    <p className="text-xs text-gray-500 capitalize">
                      {split.split_type} — {split.is_percentage ? formatPercent(split.percentage) : formatCurrency(split.flat_amount)}
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-indigo-600">-{formatCurrency(split.calculated_amount)}</p>
                </div>
              ))}
              <div className="px-4 py-3 flex items-center justify-between bg-green-50">
                <div>
                  <p className="text-sm font-bold text-green-800">Agent Net</p>
                  <p className="text-xs text-green-600">Your take-home</p>
                </div>
                <p className="text-lg font-bold text-green-700">{formatCurrency(agentNet)}</p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Notes */}
      {commission!.notes && (
        <Card title="Notes">
          <p className="text-sm text-gray-700">{commission!.notes}</p>
        </Card>
      )}

      {/* Actual amounts (if paid/pending) */}
      {(commission!.actual_gross || commission!.actual_net) && (
        <Card title="Actual Amounts" subtitle="Verified after closing">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Actual Gross</p>
              <p className="text-lg font-bold text-gray-900">{formatCurrency(commission!.actual_gross)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Actual Net</p>
              <p className="text-lg font-bold text-green-700">{formatCurrency(commission!.actual_net)}</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
