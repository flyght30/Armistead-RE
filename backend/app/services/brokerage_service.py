import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.brokerage import (
    Brokerage, Team, TeamMember,
    ComplianceRule, ComplianceViolation, PerformanceSnapshot,
)
from app.models.user import User
from app.schemas.brokerage import (
    BrokerageCreate, BrokerageUpdate, BrokerageResponse,
    TeamCreate, TeamUpdate, TeamResponse, TeamMemberAdd, TeamMemberResponse,
    ComplianceRuleCreate, ComplianceRuleUpdate, ComplianceRuleResponse,
    ComplianceViolationResponse, ComplianceDashboardResponse,
    PerformanceSnapshotResponse, AgentPerformanceSummary,
)

logger = logging.getLogger(__name__)


# --- Brokerage CRUD ---

async def create_brokerage(
    data: BrokerageCreate, db: AsyncSession
) -> BrokerageResponse:
    brokerage = Brokerage(**data.model_dump())
    db.add(brokerage)
    await db.commit()
    await db.refresh(brokerage)
    return BrokerageResponse.model_validate(brokerage)


async def get_brokerage(
    brokerage_id: UUID, db: AsyncSession
) -> BrokerageResponse:
    brokerage = await db.get(Brokerage, brokerage_id)
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")
    return BrokerageResponse.model_validate(brokerage)


async def update_brokerage(
    brokerage_id: UUID, data: BrokerageUpdate, db: AsyncSession
) -> BrokerageResponse:
    brokerage = await db.get(Brokerage, brokerage_id)
    if not brokerage:
        raise HTTPException(status_code=404, detail="Brokerage not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(brokerage, field, value)
    await db.commit()
    await db.refresh(brokerage)
    return BrokerageResponse.model_validate(brokerage)


# --- Team CRUD ---

async def create_team(
    brokerage_id: UUID, data: TeamCreate, db: AsyncSession
) -> TeamResponse:
    team = Team(brokerage_id=brokerage_id, **data.model_dump())
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return TeamResponse.model_validate(team)


async def list_teams(
    brokerage_id: UUID, db: AsyncSession
) -> List[TeamResponse]:
    stmt = (
        select(Team)
        .options(selectinload(Team.members))
        .where(Team.brokerage_id == brokerage_id)
    )
    result = await db.execute(stmt)
    teams = result.scalars().all()
    return [TeamResponse.model_validate(t) for t in teams]


async def add_team_member(
    team_id: UUID, data: TeamMemberAdd, db: AsyncSession
) -> TeamMemberResponse:
    member = TeamMember(team_id=team_id, **data.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return TeamMemberResponse.model_validate(member)


async def remove_team_member(
    team_id: UUID, user_id: UUID, db: AsyncSession
) -> None:
    stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    await db.delete(member)
    await db.commit()


# --- Compliance ---

async def create_compliance_rule(
    brokerage_id: UUID, data: ComplianceRuleCreate, db: AsyncSession
) -> ComplianceRuleResponse:
    rule = ComplianceRule(brokerage_id=brokerage_id, **data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return ComplianceRuleResponse.model_validate(rule)


async def list_compliance_rules(
    brokerage_id: UUID, db: AsyncSession
) -> List[ComplianceRuleResponse]:
    stmt = select(ComplianceRule).where(ComplianceRule.brokerage_id == brokerage_id)
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [ComplianceRuleResponse.model_validate(r) for r in rules]


async def update_compliance_rule(
    rule_id: UUID, data: ComplianceRuleUpdate, db: AsyncSession
) -> ComplianceRuleResponse:
    rule = await db.get(ComplianceRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Compliance rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return ComplianceRuleResponse.model_validate(rule)


async def get_compliance_dashboard(
    brokerage_id: UUID, db: AsyncSession
) -> ComplianceDashboardResponse:
    stmt = (
        select(ComplianceViolation)
        .join(ComplianceRule)
        .where(ComplianceRule.brokerage_id == brokerage_id)
        .order_by(ComplianceViolation.created_at.desc())
    )
    result = await db.execute(stmt)
    violations = result.scalars().all()

    unresolved = [v for v in violations if not v.resolved]
    by_severity = {}
    for v in violations:
        by_severity[v.severity] = by_severity.get(v.severity, 0) + 1

    return ComplianceDashboardResponse(
        total_violations=len(violations),
        unresolved_count=len(unresolved),
        by_severity=by_severity,
        recent_violations=[
            ComplianceViolationResponse.model_validate(v)
            for v in violations[:20]
        ],
    )


# --- Performance ---

async def list_performance_snapshots(
    agent_id: UUID, db: AsyncSession
) -> List[PerformanceSnapshotResponse]:
    stmt = (
        select(PerformanceSnapshot)
        .where(PerformanceSnapshot.agent_id == agent_id)
        .order_by(PerformanceSnapshot.period_end.desc())
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    return [PerformanceSnapshotResponse.model_validate(s) for s in snapshots]


async def get_agent_performance_summary(
    agent_id: UUID, db: AsyncSession
) -> AgentPerformanceSummary:
    user = await db.get(User, agent_id)
    if not user:
        raise HTTPException(status_code=404, detail="Agent not found")

    from app.models.transaction import Transaction
    from app.models.commission import TransactionCommission

    # Count transactions
    t_stmt = select(Transaction).where(Transaction.agent_id == agent_id)
    t_result = await db.execute(t_stmt)
    transactions = t_result.scalars().all()

    closed = [t for t in transactions if t.status == "closed"]
    active = [t for t in transactions if t.status not in ("closed", "cancelled", "draft")]

    # Sum commissions
    c_stmt = select(TransactionCommission).where(TransactionCommission.agent_id == agent_id)
    c_result = await db.execute(c_stmt)
    commissions = c_result.scalars().all()

    total_commission = sum(float(c.actual_gross or c.gross_commission or 0) for c in commissions)
    total_volume = sum(float(t.purchase_price.get("value", 0)) if isinstance(t.purchase_price, dict) else 0 for t in closed)

    return AgentPerformanceSummary(
        agent_id=agent_id,
        agent_name=user.name,
        transactions_closed=len(closed),
        total_volume=total_volume,
        total_commission=total_commission,
        avg_days_to_close=None,
        active_transactions=len(active),
    )
