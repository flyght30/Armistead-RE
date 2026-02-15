from .user import User
from .transaction import Transaction
from .party import Party
from .milestone import Milestone
from .communication import Communication
from .inspection import InspectionAnalysis, InspectionItem
from .amendment import Amendment
from .email_template import EmailTemplate
from .file import File
from .milestone_template import MilestoneTemplate, MilestoneTemplateItem
from .action_item import ActionItem

# Phase 2: Nudge Engine
from .notification_rule import NotificationRule
from .notification_log import NotificationLog
from .email_draft import EmailDraft

# Phase 4: AI Advisor
from .ai_advisor import AIAdvisorMessage
from .risk_alert import RiskAlert

# Phase 5: Money
from .commission import CommissionConfig, TransactionCommission, CommissionSplit

# Phase 3: Party Portal
from .portal import PortalAccess, PortalAccessLog, PortalUpload

# Phase 6: Docs Generation
from .document import DocumentTemplate, GeneratedDocument

# Phase 7: Brokerage
from .brokerage import Brokerage, Team, TeamMember, ComplianceRule, ComplianceViolation, PerformanceSnapshot

__all__ = [
    "User",
    "Transaction",
    "Party",
    "Milestone",
    "Communication",
    "InspectionAnalysis",
    "InspectionItem",
    "Amendment",
    "EmailTemplate",
    "File",
    "MilestoneTemplate",
    "MilestoneTemplateItem",
    "ActionItem",
    # Phase 2
    "NotificationRule",
    "NotificationLog",
    "EmailDraft",
    # Phase 4
    "AIAdvisorMessage",
    "RiskAlert",
    # Phase 5
    "CommissionConfig",
    "TransactionCommission",
    "CommissionSplit",
    # Phase 3
    "PortalAccess",
    "PortalAccessLog",
    "PortalUpload",
    # Phase 6
    "DocumentTemplate",
    "GeneratedDocument",
    # Phase 7
    "Brokerage",
    "Team",
    "TeamMember",
    "ComplianceRule",
    "ComplianceViolation",
    "PerformanceSnapshot",
]
