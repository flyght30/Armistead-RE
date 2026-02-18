import asyncio
import uuid
from datetime import datetime, timedelta, timezone

# Must be at top level
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database import Base, DATABASE_URL
from app.models.user import User
from app.models.transaction import Transaction
from app.models.party import Party
from app.models.milestone import Milestone
from app.models.amendment import Amendment
from app.models.file import File
from app.models.inspection import InspectionAnalysis, InspectionItem
from app.models.communication import Communication
from app.models.milestone_template import MilestoneTemplate, MilestoneTemplateItem
from app.models.action_item import ActionItem
from app.models.commission import CommissionConfig, TransactionCommission, CommissionSplit
from decimal import Decimal

# Fixed UUIDs for dev mode
DEV_AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _ga_conventional_buyer_items(template_id):
    """Georgia Conventional Buyer — 18 milestones."""
    items = [
        ("inspection", "Schedule Home Inspection", 1, "contract_date", "buyer_agent", 1, 1),
        ("inspection", "Home Inspection Completed", 7, "contract_date", "inspector", 2, 2),
        ("inspection", "Termite/Pest Inspection", 7, "contract_date", "buyer_agent", 2, 3),
        ("inspection", "Request Repairs (Due Diligence)", 10, "contract_date", "buyer_agent", 2, 4),
        ("inspection", "Seller Responds to Repair Request", 14, "contract_date", "seller_agent", 2, 5),
        ("inspection", "Due Diligence Period Ends", 14, "contract_date", "buyer_agent", 3, 6),
        ("appraisal", "Appraisal Ordered", 3, "contract_date", "lender", 2, 7),
        ("appraisal", "Appraisal Completed", 14, "contract_date", "lender", 3, 8),
        ("financing", "Loan Application Submitted", 3, "contract_date", "buyer", 2, 9),
        ("financing", "Credit Check & Pre-Approval Updated", 7, "contract_date", "lender", 2, 10),
        ("financing", "Loan Commitment / Clear to Close", -10, "closing_date", "lender", 5, 11),
        ("title", "Title Search Ordered", 5, "contract_date", "closing_attorney", 2, 12),
        ("title", "Title Commitment Received", 21, "contract_date", "closing_attorney", 3, 13),
        ("title", "Survey Completed (if required)", 21, "contract_date", "buyer_agent", 3, 14),
        ("other", "Homeowners Insurance Bound", -7, "closing_date", "buyer", 3, 15),
        ("closing", "Final Walk-Through", -2, "closing_date", "buyer_agent", 1, 16),
        ("closing", "Closing Disclosure Received (3-day rule)", -3, "closing_date", "lender", 2, 17),
        ("closing", "Closing Day", 0, "closing_date", "closing_attorney", 3, 18),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


def _ga_conventional_seller_items(template_id):
    """Georgia Conventional Seller — 14 milestones."""
    items = [
        ("other", "Property Disclosure Statement Provided", 3, "contract_date", "seller_agent", 2, 1),
        ("inspection", "Buyer's Inspection Period (monitor)", 7, "contract_date", "seller_agent", 2, 2),
        ("inspection", "Review & Respond to Repair Requests", 14, "contract_date", "seller_agent", 2, 3),
        ("inspection", "Schedule Agreed Repairs", 17, "contract_date", "seller", 2, 4),
        ("inspection", "Repairs Completed", 25, "contract_date", "seller", 3, 5),
        ("appraisal", "Appraisal Access Coordinated", 10, "contract_date", "seller_agent", 2, 6),
        ("appraisal", "Appraisal Value Reviewed", 21, "contract_date", "seller_agent", 3, 7),
        ("title", "Provide Title Documents / HOA Docs", 10, "contract_date", "seller_agent", 3, 8),
        ("title", "Clear Title Issues (if any)", 28, "contract_date", "closing_attorney", 3, 9),
        ("other", "Coordinate Utility Transfers", -5, "closing_date", "seller", 2, 10),
        ("other", "Move-Out Preparation", -3, "closing_date", "seller", 2, 11),
        ("closing", "Review Closing Disclosure", -3, "closing_date", "seller_agent", 2, 12),
        ("closing", "Final Walk-Through (buyer access)", -2, "closing_date", "seller_agent", 1, 13),
        ("closing", "Closing Day", 0, "closing_date", "closing_attorney", 3, 14),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


def _ga_fha_buyer_items(template_id):
    """Georgia FHA Buyer — 20 milestones (includes FHA-specific requirements)."""
    items = [
        ("inspection", "Schedule Home Inspection", 1, "contract_date", "buyer_agent", 1, 1),
        ("inspection", "Home Inspection Completed", 7, "contract_date", "inspector", 2, 2),
        ("inspection", "Termite/Wood Destroying Organism Report", 7, "contract_date", "buyer_agent", 2, 3),
        ("inspection", "Request Repairs (Due Diligence)", 10, "contract_date", "buyer_agent", 2, 4),
        ("inspection", "Seller Responds to Repair Request", 14, "contract_date", "seller_agent", 2, 5),
        ("inspection", "Due Diligence Period Ends", 14, "contract_date", "buyer_agent", 3, 6),
        ("appraisal", "FHA Appraisal Ordered", 3, "contract_date", "lender", 2, 7),
        ("appraisal", "FHA Appraisal Completed (includes MPR check)", 14, "contract_date", "lender", 3, 8),
        ("appraisal", "FHA Minimum Property Requirements Met", 18, "contract_date", "lender", 3, 9),
        ("financing", "Loan Application with FHA Case Number", 3, "contract_date", "buyer", 2, 10),
        ("financing", "Credit Check & FHA Eligibility Verified", 7, "contract_date", "lender", 2, 11),
        ("financing", "FHA Loan Commitment / Clear to Close", -10, "closing_date", "lender", 5, 12),
        ("title", "Title Search Ordered", 5, "contract_date", "closing_attorney", 2, 13),
        ("title", "Title Commitment Received", 21, "contract_date", "closing_attorney", 3, 14),
        ("title", "Survey Completed (if required)", 21, "contract_date", "buyer_agent", 3, 15),
        ("other", "Homeowners Insurance Bound (must meet FHA standards)", -7, "closing_date", "buyer", 3, 16),
        ("other", "Verify FHA Required Repairs Complete", -5, "closing_date", "buyer_agent", 2, 17),
        ("closing", "Final Walk-Through", -2, "closing_date", "buyer_agent", 1, 18),
        ("closing", "Closing Disclosure Received (3-day rule)", -3, "closing_date", "lender", 2, 19),
        ("closing", "Closing Day", 0, "closing_date", "closing_attorney", 3, 20),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


def _ga_cash_buyer_items(template_id):
    """Georgia Cash Buyer — 12 milestones (no financing/appraisal)."""
    items = [
        ("inspection", "Schedule Home Inspection", 1, "contract_date", "buyer_agent", 1, 1),
        ("inspection", "Home Inspection Completed", 7, "contract_date", "inspector", 2, 2),
        ("inspection", "Termite/Pest Inspection", 7, "contract_date", "buyer_agent", 2, 3),
        ("inspection", "Request Repairs (Due Diligence)", 10, "contract_date", "buyer_agent", 2, 4),
        ("inspection", "Seller Responds to Repair Request", 14, "contract_date", "seller_agent", 2, 5),
        ("inspection", "Due Diligence Period Ends", 14, "contract_date", "buyer_agent", 3, 6),
        ("title", "Title Search Ordered", 5, "contract_date", "closing_attorney", 2, 7),
        ("title", "Title Commitment Received", 14, "contract_date", "closing_attorney", 3, 8),
        ("other", "Proof of Funds Provided", 5, "contract_date", "buyer", 2, 9),
        ("other", "Homeowners Insurance Bound", -5, "closing_date", "buyer", 2, 10),
        ("closing", "Final Walk-Through", -1, "closing_date", "buyer_agent", 1, 11),
        ("closing", "Closing Day", 0, "closing_date", "closing_attorney", 3, 12),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


def _al_conventional_buyer_items(template_id):
    """Alabama Conventional Buyer — 16 milestones."""
    items = [
        ("inspection", "Schedule Home Inspection", 1, "contract_date", "buyer_agent", 1, 1),
        ("inspection", "Home Inspection Completed", 7, "contract_date", "inspector", 2, 2),
        ("inspection", "Wood Destroying Organism Inspection", 7, "contract_date", "buyer_agent", 2, 3),
        ("inspection", "Request Repairs", 10, "contract_date", "buyer_agent", 2, 4),
        ("inspection", "Seller Responds to Repairs", 14, "contract_date", "seller_agent", 2, 5),
        ("appraisal", "Appraisal Ordered", 3, "contract_date", "lender", 2, 6),
        ("appraisal", "Appraisal Completed", 14, "contract_date", "lender", 3, 7),
        ("financing", "Loan Application Submitted", 3, "contract_date", "buyer", 2, 8),
        ("financing", "Loan Commitment Received", -10, "closing_date", "lender", 5, 9),
        ("title", "Title Search & Examination Ordered", 5, "contract_date", "title_company", 2, 10),
        ("title", "Title Insurance Commitment Received", 21, "contract_date", "title_company", 3, 11),
        ("title", "Survey Completed", 21, "contract_date", "buyer_agent", 3, 12),
        ("other", "Homeowners Insurance Bound", -7, "closing_date", "buyer", 3, 13),
        ("closing", "Final Walk-Through", -2, "closing_date", "buyer_agent", 1, 14),
        ("closing", "Closing Disclosure Received", -3, "closing_date", "lender", 2, 15),
        ("closing", "Closing Day", 0, "closing_date", "title_company", 3, 16),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


def _al_fha_buyer_items(template_id):
    """Alabama FHA Buyer — 18 milestones (includes FHA-specific requirements)."""
    items = [
        ("inspection", "Schedule Home Inspection", 1, "contract_date", "buyer_agent", 1, 1),
        ("inspection", "Home Inspection Completed", 7, "contract_date", "inspector", 2, 2),
        ("inspection", "Wood Destroying Organism Inspection", 7, "contract_date", "buyer_agent", 2, 3),
        ("inspection", "Request Repairs", 10, "contract_date", "buyer_agent", 2, 4),
        ("inspection", "Seller Responds to Repairs", 14, "contract_date", "seller_agent", 2, 5),
        ("appraisal", "FHA Appraisal Ordered", 3, "contract_date", "lender", 2, 6),
        ("appraisal", "FHA Appraisal Completed (includes MPR check)", 14, "contract_date", "lender", 3, 7),
        ("appraisal", "FHA Minimum Property Requirements Met", 18, "contract_date", "lender", 3, 8),
        ("financing", "Loan Application with FHA Case Number", 3, "contract_date", "buyer", 2, 9),
        ("financing", "Credit Check & FHA Eligibility Verified", 7, "contract_date", "lender", 2, 10),
        ("financing", "FHA Loan Commitment / Clear to Close", -10, "closing_date", "lender", 5, 11),
        ("title", "Title Search & Examination Ordered", 5, "contract_date", "title_company", 2, 12),
        ("title", "Title Insurance Commitment Received", 21, "contract_date", "title_company", 3, 13),
        ("title", "Survey Completed", 21, "contract_date", "buyer_agent", 3, 14),
        ("other", "Homeowners Insurance Bound (must meet FHA standards)", -7, "closing_date", "buyer", 3, 15),
        ("other", "Verify FHA Required Repairs Complete", -5, "closing_date", "buyer_agent", 2, 16),
        ("closing", "Final Walk-Through", -2, "closing_date", "buyer_agent", 1, 17),
        ("closing", "Closing Disclosure Received", -3, "closing_date", "lender", 2, 18),
        ("closing", "Closing Day", 0, "closing_date", "title_company", 3, 19),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


def _al_cash_buyer_items(template_id):
    """Alabama Cash Buyer — 11 milestones (no financing or appraisal)."""
    items = [
        ("inspection", "Schedule Home Inspection", 1, "contract_date", "buyer_agent", 1, 1),
        ("inspection", "Home Inspection Completed", 7, "contract_date", "inspector", 2, 2),
        ("inspection", "Wood Destroying Organism Inspection", 7, "contract_date", "buyer_agent", 2, 3),
        ("inspection", "Request Repairs", 10, "contract_date", "buyer_agent", 2, 4),
        ("inspection", "Seller Responds to Repairs", 14, "contract_date", "seller_agent", 2, 5),
        ("title", "Title Search & Examination Ordered", 5, "contract_date", "title_company", 2, 6),
        ("title", "Title Insurance Commitment Received", 14, "contract_date", "title_company", 3, 7),
        ("other", "Proof of Funds Provided", 5, "contract_date", "buyer", 2, 8),
        ("other", "Homeowners Insurance Bound", -5, "closing_date", "buyer", 2, 9),
        ("closing", "Final Walk-Through", -1, "closing_date", "buyer_agent", 1, 10),
        ("closing", "Closing Day", 0, "closing_date", "title_company", 3, 11),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


def _al_conventional_seller_items(template_id):
    """Alabama Conventional Seller — 12 milestones."""
    items = [
        ("other", "Property Disclosure Provided", 3, "contract_date", "seller_agent", 2, 1),
        ("inspection", "Buyer's Inspection Period (monitor)", 7, "contract_date", "seller_agent", 2, 2),
        ("inspection", "Review & Respond to Repair Requests", 14, "contract_date", "seller_agent", 2, 3),
        ("inspection", "Complete Agreed Repairs", 25, "contract_date", "seller", 3, 4),
        ("appraisal", "Appraisal Access Coordinated", 10, "contract_date", "seller_agent", 2, 5),
        ("appraisal", "Appraisal Value Reviewed", 21, "contract_date", "seller_agent", 3, 6),
        ("title", "Provide Title Documents", 10, "contract_date", "seller_agent", 3, 7),
        ("title", "Clear Title Issues (if any)", 28, "contract_date", "title_company", 3, 8),
        ("other", "Coordinate Utility Transfers", -5, "closing_date", "seller", 2, 9),
        ("closing", "Review Closing Disclosure", -3, "closing_date", "seller_agent", 2, 10),
        ("closing", "Final Walk-Through (buyer access)", -2, "closing_date", "seller_agent", 1, 11),
        ("closing", "Closing Day", 0, "closing_date", "title_company", 3, 12),
    ]
    return [
        MilestoneTemplateItem(
            template_id=template_id,
            type=t, title=title, day_offset=offset,
            offset_reference=ref, responsible_party_role=role,
            reminder_days_before=reminder, sort_order=order,
        )
        for t, title, offset, ref, role, reminder, order in items
    ]


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Check if already seeded
        from sqlalchemy import select, func
        count = (await db.execute(select(func.count()).select_from(User))).scalar()
        if count and count > 0:
            print("Database already seeded. Skipping.")
            return

        now = datetime.now(timezone.utc)

        # === USER ===
        agent = User(
            id=DEV_AGENT_ID,
            clerk_id="dev_agent_001",
            email="sarah.johnson@armistead.com",
            name="Sarah Johnson",
            phone="(404) 555-0123",
            brokerage_name="Armistead Realty Group",
            license_number="GA-384729",
            state="GA",
        )
        db.add(agent)

        # === COMMISSION CONFIG — 3% rate, 20/80 broker/agent split ===
        commission_config = CommissionConfig(
            agent_id=DEV_AGENT_ID,
            commission_type="percentage",
            default_rate=Decimal("0.0300"),       # 3% commission rate
            broker_split_percentage=Decimal("0.2000"),  # 20% to broker
            default_referral_fee_percentage=None,
        )
        db.add(commission_config)

        # === MILESTONE TEMPLATES ===
        templates_created = []

        # Template 1: GA Conventional Buyer
        tpl1_id = uuid.uuid4()
        tpl1 = MilestoneTemplate(
            id=tpl1_id, name="GA Conventional Buyer",
            state_code="GA", financing_type="conventional", representation_side="buyer",
            description="Standard Georgia conventional financing buyer-side checklist. 18 milestones from contract to close.",
            is_default=True, is_active=True,
        )
        db.add(tpl1)
        db.add_all(_ga_conventional_buyer_items(tpl1_id))
        templates_created.append("GA Conventional Buyer (18 items)")

        # Template 2: GA Conventional Seller
        tpl2_id = uuid.uuid4()
        tpl2 = MilestoneTemplate(
            id=tpl2_id, name="GA Conventional Seller",
            state_code="GA", financing_type="conventional", representation_side="seller",
            description="Standard Georgia conventional financing seller-side checklist. 14 milestones from contract to close.",
            is_default=True, is_active=True,
        )
        db.add(tpl2)
        db.add_all(_ga_conventional_seller_items(tpl2_id))
        templates_created.append("GA Conventional Seller (14 items)")

        # Template 3: GA FHA Buyer
        tpl3_id = uuid.uuid4()
        tpl3 = MilestoneTemplate(
            id=tpl3_id, name="GA FHA Buyer",
            state_code="GA", financing_type="fha", representation_side="buyer",
            description="Georgia FHA financing buyer-side checklist. 20 milestones including FHA-specific requirements (MPR, case number).",
            is_default=True, is_active=True,
        )
        db.add(tpl3)
        db.add_all(_ga_fha_buyer_items(tpl3_id))
        templates_created.append("GA FHA Buyer (20 items)")

        # Template 4: GA VA Buyer (reuses FHA structure with VA-specific naming)
        tpl4_id = uuid.uuid4()
        tpl4 = MilestoneTemplate(
            id=tpl4_id, name="GA VA Buyer",
            state_code="GA", financing_type="va", representation_side="buyer",
            description="Georgia VA financing buyer-side checklist. 20 milestones including VA-specific requirements (COE, MPRs).",
            is_default=True, is_active=True,
        )
        db.add(tpl4)
        # VA items are very similar to FHA — reuse with title tweaks
        va_items = _ga_fha_buyer_items(tpl4_id)
        for item in va_items:
            item.title = item.title.replace("FHA", "VA")
        db.add_all(va_items)
        templates_created.append("GA VA Buyer (20 items)")

        # Template 5: GA Cash Buyer
        tpl5_id = uuid.uuid4()
        tpl5 = MilestoneTemplate(
            id=tpl5_id, name="GA Cash Buyer",
            state_code="GA", financing_type="cash", representation_side="buyer",
            description="Georgia cash purchase buyer-side checklist. 12 milestones — no financing or appraisal.",
            is_default=True, is_active=True,
        )
        db.add(tpl5)
        db.add_all(_ga_cash_buyer_items(tpl5_id))
        templates_created.append("GA Cash Buyer (12 items)")

        # Template 6: AL Conventional Buyer
        tpl6_id = uuid.uuid4()
        tpl6 = MilestoneTemplate(
            id=tpl6_id, name="AL Conventional Buyer",
            state_code="AL", financing_type="conventional", representation_side="buyer",
            description="Alabama conventional financing buyer-side checklist. 16 milestones from contract to close.",
            is_default=True, is_active=True,
        )
        db.add(tpl6)
        db.add_all(_al_conventional_buyer_items(tpl6_id))
        templates_created.append("AL Conventional Buyer (16 items)")

        # Template 7: AL Conventional Seller
        tpl7_id = uuid.uuid4()
        tpl7 = MilestoneTemplate(
            id=tpl7_id, name="AL Conventional Seller",
            state_code="AL", financing_type="conventional", representation_side="seller",
            description="Alabama conventional financing seller-side checklist. 12 milestones from contract to close.",
            is_default=True, is_active=True,
        )
        db.add(tpl7)
        db.add_all(_al_conventional_seller_items(tpl7_id))
        templates_created.append("AL Conventional Seller (12 items)")

        # Template 8: AL FHA Buyer
        tpl8_id = uuid.uuid4()
        tpl8 = MilestoneTemplate(
            id=tpl8_id, name="AL FHA Buyer",
            state_code="AL", financing_type="fha", representation_side="buyer",
            description="Alabama FHA financing buyer-side checklist. 19 milestones including FHA-specific requirements (MPR, case number).",
            is_default=True, is_active=True,
        )
        db.add(tpl8)
        db.add_all(_al_fha_buyer_items(tpl8_id))
        templates_created.append("AL FHA Buyer (19 items)")

        # Template 9: AL VA Buyer (reuses AL FHA structure with VA-specific naming)
        tpl9_id = uuid.uuid4()
        tpl9 = MilestoneTemplate(
            id=tpl9_id, name="AL VA Buyer",
            state_code="AL", financing_type="va", representation_side="buyer",
            description="Alabama VA financing buyer-side checklist. 19 milestones including VA-specific requirements (COE, MPRs).",
            is_default=True, is_active=True,
        )
        db.add(tpl9)
        va_al_items = _al_fha_buyer_items(tpl9_id)
        for item in va_al_items:
            item.title = item.title.replace("FHA", "VA")
        db.add_all(va_al_items)
        templates_created.append("AL VA Buyer (19 items)")

        # Template 10: AL Cash Buyer
        tpl10_id = uuid.uuid4()
        tpl10 = MilestoneTemplate(
            id=tpl10_id, name="AL Cash Buyer",
            state_code="AL", financing_type="cash", representation_side="buyer",
            description="Alabama cash purchase buyer-side checklist. 11 milestones — no financing or appraisal.",
            is_default=True, is_active=True,
        )
        db.add(tpl10)
        db.add_all(_al_cash_buyer_items(tpl10_id))
        templates_created.append("AL Cash Buyer (11 items)")

        # === TRANSACTION 1: Confirmed, full data, some overdue milestones ===
        t1_id = uuid.uuid4()
        t1 = Transaction(
            id=t1_id,
            agent_id=DEV_AGENT_ID,
            status="confirmed",
            representation_side="buyer",
            financing_type="conventional",
            property_address="1247 Peachtree Heights Dr NE",
            property_city="Atlanta",
            property_state="GA",
            property_zip="30309",
            purchase_price={"amount": 485000, "currency": "USD"},
            earnest_money_amount={"amount": 10000, "currency": "USD"},
            closing_date=now + timedelta(days=18),
            contract_execution_date=now - timedelta(days=25),
            contract_document_url="contracts/t1_purchase_agreement.pdf",
            special_stipulations={"home_warranty": True, "seller_concessions": 5000},
            ai_extraction_confidence={"property_details": 0.95, "financial_terms": 0.92, "parties": 0.88, "dates": 0.91},
            template_id=tpl1_id,
        )
        db.add(t1)

        # T1 Parties
        parties_t1 = [
            Party(transaction_id=t1_id, name="Michael Chen", role="buyer", email="mchen@email.com", phone="(404) 555-1001", is_primary=True),
            Party(transaction_id=t1_id, name="Lisa Chen", role="buyer", email="lchen@email.com", phone="(404) 555-1002"),
            Party(transaction_id=t1_id, name="Robert Williams", role="seller", email="rwilliams@email.com", phone="(404) 555-2001", is_primary=True),
            Party(transaction_id=t1_id, name="James Mitchell", role="seller_agent", email="jmitchell@kw.com", phone="(404) 555-3001", company="Keller Williams Buckhead"),
            Party(transaction_id=t1_id, name="Patricia Davis", role="closing_attorney", email="pdavis@davislaw.com", phone="(404) 555-4001", company="Davis & Associates"),
            Party(transaction_id=t1_id, name="First National Lending", role="lender", email="loans@fnlending.com", phone="(800) 555-5001", company="First National Lending"),
        ]
        db.add_all(parties_t1)

        # T1 Milestones (mix of completed, pending, overdue)
        milestones_t1 = [
            Milestone(transaction_id=t1_id, type="inspection", title="Home Inspection", due_date=now - timedelta(days=10), status="completed", responsible_party_role="buyer", sort_order=1, completed_at=now - timedelta(days=11), reminder_days_before=2, is_auto_generated=True),
            Milestone(transaction_id=t1_id, type="inspection", title="Termite Inspection", due_date=now - timedelta(days=8), status="completed", responsible_party_role="buyer", sort_order=2, completed_at=now - timedelta(days=9), reminder_days_before=2, is_auto_generated=True),
            Milestone(transaction_id=t1_id, type="appraisal", title="Property Appraisal", due_date=now - timedelta(days=3), status="completed", responsible_party_role="lender", sort_order=3, completed_at=now - timedelta(days=4), reminder_days_before=3, is_auto_generated=True),
            Milestone(transaction_id=t1_id, type="financing", title="Loan Approval", due_date=now + timedelta(days=5), status="pending", responsible_party_role="lender", sort_order=4, reminder_days_before=5, is_auto_generated=True),
            Milestone(transaction_id=t1_id, type="other", title="Final Walk-Through", due_date=now + timedelta(days=16), status="pending", responsible_party_role="buyer", sort_order=5, reminder_days_before=2, is_auto_generated=True),
            Milestone(transaction_id=t1_id, type="closing", title="Closing Day", due_date=now + timedelta(days=18), status="pending", responsible_party_role="closing_attorney", sort_order=6, reminder_days_before=3, is_auto_generated=True),
        ]
        db.add_all(milestones_t1)

        # T1 Files
        files_t1 = [
            File(name="purchase_agreement_v2.pdf", content_type="application/pdf", url="https://storage.example.com/t1/purchase_agreement_v2.pdf", transaction_id=t1_id),
            File(name="pre_approval_letter.pdf", content_type="application/pdf", url="https://storage.example.com/t1/pre_approval_letter.pdf", transaction_id=t1_id),
            File(name="property_disclosure.pdf", content_type="application/pdf", url="https://storage.example.com/t1/property_disclosure.pdf", transaction_id=t1_id),
        ]
        db.add_all(files_t1)

        # T1 Inspection
        insp_id = uuid.uuid4()
        inspection = InspectionAnalysis(
            id=insp_id, transaction_id=t1_id,
            report_document_url="https://storage.example.com/t1/inspection_report.pdf",
            executive_summary="Overall the property is in good condition for its age (built 1985). The roof was replaced in 2019 and is in excellent shape. Minor issues noted with HVAC efficiency and some cosmetic concerns in the master bathroom. One moderate concern with the electrical panel that should be addressed.",
            total_estimated_cost_low={"amount": 2800, "currency": "USD"},
            total_estimated_cost_high={"amount": 5200, "currency": "USD"},
            overall_risk_level="medium",
        )
        db.add(inspection)
        insp_items = [
            InspectionItem(analysis_id=insp_id, description="Electrical panel shows signs of double-tapping on two breakers", location="Basement utility room", severity="moderate", estimated_cost_low={"amount": 800, "currency": "USD"}, estimated_cost_high={"amount": 1500, "currency": "USD"}, risk_assessment="Could pose fire hazard if not corrected.", recommendation="Repair before closing", repair_status="pending", sort_order=1),
            InspectionItem(analysis_id=insp_id, description="HVAC system operating at reduced efficiency (12 years old)", location="Attic / whole house", severity="minor", estimated_cost_low={"amount": 200, "currency": "USD"}, estimated_cost_high={"amount": 500, "currency": "USD"}, risk_assessment="System functional but may need replacement within 3-5 years.", recommendation="Service and monitor", repair_status="pending", sort_order=2),
            InspectionItem(analysis_id=insp_id, description="Grout deterioration in master bathroom shower", location="Master bathroom", severity="minor", estimated_cost_low={"amount": 300, "currency": "USD"}, estimated_cost_high={"amount": 600, "currency": "USD"}, risk_assessment="Cosmetic but could lead to water intrusion.", recommendation="Re-grout shower tiles", repair_status="pending", sort_order=3),
            InspectionItem(analysis_id=insp_id, description="Deck railing loose at two connection points", location="Rear deck", severity="moderate", estimated_cost_low={"amount": 500, "currency": "USD"}, estimated_cost_high={"amount": 1000, "currency": "USD"}, risk_assessment="Safety concern. Does not meet current code.", recommendation="Repair or replace railing", repair_status="in_progress", sort_order=4),
        ]
        db.add_all(insp_items)

        # T1 Amendments
        amendments_t1 = [
            Amendment(transaction_id=t1_id, field_changed="purchase_price", old_value={"amount": 495000}, new_value={"amount": 485000}, reason="Price reduction after inspection findings", changed_by_id=DEV_AGENT_ID, notification_sent=True),
            Amendment(transaction_id=t1_id, field_changed="closing_date", old_value={"date": (now + timedelta(days=10)).isoformat()}, new_value={"date": (now + timedelta(days=18)).isoformat()}, reason="Extended closing for lender processing", changed_by_id=DEV_AGENT_ID, notification_sent=True),
        ]
        db.add_all(amendments_t1)

        # T1 Communications
        comms_t1 = [
            Communication(transaction_id=t1_id, type="email", recipient_email="mchen@email.com", subject="Inspection Report Summary", body="Hi Michael, attached is the inspection report summary for 1247 Peachtree Heights Dr.", status="opened", sent_at=now - timedelta(days=9), opened_at=now - timedelta(days=9, hours=-2)),
            Communication(transaction_id=t1_id, type="email", recipient_email="rwilliams@email.com", subject="Repair Request", body="Robert, based on the inspection findings, we are requesting the following repairs...", status="sent", sent_at=now - timedelta(days=7)),
        ]
        db.add_all(comms_t1)

        # === TRANSACTION 2: Confirmed, OVERDUE milestones (health = red) ===
        t2_id = uuid.uuid4()
        t2 = Transaction(
            id=t2_id,
            agent_id=DEV_AGENT_ID,
            status="confirmed",
            representation_side="seller",
            financing_type="fha",
            property_address="892 Virginia Ave NE",
            property_city="Atlanta",
            property_state="GA",
            property_zip="30306",
            purchase_price={"amount": 375000, "currency": "USD"},
            earnest_money_amount={"amount": 7500, "currency": "USD"},
            closing_date=now + timedelta(days=25),
            contract_execution_date=now - timedelta(days=20),
            ai_extraction_confidence={"property_details": 0.97, "financial_terms": 0.85, "parties": 0.72, "dates": 0.94},
        )
        db.add(t2)

        parties_t2 = [
            Party(transaction_id=t2_id, name="Amanda Foster", role="seller", email="afoster@email.com", phone="(404) 555-6001", is_primary=True),
            Party(transaction_id=t2_id, name="David Kim", role="buyer", email="dkim@email.com", phone="(678) 555-7001", is_primary=True),
            Party(transaction_id=t2_id, name="Rachel Green", role="buyer_agent", email="rgreen@remax.com", phone="(770) 555-8001", company="RE/MAX Premier"),
        ]
        db.add_all(parties_t2)

        # T2: Some milestones overdue!
        milestones_t2 = [
            Milestone(transaction_id=t2_id, type="inspection", title="Buyer's Inspection", due_date=now - timedelta(days=5), status="pending", responsible_party_role="buyer", sort_order=1, reminder_days_before=3),
            Milestone(transaction_id=t2_id, type="inspection", title="Repair Request Response", due_date=now - timedelta(days=1), status="pending", responsible_party_role="seller_agent", sort_order=2, reminder_days_before=2),
            Milestone(transaction_id=t2_id, type="appraisal", title="FHA Appraisal", due_date=now + timedelta(days=2), status="pending", responsible_party_role="lender", sort_order=3, reminder_days_before=3),
            Milestone(transaction_id=t2_id, type="financing", title="Loan Commitment", due_date=now + timedelta(days=15), status="pending", responsible_party_role="lender", sort_order=4),
            Milestone(transaction_id=t2_id, type="closing", title="Closing", due_date=now + timedelta(days=25), status="pending", responsible_party_role="closing_attorney", sort_order=5),
        ]
        db.add_all(milestones_t2)

        # === TRANSACTION 3: Confirmed, closing in 7 days ===
        t3_id = uuid.uuid4()
        t3 = Transaction(
            id=t3_id,
            agent_id=DEV_AGENT_ID,
            status="confirmed",
            representation_side="buyer",
            financing_type="va",
            property_address="3401 Collier Rd NW",
            property_city="Atlanta",
            property_state="GA",
            property_zip="30305",
            purchase_price={"amount": 625000, "currency": "USD"},
            earnest_money_amount={"amount": 15000, "currency": "USD"},
            closing_date=now + timedelta(days=7),
            contract_execution_date=now - timedelta(days=35),
            ai_extraction_confidence={"property_details": 0.98, "financial_terms": 0.96, "parties": 0.93, "dates": 0.97},
        )
        db.add(t3)

        parties_t3 = [
            Party(transaction_id=t3_id, name="Thomas Rivera", role="buyer", email="trivera@email.com", phone="(404) 555-9001", is_primary=True),
            Party(transaction_id=t3_id, name="Catherine Blake", role="seller", email="cblake@email.com", phone="(404) 555-9002", is_primary=True),
            Party(transaction_id=t3_id, name="Mark Thompson", role="seller_agent", email="mthompson@compass.com", phone="(404) 555-9003", company="Compass Atlanta"),
            Party(transaction_id=t3_id, name="Atlanta Title Services", role="closing_attorney", email="closings@atltitle.com", phone="(404) 555-9004", company="Atlanta Title Services"),
            Party(transaction_id=t3_id, name="Veterans United", role="lender", email="va@vetunited.com", phone="(800) 555-9005", company="Veterans United Home Loans"),
        ]
        db.add_all(parties_t3)

        milestones_t3 = [
            Milestone(transaction_id=t3_id, type="inspection", title="Home Inspection", due_date=now - timedelta(days=20), status="completed", responsible_party_role="buyer", sort_order=1, completed_at=now - timedelta(days=21)),
            Milestone(transaction_id=t3_id, type="appraisal", title="VA Appraisal", due_date=now - timedelta(days=12), status="completed", responsible_party_role="lender", sort_order=2, completed_at=now - timedelta(days=13)),
            Milestone(transaction_id=t3_id, type="financing", title="VA Loan Approval", due_date=now - timedelta(days=5), status="completed", responsible_party_role="lender", sort_order=3, completed_at=now - timedelta(days=6)),
            Milestone(transaction_id=t3_id, type="other", title="Final Walk-Through", due_date=now + timedelta(days=5), status="pending", responsible_party_role="buyer", sort_order=4, reminder_days_before=2),
            Milestone(transaction_id=t3_id, type="closing", title="Closing Day", due_date=now + timedelta(days=7), status="pending", responsible_party_role="closing_attorney", sort_order=5, reminder_days_before=3),
        ]
        db.add_all(milestones_t3)

        # === TRANSACTION 4: Draft ===
        t4_id = uuid.uuid4()
        t4 = Transaction(
            id=t4_id,
            agent_id=DEV_AGENT_ID,
            status="draft",
            representation_side="seller",
            property_address="456 Morningside Dr NE",
            property_city="Atlanta",
            property_state="GA",
            property_zip="30324",
        )
        db.add(t4)
        db.add(Party(transaction_id=t4_id, name="Jennifer Walsh", role="seller", email="jwalsh@email.com", phone="(404) 555-1100", is_primary=True))

        # === TRANSACTION 5: Confirmed, AL transaction ===
        t5_id = uuid.uuid4()
        t5 = Transaction(
            id=t5_id,
            agent_id=DEV_AGENT_ID,
            status="confirmed",
            representation_side="buyer",
            financing_type="conventional",
            property_address="2100 Highland Ave S",
            property_city="Birmingham",
            property_state="AL",
            property_zip="35205",
            purchase_price={"amount": 299000, "currency": "USD"},
            earnest_money_amount={"amount": 6000, "currency": "USD"},
            closing_date=now + timedelta(days=35),
            contract_execution_date=now - timedelta(days=5),
        )
        db.add(t5)

        parties_t5 = [
            Party(transaction_id=t5_id, name="Derek Washington", role="buyer", email="dwash@email.com", phone="(205) 555-2001", is_primary=True),
            Party(transaction_id=t5_id, name="Marie Thompson", role="seller", email="mthompson@email.com", phone="(205) 555-2002", is_primary=True),
            Party(transaction_id=t5_id, name="Birmingham Title Co", role="title_company", email="closings@bhamtitle.com", phone="(205) 555-2003", company="Birmingham Title Co"),
        ]
        db.add_all(parties_t5)

        # T5: Fresh milestones — buyer side, upcoming
        milestones_t5 = [
            Milestone(transaction_id=t5_id, type="inspection", title="Schedule Home Inspection", due_date=now + timedelta(days=1), status="pending", responsible_party_role="buyer_agent", sort_order=1, reminder_days_before=1),
            Milestone(transaction_id=t5_id, type="appraisal", title="Appraisal Ordered", due_date=now + timedelta(days=3), status="pending", responsible_party_role="lender", sort_order=2, reminder_days_before=2),
            Milestone(transaction_id=t5_id, type="financing", title="Loan Application Submitted", due_date=now + timedelta(days=3), status="pending", responsible_party_role="buyer", sort_order=3, reminder_days_before=2),
            Milestone(transaction_id=t5_id, type="title", title="Title Search Ordered", due_date=now + timedelta(days=5), status="pending", responsible_party_role="title_company", sort_order=4, reminder_days_before=2),
            Milestone(transaction_id=t5_id, type="closing", title="Closing Day", due_date=now + timedelta(days=35), status="pending", responsible_party_role="title_company", sort_order=5, reminder_days_before=3),
        ]
        db.add_all(milestones_t5)

        # === COMMISSIONS — auto-create with 3% rate, 20/80 broker/agent split ===
        def _make_commission(txn_id, purchase_amount, status="projected"):
            rate = Decimal("0.0300")  # 3%
            gross = Decimal(str(purchase_amount)) * rate
            broker_pct = Decimal("0.2000")  # 20% to broker
            broker_amount = gross * broker_pct
            agent_net = gross - broker_amount

            comm = TransactionCommission(
                transaction_id=txn_id,
                agent_id=DEV_AGENT_ID,
                commission_type="percentage",
                rate=rate,
                gross_commission=gross,
                projected_net=agent_net,
                status=status,
            )
            db.add(comm)

            split = CommissionSplit(
                transaction_commission_id=None,  # will set after flush
                split_type="broker",
                recipient_name="Armistead Realty Group",
                is_percentage=True,
                percentage=broker_pct,
                calculated_amount=broker_amount,
            )
            return comm, split

        # T1: $485k confirmed → projected
        comm1, split1 = _make_commission(t1_id, 485000, "projected")
        # T2: $375k confirmed → projected
        comm2, split2 = _make_commission(t2_id, 375000, "projected")
        # T3: $625k closing in 7 days → pending
        comm3, split3 = _make_commission(t3_id, 625000, "pending")
        # T5: $299k AL → projected
        comm5, split5 = _make_commission(t5_id, 299000, "projected")

        await db.flush()  # Get commission IDs

        # Now link splits to commission IDs
        split1.transaction_commission_id = comm1.id
        split2.transaction_commission_id = comm2.id
        split3.transaction_commission_id = comm3.id
        split5.transaction_commission_id = comm5.id
        db.add_all([split1, split2, split3, split5])

        await db.commit()

        total_parties = len(parties_t1) + len(parties_t2) + len(parties_t3) + 1 + len(parties_t5)
        total_milestones = len(milestones_t1) + len(milestones_t2) + len(milestones_t3) + len(milestones_t5)

        print("=" * 60)
        print("  Armistead RE — Database Seeded Successfully!")
        print("=" * 60)
        print(f"  1 User (agent): Sarah Johnson")
        print(f"  10 Milestone Templates:")
        for t in templates_created:
            print(f"    - {t}")
        print(f"  5 Transactions:")
        print(f"    - 3 confirmed (1 healthy, 1 overdue, 1 closing soon)")
        print(f"    - 1 draft")
        print(f"    - 1 AL confirmed (new)")
        print(f"  {total_parties} Parties")
        print(f"  {total_milestones} Milestones")
        print(f"  {len(amendments_t1)} Amendments")
        print(f"  {len(files_t1)} Files")
        print(f"  1 Inspection Analysis with {len(insp_items)} items")
        print(f"  {len(comms_t1)} Communications")
        print(f"  1 Commission Config (3% rate, 20/80 broker/agent)")
        print(f"  4 Transaction Commissions (with broker splits)")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
