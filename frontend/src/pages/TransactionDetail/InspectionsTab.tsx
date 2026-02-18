import React, { useState, useRef } from 'react';
import { ClipboardCheck, AlertTriangle, DollarSign, Upload, FileText, Wrench, ChevronDown } from 'lucide-react';
import { InspectionAnalysis } from '../../types/transaction';
import Card from '../../components/ui/Card';
import StatusBadge from '../../components/ui/StatusBadge';
import EmptyState from '../../components/ui/EmptyState';
import Spinner from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/ToastContext';
import apiClient from '../../lib/api';

interface InspectionsTabProps {
  inspections: InspectionAnalysis[];
  transactionId: string;
  onRefresh: () => void;
}

function extractAmount(dict: Record<string, unknown> | null | undefined): number | null {
  if (!dict || typeof dict !== 'object') return null;
  const amount = dict.amount;
  return typeof amount === 'number' ? amount : null;
}

function formatCurrency(dict: Record<string, unknown> | null | undefined): string {
  const amount = extractAmount(dict);
  if (amount == null) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatCostRange(
  low: Record<string, unknown> | null | undefined,
  high: Record<string, unknown> | null | undefined,
): string {
  const lowStr = formatCurrency(low);
  const highStr = formatCurrency(high);
  if (lowStr === 'N/A' && highStr === 'N/A') return 'N/A';
  if (lowStr === 'N/A') return highStr;
  if (highStr === 'N/A') return lowStr;
  return `${lowStr} – ${highStr}`;
}

const severityOrder: Record<string, number> = {
  critical: 0,
  major: 1,
  moderate: 2,
  minor: 3,
};

function sortedItems(items: InspectionAnalysis['items']) {
  return [...items].sort((a, b) => {
    const aOrder = severityOrder[a.severity.toLowerCase()] ?? 99;
    const bOrder = severityOrder[b.severity.toLowerCase()] ?? 99;
    if (aOrder !== bOrder) return aOrder - bOrder;
    return (a.sort_order ?? 0) - (b.sort_order ?? 0);
  });
}

function severityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical': return 'bg-red-100 text-red-700';
    case 'major': return 'bg-orange-100 text-orange-700';
    case 'moderate': return 'bg-yellow-100 text-yellow-700';
    case 'minor': return 'bg-blue-100 text-blue-700';
    default: return 'bg-gray-100 text-gray-700';
  }
}

function repairStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed': return 'bg-green-100 text-green-700';
    case 'in_progress': return 'bg-yellow-100 text-yellow-700';
    default: return 'bg-gray-100 text-gray-600';
  }
}

const REPAIR_STATUSES = [
  { value: 'pending', label: 'Pending', color: 'text-gray-600' },
  { value: 'in_progress', label: 'In Progress', color: 'text-yellow-700' },
  { value: 'completed', label: 'Completed', color: 'text-green-700' },
];

