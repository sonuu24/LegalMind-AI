"""
LangGraph Orchestrator - Master workflow controller for legal assistant.
Coordinates specialist agents using LangGraph StateGraph.
"""
import logging
import uuid
import json
from typing import TypedDict, Annotated, Literal, Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from src.models import (
    OrchestratorInput,
    OrchestratorResult,
    TaskType,
    MatterInfo,
    FirmProfile,
    SessionContext,
    AttorneyActionItem,
)
from src.config import get_settings
from src.agents import (
    ContractReviewerAgent,
    CaseResearcherAgent,
    DocumentDrafterAgent,
    DeadlineTrackerAgent,
    BillingCalculatorAgent,
)

logger = logging.getLogger(__name__)


# ============================================================
# STATE DEFINITIONS
# ============================================================

class AgentType(str, Enum):
    """Available specialist agents."""
    ORCHESTRATOR = "orchestrator"
    CONTRACT_REVIEWER = "contract_reviewer"
    CASE_RESEARCHER = "case_researcher"
    DOCUMENT_DRAFTER = "document_drafter"
    DEADLINE_TRACKER = "deadline_tracker"
    BILLING_CALCULATOR = "billing_calculator"


class LegalState(TypedDict):
    """
    State schema for legal assistant workflow.
    
    Tracks the flow of information through specialist agents.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    task_type: Optional[str]
    matter_id: str
    client_name: str
    jurisdiction: str
    session_id: str
    firm_profile: Optional[Dict[str, Any]]
    input_data: Optional[Dict[str, Any]]
    contract_review_result: Optional[Dict[str, Any]]
    case_research_result: Optional[Dict[str, Any]]
    document_draft_result: Optional[Dict[str, Any]]
    deadline_report: Optional[Dict[str, Any]]
    billing_result: Optional[Dict[str, Any]]
    confidence: float
    escalation_flag: bool
    escalation_reason: Optional[str]
    attorney_action_items: List[Dict[str, Any]]
    requires_attorney_review: bool


# ============================================================
# ORCHESTRATOR CLASS
# ============================================================

class LegalOrchestrator:
    """
    Master orchestrator for the MCP Legal Assistant.
    
    Uses LangGraph to coordinate specialist agents in a workflow.
    Routes tasks to appropriate agents and synthesizes results.
    """
    
    LEGAL_DISCLAIMER = (
        "This output is AI-generated legal research assistance only. It does not "
        "constitute legal advice and must be reviewed by a licensed attorney before "
        "any action is taken."
    )
    
    # Task classification keywords
    TASK_KEYWORDS = {
        TaskType.CONTRACT_REVIEW: [
            "review", "contract", "agreement", "check", "risks", "clause",
            "terms", "NDA", "MSA", "SOW", "amendment", "lease"
        ],
        TaskType.CASE_RESEARCH: [
            "research", "cases", "precedent", "statute", "case law",
            "legal research", "find cases", "citation", "ruling"
        ],
        TaskType.DRAFTING: [
            "draft", "document", "write", "create", "template",
            "letter", "pleading", "motion", "brief", "agreement"
        ],
        TaskType.DEADLINE: [
            "deadline", "court date", "filing", "docket", "due date",
            "statute of limitations", "response due", "hearing"
        ],
        TaskType.BILLING: [
            "billing", "invoice", "hours", "time entry", "fees",
            "bill client", "generate invoice", "time tracking"
        ],
    }
    
    # Human escalation triggers
    ESCALATION_TRIGGERS = [
        "criminal", "constitutional", "civil rights", "international",
        "cross-border", "malpractice", "conflict of interest",
        "statute of limitations", "legal advice", "class action",
    ]
    
    def __init__(self):
        """Initialize the orchestrator with specialist agents."""
        self.settings = get_settings()
        
        # Initialize specialist agents
        self.contract_reviewer = ContractReviewerAgent()
        self.case_researcher = CaseResearcherAgent()
        self.document_drafter = DocumentDrafterAgent()
        self.deadline_tracker = DeadlineTrackerAgent()
        self.billing_calculator = BillingCalculatorAgent()
        
        # Build the workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        builder = StateGraph(LegalState)
        
        # Add nodes for each agent
        builder.add_node("orchestrator", self._orchestrator_node)
        builder.add_node("contract_reviewer", self._contract_reviewer_node)
        builder.add_node("case_researcher", self._case_researcher_node)
        builder.add_node("document_drafter", self._document_drafter_node)
        builder.add_node("deadline_tracker", self._deadline_tracker_node)
        builder.add_node("billing_calculator", self._billing_calculator_node)
        builder.add_node("synthesize", self._synthesize_node)
        
        # Set entry point
        builder.set_entry_point("orchestrator")
        
        # Add conditional edges from orchestrator
        builder.add_conditional_edges(
            "orchestrator",
            self._route_from_orchestrator,
            {
                "contract_reviewer": "contract_reviewer",
                "case_researcher": "case_researcher",
                "document_drafter": "document_drafter",
                "deadline_tracker": "deadline_tracker",
                "billing_calculator": "billing_calculator",
                "synthesize": "synthesize",
            }
        )
        
        # Add edges from specialists to synthesize
        builder.add_edge("contract_reviewer", "synthesize")
        builder.add_edge("case_researcher", "synthesize")
        builder.add_edge("document_drafter", "synthesize")
        builder.add_edge("deadline_tracker", "synthesize")
        builder.add_edge("billing_calculator", "synthesize")
        
        # Final edge to END
        builder.add_edge("synthesize", END)
        
        return builder.compile()
    
    def _route_from_orchestrator(self, state: LegalState) -> str:
        """Determine which agent to route to based on task type."""
        task_type = state.get("task_type", "")
        
        routing_map = {
            TaskType.CONTRACT_REVIEW.value: "contract_reviewer",
            TaskType.CASE_RESEARCH.value: "case_researcher",
            TaskType.DRAFTING.value: "document_drafter",
            TaskType.DEADLINE.value: "deadline_tracker",
            TaskType.BILLING.value: "billing_calculator",
            TaskType.FULL_MATTER.value: "synthesize",  # Full matter goes directly to synthesize
        }
        
        return routing_map.get(task_type, "synthesize")
    
    async def _orchestrator_node(self, state: LegalState) -> LegalState:
        """
        Orchestrator node - classifies task and routes to appropriate agent.
        """
        logger.info("Orchestrator: Classifying task and routing...")
        
        task_description = ""
        if state.get("input_data"):
            task_description = state["input_data"].get("task_description", "")
        
        # Classify task
        task_type = self._classify_task(task_description)
        
        # Check for escalation triggers
        escalation_flag, escalation_reason = self._check_escalation_triggers(
            task_description, state
        )
        
        # Validate context
        validation_result = self._validate_context(state, task_type)
        
        return {
            **state,
            "task_type": task_type.value,
            "escalation_flag": escalation_flag,
            "escalation_reason": escalation_reason,
            "messages": state["messages"] + [
                AIMessage(content=f"Task classified as: {task_type.value}")
            ],
        }
    
    async def _contract_reviewer_node(self, state: LegalState) -> LegalState:
        """Contract reviewer agent node."""
        logger.info("Contract Reviewer: Analyzing contract...")
        
        try:
            from ..models import ContractReviewerInput
            
            input_data = state.get("input_data", {})
            
            # Build input for agent
            matter_info = MatterInfo(
                matter_id=state["matter_id"],
                client_name=state["client_name"],
                matter_type="Contract Review",
                jurisdiction=state["jurisdiction"],
                responsible_attorney="TBD",
            )
            
            review_input = ContractReviewerInput(
                document_text=input_data.get("document_text", ""),
                document_name=input_data.get("document_name", "Contract"),
                matter_info=matter_info,
                firm_profile=FirmProfile(**state["firm_profile"]) if state.get("firm_profile") else None,
            )
            
            # Execute review
            result = await self.contract_reviewer.review(review_input)
            
            # Extract attorney action items
            action_items = []
            for flag in result.risk_flags:
                if flag.risk_level.value == "HIGH":
                    action_items.append({
                        "item_id": flag.flag_id,
                        "description": f"Review {flag.risk_category} risk: {flag.issue_description}",
                        "priority": "HIGH",
                        "related_to": flag.section,
                    })
            
            return {
                **state,
                "contract_review_result": result.model_dump(),
                "attorney_action_items": state.get("attorney_action_items", []) + action_items,
                "confidence": 0.85 if result.risk_score < 50 else 0.70,
                "messages": state["messages"] + [
                    AIMessage(content=f"Contract review complete. Risk score: {result.risk_score}")
                ],
            }
            
        except Exception as e:
            logger.error(f"Contract review failed: {e}")
            return {
                **state,
                "contract_review_result": {"error": str(e)},
                "confidence": 0.0,
            }
    
    async def _case_researcher_node(self, state: LegalState) -> LegalState:
        """Case researcher agent node."""
        logger.info("Case Researcher: Conducting legal research...")
        
        try:
            from ..models import CaseResearcherInput
            
            input_data = state.get("input_data", {})
            
            matter_info = MatterInfo(
                matter_id=state["matter_id"],
                client_name=state["client_name"],
                matter_type="Legal Research",
                jurisdiction=state["jurisdiction"],
                responsible_attorney="TBD",
            )
            
            research_input = CaseResearcherInput(
                legal_question=input_data.get("legal_question", ""),
                jurisdiction=state["jurisdiction"],
                practice_area=input_data.get("practice_area", "General"),
                matter_info=matter_info,
                favorable_research=input_data.get("favorable_research", True),
            )
            
            result = await self.case_researcher.research(research_input)
            
            # Extract attorney action items
            action_items = [
                item.model_dump() for item in result.attorney_action_items
            ]
            
            return {
                **state,
                "case_research_result": result.model_dump(),
                "attorney_action_items": state.get("attorney_action_items", []) + action_items,
                "confidence": result.research_confidence,
                "messages": state["messages"] + [
                    AIMessage(content=f"Research complete. Cases found: {len(result.cases_found)}")
                ],
            }
            
        except Exception as e:
            logger.error(f"Case research failed: {e}")
            return {
                **state,
                "case_research_result": {"error": str(e)},
                "confidence": 0.0,
            }
    
    async def _document_drafter_node(self, state: LegalState) -> LegalState:
        """Document drafter agent node."""
        logger.info("Document Drafter: Drafting document...")
        
        try:
            from ..models import DocumentDrafterInput
            
            input_data = state.get("input_data", {})
            
            matter_info = MatterInfo(
                matter_id=state["matter_id"],
                client_name=state["client_name"],
                matter_type="Document Drafting",
                jurisdiction=state["jurisdiction"],
                responsible_attorney="TBD",
            )
            
            draft_input = DocumentDrafterInput(
                document_type=input_data.get("document_type", "Agreement"),
                party_details=input_data.get("party_details", {}),
                key_terms=input_data.get("key_terms", {}),
                jurisdiction=state["jurisdiction"],
                matter_info=matter_info,
                client_name=state["client_name"],
                special_instructions=input_data.get("special_instructions"),
            )
            
            result = await self.document_drafter.draft(draft_input)
            
            # Extract attorney action items from notes
            action_items = []
            for note in result.attorney_notes:
                if note.priority == "HIGH":
                    action_items.append({
                        "item_id": str(uuid.uuid4())[:8],
                        "description": note.note,
                        "priority": "HIGH",
                        "related_to": note.section,
                    })
            
            return {
                **state,
                "document_draft_result": result.model_dump(),
                "attorney_action_items": state.get("attorney_action_items", []) + action_items,
                "confidence": 0.80,
                "messages": state["messages"] + [
                    AIMessage(content=f"Document drafted. Word count: {result.word_count}")
                ],
            }
            
        except Exception as e:
            logger.error(f"Document drafting failed: {e}")
            return {
                **state,
                "document_draft_result": {"error": str(e)},
                "confidence": 0.0,
            }
    
    async def _deadline_tracker_node(self, state: LegalState) -> LegalState:
        """Deadline tracker agent node."""
        logger.info("Deadline Tracker: Generating deadline report...")
        
        try:
            from ..models import DeadlineTrackerInput
            
            input_data = state.get("input_data", {})
            
            tracker_input = DeadlineTrackerInput(
                firm_id=input_data.get("firm_id", state["matter_id"]),
                matter_ids=input_data.get("matter_ids"),
                generate_report=True,
            )
            
            result = await self.deadline_tracker.get_deadlines(tracker_input)
            
            # Check for critical deadlines
            action_items = []
            for deadline in result.deadlines_today + result.overdue_deadlines:
                action_items.append({
                    "item_id": deadline.deadline_id,
                    "description": f"{'OVERDUE' if deadline in result.overdue_deadlines else 'DUE TODAY'}: {deadline.description}",
                    "priority": "HIGH",
                    "related_to": deadline.category,
                })
            
            return {
                **state,
                "deadline_report": result.model_dump(),
                "attorney_action_items": state.get("attorney_action_items", []) + action_items,
                "confidence": 0.90,
                "messages": state["messages"] + [
                    AIMessage(content=f"Deadline report generated. Deadlines today: {len(result.deadlines_today)}")
                ],
            }
            
        except Exception as e:
            logger.error(f"Deadline tracking failed: {e}")
            return {
                **state,
                "deadline_report": {"error": str(e)},
                "confidence": 0.0,
            }
    
    async def _billing_calculator_node(self, state: LegalState) -> LegalState:
        """Billing calculator agent node."""
        logger.info("Billing Calculator: Processing billing...")
        
        try:
            from ..models import BillingCalculatorInput
            
            input_data = state.get("input_data", {})
            
            billing_input = BillingCalculatorInput(
                matter_id=state["matter_id"],
                billing_period_start=input_data.get("billing_period_start"),
                billing_period_end=input_data.get("billing_period_end"),
                client_name=state["client_name"],
                include_expenses=input_data.get("include_expenses", True),
                generate_invoice=input_data.get("generate_invoice", True),
            )
            
            result = await self.billing_calculator.calculate_billing(billing_input)
            
            # Check for ethics flags
            action_items = []
            for flag in result.ethics_flags:
                action_items.append({
                    "item_id": str(uuid.uuid4())[:8],
                    "description": f"Ethics review required: {flag}",
                    "priority": "HIGH",
                    "related_to": "Billing Compliance",
                })
            
            return {
                **state,
                "billing_result": result.model_dump(),
                "attorney_action_items": state.get("attorney_action_items", []) + action_items,
                "confidence": 0.85,
                "messages": state["messages"] + [
                    AIMessage(content=f"Billing complete. Total: {result.total_invoice_amount}")
                ],
            }
            
        except Exception as e:
            logger.error(f"Billing calculation failed: {e}")
            return {
                **state,
                "billing_result": {"error": str(e)},
                "confidence": 0.0,
            }
    
    async def _synthesize_node(self, state: LegalState) -> LegalState:
        """
        Synthesize node - combines results from all agents.
        """
        logger.info("Synthesizing results...")
        
        # Build final result
        result = self._build_final_result(state)
        
        return {
            **state,
            "messages": state["messages"] + [
                AIMessage(content="Task complete. Results synthesized.")
            ],
        }
    
    def _classify_task(self, task_description: str) -> TaskType:
        """
        Classify incoming task to appropriate agent.
        
        Args:
            task_description: User's task description
            
        Returns:
            TaskType enum value
        """
        task_lower = task_description.lower()
        
        # Score each task type
        scores = {}
        for task_type, keywords in self.TASK_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in task_lower)
            scores[task_type] = score
        
        # Return highest scoring task type
        if max(scores.values()) == 0:
            return TaskType.CASE_RESEARCH  # Default
        
        return max(scores, key=scores.get)
    
    def _check_escalation_triggers(
        self,
        task_description: str,
        state: LegalState,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if task requires human escalation.
        
        Args:
            task_description: User's task description
            state: Current workflow state
            
        Returns:
            (escalation_flag, escalation_reason)
        """
        task_lower = task_description.lower()
        
        for trigger in self.ESCALATION_TRIGGERS:
            if trigger in task_lower:
                return True, f"Escalation trigger detected: {trigger}"
        
        # Check contract value
        input_data = state.get("input_data", {})
        contract_value = input_data.get("contract_value", 0)
        if isinstance(contract_value, (int, float)) and contract_value > 500000:
            return True, "Contract value exceeds $500,000"
        
        return False, None
    
    def _validate_context(
        self,
        state: LegalState,
        task_type: TaskType,
    ) -> Dict[str, Any]:
        """
        Validate that required context is present for task.
        
        Args:
            state: Current workflow state
            task_type: Classified task type
            
        Returns:
            Validation result
        """
        input_data = state.get("input_data", {})
        missing = []
        
        if task_type == TaskType.CONTRACT_REVIEW:
            if not input_data.get("document_text"):
                missing.append("document_text")
        
        elif task_type == TaskType.CASE_RESEARCH:
            if not input_data.get("legal_question"):
                missing.append("legal_question")
        
        elif task_type == TaskType.DRAFTING:
            if not input_data.get("document_type"):
                missing.append("document_type")
            if not input_data.get("party_details"):
                missing.append("party_details")
        
        elif task_type == TaskType.BILLING:
            if not input_data.get("billing_period_start"):
                missing.append("billing_period_start")
            if not input_data.get("billing_period_end"):
                missing.append("billing_period_end")
        
        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
        }
    
    def _build_final_result(self, state: LegalState) -> OrchestratorResult:
        """
        Build final synthesized result.
        
        Args:
            state: Final workflow state
            
        Returns:
            OrchestratorResult
        """
        # Determine primary result based on task type
        result_data = {}
        agents_invoked = []
        
        if state.get("contract_review_result"):
            result_data["contract_review"] = state["contract_review_result"]
            agents_invoked.append("ContractReviewer")
        
        if state.get("case_research_result"):
            result_data["case_research"] = state["case_research_result"]
            agents_invoked.append("CaseResearcher")
        
        if state.get("document_draft_result"):
            result_data["document_draft"] = state["document_draft_result"]
            agents_invoked.append("DocumentDrafter")
        
        if state.get("deadline_report"):
            result_data["deadlines"] = state["deadline_report"]
            agents_invoked.append("DeadlineTracker")
        
        if state.get("billing_result"):
            result_data["billing"] = state["billing_result"]
            agents_invoked.append("BillingCalculator")
        
        # Parse attorney action items
        attorney_action_items = []
        for item in state.get("attorney_action_items", []):
            attorney_action_items.append(AttorneyActionItem(
                item_id=item.get("item_id", str(uuid.uuid4())[:8]),
                description=item.get("description", ""),
                priority=item.get("priority", "MEDIUM"),
                related_to=item.get("related_to"),
            ))
        
        return OrchestratorResult(
            task_type=TaskType(state.get("task_type", "case_research")),
            matter_id=state["matter_id"],
            client_name=state["client_name"],
            jurisdiction=state["jurisdiction"],
            agents_invoked=agents_invoked,
            confidence=state.get("confidence", 0.75),
            result=result_data,
            attorney_action_items=attorney_action_items,
            requires_attorney_review=True,
            escalation_flag=state.get("escalation_flag", False),
            escalation_reason=state.get("escalation_reason"),
            legal_disclaimer=self.LEGAL_DISCLAIMER,
            session_id=state["session_id"],
            timestamp=datetime.utcnow(),
        )
    
    async def process(self, input_data: OrchestratorInput) -> OrchestratorResult:
        """
        Process a legal task through the workflow.
        
        Args:
            input_data: Orchestrator input
            
        Returns:
            OrchestratorResult with synthesized output
        """
        logger.info(f"Processing task: {input_data.task_description[:100]}...")
        
        # Build initial state
        initial_state: LegalState = {
            "messages": [
                SystemMessage(content="You are LexPilot, the MCP Legal Assistant."),
                HumanMessage(content=input_data.task_description),
            ],
            "task_type": None,
            "matter_id": input_data.matter_info.matter_id if input_data.matter_info else "UNKNOWN",
            "client_name": input_data.matter_info.client_name if input_data.matter_info else "Unknown Client",
            "jurisdiction": input_data.matter_info.jurisdiction if input_data.matter_info else self.settings.default_jurisdiction,
            "session_id": input_data.session_context.session_id,
            "firm_profile": input_data.firm_profile.model_dump() if input_data.firm_profile else None,
            "input_data": {
                "task_description": input_data.task_description,
                **(input_data.attachments[0] if input_data.attachments else {}),
            },
            "contract_review_result": None,
            "case_research_result": None,
            "document_draft_result": None,
            "deadline_report": None,
            "billing_result": None,
            "confidence": 0.0,
            "escalation_flag": False,
            "escalation_reason": None,
            "attorney_action_items": [],
            "requires_attorney_review": True,
        }
        
        # Run the workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        # Build and return result
        result = self._build_final_result(final_state)
        
        logger.info(
            f"Task complete. Agents invoked: {result.agents_invoked}, "
            f"Confidence: {result.confidence}"
        )
        
        return result
    
    def process_sync(self, input_data: OrchestratorInput) -> OrchestratorResult:
        """
        Synchronous version of process.
        
        Args:
            input_data: Orchestrator input
            
        Returns:
            OrchestratorResult with synthesized output
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.process(input_data))
