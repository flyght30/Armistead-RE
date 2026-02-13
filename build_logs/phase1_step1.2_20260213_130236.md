# Phase 1 — Step 1.2: Database models & migrations
**Generated:** 2026-02-13T13:02:36.381628

===FILE: backend/app/database.py===
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql+asyncpg://user:pass@db/ttc"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

===END FILE===

===FILE: backend/app/models/__init__.py===
from .user import User
from .transaction import Transaction
from .party import Party
from .milestone import Milestone
from .communication import Communication
from .inspection_analysis import InspectionAnalysis, InspectionItem
from .amendment import Amendment
from .email_template import EmailTemplate

__all__ = [
    "User",
    "Transaction",
    "Party",
    "Milestone",
    "Communication",
    "InspectionAnalysis",
    "InspectionItem",
    "Amendment",
    "EmailTemplate"
]
===END FILE===

===FILE: backend/app/models/user.py===
from sqlalchemy import Column, UUID, String, JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP
from .base_model import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    clerk_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    brokerage_name = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    state = Column(String, nullable=True)
    email_signature = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/app/models/transaction.py===
from sqlalchemy import Column, UUID, ForeignKey, String, JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP
from .base_model import BaseModel
from .user import User

class Transaction(BaseModel):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False)
    representation_side = Column(String, nullable=False)
    financing_type = Column(String, nullable=True)
    property_address = Column(String, nullable=True)
    property_city = Column(String, nullable=True)
    property_state = Column(String, nullable=True)
    property_zip = Column(String, nullable=True)
    purchase_price = Column(JSON, nullable=True)
    earnest_money_amount = Column(JSON, nullable=True)
    closing_date = Column(TIMESTAMP(timezone=True), nullable=True)
    contract_document_url = Column(String, nullable=True)
    special_stipulations = Column(JSON, nullable=True)
    ai_extraction_confidence = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/app/models/party.py===
from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction

class Party(BaseModel):
    __tablename__ = "parties"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    notes = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/app/models/milestone.py===
from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction

class Milestone(BaseModel):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    responsible_party_role = Column(String, nullable=False)
    notes = Column(JSON, nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    reminder_days_before = Column(Integer, nullable=True)
    last_reminder_sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    sort_order = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/app/models/communication.py===
from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction
from .party import Party
from .milestone import Milestone

class Communication(BaseModel):
    __tablename__ = "communications"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=True)
    recipient_party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=True)
    type = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    attachments = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    resend_message_id = Column(UUID(as_uuid=True), nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=False)
    opened_at = Column(TIMESTAMP(timezone=True), nullable=True)
    clicked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    template_used = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/app/models/inspection.py===
from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction

class InspectionAnalysis(BaseModel):
    __tablename__ = "inspection_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    report_document_url = Column(String, nullable=False)
    executive_summary = Column(String, nullable=False)
    total_estimated_cost_low = Column(JSON, nullable=False)
    total_estimated_cost_high = Column(JSON, nullable=False)
    overall_risk_level = Column(String, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class InspectionItem(BaseModel):
    __tablename__ = "inspection_items"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("inspection_analyses.id"), nullable=False)
    description = Column(String, nullable=False)
    location = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    estimated_cost_low = Column(JSON, nullable=False)
    estimated_cost_high = Column(JSON, nullable=False)
    risk_assessment = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)
    repair_status = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/app/models/amendment.py===
from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction
from .user import User

class Amendment(BaseModel):
    __tablename__ = "amendments"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    field_changed = Column(String, nullable=False)
    old_value = Column(JSON, nullable=False)
    new_value = Column(JSON, nullable=False)
    reason = Column(String, nullable=False)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notification_sent = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/app/models/email_template.py===
from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .user import User

class EmailTemplate(BaseModel):
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    representation_side = Column(String, nullable=True)
    recipient_role = Column(String, nullable=False)
    subject_template = Column(String, nullable=False)
    body_template = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

===END FILE===

===FILE: backend/alembic.ini===
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://user:pass@db/ttc
target_metadata = app.database.Base.metadata
revision_identifier = head

[post_hooks]
always_run = true

[format]
version = 2.0
===END FILE===

===FILE: backend/alembic/env.py===
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.database import engine, Base

target_metadata = Base.metadata

async def run_migrations_offline():
    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = engine

    async with connectable.connect() as connection:
        await connection.run_sync(target_metadata.create_all)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
===END FILE===
