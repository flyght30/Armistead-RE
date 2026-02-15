from .common import PaginationParams, APIResponse
from .transaction import TransactionCreate, TransactionUpdate, TransactionResponse, TransactionDetailResponse, TransactionList
from .party import PartyCreate, PartyUpdate, PartyResponse
from .contract_parsing import ContractExtractionSchema, ParseResponse
from .milestone import MilestoneCreate, MilestoneUpdate, MilestoneResponse
from .amendment import AmendmentResponse
from .file import FileResponse
from .inspection import InspectionAnalysisResponse, InspectionItemResponse
from .communication import CommunicationResponse
from .milestone_template import (
    MilestoneTemplateCreate, MilestoneTemplateUpdate, MilestoneTemplateResponse,
    MilestoneTemplateListResponse, ApplyTemplateRequest, ApplyTemplateResponse,
)
from .action_item import (
    ActionItemCreate, ActionItemUpdate, ActionItemResponse,
    TodayViewResponse, HealthScoreResponse,
)

# Phase 2: Nudge Engine
from .notification import (
    NotificationRuleCreate, NotificationRuleUpdate, NotificationRuleResponse,
    EmailDraftCreate, EmailDraftUpdate, EmailDraftResponse,
    NotificationLogResponse, NotificationSettingsUpdate,
)

# Phase 4: AI Advisor
from .ai_advisor import (
    AdvisorChatRequest, AdvisorChatResponse, AdvisorConversation,
    RiskAlertResponse, RiskAlertUpdate, ClosingReadinessResponse,
    RiskDashboardResponse,
)

# Phase 5: Money
from .commission import (
    CommissionConfigCreate, CommissionConfigUpdate, CommissionConfigResponse,
    TransactionCommissionCreate, TransactionCommissionUpdate, TransactionCommissionResponse,
    CommissionSplitCreate, CommissionSplitResponse,
    PipelineSummary, CSVExportRequest,
)

# Phase 3: Party Portal
from .portal import (
    PortalAccessCreate, PortalAccessResponse, PortalAccessLogResponse,
    PortalUploadResponse, PortalUploadReview, PortalTransactionView,
)

# Phase 6: Docs Generation
from .document import (
    DocumentTemplateResponse, GenerateDocumentRequest,
    GeneratedDocumentResponse, DocumentPreviewResponse,
)

# Phase 7: Brokerage
from .brokerage import (
    BrokerageCreate, BrokerageUpdate, BrokerageResponse,
    TeamCreate, TeamUpdate, TeamResponse, TeamMemberAdd, TeamMemberResponse,
    ComplianceRuleCreate, ComplianceRuleUpdate, ComplianceRuleResponse,
    ComplianceViolationResponse, ComplianceDashboardResponse,
    PerformanceSnapshotResponse, AgentPerformanceSummary,
)
