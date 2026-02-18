from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# --- Commission Config Schemas ---

class CommissionConfigCreate(BaseModel):
    commission_type: str = "percentage"  # percentage, flat, tiered
    default_rate: Optional[Decimal] = None
    default_flat_amount: Optional[Decimal] = None
    tiered_rates: Optional[dict] = None
    broker_split_percentage: Optional[Decimal] = None
    default_referral_fee_percentage: Optional[Decimal] = None
    team_splits: Optional[dict] = None


class CommissionConfigUpdate(BaseModel):
    commission_type: Optional[str] = None
    default_rate: Optional[Decimal] = None
    default_flat_amount: Optional[Decimal] = None
    tiered_rates: Optional[dict] = None
    broker_split_percentage: Optional[Decimal] = None
    default_referral_fee_percentage: Optional[Decimal] = None
    team_splits: Optional[dict] = None


class CommissionConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    commission_type: str
    default_rate: Optional[Decimal] = None
    default_flat_amount: Optional[Decimal] = None
    tiered_rates: Optional[dict] = None
    broker_split_percentage: Optional[Decimal] = None
    default_referral_fee_percentage: Optional[Decimal] = None
    team_splits: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- Commission Split Schemas ---

class CommissionSplitCreate(BaseModel):
    split_type: str  # broker, referral, team_member
    recipient_name: str
    is_percentage: bool = True
    percentage: Optional[Decimal] = None
    flat_amount: Optional[Decimal] = None


class CommissionSplitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    split_type: str
    recipient_name: str
    is_percentage: bool
    percentage: Optional[Decimal] = None
    flat_amount: Optional[Decimal] = None
    calculated_amount: Optional[Decimal] = None


# --- Transaction Commission Schemas ---

class TransactionCommissionCreate(BaseModel):
    commission_type: str = "percentage"
    rate: Optional[Decimal] = None
    flat_amount: Optional[Decimal] = None
    tiered_rates: Optional[dict] = None
    is_manual_override: bool = False
    is_dual_agency: bool = False
    notes: Optional[str] = None
    splits: list[CommissionSplitCreate] = []


class TransactionCommissionUpdate(BaseModel):
    commission_type: Optional[str] = None
    rate: Optional[Decimal] = None
    flat_amount: Optional[Decimal] = None
    tiered_rates: Optional[dict] = None
    gross_commission: Optional[Decimal] = None
    is_manual_override: Optional[bool] = None
    actual_gross: Optional[Decimal] = None
    actual_net: Optional[Decimal] = None
    status: Optional[str] = None  # projected, pending, paid
    is_dual_agency: Optional[bool] = None
    notes: Optional[str] = None


class TransactionCommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    agent_id: UUID
    commission_type: str
    rate: Optional[Decimal] = None
    flat_amount: Optional[Decimal] = None
    tiered_rates: Optional[dict] = None
    gross_commission: Optional[Decimal] = None
    is_manual_override: bool
    projected_net: Optional[Decimal] = None
    actual_net: Optional[Decimal] = None
    actual_gross: Optional[Decimal] = None
    status: str
    is_dual_agency: bool
    notes: Optional[str] = None
    splits: list[CommissionSplitResponse] = []
    created_at: datetime
    updated_at: datetime


# --- Pipeline Schemas ---

class PipelineItem(BaseModel):
    transaction_id: UUID
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_state: Optional[str] = None
    status: Optional[str] = None
    purchase_price: Optional[float] = None
    gross_commission: Optional[float] = None
    agent_net: Optional[float] = None
    broker_split: Optional[float] = None
    commission_status: str
    rate: Optional[float] = None
    closing_date: Optional[datetime] = None


class PipelineSummary(BaseModel):
    total_gross: float
    total_net: float
    pending_amount: float
    paid_amount: float
    total_projected_gross: Decimal
    total_projected_net: Decimal
    total_actual_gross: Decimal
    total_actual_net: Decimal
    transaction_count: int
    avg_commission_rate: Optional[Decimal] = None
    by_status: dict  # {projected: {count, gross, net}, pending: ..., paid: ...}
    by_month: list[dict]  # [{month, gross, net, count}]
    items: list[PipelineItem] = []


class CSVExportRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
