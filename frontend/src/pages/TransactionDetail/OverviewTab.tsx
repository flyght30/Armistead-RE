import React, { useState } from 'react';
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
} from 'lucide-react';
import { TransactionDetail } from '../../types/transaction';
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

function formatPrice(price: Record<string, unknown> | null | undefined): string {
  if (!price) return 'Not set';
  const amount = price.amount ?? price.value;
  if (typeof amount === 'number') {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  }
  return String(amount ?? 'Not set');
}

function formatDate(dateStr: string | null | undefined): string {
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

export default function OverviewTab({ transaction, onRefresh }: OverviewTabProps) {
  const t = transaction;
  const { toast } = useToast();

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [confirming, setConfirming] = useState(false);

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
      const message =
        err instanceof Error ? err.message : 'Failed to parse contract';
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

  const canConfirm = t.status === 'draft' || t.status === 'pending_review';
  const hasContract = Boolean(t.contract_document_url);

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-end gap-3">
        {hasContract && !editing && (
          <button
            onClick={handleParse}
            disabled={parsing}
            className="inline-flex items-center gap-2 rounded-lg border border-purple-300 bg-purple-50 px-4 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 transition-colors disabled:opacity-50"
          >
            {parsing ? <Spinner size="sm" /> : <Sparkles className="w-4 h-4" />}
            {parsing ? 'Parsing...' : 'Parse Contract'}
          </button>
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
                  <p className="text-sm font-medium text-gray-900 capitalize mt-1">
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
                  <p className="text-lg font-semibold text-gray-900">{formatPrice(t.earnest_money_amount)}</p>
                </div>
              </div>
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
                  <p className="text-sm font-medium text-gray-900">{formatDate(t.closing_date)}</p>
                </div>
              </div>
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
              <div className="pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Special Stipulations</p>
                <pre className="text-xs bg-gray-50 rounded-lg p-3 text-gray-700 overflow-x-auto">
                  {JSON.stringify(t.special_stipulations, null, 2)}
                </pre>
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
