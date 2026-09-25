"""
FastAPI Server for MCP Legal Assistant.
Provides REST API endpoints for external clients.
"""
import logging
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from src.config import get_settings
from src.models import (
    OrchestratorInput,
    SessionContext,
    MatterInfo,
    FirmProfile,
    ContractReviewerInput,
    CaseResearcherInput,
    DocumentDrafterInput,
    DeadlineTrackerInput,
    BillingCalculatorInput,
)
from src.orchestrator import LegalOrchestrator
from src.agents import (
    ContractReviewerAgent,
    CaseResearcherAgent,
    DocumentDrafterAgent,
    DeadlineTrackerAgent,
    BillingCalculatorAgent,
)

logger = logging.getLogger(__name__)


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class ContractReviewRequest(BaseModel):
    """Request model for contract review endpoint."""
    document_text: str
    document_name: str
    matter_id: str
    client_name: str
    jurisdiction: str
    firm_profile: Optional[Dict[str, Any]] = None


class CaseResearchRequest(BaseModel):
    """Request model for case research endpoint."""
    legal_question: str
    jurisdiction: str
    practice_area: str
    matter_id: str
    client_name: str
    favorable_research: bool = True


class DocumentDraftRequest(BaseModel):
    """Request model for document drafting endpoint."""
    document_type: str
    party_details: Dict[str, Any]
    key_terms: Dict[str, Any] = Field(default_factory=dict)
    jurisdiction: str
    matter_id: str
    client_name: str
    special_instructions: Optional[str] = None


class DeadlineTrackerRequest(BaseModel):
    """Request model for deadline tracking endpoint."""
    firm_id: str
    matter_ids: Optional[List[str]] = None
    generate_report: bool = True


class BillingRequest(BaseModel):
    """Request model for billing endpoint."""
    matter_id: str
    billing_period_start: date
    billing_period_end: date
    client_name: str
    include_expenses: bool = True
    generate_invoice: bool = True


class OrchestratorRequest(BaseModel):
    """Request model for orchestrator endpoint."""
    task_description: str
    matter_id: str
    client_name: str
    jurisdiction: Optional[str] = None
    firm_profile: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime


class StandardResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


