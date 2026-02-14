import React, { useState, useEffect } from 'react';
import apiClient from '../lib/api';
import { MilestoneTemplate } from '../types/transaction';
import Modal from './ui/Modal';
import Spinner from './ui/Spinner';

interface TemplatePickerProps {
  isOpen: boolean;
  onClose: () => void;
  transactionId: string;
  stateCode?: string;
  financingType?: string;
  representationSide?: string;
  onApplied: (result: { milestones_created: number; milestones_skipped: number }) => void;
}

export default function TemplatePicker({
  isOpen,
  onClose,
  transactionId,
  stateCode,
  financingType,
  representationSide,
  onApplied,
}: TemplatePickerProps) {
  const [templates, setTemplates] = useState<MilestoneTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [contractDate, setContractDate] = useState(new Date().toISOString().split('T')[0]);
  const [closingDate, setClosingDate] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
    }
  }, [isOpen, stateCode, financingType, representationSide]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (stateCode) params.state_code = stateCode;
      if (financingType) params.financing_type = financingType;
      if (representationSide) params.representation_side = representationSide;

      const res = await apiClient.get('/templates/milestones', { params });
      setTemplates(res.data);
    } catch {
      setError('Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!selectedTemplate) return;
    setApplying(true);
    setError(null);

    try {
      const body: Record<string, string> = {
        template_id: selectedTemplate,
        contract_execution_date: new Date(contractDate).toISOString(),
      };
      if (closingDate) {
        body.closing_date = new Date(closingDate).toISOString();
      }

      const res = await apiClient.post(`/transactions/${transactionId}/apply-template`, body);
      onApplied(res.data);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to apply template');
    } finally {
      setApplying(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Apply Milestone Template">
      <div className="space-y-4">
        {loading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : templates.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">
            No templates available{stateCode ? ` for ${stateCode}` : ''}. Templates can be created from the admin panel.
          </p>
        ) : (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Select Template</label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {templates.map(t => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTemplate(t.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedTemplate === t.id
                        ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900">{t.name}</span>
                      <span className="text-xs text-gray-500">{t.item_count || '?'} milestones</span>
                    </div>
                    {t.description && (
                      <p className="text-xs text-gray-500 mt-1">{t.description}</p>
                    )}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contract Date</label>
                <input
                  type="date"
                  value={contractDate}
                  onChange={e => setContractDate(e.target.value)}
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Closing Date <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  type="date"
                  value={closingDate}
                  onChange={e => setClosingDate(e.target.value)}
                  className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            {!closingDate && (
              <p className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg">
                Without a closing date, milestones that reference the closing date will be created without due dates and marked as "Pending Date."
              </p>
            )}

            {error && (
              <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
            )}
          </>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={!selectedTemplate || applying}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {applying ? 'Applying...' : 'Apply Template'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
