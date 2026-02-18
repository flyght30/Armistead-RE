import React, { useState, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MapPin,
  DollarSign,
  Calendar,
  Brain,
  FileCheck,
  Pencil,
  X,
  Save,
  Sparkles,
  CheckCircle,
  Phone,
  Upload,
  AlertTriangle,
  Mail,
  Clock,
  UploadCloud,
  TrendingUp,
} from 'lucide-react';
import { TransactionDetail, SmartSuggestion } from '../../types/transaction';
import Card from '../../components/ui/Card';
import StatusBadge from '../../components/ui/StatusBadge';
import FormInput from '../../components/ui/FormInput';
import FormSelect from '../../components/ui/FormSelect';
import Spinner from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/ToastContext';
import apiClient from '../../lib/api';

interface OverviewTabProps {
  transaction: TransactionDetail;
  onRefresh: () => void;
}

interface FormState {
  property_address: string;
  property_city: string;
  property_state: string;
  property_zip: string;
  purchase_price: string;
  earnest_money_amount: string;
  closing_date: string;
  representation_side: string;
  financing_type: string;
}

function extractAmount(price: Record<string, unknown> | null | undefined): string {
  if (!price) return '';
  const amount = price.amount ?? price.value;
  if (typeof amount === 'number') return String(amount);
  return '';
}

function extractNumeric(price: Record<string, unknown> | null | undefined): number | null {
  if (!price) return null;
  const amount = price.amount ?? price.value;
  return typeof amount === 'number' ? amount : null;
}

function formatPrice(price: Record<string, unknown> | null | undefined): string {
  if (!price) return 'Not set';
  const amount = price.amount ?? price.value;
  if (typeof amount === 'number') {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  }
  return String(amount ?? 'Not set');
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Not set';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return 'Not set';
  }
}

function formatDateLong(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Not set';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return 'Not set';
  }
}

function toDateInputValue(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toISOString().split('T')[0];
  } catch {
    return '';
  }
}

