import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Globe,
  Link2,
  Copy,
  Check,
  UserPlus,
  Shield,
  Eye,
  Upload,
  XCircle,
  CheckCircle2,
} from 'lucide-react';
import apiClient from '../lib/api';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import Modal from '../components/ui/Modal';
import { FullPageSpinner } from '../components/ui/Spinner';
import EmptyState from '../components/ui/EmptyState';

interface PortalAccess {
  id: string;
  transaction_id: string;
  party_id: string | null;
  party_name: string | null;
  party_email: string | null;
  token: string;
  permissions: string[];
  is_active: boolean;
  expires_at: string | null;
  last_accessed_at: string | null;
  created_at: string;
}

interface PortalUpload {
  id: string;
  transaction_id: string;
  uploaded_by_email: string;
  file_name: string;
  quarantine_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Never';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return '--'; }
}

export default function Portal() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [newAccess, setNewAccess] = useState({ party_email: '', permissions: ['view_timeline', 'view_documents'] });

  const { data: accesses, isLoading } = useQuery({
    queryKey: ['portal-access', id],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${id}/portal-access`);
      return res.data as PortalAccess[];
    },
    enabled: !!id,
  });

  const { data: uploads } = useQuery({
    queryKey: ['portal-uploads', id],
    queryFn: async () => {
      const res = await apiClient.get(`/transactions/${id}/portal-uploads`);
      return res.data as PortalUpload[];
    },
    enabled: !!id,
  });

  const createMutation = useMutation({
    mutationFn: async (data: { party_email: string; permissions: string[] }) => {
      const res = await apiClient.post(`/transactions/${id}/portal-access`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-access', id] });
      setShowCreateModal(false);
      setNewAccess({ party_email: '', permissions: ['view_timeline', 'view_documents'] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async (accessId: string) => {
      await apiClient.post(`/portal-access/${accessId}/revoke`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-access', id] });
    },
  });

  const reviewMutation = useMutation({
    mutationFn: async ({ uploadId, action }: { uploadId: string; action: 'approved' | 'rejected' }) => {
      await apiClient.patch(`/portal-uploads/${uploadId}/review`, { quarantine_status: action });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-uploads', id] });
    },
  });

  const copyPortalLink = (token: string, accessId: string) => {
    const url = `${window.location.origin}/portal/${token}`;
    navigator.clipboard.writeText(url);
    setCopiedId(accessId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (isLoading) return <FullPageSpinner />;

  const pendingUploads = uploads?.filter((u) => u.quarantine_status === 'pending') ?? [];

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
        title="Client Portal"
        subtitle="Share transaction progress with clients and parties"
        actions={
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            Grant Access
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Access List */}
        <div className="lg:col-span-2">
          <Card title="Portal Access" subtitle={`${accesses?.length ?? 0} active links`}>
            {!accesses || accesses.length === 0 ? (
              <EmptyState
                icon={Globe}
                title="No portal access granted"
                description="Grant access to clients so they can view transaction progress."
                action={{ label: 'Grant Access', onClick: () => setShowCreateModal(true) }}
              />
            ) : (
              <div className="space-y-3">
                {accesses.map((access) => (
                  <div key={access.id} className={`p-4 rounded-lg border ${access.is_active ? 'border-gray-200' : 'border-gray-100 bg-gray-50 opacity-60'}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {access.party_name || access.party_email || 'Unknown'}
                        </p>
                        {access.party_email && (
                          <p className="text-xs text-gray-500">{access.party_email}</p>
                        )}
                        <div className="flex flex-wrap gap-1 mt-2">
                          {access.permissions.map((p) => (
                            <span key={p} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-medium">
                              <Shield className="w-2.5 h-2.5" />
                              {p.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                        <p className="text-[10px] text-gray-400 mt-2">
                          Last accessed: {formatDate(access.last_accessed_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {access.is_active && (
                          <>
                            <button
                              onClick={() => copyPortalLink(access.token, access.id)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                              title="Copy portal link"
                            >
                              {copiedId === access.id ? (
                                <Check className="w-4 h-4 text-green-500" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                            <button
                              onClick={() => revokeMutation.mutate(access.id)}
                              className="text-xs text-red-500 hover:text-red-700 font-medium"
                            >
                              Revoke
                            </button>
                          </>
                        )}
                        {!access.is_active && (
                          <span className="text-xs text-gray-400">Revoked</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Pending Uploads */}
        <div>
          <Card title="Pending Uploads" subtitle={`${pendingUploads.length} need review`}>
            {pendingUploads.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">No uploads pending review</p>
            ) : (
              <div className="space-y-3">
                {pendingUploads.map((upload) => (
                  <div key={upload.id} className="p-3 rounded-lg border border-yellow-200 bg-yellow-50">
                    <div className="flex items-start gap-2">
                      <Upload className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-900 truncate">{upload.file_name}</p>
                        <p className="text-[10px] text-gray-500">From: {upload.uploaded_by_email}</p>
                        <div className="flex gap-2 mt-2">
                          <button
                            onClick={() => reviewMutation.mutate({ uploadId: upload.id, action: 'approved' })}
                            className="inline-flex items-center gap-1 text-[10px] font-medium text-green-600 hover:text-green-800"
                          >
                            <CheckCircle2 className="w-3 h-3" /> Approve
                          </button>
                          <button
                            onClick={() => reviewMutation.mutate({ uploadId: upload.id, action: 'rejected' })}
                            className="inline-flex items-center gap-1 text-[10px] font-medium text-red-500 hover:text-red-700"
                          >
                            <XCircle className="w-3 h-3" /> Reject
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Create Access Modal */}
      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Grant Portal Access">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Party Email</label>
            <input
              type="email"
              value={newAccess.party_email}
              onChange={(e) => setNewAccess({ ...newAccess, party_email: e.target.value })}
              placeholder="client@example.com"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Permissions</label>
            {['view_timeline', 'view_documents', 'upload_documents', 'send_messages'].map((perm) => (
              <label key={perm} className="flex items-center gap-2 mb-2">
                <input
                  type="checkbox"
                  checked={newAccess.permissions.includes(perm)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setNewAccess({ ...newAccess, permissions: [...newAccess.permissions, perm] });
                    } else {
                      setNewAccess({ ...newAccess, permissions: newAccess.permissions.filter((p) => p !== perm) });
                    }
                  }}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700 capitalize">{perm.replace(/_/g, ' ')}</span>
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => setShowCreateModal(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => createMutation.mutate(newAccess)}
              disabled={!newAccess.party_email || createMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? 'Creating...' : 'Grant Access'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