function RepairStatusDropdown({
  itemId,
  currentStatus,
  onUpdate,
}: {
  itemId: string;
  currentStatus: string;
  onUpdate: () => void;
}) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [updating, setUpdating] = useState(false);

  async function changeStatus(newStatus: string) {
    if (newStatus === currentStatus) {
      setOpen(false);
      return;
    }
    setUpdating(true);
    try {
      await apiClient.patch(`/inspection-items/${itemId}`, { repair_status: newStatus });
      toast('success', `Status updated to ${newStatus.replace('_', ' ')}`);
      onUpdate();
    } catch {
      toast('error', 'Failed to update status');
    } finally {
      setUpdating(false);
      setOpen(false);
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={updating}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer hover:ring-2 hover:ring-indigo-200 transition-all ${repairStatusColor(currentStatus)} ${updating ? 'opacity-50' : ''}`}
      >
        {updating ? (
          <Spinner size="sm" />
        ) : (
          <>
            {currentStatus.replace('_', ' ')}
            <ChevronDown className="w-3 h-3" />
          </>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]">
            {REPAIR_STATUSES.map((s) => (
              <button
                key={s.value}
                onClick={() => changeStatus(s.value)}
                className={`w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50 transition-colors ${
                  s.value === currentStatus ? 'font-semibold bg-gray-50' : ''
                } ${s.color}`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function InspectionsTab({ inspections, transactionId, onRefresh }: InspectionsTabProps) {
  const { toast } = useToast();
  const [uploadingInspection, setUploadingInspection] = useState(false);
  const [uploadingAddendum, setUploadingAddendum] = useState(false);
  const inspectionFileRef = useRef<HTMLInputElement>(null);
  const addendumFileRef = useRef<HTMLInputElement>(null);

  async function handleInspectionUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingInspection(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiClient.post(
        `/transactions/${transactionId}/files/upload-inspection`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 },
      );
      const data = res.data;
      toast('success', `Inspection parsed: ${data.items_created} findings extracted (${data.overall_risk_level} risk)`);
      onRefresh();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || (err instanceof Error ? err.message : 'Failed to parse inspection');
      toast('error', message);
    } finally {
      setUploadingInspection(false);
      if (inspectionFileRef.current) inspectionFileRef.current.value = '';
    }
  }

  async function handleAddendumUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingAddendum(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiClient.post(
        `/transactions/${transactionId}/files/upload-addendum`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 },
      );
      const data = res.data;
      toast(
        'success',
        `${data.addendum_type.replace('_', ' ')}: ${data.items_parsed} items parsed, ${data.items_matched_to_inspection} matched to inspection`,
      );
      onRefresh();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || (err instanceof Error ? err.message : 'Failed to parse addendum');
      toast('error', message);
    } finally {
      setUploadingAddendum(false);
      if (addendumFileRef.current) addendumFileRef.current.value = '';
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload Action Bar */}
      <div className="flex flex-wrap items-center gap-3">
        <input ref={inspectionFileRef} type="file" accept=".pdf" className="hidden" onChange={handleInspectionUpload} />
        <button
          onClick={() => inspectionFileRef.current?.click()}
          disabled={uploadingInspection}
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-300 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 transition-colors disabled:opacity-50"
        >
          {uploadingInspection ? <Spinner size="sm" /> : <Upload className="w-4 h-4" />}
          {uploadingInspection ? 'Parsing Report...' : 'Upload Inspection Report'}
        </button>

        <input ref={addendumFileRef} type="file" accept=".pdf" className="hidden" onChange={handleAddendumUpload} />
        <button
          onClick={() => addendumFileRef.current?.click()}
          disabled={uploadingAddendum}
          className="inline-flex items-center gap-2 rounded-lg border border-orange-300 bg-orange-50 px-4 py-2 text-sm font-medium text-orange-700 hover:bg-orange-100 transition-colors disabled:opacity-50"
        >
          {uploadingAddendum ? <Spinner size="sm" /> : <Wrench className="w-4 h-4" />}
          {uploadingAddendum ? 'Parsing Addendum...' : 'Upload Repair Addendum'}
        </button>
      </div>

      {inspections.length === 0 ? (
        <EmptyState
          icon={ClipboardCheck}
          title="No inspection analyses yet"
          description="Upload a home inspection report PDF above and the AI will extract all findings, categorize them by severity, and estimate repair costs."
        />
      ) : (
        inspections.map((inspection) => (
          <div key={inspection.id} className="space-y-4">
            {/* Summary Card */}
            <Card title="Inspection Summary">
              <div className="space-y-4">
                {/* Risk Level + Stats */}
                <div className="flex items-center gap-4 flex-wrap">
                  {inspection.overall_risk_level && (
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-gray-400 flex-shrink-0" />
                      <span className="text-sm text-gray-600">Risk:</span>
                      <StatusBadge status={inspection.overall_risk_level} />
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">{inspection.items.length} findings</span>
                  </div>
                  {inspection.items.length > 0 && (() => {
                    const completed = inspection.items.filter(i => i.repair_status === 'completed').length;
                    const inProgress = inspection.items.filter(i => i.repair_status === 'in_progress').length;
                    const total = inspection.items.length;
                    return (completed > 0 || inProgress > 0) ? (
                      <div className="flex items-center gap-2">
                        <Wrench className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-600">
                          {completed}/{total} repaired{inProgress > 0 ? `, ${inProgress} in progress` : ''}
                        </span>
                      </div>
                    ) : null;
                  })()}
                </div>

                {/* Repair Progress Bar */}
                {inspection.items.length > 0 && (() => {
                  const completed = inspection.items.filter(i => i.repair_status === 'completed').length;
                  const inProgress = inspection.items.filter(i => i.repair_status === 'in_progress').length;
                  const total = inspection.items.length;
                  if (completed === 0 && inProgress === 0) return null;
                  const completedPct = (completed / total) * 100;
                  const inProgressPct = (inProgress / total) * 100;
                  return (
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="h-2 rounded-full flex overflow-hidden">
                        {completedPct > 0 && (
                          <div className="bg-green-500 h-2" style={{ width: `${completedPct}%` }} />
                        )}
                        {inProgressPct > 0 && (
                          <div className="bg-yellow-400 h-2" style={{ width: `${inProgressPct}%` }} />
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* Executive Summary */}
                {inspection.executive_summary && (
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {inspection.executive_summary}
                  </p>
                )}

                {/* Total Estimated Cost Range */}
                {(extractAmount(inspection.total_estimated_cost_low) != null ||
                  extractAmount(inspection.total_estimated_cost_high) != null) && (
                  <div className="flex items-center gap-3 pt-3 border-t border-gray-100">
                    <DollarSign className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">
                        Total Estimated Repair Costs
                      </p>
                      <p className="text-lg font-bold text-gray-900">
                        {formatCostRange(
                          inspection.total_estimated_cost_low,
                          inspection.total_estimated_cost_high,
                        )}
                      </p>
                    </div>
                  </div>
                )}

                {/* Report Link */}
                {inspection.report_document_url && (
                  <div className="pt-3 border-t border-gray-100">
                    <a
                      href={inspection.report_document_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-500 transition-colors"
                    >
                      <ClipboardCheck className="w-4 h-4" />
                      View Full Inspection Report
                    </a>
                  </div>
                )}
              </div>
            </Card>

            {/* Items Table */}
            {inspection.items.length > 0 && (
              <Card
                title={`Inspection Items (${inspection.items.length})`}
                subtitle="Click repair status to change it"
                padding={false}
              >
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Severity
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Description
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Location
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Est. Cost
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Action
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sortedItems(inspection.items).map((item) => (
                        <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${severityColor(item.severity)}`}>
                              {item.severity}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <p className="text-sm text-gray-900 max-w-sm">{item.description}</p>
                            {item.risk_assessment && (
                              <p className="text-xs text-gray-500 mt-1">{item.risk_assessment}</p>
                            )}
                            {item.report_reference && (
                              <p className="text-xs text-indigo-500 mt-0.5">Ref: {item.report_reference}</p>
                            )}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="text-sm text-gray-700">{item.location || '—'}</span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="text-sm text-gray-900">
                              {formatCostRange(item.estimated_cost_low, item.estimated_cost_high)}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <RepairStatusDropdown
                              itemId={item.id}
                              currentStatus={item.repair_status}
                              onUpdate={onRefresh}
                            />
                          </td>
                          <td className="px-4 py-3">
                            <p className="text-sm text-gray-700 max-w-xs">
                              {item.recommendation || '—'}
                            </p>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        ))
      )}
    </div>
  );
}