# ============================================================
# APP FACTORY
# ============================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    settings = get_settings()
    
    app = FastAPI(
        title="MCP Legal Assistant API",
        description="AI-powered legal research and drafting assistant for law firms",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize agents
    app.state.orchestrator = LegalOrchestrator()
    app.state.contract_reviewer = ContractReviewerAgent()
    app.state.case_researcher = CaseResearcherAgent()
    app.state.document_drafter = DocumentDrafterAgent()
    app.state.deadline_tracker = DeadlineTrackerAgent()
    app.state.billing_calculator = BillingCalculatorAgent()
    
    # Register routes
    register_routes(app)
    
    return app


def register_routes(app: FastAPI):
    """Register all API routes."""

    # Register authentication routes
    try:
        from src.auth import register_auth_routes
        register_auth_routes(app)
        logger.info("Authentication routes registered")
    except ImportError as e:
        logger.warning(f"Authentication not available: {e}")

    @app.get("/", response_model=StandardResponse)
    async def root():
        """Root endpoint - API information."""
        return StandardResponse(
            success=True,
            data={
                "name": "MCP Legal Assistant API",
                "version": "1.0.0",
                "description": "AI-powered legal research and drafting assistant",
            },
            message="Welcome to the MCP Legal Assistant API",
        )
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.utcnow(),
        )
    
    # ============================================================
    # SPECIALIST AGENT ENDPOINTS
    # ============================================================
    
    @app.post("/api/v1/contract/review", response_model=StandardResponse)
    async def review_contract(request: ContractReviewRequest):
        """
        Review a contract for risk clauses and unfavorable terms.
        
        Returns detailed risk analysis with suggested revisions.
        """
        try:
            agent: ContractReviewerAgent = app.state.contract_reviewer
            
            matter_info = MatterInfo(
                matter_id=request.matter_id,
                client_name=request.client_name,
                matter_type="Contract Review",
                jurisdiction=request.jurisdiction,
                responsible_attorney="TBD",
            )
            
            input_data = ContractReviewerInput(
                document_text=request.document_text,
                document_name=request.document_name,
                matter_info=matter_info,
                firm_profile=FirmProfile(**request.firm_profile) if request.firm_profile else None,
            )
            
            result = await agent.review(input_data)
            
            return StandardResponse(
                success=True,
                data=result.model_dump(),
                message="Contract review completed successfully",
            )
            
        except Exception as e:
            logger.error(f"Contract review failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/case/research", response_model=StandardResponse)
    async def research_case(request: CaseResearchRequest):
        """
        Conduct legal research across case law and statutes.
        
        Returns structured research memo with verified citations.
        """
        try:
            agent: CaseResearcherAgent = app.state.case_researcher
            
            matter_info = MatterInfo(
                matter_id=request.matter_id,
                client_name=request.client_name,
                matter_type="Legal Research",
                jurisdiction=request.jurisdiction,
                responsible_attorney="TBD",
            )
            
            input_data = CaseResearcherInput(
                legal_question=request.legal_question,
                jurisdiction=request.jurisdiction,
                practice_area=request.practice_area,
                matter_info=matter_info,
                favorable_research=request.favorable_research,
            )
            
            result = await agent.research(input_data)
            
            return StandardResponse(
                success=True,
                data=result.model_dump(),
                message="Legal research completed successfully",
            )
            
        except Exception as e:
            logger.error(f"Case research failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/document/draft", response_model=StandardResponse)
    async def draft_document(request: DocumentDraftRequest):
        """
        Draft a legal document.
        
        Returns first-draft document ready for attorney review.
        """
        try:
            agent: DocumentDrafterAgent = app.state.document_drafter
            
            matter_info = MatterInfo(
                matter_id=request.matter_id,
                client_name=request.client_name,
                matter_type="Document Drafting",
                jurisdiction=request.jurisdiction,
                responsible_attorney="TBD",
            )
            
            input_data = DocumentDrafterInput(
                document_type=request.document_type,
                party_details=request.party_details,
                key_terms=request.key_terms,
                jurisdiction=request.jurisdiction,
                matter_info=matter_info,
                client_name=request.client_name,
                special_instructions=request.special_instructions,
            )
            
            result = await agent.draft(input_data)
            
            return StandardResponse(
                success=True,
                data=result.model_dump(),
                message="Document drafting completed successfully",
            )
            
        except Exception as e:
            logger.error(f"Document drafting failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/deadlines/check", response_model=StandardResponse)
    async def check_deadlines(request: DeadlineTrackerRequest):
        """
        Check deadlines for a firm or specific matters.
        
        Returns daily docket report with urgency alerts.
        """
        try:
            agent: DeadlineTrackerAgent = app.state.deadline_tracker
            
            input_data = DeadlineTrackerInput(
                firm_id=request.firm_id,
                matter_ids=request.matter_ids,
                generate_report=request.generate_report,
            )
            
            result = await agent.get_deadlines(input_data)
            
            return StandardResponse(
                success=True,
                data=result.model_dump(),
                message="Deadline report generated successfully",
            )
            
        except Exception as e:
            logger.error(f"Deadline tracking failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/billing/calculate", response_model=StandardResponse)
    async def calculate_billing(request: BillingRequest):
        """
        Calculate billing and generate invoice.
        
        Returns detailed billing summary and invoice.
        """
        try:
            agent: BillingCalculatorAgent = app.state.billing_calculator
            
            input_data = BillingCalculatorInput(
                matter_id=request.matter_id,
                billing_period_start=request.billing_period_start,
                billing_period_end=request.billing_period_end,
                client_name=request.client_name,
                include_expenses=request.include_expenses,
                generate_invoice=request.generate_invoice,
            )
            
            result = await agent.calculate_billing(input_data)
            
            return StandardResponse(
                success=True,
                data=result.model_dump(),
                message="Billing calculation completed successfully",
            )
            
        except Exception as e:
            logger.error(f"Billing calculation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================================
    # ORCHESTRATOR ENDPOINT
    # ============================================================
    
    @app.post("/api/v1/orchestrate", response_model=StandardResponse)
    async def orchestrate_task(request: OrchestratorRequest):
        """
        Orchestrate a legal task through the appropriate specialist agent.
        
        Automatically routes to the correct agent based on task type.
        """
        try:
            orchestrator: LegalOrchestrator = app.state.orchestrator
            
            session_context = SessionContext(
                session_id=str(uuid.uuid4()),
                firm_id=request.firm_profile.get("firm_name", "unknown") if request.firm_profile else "unknown",
                matter_id=request.matter_id,
                user_id="api-user",
            )
            
            matter_info = MatterInfo(
                matter_id=request.matter_id,
                client_name=request.client_name,
                matter_type="General",
                jurisdiction=request.jurisdiction or get_settings().default_jurisdiction,
                responsible_attorney="TBD",
            )
            
            input_data = OrchestratorInput(
                task_description=request.task_description,
                session_context=session_context,
                matter_info=matter_info,
                firm_profile=FirmProfile(**request.firm_profile) if request.firm_profile else None,
                attachments=request.attachments,
            )
            
            result = await orchestrator.process(input_data)
            
            return StandardResponse(
                success=True,
                data=result.model_dump(),
                message="Task orchestrated successfully",
            )
            
        except Exception as e:
            logger.error(f"Task orchestration failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============================================================
    # UTILITY ENDPOINTS
    # ============================================================
    
    @app.get("/api/v1/templates", response_model=StandardResponse)
    async def list_templates():
        """List available document templates."""
        agent: DocumentDrafterAgent = app.state.document_drafter
        
        templates = {
            doc_type: {"description": desc, "supported": True}
            for doc_type, desc in agent.SUPPORTED_DOCUMENTS.items()
        }
        
        return StandardResponse(
            success=True,
            data={"templates": templates},
            message=f"Found {len(templates)} document templates",
        )
    
    @app.post("/api/v1/validate/time-description", response_model=StandardResponse)
    async def validate_time_description(description: str):
        """Validate a time entry description for quality."""
        agent: BillingCalculatorAgent = app.state.billing_calculator
        
        validation = agent.validate_time_description(description)
        
        return StandardResponse(
            success=True,
            data=validation,
            message="Time description validated",
        )


# ============================================================
# SERVER RUNNER
# ============================================================

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Run the FastAPI server.
    
    Args:
        host: Server host
        port: Server port
        reload: Enable auto-reload (development mode)
    """
    settings = get_settings()
    
    uvicorn.run(
        "src.server.server:create_app",
        host=host or settings.host,
        port=port or settings.port,
        reload=reload,
        factory=True,
        log_level=settings.log_level,
    )


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_server(reload=True)
