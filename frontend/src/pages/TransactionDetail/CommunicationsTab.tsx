import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, Mail, Phone, Plus, Send, Loader2, Trash2, Edit3 } from 'lucide-react';
import { Communication } from '../../types/transaction';
import StatusBadge from '../../components/ui/StatusBadge';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';
import apiClient from '../../lib/api';

interface CommunicationsTabProps {
  communications: Communication[];
  transactionId?: string;
  onRefresh?: () => void;
}

interface EmailDraft {
  id: string;
  transaction_id: string;
  to_email: string;
  subject: string;
  body_html: string;
  status: string;
  created_at: string;
  sent_at: string | null;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return ''; }
}

const typeIcon: Record<string, React.ReactNode> = {
  email: <Mail className="w-5 h-5 text-blue-500" />,
  sms: <Phone className="w-5 h-5 text-green-500" />,
};

const draftStatusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  approved: 'bg-blue-100 text-blue-700',
  sent: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-600',
};

export default function CommunicationsTab({ communications, transactionId, onRefresh }: CommunicationsTabProps) {
  const queryClient = useQueryClient();
  const [showComposer, setShowComposer] = useState(false);
  const [activeView, setActiveView] = useState<'sent' | 'drafts'>('sent');
  const [composerData, setComposerData] = useState({
    to_email: '',
    subject: '',
    body_html: '',
    transaction_id: transactionId || '',
  });

  const { data: drafts } = useQuery({
    queryKey: ['email-drafts', transactionId],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${transactionId}/email-drafts`);
      return res.data as EmailDraft[];
    },
    enabled: !!transactionId,
  });

  const createDraftMutation = useMutation({
    mutationFn: async (data: typeof composerData) => {
      const res = await apiClient.post('/email-drafts', data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-drafts', transactionId] });
      setShowComposer(false);
      setComposerData({ to_email: '', subject: '', body_html: '', transaction_id: transactionId || '' });
      setActiveView('drafts');
    },
  });

  const sendDraftMutation = useMutation({
    mutationFn: async (draftId: string) => {
      const res = await apiClient.post(`/email-drafts/${draftId}/send`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-drafts', transactionId] });
      onRefresh?.();
    },
  });

  const deleteDraftMutation = useMutation({
    mutationFn: async (draftId: string) => {
      await apiClient.delete(`/email-drafts/${draftId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-drafts', transactionId] });
    },
  });

  const sorted = [...communications].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  const pendingDrafts = drafts?.filter((d) => d.status !== 'sent') ?? [];
  const sentDrafts = drafts?.filter((d) => d.status === 'sent') ?? [];

  return (
    <div className="max-w-3xl">
      {/* Tab Bar + Compose Button */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveView('sent')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeView === 'sent' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            Sent ({sorted.length + sentDrafts.length})
          </button>
          <button
            onClick={() => setActiveView('drafts')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeView === 'drafts' ? 'bg-indigo-100 text-indigo-700' : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            Drafts ({pendingDrafts.length})
          </button>
        </div>
        <button
          onClick={() => setShowComposer(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Compose
        </button>
      </div>

      {/* Sent View */}
      {activeView === 'sent' && (
        <>
          {sorted.length === 0 && sentDrafts.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="No communications yet"
              description="Compose an email to get started."
              action={{ label: 'Compose Email', onClick: () => setShowComposer(true) }}
            />
          ) : (
            <div className="space-y-4">
              {sorted.map((comm) => (
                <div key={comm.id} className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {typeIcon[comm.type] || <MessageSquare className="w-5 h-5 text-gray-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">
                            {comm.subject || `${comm.type.toUpperCase()} Communication`}
                          </p>
                          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                            <span>To: {comm.recipient_email}</span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <StatusBadge status={comm.status} />
                          <time className="text-xs text-gray-400">
                            {formatDate(comm.sent_at || comm.created_at)}
                          </time>
                        </div>
                      </div>
                      {comm.body && (
                        <p className="text-sm text-gray-600 mt-3 whitespace-pre-wrap">{comm.body}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Drafts View */}
      {activeView === 'drafts' && (
        <>
          {pendingDrafts.length === 0 ? (
            <EmptyState
              icon={Edit3}
              title="No drafts"
              description="Compose an email to create a draft."
              action={{ label: 'Compose', onClick: () => setShowComposer(true) }}
            />
          ) : (
            <div className="space-y-3">
              {pendingDrafts.map((draft) => (
                <div key={draft.id} className="bg-white rounded-xl border border-gray-200 p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900">{draft.subject || '(No subject)'}</p>
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium ${draftStatusColors[draft.status] || 'bg-gray-100 text-gray-600'}`}>
                          {draft.status}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">To: {draft.to_email}</p>
                      {draft.body_html && (
                        <p className="text-xs text-gray-400 mt-1 truncate">{draft.body_html.replace(/<[^>]*>/g, '').slice(0, 100)}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 ml-4">
                      <button
                        onClick={() => sendDraftMutation.mutate(draft.id)}
                        disabled={sendDraftMutation.isPending}
                        className="p-1.5 rounded-lg hover:bg-green-50 text-green-600 hover:text-green-700 transition-colors"
                        title="Send"
                      >
                        {sendDraftMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Send className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => deleteDraftMutation.mutate(draft.id)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-red-400 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Compose Modal */}
      <Modal isOpen={showComposer} onClose={() => setShowComposer(false)} title="Compose Email" maxWidth="lg">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
            <input
              type="email"
              value={composerData.to_email}
              onChange={(e) => setComposerData({ ...composerData, to_email: e.target.value })}
              placeholder="recipient@example.com"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
            <input
              type="text"
              value={composerData.subject}
              onChange={(e) => setComposerData({ ...composerData, subject: e.target.value })}
              placeholder="Email subject"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Body</label>
            <textarea
              value={composerData.body_html}
              onChange={(e) => setComposerData({ ...composerData, body_html: e.target.value })}
              placeholder="Write your email..."
              rows={8}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => setShowComposer(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => createDraftMutation.mutate(composerData)}
              disabled={!composerData.to_email || !composerData.subject || createDraftMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {createDraftMutation.isPending ? 'Saving...' : 'Save Draft'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
