import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  LayoutGrid,
  Clock,
  Users,
  FileText,
  ClipboardCheck,
  History,
  MessageSquare,
  Bot,
  Globe,
  FileBarChart,
} from 'lucide-react';
import apiClient from '../../lib/api';
import { TransactionDetail as TransactionDetailType, HealthScoreData } from '../../types/transaction';
import PageHeader from '../../components/ui/PageHeader';
import StatusBadge from '../../components/ui/StatusBadge';
import HealthBadge from '../../components/ui/HealthBadge';
import Tabs, { TabItem } from '../../components/ui/Tabs';
import { FullPageSpinner } from '../../components/ui/Spinner';
import OverviewTab from './OverviewTab';
import TimelineTab from './TimelineTab';
import PartiesTab from './PartiesTab';
import DocumentsTab from './DocumentsTab';
import InspectionsTab from './InspectionsTab';
import HistoryTab from './HistoryTab';
import CommunicationsTab from './CommunicationsTab';

const fetchTransaction = async (id: string): Promise<TransactionDetailType> => {
  const response = await apiClient.get<TransactionDetailType>(`/transactions/${id}`);
  return response.data;
};

const fetchHealthScore = async (id: string): Promise<HealthScoreData> => {
  const response = await apiClient.get<HealthScoreData>(`/transactions/${id}/health`);
  return response.data;
};

export default function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['transaction', id],
    queryFn: () => fetchTransaction(id!),
    enabled: !!id,
  });

  const { data: healthData } = useQuery({
    queryKey: ['health', id],
    queryFn: () => fetchHealthScore(id!),
    enabled: !!id && data?.status !== 'draft',
  });

  if (isLoading) return <FullPageSpinner />;
  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-gray-500 mb-4">Transaction not found or failed to load.</p>
        <button
          onClick={() => navigate('/')}
          className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const tabs: TabItem[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutGrid className="w-4 h-4" /> },
    { id: 'timeline', label: 'Timeline', icon: <Clock className="w-4 h-4" />, count: data.milestones.length },
    { id: 'parties', label: 'Parties', icon: <Users className="w-4 h-4" />, count: data.parties.length },
    { id: 'documents', label: 'Documents', icon: <FileText className="w-4 h-4" />, count: data.files.length },
    { id: 'inspections', label: 'Inspections', icon: <ClipboardCheck className="w-4 h-4" />, count: data.inspection_analyses.length },
    { id: 'history', label: 'History', icon: <History className="w-4 h-4" />, count: data.amendments.length },
    { id: 'communications', label: 'Comms', icon: <MessageSquare className="w-4 h-4" />, count: data.communications.length },
  ];

  return (
    <div>
      <div className="mb-4">
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </button>
      </div>

      <PageHeader
        title={data.property_address || 'Untitled Transaction'}
        subtitle={
          data.property_city
            ? `${data.property_city}, ${data.property_state} ${data.property_zip}`
            : undefined
        }
        actions={
          <div className="flex items-center gap-3">
            <HealthBadge score={healthData?.score ?? data.health_score} size="lg" />
            <StatusBadge status={data.status} />
            <span className="text-sm text-gray-500 capitalize">{data.representation_side} Side</span>
          </div>
        }
      />

      {/* Quick Action Buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        <Link
          to={`/transaction/${id}/advisor`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
        >
          <Bot className="w-4 h-4" />
          AI Advisor
        </Link>
        <Link
          to={`/transaction/${id}/portal`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
        >
          <Globe className="w-4 h-4" />
          Client Portal
        </Link>
        <Link
          to={`/transaction/${id}/documents`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
        >
          <FileBarChart className="w-4 h-4" />
          Generate Docs
        </Link>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab}>
        {(tab) => {
          switch (tab) {
            case 'overview':
              return <OverviewTab transaction={data} onRefresh={refetch} />;
            case 'timeline':
              return <TimelineTab milestones={data.milestones} transactionId={id!} onRefresh={refetch} />;
            case 'parties':
              return <PartiesTab parties={data.parties} transactionId={id!} onRefresh={refetch} />;
            case 'documents':
              return <DocumentsTab files={data.files} transactionId={id!} onRefresh={refetch} />;
            case 'inspections':
              return <InspectionsTab inspections={data.inspection_analyses} />;
            case 'history':
              return <HistoryTab amendments={data.amendments} />;
            case 'communications':
              return <CommunicationsTab communications={data.communications} transactionId={id!} onRefresh={refetch} />;
            default:
              return null;
          }
        }}
      </Tabs>
    </div>
  );
}
