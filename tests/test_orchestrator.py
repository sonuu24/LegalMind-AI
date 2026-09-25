"""
Tests for LangGraph Orchestrator.
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.models import (
    OrchestratorInput,
    SessionContext,
    MatterInfo,
    FirmProfile,
    TaskType,
)
from src.orchestrator import LegalOrchestrator


class TestLegalOrchestrator:
    """Test cases for LegalOrchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return LegalOrchestrator()
    
    @pytest.fixture
    def session_context(self):
        """Create session context for testing."""
        return SessionContext(
            session_id="test-session-123",
            firm_id="test-firm",
            matter_id="TEST-001",
            user_id="test-user",
        )
    
    @pytest.fixture
    def matter_info(self):
        """Create matter info for testing."""
        return MatterInfo(
            matter_id="TEST-001",
            client_name="Test Client",
            matter_type="General",
            jurisdiction="Texas",
            responsible_attorney="Test Attorney",
        )
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test that orchestrator initializes correctly."""
        assert orchestrator is not None
        assert hasattr(orchestrator, 'graph')
        assert hasattr(orchestrator, 'contract_reviewer')
        assert hasattr(orchestrator, 'case_researcher')
        assert hasattr(orchestrator, 'document_drafter')
        assert hasattr(orchestrator, 'deadline_tracker')
        assert hasattr(orchestrator, 'billing_calculator')
    
    def test_task_classification_contract(self, orchestrator):
        """Test task classification for contract review."""
        task_descriptions = [
            "Review this contract for risks",
            "Check the agreement for unfavorable terms",
            "Analyze this NDA for problematic clauses",
            "Find risks in this service agreement",
        ]
        
        for description in task_descriptions:
            task_type = orchestrator._classify_task(description)
            assert task_type == TaskType.CONTRACT_REVIEW, \
                f"Expected CONTRACT_REVIEW for: {description}"
    
    def test_task_classification_research(self, orchestrator):
        """Test task classification for case research."""
        task_descriptions = [
            "Find cases similar to this one",
            "Research precedents for breach of contract",
            "Look up statute of limitations in Texas",
            "Search for relevant case law",
        ]
        
        for description in task_descriptions:
            task_type = orchestrator._classify_task(description)
            assert task_type == TaskType.CASE_RESEARCH, \
                f"Expected CASE_RESEARCH for: {description}"
    
    def test_task_classification_drafting(self, orchestrator):
        """Test task classification for document drafting."""
        task_descriptions = [
            "Draft an NDA agreement",
            "Create a demand letter",
            "Write a contract template",
            "Prepare a motion to dismiss",
        ]
        
        for description in task_descriptions:
            task_type = orchestrator._classify_task(description)
            assert task_type == TaskType.DRAFTING, \
                f"Expected DRAFTING for: {description}"
    
    def test_task_classification_deadline(self, orchestrator):
        """Test task classification for deadline tracking."""
        task_descriptions = [
            "Check filing deadlines for this case",
            "When is the statute of limitations?",
            "Track court dates and deadlines",
            "Generate docket report",
        ]
        
        for description in task_descriptions:
            task_type = orchestrator._classify_task(description)
            assert task_type == TaskType.DEADLINE, \
                f"Expected DEADLINE for: {description}"
    
    def test_task_classification_billing(self, orchestrator):
        """Test task classification for billing."""
        task_descriptions = [
            "Generate invoice for this matter",
            "Calculate billing hours",
            "Create time entry report",
            "Bill the client for work done",
        ]
        
        for description in task_descriptions:
            task_type = orchestrator._classify_task(description)
            assert task_type == TaskType.BILLING, \
                f"Expected BILLING for: {description}"
    
    def test_escalation_triggers(self, orchestrator, session_context, matter_info):
        """Test escalation trigger detection."""
        escalation_triggers = [
            "This involves criminal charges",
            "Constitutional rights are at issue",
            "Cross-border international matter",
            "Potential conflict of interest",
            "Statute of limitations expires soon",
            "Client is asking for legal advice",
        ]
        
        state = {
            "session_id": session_context.session_id,
            "matter_id": matter_info.matter_id,
            "client_name": matter_info.client_name,
            "jurisdiction": matter_info.jurisdiction,
            "input_data": {},
            "attorney_action_items": [],
        }
        
        for trigger_text in escalation_triggers:
            escalation_flag, escalation_reason = orchestrator._check_escalation_triggers(
                trigger_text, state
            )
            assert escalation_flag is True, \
                f"Expected escalation for: {trigger_text}"
            assert escalation_reason is not None
    
    def test_no_escalation_for_normal_tasks(self, orchestrator, session_context, matter_info):
        """Test that normal tasks don't trigger escalation."""
        normal_tasks = [
            "Review this standard NDA",
            "Research contract law precedents",
            "Draft a service agreement",
            "Check filing deadlines",
            "Generate monthly invoice",
        ]
        
        state = {
            "session_id": session_context.session_id,
            "matter_id": matter_info.matter_id,
            "client_name": matter_info.client_name,
            "jurisdiction": matter_info.jurisdiction,
            "input_data": {"contract_value": 100000},  # Below threshold
            "attorney_action_items": [],
        }
        
        for task_text in normal_tasks:
            escalation_flag, escalation_reason = orchestrator._check_escalation_triggers(
                task_text, state
            )
            assert escalation_flag is False, \
                f"Expected no escalation for: {task_text}"
    
    def test_high_value_contract_escalation(self, orchestrator, session_context, matter_info):
        """Test that high-value contracts trigger escalation."""
        state = {
            "session_id": session_context.session_id,
            "matter_id": matter_info.matter_id,
            "client_name": matter_info.client_name,
            "jurisdiction": matter_info.jurisdiction,
            "input_data": {"contract_value": 600000},  # Above $500k threshold
            "attorney_action_items": [],
        }
        
        escalation_flag, escalation_reason = orchestrator._check_escalation_triggers(
            "Review this contract", state
        )
        
        assert escalation_flag is True
        assert "$500,000" in escalation_reason
    
    def test_context_validation_contract(self, orchestrator):
        """Test context validation for contract review."""
        state = {
            "input_data": {
                "document_text": "Contract text here...",
            }
        }
        
        result = orchestrator._validate_context(state, TaskType.CONTRACT_REVIEW)
        assert result["valid"] is True
        assert len(result["missing_fields"]) == 0
    
    def test_context_validation_missing_fields(self, orchestrator):
        """Test context validation with missing fields."""
        state = {
            "input_data": {}  # Missing required fields
        }
        
        result = orchestrator._validate_context(state, TaskType.CONTRACT_REVIEW)
        assert result["valid"] is False
        assert "document_text" in result["missing_fields"]
    
    @pytest.mark.asyncio
    async def test_process_contract_review(self, orchestrator, session_context, matter_info):
        """Test processing a contract review task."""
        # Skip if no API key available
        import os
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key available")
        
        input_data = OrchestratorInput(
            task_description="Review this contract for risks",
            session_context=session_context,
            matter_info=matter_info,
            attachments=[{
                "document_text": """
                SIMPLE AGREEMENT
                
                This Agreement is made between Party A and Party B.
                
                1. PAYMENT: Payment due in 30 days.
                2. TERMINATION: Either party may terminate with 30 days notice.
                3. GOVERNING LAW: Texas law applies.
                """,
                "document_name": "Test Agreement",
            }],
        )
        
        result = await orchestrator.process(input_data)
        
        assert result is not None
        assert result.task_type == TaskType.CONTRACT_REVIEW
        assert result.matter_id == matter_info.matter_id
        assert result.requires_attorney_review is True
        assert "legal advice" in result.legal_disclaimer.lower()
    
    def test_build_final_result(self, orchestrator, session_context, matter_info):
        """Test final result building."""
        state = {
            "task_type": TaskType.CONTRACT_REVIEW.value,
            "matter_id": matter_info.matter_id,
            "client_name": matter_info.client_name,
            "jurisdiction": matter_info.jurisdiction,
            "session_id": session_context.session_id,
            "contract_review_result": {
                "review_id": "TEST-123",
                "risk_score": 50,
            },
            "case_research_result": None,
            "document_draft_result": None,
            "deadline_report": None,
            "billing_result": None,
            "confidence": 0.85,
            "escalation_flag": False,
            "escalation_reason": None,
            "attorney_action_items": [
                {
                    "item_id": "ACTION-001",
                    "description": "Review high-risk clause",
                    "priority": "HIGH",
                    "related_to": "Payment Terms",
                }
            ],
            "requires_attorney_review": True,
        }
        
        result = orchestrator._build_final_result(state)
        
        assert result is not None
        assert result.task_type == TaskType.CONTRACT_REVIEW
        assert "ContractReviewer" in result.agents_invoked
        assert len(result.attorney_action_items) > 0
        assert result.requires_attorney_review is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
