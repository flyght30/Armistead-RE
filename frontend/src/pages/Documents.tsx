import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  FileText,
  Download,
  Eye,
  Loader2,
  Plus,
  ClipboardList,
  FileBarChart,
  Receipt,
  ClipboardCheck,
  ScrollText,
} from 'lucide-react';
import apiClient from '../lib/api';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import { FullPageSpinner } from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';

interface DocumentTemplate {
  id: string;
  name: string;
  document_type: string;
  description: string;
}

interface GeneratedDocument {
  id: string;
  transaction_id: string;
  document_type: string;
  title: string;
  file_url: string | null;
  html_content: string | null;
  created_at: string;
}

const docTypeIcons: Record<string, React.ReactNode> = {
  closing_checklist: <ClipboardList className="w-5 h-5 text-blue-500" />,
  amendment_summary: <ScrollText className="w-5 h-5 text-purple-500" />,
  commission_statement: <Receipt className="w-5 h-5 text-green-500" />,
  inspection_report: <ClipboardCheck className="w-5 h-5 text-orange-500" />,
  transaction_summary: <FileBarChart className="w-5 h-5 text-indigo-500" />,
};

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return '--'; }
}

export default function Documents() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);

  const { data: templates } = useQuery({
    queryKey: ['doc-templates'],
    queryFn: async () => {
      const res = await apiClient.get('/document-templates');
      return res.data as DocumentTemplate[];
    },
  });

  const { data: generated, isLoading } = useQuery({
    queryKey: ['generated-docs', id],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${id}/documents`);
      return res.data as GeneratedDocument[];
    },
    enabled: !!id,
  });

  const generateMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const res = await apiClient.post(`/transactions/${id}/documents/generate`, {
        template_id: templateId,
      });
      return res.data as GeneratedDocument;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['generated-docs', id] });
    },
  });

  const previewMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const res = await apiClient.post(`/transactions/${id}/documents/preview`, {
        template_id: templateId,
      });
      return res.data as { html_content: string };
    },
    onSuccess: (data) => {
      setPreviewHtml(data.html_content);
    },
  });

  if (isLoading) return <FullPageSpinner />;

  return (
    <div>
      <div className="mb-4">
        <button
          onClick={() => navigate(`/transaction/${id}`)}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Transaction
        </button>
      </div>

      <PageHeader
        title="Document Generation"
        subtitle="Generate and manage transaction documents"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Templates */}
        <div>
          <Card title="Templates" subtitle="Click to generate">
            <div className="space-y-2">
              {(templates ?? []).map((tmpl) => (
                <div key={tmpl.id} className="p-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/50 transition-colors">
                  <div className="flex items-start gap-3">
                    {docTypeIcons[tmpl.document_type] || <FileText className="w-5 h-5 text-gray-400" />}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{tmpl.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{tmpl.description}</p>
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => previewMutation.mutate(tmpl.id)}
                          disabled={previewMutation.isPending}
                          className="inline-flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gray-800"
                        >
                          <Eye className="w-3 h-3" /> Preview
                        </button>
                        <button
                          onClick={() => generateMutation.mutate(tmpl.id)}
                          disabled={generateMutation.isPending}
                          className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800"
                        >
                          {generateMutation.isPending ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Plus className="w-3 h-3" />
                          )}
                          Generate
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {(!templates || templates.length === 0) && (
                <p className="text-sm text-gray-400 text-center py-4">No templates available</p>
              )}
            </div>
          </Card>
        </div>

        {/* Generated Documents */}
        <div className="lg:col-span-2">
          <Card title="Generated Documents" subtitle={`${generated?.length ?? 0} documents`}>
            {!generated || generated.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="No documents generated yet"
                description="Select a template from the left to generate a document."
              />
            ) : (
              <div className="space-y-3">
                {[...generated].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).map((doc) => (
                  <div key={doc.id} className="flex items-center gap-4 p-4 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
                    {docTypeIcons[doc.document_type] || <FileText className="w-5 h-5 text-gray-400" />}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{doc.title}</p>
                      <p className="text-xs text-gray-500">{formatDate(doc.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {doc.html_content && (
                        <button
                          onClick={() => setPreviewHtml(doc.html_content)}
                          className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                          title="Preview"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      )}
                      {doc.file_url && (
                        <a
                          href={doc.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Preview Panel */}
      {previewHtml && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Document Preview</h2>
              <button
                onClick={() => setPreviewHtml(null)}
                className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
            <div className="overflow-y-auto p-8">
              <div
                className="prose max-w-none"
                dangerouslySetInnerHTML={{ __html: previewHtml }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
