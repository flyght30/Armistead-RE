import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText } from 'lucide-react';
import apiClient from '../lib/api';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import FormInput from '../components/ui/FormInput';
import FormSelect from '../components/ui/FormSelect';
import Spinner from '../components/ui/Spinner';
import { useToast } from '../components/ui/ToastContext';
import TemplatePicker from '../components/TemplatePicker';

// A fixed agent_id for dev mode (matches seed.py)
const DEV_AGENT_ID = '00000000-0000-0000-0000-000000000001';

type Mode = 'upload' | 'manual';

const sideOptions = [
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

const NewTransaction: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<Mode>('upload');
  const [submitting, setSubmitting] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Template picker state (shown after creating a transaction)
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [createdTxnId, setCreatedTxnId] = useState<string | null>(null);
  const [createdTxnMeta, setCreatedTxnMeta] = useState<{
    stateCode?: string;
    financingType?: string;
    representationSide?: string;
  }>({});

  // Upload mode state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadSide, setUploadSide] = useState('buyer');

  // Manual mode state
  const [form, setForm] = useState({
    representation_side: 'buyer',
    property_address: '',
    property_city: '',
    property_state: '',
    property_zip: '',
    financing_type: 'conventional',
    purchase_price: '',
    earnest_money: '',
    closing_date: '',
  });

  const updateField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  // --- Upload mode handlers ---

  const handleFileSelect = (file: File) => {
    if (file.type !== 'application/pdf') {
      toast('error', 'Only PDF files are accepted');
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) {
      toast('error', 'Please select a contract PDF to upload');
      return;
    }

    setSubmitting(true);
    try {
      // Step 1: Create minimal transaction
      const txResponse = await apiClient.post('/transactions', {
        agent_id: DEV_AGENT_ID,
        representation_side: uploadSide,
      });
      const txId = txResponse.data.id;

      // Step 2: Upload file
      const formData = new FormData();
      formData.append('file', selectedFile);
      await apiClient.post(`/transactions/${txId}/files`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // Step 3: Trigger AI parse
      await apiClient.post(`/transactions/${txId}/parse`);

      toast('success', 'Contract uploaded and parsing started');
      // Show template picker before navigating
      setCreatedTxnId(txId);
      setCreatedTxnMeta({ representationSide: uploadSide });
      setShowTemplatePicker(true);
    } catch (error) {
      console.error('Upload flow error:', error);
      toast('error', 'Failed to upload and parse contract. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // --- Manual mode handler ---

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const payload: Record<string, unknown> = {
        agent_id: DEV_AGENT_ID,
        representation_side: form.representation_side,
        financing_type: form.financing_type || null,
        property_address: form.property_address || null,
        property_city: form.property_city || null,
        property_state: form.property_state || null,
        property_zip: form.property_zip || null,
        purchase_price: form.purchase_price
          ? { amount: parseFloat(form.purchase_price) }
          : null,
        earnest_money_amount: form.earnest_money
          ? { amount: parseFloat(form.earnest_money) }
          : null,
        closing_date: form.closing_date
          ? new Date(form.closing_date).toISOString()
          : null,
      };

      const response = await apiClient.post('/transactions', payload);
      toast('success', 'Transaction created successfully');
      // Show template picker before navigating
      setCreatedTxnId(response.data.id);
      setCreatedTxnMeta({
        stateCode: form.property_state?.toUpperCase() || undefined,
        financingType: form.financing_type || undefined,
        representationSide: form.representation_side || undefined,
      });
      setShowTemplatePicker(true);
    } catch (error) {
      console.error('Manual creation error:', error);
      toast('error', 'Failed to create transaction. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // --- Tab button helper ---

  const tabClass = (tabMode: Mode) =>
    `px-5 py-2.5 text-sm font-medium rounded-lg transition-colors ${
      mode === tabMode
        ? 'bg-indigo-600 text-white shadow-sm'
        : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
    }`;

  return (
    <div>
      <PageHeader
        title="New Transaction"
        subtitle="Create a new real estate transaction"
      />

      {/* Mode toggle tabs */}
      <div className="flex items-center gap-2 mb-6">
        <button
          type="button"
          className={tabClass('upload')}
          onClick={() => setMode('upload')}
          disabled={submitting}
        >
          <span className="inline-flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload Contract
          </span>
        </button>
        <button
          type="button"
          className={tabClass('manual')}
          onClick={() => setMode('manual')}
          disabled={submitting}
        >
          <span className="inline-flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Enter Manually
          </span>
        </button>
      </div>

      {/* ===== UPLOAD MODE ===== */}
      {mode === 'upload' && (
        <div className="max-w-2xl space-y-6">
          <Card title="Upload Contract PDF">
            <div className="space-y-4">
              <FormSelect
                label="Representation Side"
                options={sideOptions}
                value={uploadSide}
                onChange={(e) => setUploadSide(e.target.value)}
                disabled={submitting}
              />

              {/* Drag-and-drop zone */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Contract File
                </label>
                <div
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={handleBrowseClick}
                  className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 cursor-pointer transition-colors ${
                    dragOver
                      ? 'border-indigo-500 bg-indigo-50'
                      : selectedFile
                        ? 'border-green-400 bg-green-50'
                        : 'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={handleFileInputChange}
                    disabled={submitting}
                  />

                  {selectedFile ? (
                    <>
                      <FileText className="w-10 h-10 text-green-500 mb-2" />
                      <p className="text-sm font-medium text-gray-900">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      <p className="text-xs text-indigo-600 mt-2">
                        Click or drop another file to replace
                      </p>
                    </>
                  ) : (
                    <>
                      <Upload className="w-10 h-10 text-gray-400 mb-2" />
                      <p className="text-sm text-gray-600">
                        <span className="font-medium text-indigo-600">
                          Browse files
                        </span>{' '}
                        or drag and drop
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        PDF files only
                      </p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Upload actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/')}
              disabled={submitting}
              className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleUploadSubmit}
              disabled={submitting || !selectedFile}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? (
                <>
                  <Spinner size="sm" className="text-white" />
                  Uploading & Parsing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload & Parse
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ===== MANUAL MODE ===== */}
      {mode === 'manual' && (
        <form onSubmit={handleManualSubmit} className="max-w-2xl space-y-6">
          {/* Representation */}
          <Card title="Transaction Type">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormSelect
                label="Representation Side"
                options={sideOptions}
                value={form.representation_side}
                onChange={(e) =>
                  updateField('representation_side', e.target.value)
                }
                disabled={submitting}
              />
              <FormSelect
                label="Financing Type"
                options={financingOptions}
                value={form.financing_type}
                onChange={(e) => updateField('financing_type', e.target.value)}
                disabled={submitting}
              />
            </div>
          </Card>

          {/* Property Details */}
          <Card title="Property Information">
            <div className="space-y-4">
              <FormInput
                label="Street Address"
                placeholder="123 Main Street"
                value={form.property_address}
                onChange={(e) =>
                  updateField('property_address', e.target.value)
                }
                disabled={submitting}
              />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <FormInput
                  label="City"
                  placeholder="Atlanta"
                  value={form.property_city}
                  onChange={(e) =>
                    updateField('property_city', e.target.value)
                  }
                  disabled={submitting}
                />
                <FormInput
                  label="State"
                  placeholder="GA"
                  value={form.property_state}
                  onChange={(e) =>
                    updateField('property_state', e.target.value)
                  }
                  maxLength={2}
                  disabled={submitting}
                />
                <FormInput
                  label="ZIP Code"
                  placeholder="30301"
                  value={form.property_zip}
                  onChange={(e) => updateField('property_zip', e.target.value)}
                  maxLength={10}
                  disabled={submitting}
                />
              </div>
            </div>
          </Card>

          {/* Financial */}
          <Card title="Financial Details">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormInput
                label="Purchase Price ($)"
                type="number"
                placeholder="450000"
                value={form.purchase_price}
                onChange={(e) =>
                  updateField('purchase_price', e.target.value)
                }
                disabled={submitting}
              />
              <FormInput
                label="Earnest Money ($)"
                type="number"
                placeholder="10000"
                value={form.earnest_money}
                onChange={(e) =>
                  updateField('earnest_money', e.target.value)
                }
                disabled={submitting}
              />
            </div>
            <div className="mt-4">
              <FormInput
                label="Closing Date"
                type="date"
                value={form.closing_date}
                onChange={(e) => updateField('closing_date', e.target.value)}
                disabled={submitting}
              />
            </div>
          </Card>

          {/* Manual actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/')}
              disabled={submitting}
              className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? (
                <>
                  <Spinner size="sm" className="text-white" />
                  Creating...
                </>
              ) : (
                'Create Transaction'
              )}
            </button>
          </div>
        </form>
      )}

      {/* Template Picker Modal — shown after creating a transaction */}
      {createdTxnId && (
        <TemplatePicker
          isOpen={showTemplatePicker}
          onClose={() => {
            setShowTemplatePicker(false);
            navigate(`/transaction/${createdTxnId}`);
          }}
          transactionId={createdTxnId}
          stateCode={createdTxnMeta.stateCode}
          financingType={createdTxnMeta.financingType}
          representationSide={createdTxnMeta.representationSide}
          onApplied={(result) => {
            toast(
              'success',
              `Template applied: ${result.milestones_created} milestones created${
                result.milestones_skipped > 0
                  ? `, ${result.milestones_skipped} skipped`
                  : ''
              }`
            );
            navigate(`/transaction/${createdTxnId}`);
          }}
        />
      )}
    </div>
  );
};

export default NewTransaction;
