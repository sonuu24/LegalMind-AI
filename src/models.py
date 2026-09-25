"""
Pydantic models for MCP Legal Assistant data structures.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class TaskType(str, Enum):
    """Types of legal tasks."""
    CONTRACT_REVIEW = "contract_review"
    CASE_RESEARCH = "case_research"
    DRAFTING = "drafting"
    DEADLINE = "deadline"
    BILLING = "billing"
    FULL_MATTER = "full_matter"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NEUTRAL = "NEUTRAL"


class UrgencyLevel(str, Enum):
    """Deadline urgency levels."""
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    ADMINISTRATIVE = "ADMINISTRATIVE"


class AlertStatus(str, Enum):
    """Alert delivery status."""
    NOT_SENT = "NOT_SENT"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    OVERDUE = "OVERDUE"


class VerificationStatus(str, Enum):
    """Citation verification status."""
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED - needs attorney check"


class DocumentType(str, Enum):
    """Supported document types."""
    NDA = "NDA"
    SAAS_AGREEMENT = "SaaS Agreement"
    EMPLOYMENT = "Employment"
    SERVICE = "Service"
    MSA = "MSA"
    SOW = "SOW"
    OTHER = "Other"


# ============================================================
# BASE MODELS
# ============================================================

class FirmProfile(BaseModel):
    """Law firm profile and configuration."""
    firm_name: str
    jurisdiction: str
    practice_areas: List[str]
    billing_increment: float = 0.1
    conflict_check_required: bool = True
    malpractice_carrier: Optional[str] = None
    attorney_rates: Optional[Dict[str, float]] = None


class MatterInfo(BaseModel):
    """Legal matter information."""
    matter_id: str
    client_name: str
    matter_type: str
    jurisdiction: str
    responsible_attorney: str
    opposing_parties: Optional[List[str]] = None
    contract_value: Optional[float] = None
    open_date: Optional[date] = None


class SessionContext(BaseModel):
    """Current session context."""
    session_id: str
    firm_id: str
    matter_id: Optional[str] = None
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# ORCHESTRATOR MODELS
# ============================================================

class OrchestratorInput(BaseModel):
    """Input to the orchestrator agent."""
    task_description: str
    session_context: SessionContext
    matter_info: Optional[MatterInfo] = None
    firm_profile: Optional[FirmProfile] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class AttorneyActionItem(BaseModel):
    """Action item requiring attorney attention."""
    item_id: str
    description: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    due_date: Optional[datetime] = None
    related_to: Optional[str] = None


class OrchestratorResult(BaseModel):
    """Result from the orchestrator agent."""
    task_type: TaskType
    matter_id: str
    client_name: str
    jurisdiction: str
    agents_invoked: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    result: Dict[str, Any]
    attorney_action_items: List[AttorneyActionItem]
    requires_attorney_review: bool = True
    escalation_flag: bool = False
    escalation_reason: Optional[str] = None
    legal_disclaimer: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# CONTRACT REVIEWER MODELS
# ============================================================

class RiskFlag(BaseModel):
    """Individual risk flag in contract review."""
    flag_id: str
    section: str
    clause_number: Optional[str] = None
    risk_level: RiskLevel
    risk_category: str
    issue_description: str
    original_text: str
    suggested_revision: Optional[str] = None
    attorney_action: str


class ContractReviewResult(BaseModel):
    """Result from contract review."""
    review_id: str
    document_name: str
    document_type: str
    parties: Dict[str, str]
    effective_date: Optional[str] = None
    governing_law: Optional[str] = None
    contract_value: Optional[str] = None
    overall_risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    executive_summary: str
    risk_flags: List[RiskFlag]
    missing_clauses: List[str]
    defined_terms_issues: List[str]
    total_high_risks: int = 0
    total_medium_risks: int = 0
    total_low_risks: int = 0
    recommended_negotiation_points: List[str]
    attorney_review_required: bool = True
    legal_disclaimer: str
    
    @field_validator('total_high_risks', 'total_medium_risks', 'total_low_risks', mode='before')
    @classmethod
    def count_risks(cls, v, info) -> int:
        if v != 0:
            return v
        # Auto-count from risk_flags if not provided
        risk_flags = info.data.get('risk_flags', [])
        if info.field_name == 'total_high_risks':
            return len([f for f in risk_flags if f.risk_level == RiskLevel.HIGH])
        elif info.field_name == 'total_medium_risks':
            return len([f for f in risk_flags if f.risk_level == RiskLevel.MEDIUM])
        elif info.field_name == 'total_low_risks':
            return len([f for f in risk_flags if f.risk_level == RiskLevel.LOW])
        return v


# ============================================================
# CASE RESEARCHER MODELS
# ============================================================

class CaseFound(BaseModel):
    """Case found during research."""
    citation: str
    court: str
    year: int
    holding: str
    relevant_quote: Optional[str] = None
    pinpoint_citation: Optional[str] = None
    subsequent_history: Optional[str] = None
    relevance_to_matter: str
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    favors_client: bool = True


class ResearchResult(BaseModel):
    """Result from case research."""
    research_id: str
    matter_id: str
    question_presented: str
    jurisdiction: str
    practice_area: str
    brief_answer: str
    research_memo_text: str
    cases_found: List[CaseFound]
    statutes_found: List[str]
    adverse_authority: List[CaseFound] = []
    internal_db_matches: List[Dict[str, Any]] = []
    circuit_splits_identified: List[str] = []
    unsettled_law_flags: List[str] = []
    research_confidence: float = Field(ge=0.0, le=1.0)
    attorney_action_items: List[AttorneyActionItem] = []
    legal_disclaimer: str


# ============================================================
# DOCUMENT DRAFTER MODELS
# ============================================================

class AttorneyNote(BaseModel):
    """Note for attorney review."""
    section: str
    note: str
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class DraftResult(BaseModel):
    """Result from document drafting."""
    draft_id: str
    matter_id: str
    document_type: str
    document_title: str
    jurisdiction: str
    parties: Dict[str, Any]
    effective_date: Optional[str] = None
    draft_version: str = "v0.1 - First Draft for Attorney Review"
    full_document_text: str
    docx_file_path: Optional[str] = None
    attorney_notes: List[AttorneyNote] = []
    unfilled_placeholders: List[str] = []
    jurisdiction_flags: List[str] = []
    consistency_issues: List[str] = []
    clause_library_suggestions: List[str] = []
    word_count: int = 0
    estimated_review_time_minutes: int = 0
    attorney_review_required: bool = True
    legal_disclaimer: str


# ============================================================
# DEADLINE TRACKER MODELS
# ============================================================

class DeadlineInfo(BaseModel):
    """Individual deadline information."""
    deadline_id: str
    description: str
    due_date: date
    days_remaining: int
    urgency: UrgencyLevel
    category: str
    court_rule_reference: Optional[str] = None
    calculation_method: str
    alert_status: AlertStatus = AlertStatus.NOT_SENT
    requires_attorney_confirmation: bool = True


class MatterDeadlines(BaseModel):
    """Deadlines for a single matter."""
    matter_id: str
    client_name: str
    matter_type: str
    responsible_attorney: str
    deadlines: List[DeadlineInfo]


class DeadlineReport(BaseModel):
    """Daily deadline report."""
    docket_report_date: date
    firm_id: str
    deadlines_today: List[DeadlineInfo] = []
    deadlines_this_week: List[DeadlineInfo] = []
    deadlines_next_30_days: List[DeadlineInfo] = []
    sol_expiring_90_days: List[DeadlineInfo] = []
    overdue_deadlines: List[DeadlineInfo] = []
    alerts_sent: List[Dict[str, Any]] = []
    matters: List[MatterDeadlines] = []
    system_health: Dict[str, int] = {}


# ============================================================
# BILLING CALCULATOR MODELS
# ============================================================

class TimeEntry(BaseModel):
    """Individual time entry."""
    entry_id: str
    date: date
    timekeeper_id: str
    timekeeper_name: str
    matter_id: str
    hours: float = Field(ge=0.0)
    description: str
    billing_code: Optional[str] = None
    billable: bool = True
    rate: Optional[float] = None


class ExpenseEntry(BaseModel):
    """Expense entry for billing."""
    expense_id: str
    date: date
    description: str
    amount: float
    matter_id: str


class TrustAccount(BaseModel):
    """Trust account information."""
    balance_before: float
    applied_to_invoice: float
    balance_after: float
    replenishment_requested: bool = False


class MatterBudget(BaseModel):
    """Matter budget tracking."""
    total_budget: Optional[float] = None
    total_billed_to_date: float = 0.0
    percent_consumed: float = 0.0
    projected_at_completion: Optional[float] = None
    over_budget_flag: bool = False


class BillingResult(BaseModel):
    """Result from billing calculation."""
    billing_id: str
    matter_id: str
    client_name: str
    billing_period: Dict[str, date]
    invoice_number: str
    time_entries_processed: int = 0
    time_entries_flagged: List[Dict[str, Any]] = []
    block_billing_detected: List[Dict[str, Any]] = []
    total_hours: float = 0.0
    total_fees: str = "$0.00"
    total_expenses: str = "$0.00"
    total_invoice_amount: str = "$0.00"
    invoice_html: Optional[str] = None
    invoice_pdf_path: Optional[str] = None
    trust_account: Optional[TrustAccount] = None
    ethics_flags: List[str] = []
    matter_budget: Optional[MatterBudget] = None
    ready_to_send: bool = False
    requires_attorney_approval: bool = True


# ============================================================
# MCP TOOL SCHEMAS
# ============================================================

class ContractReviewerInput(BaseModel):
    """Input for contract review tool."""
    document_text: str
    document_name: str
    matter_info: MatterInfo
    firm_profile: Optional[FirmProfile] = None


class CaseResearcherInput(BaseModel):
    """Input for case research tool."""
    legal_question: str
    jurisdiction: str
    practice_area: str
    matter_info: MatterInfo
    favorable_research: bool = True


class DocumentDrafterInput(BaseModel):
    """Input for document drafting tool."""
    document_type: str
    party_details: Dict[str, Any]
    key_terms: Dict[str, Any]
    jurisdiction: str
    special_instructions: Optional[str] = None
    matter_info: MatterInfo


class DeadlineTrackerInput(BaseModel):
    """Input for deadline tracking tool."""
    firm_id: str
    matter_ids: Optional[List[str]] = None
    generate_report: bool = True


class BillingCalculatorInput(BaseModel):
    """Input for billing calculation tool."""
    matter_id: str
    billing_period_start: date
    billing_period_end: date
    include_expenses: bool = True
    generate_invoice: bool = True
