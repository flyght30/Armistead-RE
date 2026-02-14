import React, { useState } from 'react';
import { Users, Mail, Phone, Building2, Star, Plus, Pencil, Trash2 } from 'lucide-react';
import { Party } from '../../types/party';
import StatusBadge from '../../components/ui/StatusBadge';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';
import FormInput from '../../components/ui/FormInput';
import FormSelect from '../../components/ui/FormSelect';
import { useToast } from '../../components/ui/ToastContext';
import apiClient from '../../lib/api';

interface PartiesTabProps {
  parties: Party[];
  transactionId: string;
  onRefresh: () => void;
}

interface PartyFormData {
  name: string;
  role: string;
  email: string;
  phone: string;
  company: string;
  is_primary: boolean;
}

const EMPTY_FORM: PartyFormData = {
  name: '',
  role: '',
  email: '',
  phone: '',
  company: '',
  is_primary: false,
};

const ROLE_OPTIONS = [
  { value: 'buyer', label: 'Buyer' },
  { value: 'seller', label: 'Seller' },
  { value: 'buyer_agent', label: 'Buyer Agent' },
  { value: 'seller_agent', label: 'Seller Agent' },
  { value: 'attorney', label: 'Attorney' },
  { value: 'lender', label: 'Lender' },
  { value: 'inspector', label: 'Inspector' },
  { value: 'title_company', label: 'Title Company' },
  { value: 'other', label: 'Other' },
];

function PartyCard({
  party,
  onEdit,
  onDelete,
}: {
  party: Party;
  onEdit: (party: Party) => void;
  onDelete: (party: Party) => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{party.name}</h3>
          {party.is_primary && (
            <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 flex-shrink-0" />
          )}
        </div>
        <div className="flex items-center gap-1 ml-2 flex-shrink-0">
          <button
            onClick={() => onEdit(party)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 opacity-0 group-hover:opacity-100 transition-all"
            title="Edit party"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(party)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
            title="Delete party"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <StatusBadge status={party.role} />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <a
            href={`mailto:${party.email}`}
            className="hover:text-indigo-600 transition-colors truncate"
          >
            {party.email}
          </a>
        </div>

        {party.phone && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Phone className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <a href={`tel:${party.phone}`} className="hover:text-indigo-600 transition-colors">
              {party.phone}
            </a>
          </div>
        )}

        {party.company && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Building2 className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span>{party.company}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PartiesTab({ parties, transactionId, onRefresh }: PartiesTabProps) {
  const { toast } = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingParty, setEditingParty] = useState<Party | null>(null);
  const [form, setForm] = useState<PartyFormData>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  function openAddModal() {
    setEditingParty(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  }

  function openEditModal(party: Party) {
    setEditingParty(party);
    setForm({
      name: party.name,
      role: party.role,
      email: party.email,
      phone: party.phone ?? '',
      company: party.company ?? '',
      is_primary: party.is_primary,
    });
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingParty(null);
    setForm(EMPTY_FORM);
  }

  function updateField<K extends keyof PartyFormData>(key: K, value: PartyFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);

    const payload: Record<string, unknown> = {
      name: form.name,
      role: form.role,
      email: form.email,
      is_primary: form.is_primary,
    };
    if (form.phone.trim()) payload.phone = form.phone.trim();
    if (form.company.trim()) payload.company = form.company.trim();

    try {
      if (editingParty) {
        await apiClient.patch(
          `/transactions/${transactionId}/parties/${editingParty.id}`,
          payload,
        );
        toast('success', `Updated ${form.name}`);
      } else {
        await apiClient.post(`/transactions/${transactionId}/parties`, payload);
        toast('success', `Added ${form.name}`);
      }
      closeModal();
      onRefresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      toast('error', message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(party: Party) {
    if (!window.confirm(`Remove ${party.name} from this transaction?`)) return;

    try {
      await apiClient.delete(`/transactions/${transactionId}/parties/${party.id}`);
      toast('success', `Removed ${party.name}`);
      onRefresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to remove party. Please try again.';
      toast('error', message);
    }
  }

  const isFormValid = form.name.trim() !== '' && form.role !== '' && form.email.trim() !== '';

  return (
    <>
      {/* Header with Add button */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          {parties.length} {parties.length === 1 ? 'party' : 'parties'}
        </p>
        <button
          onClick={openAddModal}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Party
        </button>
      </div>

      {/* Grid or empty state */}
      {parties.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No parties yet"
          description="Add buyers, sellers, agents, and other parties to this transaction."
          action={{ label: 'Add Party', onClick: openAddModal }}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {parties.map((party) => (
            <PartyCard
              key={party.id}
              party={party}
              onEdit={openEditModal}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={closeModal}
        title={editingParty ? 'Edit Party' : 'Add Party'}
        maxWidth="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormInput
              label="Name"
              placeholder="John Doe"
              required
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
            />
            <FormSelect
              label="Role"
              options={ROLE_OPTIONS}
              placeholder="Select a role"
              required
              value={form.role}
              onChange={(e) => updateField('role', e.target.value)}
            />
          </div>

          <FormInput
            label="Email"
            type="email"
            placeholder="john@example.com"
            required
            value={form.email}
            onChange={(e) => updateField('email', e.target.value)}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormInput
              label="Phone"
              type="tel"
              placeholder="(555) 123-4567"
              value={form.phone}
              onChange={(e) => updateField('phone', e.target.value)}
            />
            <FormInput
              label="Company"
              placeholder="Acme Realty"
              value={form.company}
              onChange={(e) => updateField('company', e.target.value)}
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_primary}
              onChange={(e) => updateField('is_primary', e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-gray-700">Primary contact for this role</span>
          </label>

          <div className="flex items-center justify-end gap-3 pt-2 border-t border-gray-200">
            <button
              type="button"
              onClick={closeModal}
              className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isFormValid || submitting}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? (
                <>
                  <svg
                    className="animate-spin h-4 w-4"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Saving...
                </>
              ) : editingParty ? (
                'Save Changes'
              ) : (
                'Add Party'
              )}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
