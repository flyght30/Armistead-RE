import React from 'react';
import { MessageSquare, Mail, Phone } from 'lucide-react';
import { Communication } from '../../types/transaction';
import StatusBadge from '../../components/ui/StatusBadge';
import EmptyState from '../../components/ui/EmptyState';

interface CommunicationsTabProps {
  communications: Communication[];
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

const typeIcon: Record<string, React.ReactNode> = {
  email: <Mail className="w-5 h-5 text-blue-500" />,
  sms: <Phone className="w-5 h-5 text-green-500" />,
};

export default function CommunicationsTab({ communications }: CommunicationsTabProps) {
  if (communications.length === 0) {
    return (
      <EmptyState
        icon={MessageSquare}
        title="No communications yet"
        description="Emails, SMS messages, and other communications will be tracked here."
      />
    );
  }

  const sorted = [...communications].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-4 max-w-3xl">
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
  );
}
