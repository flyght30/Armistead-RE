import { z } from 'zod';
import { PartySchema } from './party';

export const MilestoneSchema = z.object({
  id: z.string().uuid(),
  transaction_id: z.string().uuid(),
  type: z.string(),
  title: z.string(),
  due_date: z.string().nullable().optional(),
  status: z.string(),
  responsible_party_role: z.string(),
  notes: z.record(z.any()).nullable().optional(),
  reminder_days_before: z.number().nullable().optional(),
  sort_order: z.number().default(0),
  completed_at: z.string().nullable().optional(),
  last_reminder_sent_at: z.string().nullable().optional(),
  template_item_id: z.string().uuid().nullable().optional(),
  is_auto_generated: z.boolean().default(false),
  created_at: z.string(),
  updated_at: z.string(),
});

export const AmendmentSchema = z.object({
  id: z.string().uuid(),
  transaction_id: z.string().uuid(),
  field_changed: z.string(),
  old_value: z.record(z.any()),
  new_value: z.record(z.any()),
  reason: z.string(),
  changed_by_id: z.string().uuid(),
  notification_sent: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const FileSchema = z.object({
  id: z.string().uuid(),
  transaction_id: z.string().uuid().nullable().optional(),
  name: z.string(),
  content_type: z.string(),
  url: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const InspectionItemSchema = z.object({
  id: z.string().uuid(),
  analysis_id: z.string().uuid(),
  description: z.string(),
  location: z.string(),
  severity: z.string(),
  estimated_cost_low: z.record(z.any()),
  estimated_cost_high: z.record(z.any()),
  risk_assessment: z.string(),
  recommendation: z.string(),
  repair_status: z.string(),
  sort_order: z.number(),
  report_reference: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const InspectionAnalysisSchema = z.object({
  id: z.string().uuid(),
  transaction_id: z.string().uuid(),
  report_document_url: z.string(),
  executive_summary: z.string(),
  total_estimated_cost_low: z.record(z.any()),
  total_estimated_cost_high: z.record(z.any()),
  overall_risk_level: z.string(),
  items: z.array(InspectionItemSchema).default([]),
  created_at: z.string(),
  updated_at: z.string(),
});

export const CommunicationSchema = z.object({
  id: z.string().uuid(),
  transaction_id: z.string().uuid(),
  milestone_id: z.string().uuid().nullable().optional(),
  recipient_party_id: z.string().uuid().nullable().optional(),
  type: z.string(),
  recipient_email: z.string(),
  subject: z.string(),
  body: z.string(),
  attachments: z.record(z.any()).nullable().optional(),
  status: z.string(),
  sent_at: z.string().nullable().optional(),
  opened_at: z.string().nullable().optional(),
  clicked_at: z.string().nullable().optional(),
  template_used: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const TransactionSchema = z.object({
  id: z.string().uuid(),
  agent_id: z.string().uuid(),
  status: z.string(),
  representation_side: z.string(),
  financing_type: z.string().nullable().optional(),
  property_address: z.string().nullable().optional(),
  property_city: z.string().nullable().optional(),
  property_state: z.string().nullable().optional(),
  property_zip: z.string().nullable().optional(),
  property_county: z.string().nullable().optional(),
  purchase_price: z.record(z.any()).nullable().optional(),
  earnest_money_amount: z.record(z.any()).nullable().optional(),
  closing_date: z.string().nullable().optional(),
  contract_document_url: z.string().nullable().optional(),
  special_stipulations: z.record(z.any()).nullable().optional(),
  ai_extraction_confidence: z.record(z.any()).nullable().optional(),
  contract_execution_date: z.string().nullable().optional(),
  health_score: z.number().nullable().optional(),
  template_id: z.string().uuid().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  parties: z.array(PartySchema).default([]),
});

export const TransactionDetailSchema = TransactionSchema.extend({
  milestones: z.array(MilestoneSchema).default([]),
  amendments: z.array(AmendmentSchema).default([]),
  files: z.array(FileSchema).default([]),
  inspection_analyses: z.array(InspectionAnalysisSchema).default([]),
  communications: z.array(CommunicationSchema).default([]),
});

export type Transaction = z.infer<typeof TransactionSchema>;
export type TransactionDetail = z.infer<typeof TransactionDetailSchema>;
export type Milestone = z.infer<typeof MilestoneSchema>;
export type Amendment = z.infer<typeof AmendmentSchema>;
export type TransactionFile = z.infer<typeof FileSchema>;
export type InspectionAnalysis = z.infer<typeof InspectionAnalysisSchema>;
export type InspectionItem = z.infer<typeof InspectionItemSchema>;
export type Communication = z.infer<typeof CommunicationSchema>;

export interface DashboardStats {
  total: number;
  draft: number;
  pending_review: number;
  confirmed: number;
  closing_this_month: number;
}

// Phase 1: Action Item types
export interface ActionItem {
  id: string;
  transaction_id: string;
  milestone_id?: string | null;
  type: string;
  title: string;
  description?: string | null;
  priority: string;
  status: string;
  due_date?: string | null;
  snoozed_until?: string | null;
  completed_at?: string | null;
  agent_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TodayViewData {
  overdue: ActionItem[];
  due_today: ActionItem[];
  coming_up: ActionItem[];
  this_week: ActionItem[];
  summary: {
    overdue_count: number;
    due_today_count: number;
    coming_up_count: number;
    this_week_count: number;
  };
}

export interface HealthScoreData {
  score: number;
  color: string;
  breakdown: {
    overdue_milestones: { count: number; penalty: number };
    upcoming_no_action: { count: number; penalty: number };
    missing_parties: { details: string[]; penalty: number };
    missing_documents: { details: string[]; penalty: number };
    pace_ratio: { remaining_milestones: number; days_to_close: number | null; penalty: number };
  };
}

export interface MilestoneTemplate {
  id: string;
  name: string;
  state_code: string;
  financing_type: string;
  representation_side: string;
  description?: string | null;
  is_default: boolean;
  is_active: boolean;
  item_count?: number | null;
  created_at: string;
  updated_at: string;
}

// Power Features: Risk Alerts
export interface RiskAlertType {
  id: string;
  transaction_id: string;
  agent_id: string;
  alert_type: string;
  severity: string; // low, medium, high, critical
  message: string;
  suggested_action?: string | null;
  is_acknowledged: boolean;
  acknowledged_at?: string | null;
  dismissed_at?: string | null;
  created_at: string;
  updated_at: string;
}

// Power Features: Smart Suggestions
export interface SmartSuggestion {
  icon: string; // phone, upload, alert, calendar, mail, check
  title: string;
  description: string;
  priority: string; // high, medium, low
}

// Power Features: Closing Readiness Category
export interface ClosingReadinessCategory {
  score: number;
  weight: number;
  label: string;
  completed?: number;
  total?: number;
}

// Power Features: Enhanced Closing Readiness
export interface ClosingReadinessData {
  transaction_id: string;
  overall_score: number;
  status: string; // ready, at_risk, not_ready
  categories: Record<string, ClosingReadinessCategory>;
  blockers: Array<{ type: string; description: string; severity: string; category?: string }>;
  recommendations: string[];
}
