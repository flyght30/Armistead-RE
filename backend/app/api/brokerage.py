from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.brokerage import (
    BrokerageCreate, BrokerageUpdate, BrokerageResponse,
    TeamCreate, TeamUpdate, TeamResponse, TeamMemberAdd, TeamMemberResponse,
    ComplianceRuleCreate, ComplianceRuleUpdate, ComplianceRuleResponse,
    ComplianceDashboardResponse,
    PerformanceSnapshotResponse, AgentPerformanceSummary,
)
from app.services import brokerage_service

router = APIRouter()

DEV_AGENT_ID = "00000000-0000-0000-0000-000000000001"


# --- Brokerage ---

@router.post("/brokerages", response_model=BrokerageResponse)
async def create_brokerage(
    data: BrokerageCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.create_brokerage(data, db)


@router.get("/brokerages/{brokerage_id}", response_model=BrokerageResponse)
async def get_brokerage(
    brokerage_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.get_brokerage(brokerage_id, db)


@router.patch("/brokerages/{brokerage_id}", response_model=BrokerageResponse)
async def update_brokerage(
    brokerage_id: UUID,
    data: BrokerageUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.update_brokerage(brokerage_id, data, db)


# --- Teams ---

@router.post("/brokerages/{brokerage_id}/teams", response_model=TeamResponse)
async def create_team(
    brokerage_id: UUID,
    data: TeamCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.create_team(brokerage_id, data, db)


@router.get("/brokerages/{brokerage_id}/teams", response_model=List[TeamResponse])
async def list_teams(
    brokerage_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.list_teams(brokerage_id, db)


@router.post("/teams/{team_id}/members", response_model=TeamMemberResponse)
async def add_team_member(
    team_id: UUID,
    data: TeamMemberAdd,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.add_team_member(team_id, data, db)


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await brokerage_service.remove_team_member(team_id, user_id, db)
    return {"success": True}


# --- Compliance ---

@router.post("/brokerages/{brokerage_id}/compliance-rules", response_model=ComplianceRuleResponse)
async def create_compliance_rule(
    brokerage_id: UUID,
    data: ComplianceRuleCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.create_compliance_rule(brokerage_id, data, db)


@router.get("/brokerages/{brokerage_id}/compliance-rules", response_model=List[ComplianceRuleResponse])
async def list_compliance_rules(
    brokerage_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.list_compliance_rules(brokerage_id, db)


@router.patch("/compliance-rules/{rule_id}", response_model=ComplianceRuleResponse)
async def update_compliance_rule(
    rule_id: UUID,
    data: ComplianceRuleUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.update_compliance_rule(rule_id, data, db)


@router.get("/brokerages/{brokerage_id}/compliance-dashboard", response_model=ComplianceDashboardResponse)
async def get_compliance_dashboard(
    brokerage_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.get_compliance_dashboard(brokerage_id, db)


# --- Performance ---

@router.get("/agents/{agent_id}/performance", response_model=List[PerformanceSnapshotResponse])
async def list_performance_snapshots(
    agent_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.list_performance_snapshots(agent_id, db)


@router.get("/agents/{agent_id}/performance-summary", response_model=AgentPerformanceSummary)
async def get_agent_performance_summary(
    agent_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await brokerage_service.get_agent_performance_summary(agent_id, db)