function daysUntilClosing(closingDate: string | null | undefined): number | null {
  if (!closingDate) return null;
  try {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const close = new Date(closingDate);
    close.setHours(0, 0, 0, 0);
    return Math.ceil((close.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

function ClosingCountdown({ closingDate }: { closingDate: string | null | undefined }) {
  const days = daysUntilClosing(closingDate);
  if (days == null) return null;

  let color: string;
  let bgColor: string;
  let label: string;

  if (days < 0) {
    color = 'text-red-700';
    bgColor = 'bg-red-50 border-red-200';
    label = `${Math.abs(days)} days past closing`;
  } else if (days === 0) {
    color = 'text-green-700';
    bgColor = 'bg-green-50 border-green-200';
    label = 'Closing today!';
  } else if (days <= 7) {
    color = 'text-red-700';
    bgColor = 'bg-red-50 border-red-200';
    label = `${days} day${days === 1 ? '' : 's'} to closing`;
  } else if (days <= 14) {
    color = 'text-orange-700';
    bgColor = 'bg-orange-50 border-orange-200';
    label = `${days} days to closing`;
  } else if (days <= 30) {
    color = 'text-yellow-700';
    bgColor = 'bg-yellow-50 border-yellow-200';
    label = `${days} days to closing`;
  } else {
    color = 'text-blue-700';
    bgColor = 'bg-blue-50 border-blue-200';
    label = `${days} days to closing`;
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium ${bgColor} ${color}`}>
      <Clock className="w-4 h-4" />
      {label}
    </div>
  );
}

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-600 w-10 text-right">{pct}%</span>
    </div>
  );
}

const representationOptions = [
  { value: 'buyer', label: 'Buyer' },
  { value: 'seller', label: 'Seller' },
  { value: 'dual', label: 'Dual' },
];

const financingOptions = [
  { value: 'conventional', label: 'Conventional' },
  { value: 'fha', label: 'FHA' },
  { value: 'va', label: 'VA' },
  { value: 'cash', label: 'Cash' },
  { value: 'other', label: 'Other' },
];

const iconMap: Record<string, React.ElementType> = {
  phone: Phone,
  upload: Upload,
  alert: AlertTriangle,
  calendar: Calendar,
  mail: Mail,
  check: CheckCircle,
};

function SmartSuggestionsCard({ transactionId }: { transactionId: string }) {
  const { data: suggestions, isLoading } = useQuery({
    queryKey: ['smart-suggestions', transactionId],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${transactionId}/advisor/suggestions`);
      return res.data as SmartSuggestion[];
    },
    staleTime: 5 * 60 * 1000,
  });

  if (!isLoading && (!suggestions || suggestions.length === 0)) return null;

  return (
    <Card
      title="Recommended Next Steps"
      action={<Sparkles className="w-4 h-4 text-yellow-500" />}
    >
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse flex gap-3">
              <div className="w-8 h-8 bg-gray-200 rounded-lg flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3 bg-gray-200 rounded w-3/4" />
                <div className="h-3 bg-gray-200 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {suggestions!.map((s, i) => {
            const Icon = iconMap[s.icon] || CheckCircle;
            return (
              <div key={i} className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  s.priority === 'high' ? 'bg-red-100 text-red-600' :
                  s.priority === 'medium' ? 'bg-yellow-100 text-yellow-600' :
                  'bg-blue-100 text-blue-600'
                }`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900">{s.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function ContractUploadZone({
  transactionId,
  onRefresh,
}: {
  transactionId: string;
  onRefresh: () => void;
}) {
  const { toast } = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiClient.post(
        `/transactions/${transactionId}/files/upload-contract`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 },
      );
      toast('success', res.data?.message || 'Contract uploaded and parsed');
      onRefresh();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || (err instanceof Error ? err.message : 'Upload failed');
      toast('error', message);
    } finally {
      setUploading(false);
    }
  }, [transactionId, onRefresh, toast]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    if (fileRef.current) fileRef.current.value = '';
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type === 'application/pdf') {
      handleUpload(file);
    } else {
      toast('error', 'Please upload a PDF file');
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !uploading && fileRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
        dragOver
          ? 'border-indigo-400 bg-indigo-50'
          : 'border-gray-300 hover:border-indigo-300 hover:bg-gray-50'
      } ${uploading ? 'opacity-60 cursor-wait' : ''}`}
    >
      <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
      {uploading ? (
        <div className="flex flex-col items-center gap-3">
          <Spinner size="lg" />
          <div>
            <p className="text-sm font-medium text-gray-700">Parsing contract with AI...</p>
            <p className="text-xs text-gray-500 mt-1">This may take up to 60 seconds</p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center">
            <UploadCloud className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">
              Drop a contract PDF here, or <span className="text-indigo-600">click to browse</span>
            </p>
            <p className="text-xs text-gray-500 mt-1">
              AI will extract parties, dates, financial terms, and provisions
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function CommissionSummary({ transactionId }: { transactionId: string }) {
  const { data: commission } = useQuery({
    queryKey: ['commission-summary', transactionId],
    queryFn: async () => {
      try {
        const res = await apiClient.get(`/transactions/${transactionId}/commission`);
        return res.data;
      } catch {
        return null;
      }
    },
    staleTime: 30 * 1000,
  });

  if (!commission) return null;

  const gross = commission.gross_commission ?? 0;
  const net = commission.projected_net ?? 0;
  const rate = commission.rate ?? 0;

  return (
    <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
      <TrendingUp className="w-5 h-5 text-green-600 flex-shrink-0" />
      <div className="flex-1">
        <p className="text-xs text-gray-500 uppercase tracking-wide">Commission ({(rate * 100).toFixed(1)}%)</p>
        <div className="flex items-baseline gap-3">
          <p className="text-sm font-semibold text-green-700">
            {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(net)} net
          </p>
          <p className="text-xs text-gray-500">
            {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(gross)} gross
          </p>
        </div>
      </div>
    </div>
  );
}

export default function OverviewTab({ transaction, onRefresh }: OverviewTabProps) {
  const t = transaction;
  const { toast } = useToast();

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const contractFileRef = useRef<HTMLInputElement>(null);
  const [reUploading, setReUploading] = useState(false);

  const [form, setForm] = useState<FormState>(() => buildFormState(t));

  function buildFormState(txn: TransactionDetail): FormState {
    return {
      property_address: txn.property_address || '',
      property_city: txn.property_city || '',
      property_state: txn.property_state || '',
      property_zip: txn.property_zip || '',
      purchase_price: extractAmount(txn.purchase_price),
      earnest_money_amount: extractAmount(txn.earnest_money_amount),
      closing_date: toDateInputValue(txn.closing_date),
      representation_side: txn.representation_side || '',
      financing_type: txn.financing_type || '',
    };
  }

  function handleChange(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleCancel() {
    setForm(buildFormState(t));
    setEditing(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const body: Record<string, unknown> = {
        representation_side: form.representation_side,
        financing_type: form.financing_type || null,
        property_address: form.property_address || null,
        property_city: form.property_city || null,
        property_state: form.property_state || null,
        property_zip: form.property_zip || null,
        closing_date: form.closing_date || null,
      };

      if (form.purchase_price) {
        body.purchase_price = { amount: parseFloat(form.purchase_price) };
      } else {
        body.purchase_price = null;
      }

      if (form.earnest_money_amount) {
        body.earnest_money_amount = { amount: parseFloat(form.earnest_money_amount) };
      } else {
        body.earnest_money_amount = null;
      }

      await apiClient.patch(`/transactions/${t.id}`, body);
      toast('success', 'Transaction updated successfully');
      setEditing(false);
      onRefresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to update transaction';
      toast('error', message);
    } finally {
      setSaving(false);
    }
  }

  async function handleParse() {
    setParsing(true);
    try {
      const res = await apiClient.post(`/transactions/${t.id}/parse`);
      toast('success', res.data?.message || 'Contract parsed successfully');
      onRefresh();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message =
        axiosErr?.response?.data?.detail || (err instanceof Error ? err.message : 'Failed to parse contract');
      toast('error', message);
    } finally {
      setParsing(false);
    }
  }

  async function handleConfirm() {
    setConfirming(true);
    try {
      const res = await apiClient.post(`/transactions/${t.id}/confirm`);
      toast('success', res.data?.message || 'Transaction confirmed');
      onRefresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to confirm transaction';
      toast('error', message);
    } finally {
      setConfirming(false);
    }
  }

  async function handleReUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setReUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiClient.post(
        `/transactions/${t.id}/files/upload-contract`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 },
      );
      toast('success', res.data?.message || 'Contract re-uploaded and parsed');
      onRefresh();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || (err instanceof Error ? err.message : 'Upload failed');
      toast('error', message);
    } finally {
      setReUploading(false);
      if (contractFileRef.current) contractFileRef.current.value = '';
    }
  }

  const canConfirm = t.status === 'draft' || t.status === 'pending_review';
  const hasContract = Boolean(t.contract_document_url);

  // Earnest money as % of purchase price
  const purchaseAmt = extractNumeric(t.purchase_price);
  const earnestAmt = extractNumeric(t.earnest_money_amount);
  const earnestPct = purchaseAmt && earnestAmt ? ((earnestAmt / purchaseAmt) * 100).toFixed(1) : null;

  return (
    <div className="space-y-6">
      {/* Smart Suggestions */}
      <SmartSuggestionsCard transactionId={t.id} />

      {/* Contract Upload Zone (when no contract) */}
      {!hasContract && !editing && (
        <ContractUploadZone transactionId={t.id} onRefresh={onRefresh} />
      )}

      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <ClosingCountdown closingDate={t.closing_date} />
        <div className="flex items-center gap-3">
          {hasContract && !editing && (
            <>
              <input ref={contractFileRef} type="file" accept=".pdf" className="hidden" onChange={handleReUpload} />
              <button
                onClick={() => contractFileRef.current?.click()}
                disabled={reUploading}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                {reUploading ? <Spinner size="sm" /> : <Upload className="w-4 h-4" />}
                {reUploading ? 'Uploading...' : 'Re-upload Contract'}
              </button>
              <button
                onClick={handleParse}
                disabled={parsing}
                className="inline-flex items-center gap-2 rounded-lg border border-purple-300 bg-purple-50 px-4 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 transition-colors disabled:opacity-50"
              >
                {parsing ? <Spinner size="sm" /> : <Sparkles className="w-4 h-4" />}
                {parsing ? 'Parsing...' : 'Re-parse'}
              </button>
            </>
          )}

          {canConfirm && !editing && (
            <button
              onClick={handleConfirm}
              disabled={confirming}
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {confirming ? <Spinner size="sm" className="text-white" /> : <CheckCircle className="w-4 h-4" />}
              {confirming ? 'Confirming...' : 'Confirm Transaction'}
            </button>
          )}

          {editing ? (
            <div className="flex items-center gap-2">
              <button
                onClick={handleCancel}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                {saving ? <Spinner size="sm" className="text-white" /> : <Save className="w-4 h-4" />}
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <Pencil className="w-4 h-4" />
              Edit
            </button>
          )}
        </div>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Property Details */}
        <Card title="Property Details" subtitle="Address and location information">
          {editing ? (
            <div className="space-y-4">
              <FormInput
                label="Street Address"
                value={form.property_address}
                onChange={(e) => handleChange('property_address', e.target.value)}
                placeholder="123 Main St"
              />
              <div className="grid grid-cols-3 gap-3">
                <FormInput
                  label="City"
                  value={form.property_city}
                  onChange={(e) => handleChange('property_city', e.target.value)}
                  placeholder="Atlanta"
                />
                <FormInput
                  label="State"
                  value={form.property_state}
                  onChange={(e) => handleChange('property_state', e.target.value)}
                  placeholder="GA"
                  maxLength={2}
                />
                <FormInput
                  label="ZIP"
                  value={form.property_zip}
                  onChange={(e) => handleChange('property_zip', e.target.value)}
                  placeholder="30301"
                  maxLength={10}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <FormSelect
                  label="Representation"
                  options={representationOptions}
                  value={form.representation_side}
                  onChange={(e) => handleChange('representation_side', e.target.value)}
                />
                <FormSelect
                  label="Financing Type"
                  options={financingOptions}
                  value={form.financing_type}
                  onChange={(e) => handleChange('financing_type', e.target.value)}
                  placeholder="Select type"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <MapPin className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-gray-900">{t.property_address || 'No address set'}</p>
                  {t.property_city && (
                    <p className="text-sm text-gray-500">
                      {t.property_city}, {t.property_state} {t.property_zip}
                      {t.property_county && ` (${t.property_county} County)`}
                    </p>
                  )}
                </div>
              </div>
              <div className="pt-3 border-t border-gray-100 grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Representation</p>
                  <p className="text-sm font-medium text-gray-900 capitalize mt-1">{t.representation_side}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Financing</p>
                  <p className="text-sm font-medium text-gray-900 uppercase mt-1">
                    {t.financing_type || 'Not specified'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* Financial Terms */}
        <Card title="Financial Terms" subtitle="Pricing and earnest money">
          {editing ? (
            <div className="space-y-4">
              <FormInput
                label="Purchase Price ($)"
                type="number"
                min="0"
                step="0.01"
                value={form.purchase_price}
                onChange={(e) => handleChange('purchase_price', e.target.value)}
                placeholder="0.00"
              />
              <FormInput
                label="Earnest Money ($)"
                type="number"
                min="0"
                step="0.01"
                value={form.earnest_money_amount}
                onChange={(e) => handleChange('earnest_money_amount', e.target.value)}
                placeholder="0.00"
              />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <DollarSign className="w-5 h-5 text-green-600 flex-shrink-0" />
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Purchase Price</p>
                  <p className="text-lg font-bold text-gray-900">{formatPrice(t.purchase_price)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <DollarSign className="w-5 h-5 text-blue-600 flex-shrink-0" />
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Earnest Money</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {formatPrice(t.earnest_money_amount)}
                    {earnestPct && (
                      <span className="text-sm font-normal text-gray-500 ml-2">({earnestPct}%)</span>
                    )}
                  </p>
                  {t.special_stipulations?.earnest_money_holder && (
                    <p className="text-xs text-gray-500 mt-0.5">Held by {t.special_stipulations.earnest_money_holder}</p>
                  )}
                </div>
              </div>
              {t.special_stipulations?.seller_concessions && (
                <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
                  <DollarSign className="w-5 h-5 text-orange-500 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Seller Concessions</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {formatCurrency(t.special_stipulations.seller_concessions)}
                    </p>
                  </div>
                </div>
              )}
              {t.special_stipulations?.home_warranty && (
                <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
                  <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Home Warranty</p>
                    <p className="text-sm font-medium text-gray-900">
                      {t.special_stipulations.home_warranty_amount
                        ? `${formatCurrency(t.special_stipulations.home_warranty_amount)} — paid by ${t.special_stipulations.home_warranty_paid_by || 'TBD'}`
                        : 'Included'}
                    </p>
                  </div>
                </div>
              )}
              <CommissionSummary transactionId={t.id} />
            </div>
          )}
        </Card>

        {/* Key Dates */}
        <Card title="Key Dates" subtitle="Important timeline information">
          {editing ? (
            <div className="space-y-4">
              <FormInput
                label="Closing Date"
                type="date"
                value={form.closing_date}
                onChange={(e) => handleChange('closing_date', e.target.value)}
              />
              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-gray-100">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Created</p>
                  <p className="text-sm text-gray-700">{formatDate(t.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Last Updated</p>
                  <p className="text-sm text-gray-700">{formatDate(t.updated_at)}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Calendar className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Closing Date</p>
                  <p className="text-sm font-medium text-gray-900">{formatDateLong(t.closing_date)}</p>
                </div>
              </div>
              {t.contract_execution_date && (
                <div className="flex items-center gap-3">
                  <Calendar className="w-5 h-5 text-green-600 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Contract Date</p>
                    <p className="text-sm font-medium text-gray-900">{formatDate(t.contract_execution_date)}</p>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4 pt-3 border-t border-gray-100">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Created</p>
                  <p className="text-sm text-gray-700">{formatDate(t.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Last Updated</p>
                  <p className="text-sm text-gray-700">{formatDate(t.updated_at)}</p>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* Contract Status */}
        <Card title="Contract Status" subtitle="Current transaction state">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <FileCheck className="w-5 h-5 text-gray-400 flex-shrink-0" />
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-700">Status:</span>
                <StatusBadge status={t.status} />
              </div>
            </div>
            {t.contract_document_url && (
              <p className="text-sm text-gray-500">Contract document uploaded</p>
            )}
            {t.special_stipulations && Object.keys(t.special_stipulations).length > 0 && (
              <div className="pt-3 border-t border-gray-100 space-y-3">
                {t.special_stipulations.contract_type && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Contract Type</p>
                    <p className="text-sm text-gray-700">{t.special_stipulations.contract_type}</p>
                  </div>
                )}
                {t.special_stipulations.contingencies && Array.isArray(t.special_stipulations.contingencies) && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Active Contingencies</p>
                    <div className="flex flex-wrap gap-1.5">
                      {t.special_stipulations.contingencies.map((c: string, i: number) => (
                        <span key={i} className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full capitalize">{c}</span>
                      ))}
                    </div>
                  </div>
                )}
                {t.special_stipulations.additional_provisions && Array.isArray(t.special_stipulations.additional_provisions) && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Additional Provisions</p>
                    <ul className="text-xs text-gray-700 space-y-1">
                      {t.special_stipulations.additional_provisions.map((p: string, i: number) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="text-gray-400 mt-0.5">•</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {t.special_stipulations.wood_infestation_report && (
                    <span className="text-xs px-2 py-0.5 bg-green-50 text-green-700 rounded-full">Wood Infestation Report</span>
                  )}
                  {t.special_stipulations.fha_va_agreement && (
                    <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded-full">FHA/VA Agreement</span>
                  )}
                  {t.special_stipulations.lead_based_paint && (
                    <span className="text-xs px-2 py-0.5 bg-yellow-50 text-yellow-700 rounded-full">Lead Paint Disclosure</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* AI Confidence */}
        {t.ai_extraction_confidence && Object.keys(t.ai_extraction_confidence).length > 0 && (
          <Card
            title="AI Extraction Confidence"
            subtitle="How confident the AI is in each parsed field"
            className="lg:col-span-2"
          >
            <div className="flex items-start gap-3 mb-4">
              <Brain className="w-5 h-5 text-purple-600 flex-shrink-0" />
              <p className="text-sm text-gray-600">
                Fields were automatically extracted from the contract document. Review any low-confidence fields.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {Object.entries(t.ai_extraction_confidence).map(([field, score]) => (
                <div key={field}>
                  <p className="text-sm text-gray-700 capitalize mb-1">{field.replace(/_/g, ' ')}</p>
                  <ConfidenceBar score={score as number} />
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
