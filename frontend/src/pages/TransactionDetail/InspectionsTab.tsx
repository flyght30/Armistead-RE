import React from 'react';
import { ClipboardCheck, AlertTriangle, DollarSign } from 'lucide-react';
import { InspectionAnalysis } from '../../types/transaction';
import Card from '../../components/ui/Card';
import StatusBadge from '../../components/ui/StatusBadge';
import EmptyState from '../../components/ui/EmptyState';

interface InspectionsTabProps {
  inspections: InspectionAnalysis[];
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
  high: 1,
  medium: 2,
  low: 3,
};

function sortedItems(items: InspectionAnalysis['items']) {
  return [...items].sort((a, b) => {
    const aOrder = a.sort_order ?? severityOrder[a.severity.toLowerCase()] ?? 99;
    const bOrder = b.sort_order ?? severityOrder[b.severity.toLowerCase()] ?? 99;
    return aOrder - bOrder;
  });
}

export default function InspectionsTab({ inspections }: InspectionsTabProps) {
  if (inspections.length === 0) {
    return (
      <EmptyState
        icon={ClipboardCheck}
        title="No inspection analyses yet"
        description="Inspection reports and AI analysis will appear here once uploaded and processed."
      />
    );
  }

  return (
    <div className="space-y-8">
      {inspections.map((inspection) => (
        <div key={inspection.id} className="space-y-4">
          {/* Summary Card */}
          <Card title="Inspection Summary">
            <div className="space-y-4">
              {/* Risk Level */}
              {inspection.overall_risk_level && (
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  <span className="text-sm text-gray-600">Overall Risk Level:</span>
                  <StatusBadge status={inspection.overall_risk_level} />
                </div>
              )}

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
              subtitle="Individual findings sorted by priority"
              padding={false}
            >
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Severity
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Description
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Location
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Est. Cost
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Repair Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Recommendation
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sortedItems(inspection.items).map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <StatusBadge status={item.severity} />
                        </td>
                        <td className="px-6 py-4">
                          <p className="text-sm text-gray-900 max-w-xs">{item.description}</p>
                          {item.risk_assessment && (
                            <p className="text-xs text-gray-500 mt-1">
                              Risk: {item.risk_assessment}
                            </p>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-gray-700">{item.location || '—'}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-gray-900">
                            {formatCostRange(item.estimated_cost_low, item.estimated_cost_high)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {item.repair_status ? (
                            <StatusBadge status={item.repair_status} />
                          ) : (
                            <span className="text-sm text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
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
      ))}
    </div>
  );
}
