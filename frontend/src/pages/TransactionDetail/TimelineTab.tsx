import React, { useState } from 'react';
import { Milestone } from '../../types/transaction';
import Timeline, { TimelineItem } from '../../components/ui/Timeline';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';
import FormInput from '../../components/ui/FormInput';
import FormSelect from '../../components/ui/FormSelect';
import { useToast } from '../../components/ui/ToastContext';
import apiClient from '../../lib/api';
import { Clock, Plus, Check, Pencil, Trash2 } from 'lucide-react';

interface TimelineTabProps {
  milestones: Milestone[];
  transactionId: string;
  onRefresh: () => void;
}

const MILESTONE_TYPE_OPTIONS = [
  { value: 'inspection', label: 'Inspection' },
  { value: 'appraisal', label: 'Appraisal' },
  { value: 'financing', label: 'Financing' },
  { value: 'closing', label: 'Closing' },
  { value: 'title_search', label: 'Title Search' },
  { value: 'survey', label: 'Survey' },
  { value: 'other', label: 'Other' },
];

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
  { value: 'overdue', label: 'Overdue' },
];

const ROLE_OPTIONS = [
  { value: 'buyer', label: 'Buyer' },
  { value: 'seller', label: 'Seller' },
  { value: 'buyer_agent', label: 'Buyer Agent' },
  { value: 'seller_agent', label: 'Seller Agent' },
  { value: 'attorney', label: 'Attorney' },
  { value: 'lender', label: 'Lender' },
  { value: 'inspector', label: 'Inspector' },
];

interface MilestoneFormData {
  title: string;
  type: string;
  due_date: string;
  responsible_party_role: string;
  status: string;
}

const EMPTY_FORM: MilestoneFormData = {
  title: '',
  type: 'other',
  due_date: '',
  responsible_party_role: 'buyer',
  status: 'pending',
};

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return '';
  }
}

function getMilestoneStatus(m: Milestone): TimelineItem['status'] {
  if (m.status === 'completed') return 'completed';
  if (m.status === 'in_progress') return 'in_progress';
  if (m.status === 'overdue') return 'overdue';
  if (m.due_date && new Date(m.due_date) < new Date() && m.status !== 'completed') {
    return 'overdue';
  }
  return 'not_started';
}

