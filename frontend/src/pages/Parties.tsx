import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Users, Search, Mail, Phone, Building2 } from 'lucide-react';
import apiClient from '../lib/api';
import { Transaction } from '../types/transaction';
import { Party } from '../types/party';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import DataTable, { Column } from '../components/ui/DataTable';
import StatusBadge from '../components/ui/StatusBadge';
import EmptyState from '../components/ui/EmptyState';
import { FullPageSpinner } from '../components/ui/Spinner';

interface TransactionListResponse {
  items: Transaction[];
  pagination: { page: number; limit: number };
}

interface PartyWithTransaction extends Party {
  transaction_address?: string;
}

const fetchAllParties = async (): Promise<PartyWithTransaction[]> => {
  const response = await apiClient.get<TransactionListResponse>('/transactions', {
    params: { limit: 100 },
  });
  const parties: PartyWithTransaction[] = [];
  for (const txn of response.data.items) {
    for (const party of txn.parties) {
      parties.push({
        ...party,
        transaction_address: txn.property_address || 'Untitled',
      });
    }
  }
  return parties;
};

export default function Parties() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: parties, isLoading } = useQuery({
    queryKey: ['all-parties'],
    queryFn: fetchAllParties,
  });

  const filteredParties = useMemo(() => {
    if (!parties) return [];
    if (!searchQuery) return parties;
    const q = searchQuery.toLowerCase();
    return parties.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.email.toLowerCase().includes(q) ||
        (p.company || '').toLowerCase().includes(q)
    );
  }, [parties, searchQuery]);

  const columns: Column<PartyWithTransaction>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      render: (row) => (
        <div>
          <p className="font-medium text-gray-900">{row.name}</p>
          {row.is_primary && (
            <span className="text-xs text-yellow-600">Primary</span>
          )}
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      sortable: true,
      render: (row) => <StatusBadge status={row.role} />,
    },
    {
      key: 'email',
      header: 'Email',
      render: (row) => (
        <a href={`mailto:${row.email}`} className="text-sm text-indigo-600 hover:text-indigo-800 transition-colors">
          {row.email}
        </a>
      ),
    },
    {
      key: 'phone',
      header: 'Phone',
      render: (row) =>
        row.phone ? (
          <a href={`tel:${row.phone}`} className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
            {row.phone}
          </a>
        ) : (
          <span className="text-gray-400">--</span>
        ),
    },
    {
      key: 'company',
      header: 'Company',
      sortable: true,
      render: (row) => (
        <span className="text-sm text-gray-600">{row.company || '--'}</span>
      ),
    },
    {
      key: 'transaction_address',
      header: 'Transaction',
      render: (row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/transaction/${row.transaction_id}`);
          }}
          className="text-sm text-indigo-600 hover:text-indigo-800 transition-colors"
        >
          {row.transaction_address}
        </button>
      ),
    },
  ];

  if (isLoading) return <FullPageSpinner />;

  return (
    <div>
      <PageHeader
        title="Party Directory"
        subtitle={`${parties?.length || 0} parties across all transactions`}
      />

      <Card padding={false}>
        <div className="px-4 pt-4 pb-3 border-b border-gray-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, email, or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none w-full sm:w-80"
            />
          </div>
        </div>

        {filteredParties.length === 0 && !searchQuery ? (
          <EmptyState
            icon={Users}
            title="No parties found"
            description="Parties will appear here once they are added to transactions."
          />
        ) : (
          <DataTable
            columns={columns}
            data={filteredParties}
            keyExtractor={(row) => row.id}
            emptyMessage={searchQuery ? `No parties matching "${searchQuery}"` : 'No parties found'}
          />
        )}
      </Card>
    </div>
  );
}
