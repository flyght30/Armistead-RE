import csv
import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.commission import CommissionConfig, TransactionCommission, CommissionSplit
from app.models.transaction import Transaction
from app.schemas.commission import (
    CommissionConfigCreate, CommissionConfigUpdate, CommissionConfigResponse,
    TransactionCommissionCreate, TransactionCommissionUpdate, TransactionCommissionResponse,
    PipelineSummary, PipelineItem,
)

logger = logging.getLogger(__name__)


# --- Commission Config ---

async def get_config(agent_id: UUID, db: AsyncSession) -> Optional[CommissionConfigResponse]:
    stmt = select(CommissionConfig).where(CommissionConfig.agent_id == agent_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    if not config:
        return None
    return CommissionConfigResponse.model_validate(config)


async def upsert_config(
    agent_id: UUID, config_data: CommissionConfigCreate, db: AsyncSession
) -> CommissionConfigResponse:
    stmt = select(CommissionConfig).where(CommissionConfig.agent_id == agent_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        for field, value in config_data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
    else:
        config = CommissionConfig(agent_id=agent_id, **config_data.model_dump())
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return CommissionConfigResponse.model_validate(config)


# --- Transaction Commission ---

async def get_transaction_commission(
    transaction_id: UUID, db: AsyncSession
) -> Optional[TransactionCommissionResponse]:
    stmt = (
        select(TransactionCommission)
        .options(selectinload(TransactionCommission.splits))
        .where(TransactionCommission.transaction_id == transaction_id)
    )
    result = await db.execute(stmt)
    commission = result.scalar_one_or_none()
    if not commission:
        return None
    return TransactionCommissionResponse.model_validate(commission)


async def create_transaction_commission(
    transaction_id: UUID,
    agent_id: UUID,
    commission_data: TransactionCommissionCreate,
    db: AsyncSession,
) -> TransactionCommissionResponse:
    # Get transaction for price data
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Calculate gross commission
    purchase_price = _extract_price(transaction.purchase_price)
    gross = _calculate_gross(
        purchase_price,
        commission_data.commission_type,
        commission_data.rate,
        commission_data.flat_amount,
        commission_data.tiered_rates,
    )

    commission = TransactionCommission(
        transaction_id=transaction_id,
        agent_id=agent_id,
        commission_type=commission_data.commission_type,
        rate=commission_data.rate,
        flat_amount=commission_data.flat_amount,
        tiered_rates=commission_data.tiered_rates,
        gross_commission=gross,
        is_manual_override=commission_data.is_manual_override,
        is_dual_agency=commission_data.is_dual_agency,
        notes=commission_data.notes,
        status="projected",
    )
    db.add(commission)
    await db.flush()

    # Add splits
    net = gross or Decimal("0")
    for split_data in commission_data.splits:
        split = CommissionSplit(
            transaction_commission_id=commission.id,
            **split_data.model_dump(),
        )
        if split.is_percentage and split.percentage and gross:
            split.calculated_amount = gross * split.percentage
            net -= split.calculated_amount
        elif not split.is_percentage and split.flat_amount:
            split.calculated_amount = split.flat_amount
            net -= split.calculated_amount
        db.add(split)

    commission.projected_net = net
    await db.commit()
    await db.refresh(commission)

    # Re-fetch with splits loaded
    return await get_transaction_commission(transaction_id, db)


async def update_transaction_commission(
    transaction_id: UUID,
    commission_update: TransactionCommissionUpdate,
    db: AsyncSession,
) -> TransactionCommissionResponse:
    stmt = (
        select(TransactionCommission)
        .options(selectinload(TransactionCommission.splits))
        .where(TransactionCommission.transaction_id == transaction_id)
    )
    result = await db.execute(stmt)
    commission = result.scalar_one_or_none()
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found for transaction")

    update_data = commission_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(commission, field, value)

    # Recalculate if price-affecting fields changed
    if any(f in update_data for f in ("rate", "flat_amount", "gross_commission", "commission_type")):
        transaction = await db.get(Transaction, transaction_id)
        purchase_price = _extract_price(transaction.purchase_price) if transaction else None
        if purchase_price and not update_data.get("gross_commission"):
            commission.gross_commission = _calculate_gross(
                purchase_price,
                commission.commission_type,
                commission.rate,
                commission.flat_amount,
                commission.tiered_rates,
            )

    await db.commit()
    return await get_transaction_commission(transaction_id, db)


# --- Pipeline ---

async def get_pipeline_summary(
    agent_id: UUID, db: AsyncSession
) -> PipelineSummary:
    # Join commissions with transactions to get property info
    stmt = (
        select(TransactionCommission, Transaction)
        .join(Transaction, TransactionCommission.transaction_id == Transaction.id)
        .options(selectinload(TransactionCommission.splits))
        .where(TransactionCommission.agent_id == agent_id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    total_projected_gross = Decimal("0")
    total_projected_net = Decimal("0")
    total_actual_gross = Decimal("0")
    total_actual_net = Decimal("0")
    pending_amount = Decimal("0")
    paid_amount = Decimal("0")
    by_status = {}
    rates = []
    items = []

    for c, txn in rows:
        if c.gross_commission:
            total_projected_gross += c.gross_commission
        if c.projected_net:
            total_projected_net += c.projected_net
        if c.actual_gross:
            total_actual_gross += c.actual_gross
        if c.actual_net:
            total_actual_net += c.actual_net
        if c.rate:
            rates.append(c.rate)

        # Track pending/paid amounts
        if c.status == "pending":
            pending_amount += c.gross_commission or Decimal("0")
        elif c.status == "paid":
            paid_amount += c.actual_gross or c.gross_commission or Decimal("0")

        status = c.status
        if status not in by_status:
            by_status[status] = {"count": 0, "gross": Decimal("0"), "net": Decimal("0")}
        by_status[status]["count"] += 1
        by_status[status]["gross"] += c.gross_commission or Decimal("0")
        by_status[status]["net"] += c.projected_net or Decimal("0")

        # Extract purchase price from JSON
        purchase_price = None
        if txn.purchase_price and isinstance(txn.purchase_price, dict):
            purchase_price = txn.purchase_price.get("amount")

        # Calculate broker split from splits
        broker_split = None
        for split in c.splits:
            if split.split_type == "broker" and split.calculated_amount:
                broker_split = float(split.calculated_amount)
                break

        items.append(PipelineItem(
            transaction_id=txn.id,
            property_address=txn.property_address,
            property_city=txn.property_city,
            property_state=txn.property_state,
            status=txn.status,
            purchase_price=float(purchase_price) if purchase_price else None,
            gross_commission=float(c.gross_commission) if c.gross_commission else None,
            agent_net=float(c.projected_net) if c.projected_net else None,
            broker_split=broker_split,
            commission_status=c.status,
            rate=float(c.rate) if c.rate else None,
            closing_date=txn.closing_date,
        ))

    # Convert Decimals to float for JSON serialization in by_status
    for s in by_status:
        by_status[s]["gross"] = float(by_status[s]["gross"])
        by_status[s]["net"] = float(by_status[s]["net"])

    avg_rate = sum(rates) / len(rates) if rates else None

    return PipelineSummary(
        total_gross=float(total_projected_gross),
        total_net=float(total_projected_net),
        pending_amount=float(pending_amount),
        paid_amount=float(paid_amount),
        total_projected_gross=total_projected_gross,
        total_projected_net=total_projected_net,
        total_actual_gross=total_actual_gross,
        total_actual_net=total_actual_net,
        transaction_count=len(rows),
        avg_commission_rate=avg_rate,
        by_status=by_status,
        by_month=[],
        items=items,
    )


async def export_csv(
    agent_id: UUID, db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
) -> str:
    """Export commission data as CSV string."""
    stmt = (
        select(TransactionCommission)
        .options(selectinload(TransactionCommission.splits))
        .where(TransactionCommission.agent_id == agent_id)
    )
    if status:
        stmt = stmt.where(TransactionCommission.status == status)
    if start_date:
        stmt = stmt.where(TransactionCommission.created_at >= start_date)
    if end_date:
        stmt = stmt.where(TransactionCommission.created_at <= end_date)

    result = await db.execute(stmt)
    commissions = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Transaction ID", "Commission Type", "Rate", "Gross Commission",
        "Projected Net", "Actual Gross", "Actual Net", "Status",
        "Dual Agency", "Created At",
    ])
    for c in commissions:
        writer.writerow([
            str(c.transaction_id), c.commission_type, str(c.rate or ""),
            str(c.gross_commission or ""), str(c.projected_net or ""),
            str(c.actual_gross or ""), str(c.actual_net or ""),
            c.status, c.is_dual_agency, str(c.created_at),
        ])

    return output.getvalue()


# --- Helpers ---

def _extract_price(purchase_price_json) -> Optional[Decimal]:
    """Extract numeric price from the JSON purchase_price field."""
    if not purchase_price_json:
        return None
    if isinstance(purchase_price_json, dict):
        val = purchase_price_json.get("value") or purchase_price_json.get("amount")
        if val:
            return Decimal(str(val))
    if isinstance(purchase_price_json, (int, float)):
        return Decimal(str(purchase_price_json))
    return None


def _calculate_gross(
    purchase_price: Optional[Decimal],
    commission_type: str,
    rate: Optional[Decimal],
    flat_amount: Optional[Decimal],
    tiered_rates: Optional[dict],
) -> Optional[Decimal]:
    if commission_type == "percentage" and rate and purchase_price:
        return purchase_price * rate
    elif commission_type == "flat" and flat_amount:
        return flat_amount
    elif commission_type == "tiered" and tiered_rates and purchase_price:
        # Simple tiered: apply rate based on price tier
        tiers = tiered_rates.get("tiers", [])
        for tier in sorted(tiers, key=lambda t: t.get("min", 0), reverse=True):
            if purchase_price >= Decimal(str(tier.get("min", 0))):
                return purchase_price * Decimal(str(tier.get("rate", 0)))
        return None
    return None