export default function TimelineTab({ milestones, transactionId, onRefresh }: TimelineTabProps) {
  const { toast } = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingMilestone, setEditingMilestone] = useState<Milestone | null>(null);
  const [form, setForm] = useState<MilestoneFormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const completedCount = milestones.filter((m) => m.status === 'completed').length;
  const sorted = [...milestones].sort((a, b) => a.sort_order - b.sort_order);

  function openAddModal() {
    setEditingMilestone(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  }

  function openEditModal(milestone: Milestone) {
    setEditingMilestone(milestone);
    setForm({
      title: milestone.title,
      type: milestone.type,
      due_date: milestone.due_date ? milestone.due_date.split('T')[0] : '',
      responsible_party_role: milestone.responsible_party_role,
      status: milestone.status,
    });
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingMilestone(null);
    setForm(EMPTY_FORM);
  }

  function updateField(field: keyof MilestoneFormData, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        title: form.title,
        type: form.type,
        due_date: form.due_date,
        responsible_party_role: form.responsible_party_role,
        status: form.status,
      };

      if (editingMilestone) {
        await apiClient.patch(
          `/transactions/${transactionId}/milestones/${editingMilestone.id}`,
          payload,
        );
        toast('success', 'Milestone updated');
      } else {
        await apiClient.post(`/transactions/${transactionId}/milestones`, payload);
        toast('success', 'Milestone created');
      }

      closeModal();
      onRefresh();
    } catch {
      toast('error', editingMilestone ? 'Failed to update milestone' : 'Failed to create milestone');
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkComplete(milestone: Milestone) {
    try {
      await apiClient.patch(
        `/transactions/${transactionId}/milestones/${milestone.id}`,
        { status: 'completed', completed_at: new Date().toISOString() },
      );
      toast('success', `"${milestone.title}" marked as completed`);
      onRefresh();
    } catch {
      toast('error', 'Failed to mark milestone as completed');
    }
  }

  async function handleDelete(milestone: Milestone) {
    if (!window.confirm(`Are you sure you want to delete "${milestone.title}"?`)) return;
    try {
      await apiClient.delete(`/transactions/${transactionId}/milestones/${milestone.id}`);
      toast('success', `"${milestone.title}" deleted`);
      onRefresh();
    } catch {
      toast('error', 'Failed to delete milestone');
    }
  }

  const items: TimelineItem[] = sorted.map((m) => ({
    id: m.id,
    title: m.title,
    subtitle: m.responsible_party_role
      ? `Responsible: ${m.responsible_party_role.replace(/_/g, ' ')}`
      : undefined,
    date: m.completed_at
      ? `Completed ${formatDate(m.completed_at)}`
      : m.due_date
        ? `Due ${formatDate(m.due_date)}`
        : undefined,
    status: getMilestoneStatus(m),
    description: m.type !== m.title ? m.type.replace(/_/g, ' ') : undefined,
  }));

  if (milestones.length === 0) {
    return (
      <EmptyState
        icon={Clock}
        title="No milestones yet"
        description="Add milestones to track key dates and deadlines for this transaction."
        action={{ label: 'Add Milestone', onClick: openAddModal }}
      />
    );
  }

  return (
    <div className="max-w-2xl">
      {/* Header with progress and add button */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex-1 mr-4">
          <h3 className="text-sm font-medium text-gray-500">
            {completedCount} of {milestones.length} milestones completed
          </h3>
          <div className="mt-2 bg-gray-200 rounded-full h-2 w-full">
            <div
              className="bg-green-500 rounded-full h-2 transition-all"
              style={{
                width: `${(completedCount / milestones.length) * 100}%`,
              }}
            />
          </div>
        </div>
        <button
          onClick={openAddModal}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Milestone
        </button>
      </div>

      {/* Timeline with action buttons */}
      <div className="flow-root">
        <ul className="-mb-8">
          {sorted.map((milestone, idx) => {
            const item = items[idx];
            const isLast = idx === sorted.length - 1;
            const isCompleted = milestone.status === 'completed';

            return (
              <li key={milestone.id}>
                <div className="relative pb-8">
                  {!isLast && (
                    <span
                      className={`absolute left-3 top-6 -ml-px h-full w-0.5 ${
                        isCompleted ? 'bg-green-300' : item.status === 'overdue' ? 'bg-red-300' : 'bg-gray-200'
                      }`}
                      aria-hidden="true"
                    />
                  )}
                  <div className="relative flex items-start gap-4">
                    <div
                      className={`relative flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full ${
                        isCompleted
                          ? 'bg-green-500'
                          : item.status === 'overdue'
                            ? 'bg-red-500'
                            : item.status === 'in_progress'
                              ? 'bg-blue-500'
                              : 'bg-gray-300'
                      }`}
                    >
                      {isCompleted && <Check className="w-3 h-3 text-white" />}
                      {item.status === 'overdue' && !isCompleted && (
                        <Clock className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900">{milestone.title}</p>
                        <div className="flex items-center gap-1 ml-2">
                          {!isCompleted && (
                            <button
                              onClick={() => handleMarkComplete(milestone)}
                              title="Mark Complete"
                              className="p-1 rounded hover:bg-green-50 text-gray-400 hover:text-green-600 transition-colors"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => openEditModal(milestone)}
                            title="Edit"
                            className="p-1 rounded hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition-colors"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(milestone)}
                            title="Delete"
                            className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-600 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      {item.subtitle && (
                        <p className="text-xs text-gray-500 mt-0.5">{item.subtitle}</p>
                      )}
                      {item.date && (
                        <time className="text-xs text-gray-500 mt-0.5 block">{item.date}</time>
                      )}
                      {item.description && (
                        <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                      )}
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Add/Edit Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={closeModal}
        title={editingMilestone ? 'Edit Milestone' : 'Add Milestone'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormInput
            label="Title"
            value={form.title}
            onChange={(e) => updateField('title', e.target.value)}
            placeholder="e.g., Home Inspection"
            required
          />

          <FormSelect
            label="Type"
            options={MILESTONE_TYPE_OPTIONS}
            value={form.type}
            onChange={(e) => updateField('type', e.target.value)}
          />

          <FormInput
            label="Due Date"
            type="date"
            value={form.due_date}
            onChange={(e) => updateField('due_date', e.target.value)}
            required
          />

          <FormSelect
            label="Responsible Party Role"
            options={ROLE_OPTIONS}
            value={form.responsible_party_role}
            onChange={(e) => updateField('responsible_party_role', e.target.value)}
          />

          <FormSelect
            label="Status"
            options={STATUS_OPTIONS}
            value={form.status}
            onChange={(e) => updateField('status', e.target.value)}
          />

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={closeModal}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving...' : editingMilestone ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
