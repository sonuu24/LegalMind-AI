"""
Tests for Contract Reviewer Agent.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

from src.models import ContractReviewerInput, MatterInfo
from src.agents.contract_reviewer import ContractReviewerAgent


class TestContractReviewerAgent:
    """Test cases for ContractReviewerAgent."""
    
    @pytest.fixture
    def sample_contract(self):
        """Sample contract text for testing."""
        return """
        SOFTWARE LICENSE AGREEMENT
        
        This Software License Agreement ("Agreement") is entered into as of January 1, 2024,
        between TechCorp Inc. ("Licensor") and Client Company LLC ("Licensee").
        
        1. GRANT OF LICENSE
        Licensor hereby grants to Licensee a non-exclusive, non-transferable license to use
        the software without any restrictions.
        
        2. PAYMENT TERMS
        Licensee shall pay all invoices within 90 days of receipt. Late payments will incur
        a penalty of 5% per month. Licensee agrees to unlimited payment obligations without
        any cap on total fees.
        
        3. INTELLECTUAL PROPERTY
        All work product created by Licensee shall be owned by Licensor. This includes
        all modifications, derivatives, and improvements without exception.
        
        4. INDEMNIFICATION
        Licensee agrees to indemnify and hold harmless Licensor from any and all claims,
        damages, or expenses arising out of Licensee's use of the software, including
        third-party claims.
        
        5. LIMITATION OF LIABILITY
        Licensor's liability shall not be limited in any way. Licensee waives all rights
        to consequential damages but Licensor retains full rights.
        
        6. CONFIDENTIALITY
        "Confidential Information" means all information disclosed by Licensor to Licensee,
        whether marked confidential or not. This obligation shall continue indefinitely.
        
        7. TERMINATION
        Licensor may terminate this agreement at any time without notice. Licensee may
        terminate with 90 days written notice.
        
        8. GOVERNING LAW
        This agreement shall be governed by the laws of the State of California.
        Any disputes shall be resolved in courts located in San Francisco, California.
        Licensee waives right to jury trial and agrees to mandatory arbitration.
        
        9. NON-COMPETE
        Licensee agrees not to compete with Licensor in any software business worldwide
        for a period of 5 years after termination of this agreement.
        """
    
    @pytest.fixture
    def matter_info(self):
        """Sample matter info for testing."""
        return MatterInfo(
            matter_id="TEST-001",
            client_name="Test Client",
            matter_type="Contract Review",
            jurisdiction="Texas",
            responsible_attorney="Test Attorney",
        )
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        agent = ContractReviewerAgent()
        assert agent is not None
        assert hasattr(agent, 'review')
        assert hasattr(agent, 'review_sync')
    
    @pytest.mark.asyncio
    async def test_review_contract(self, sample_contract, matter_info):
        """Test contract review functionality."""
        # Skip if no API key available
        import os
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No API key available")
        
        agent = ContractReviewerAgent()
        
        input_data = ContractReviewerInput(
            document_text=sample_contract,
            document_name="Test Software License Agreement",
            matter_info=matter_info,
        )
        
        result = await agent.review(input_data)
        
        assert result is not None
        assert result.review_id is not None
        assert result.document_name == "Test Software License Agreement"
        assert result.risk_flags is not None
        assert result.legal_disclaimer is not None
        assert "attorney review" in result.legal_disclaimer.lower()
    
    def test_risk_flag_creation(self):
        """Test risk flag model creation."""
        from src.models import RiskFlag, RiskLevel
        
        flag = RiskFlag(
            flag_id="TEST-001",
            section="Payment Terms",
            clause_number="2",
            risk_level=RiskLevel.HIGH,
            risk_category="PAYMENT & FINANCIAL",
            issue_description="Payment terms exceed 60 days",
            original_text="Licensee shall pay all invoices within 90 days",
            suggested_revision="Licensee shall pay all invoices within 30 days",
            attorney_action="Negotiate shorter payment terms",
        )
        
        assert flag.flag_id == "TEST-001"
        assert flag.risk_level == RiskLevel.HIGH
        assert "Payment" in flag.section
    
    def test_parse_result_structure(self, sample_contract, matter_info):
        """Test that result parsing creates proper structure."""
        # Mock response from LLM
        mock_response = {
            "review_id": "TEST-123",
            "document_name": "Test Agreement",
            "document_type": "SaaS Agreement",
            "parties": {"party_a": "TechCorp Inc.", "party_b": "Client Company LLC"},
            "effective_date": "January 1, 2024",
            "governing_law": "California",
            "contract_value": "$50,000",
            "overall_risk_level": "HIGH",
            "risk_score": 75,
            "executive_summary": "This contract contains multiple high-risk clauses.",
            "risk_flags": [
                {
                    "flag_id": "FLAG-001",
                    "section": "Payment Terms",
                    "clause_number": "2",
                    "risk_level": "HIGH",
                    "risk_category": "PAYMENT & FINANCIAL",
                    "issue_description": "Payment terms exceed 60 days",
                    "original_text": "90 days payment terms",
                    "suggested_revision": "30 days payment terms",
                    "attorney_action": "Negotiate shorter terms"
                }
            ],
            "missing_clauses": ["Force Majeure", "Severability"],
            "defined_terms_issues": [],
            "total_high_risks": 1,
            "total_medium_risks": 0,
            "total_low_risks": 0,
            "recommended_negotiation_points": ["Payment terms", "Liability cap"],
            "attorney_review_required": True,
            "legal_disclaimer": "Test disclaimer",
        }
        
        agent = ContractReviewerAgent()
        
        input_data = ContractReviewerInput(
            document_text=sample_contract,
            document_name="Test Agreement",
            matter_info=matter_info,
        )
        
        # Test parsing
        result = agent._parse_result(mock_response, input_data)
        
        assert result.review_id == "TEST-123"
        assert result.document_type == "SaaS Agreement"
        assert len(result.risk_flags) == 1
        assert result.risk_flags[0].risk_level.value == "HIGH"
        assert result.total_high_risks == 1
        assert result.overall_risk_level.value == "HIGH"


class TestDocumentParser:
    """Test cases for document parsing utilities."""
    
    def test_parse_text_content(self):
        """Test text content parsing."""
        from src.pdf_parser import parse_text_content
        
        text = """
        AGREEMENT between Party A and Party B.
        Effective Date: January 1, 2024
        
        Section 1: Definitions
        "Confidential Information" means all proprietary data.
        
        Section 2: Terms
        This agreement shall continue for 2 years.
        """
        
        parsed = parse_text_content(text, "Test Agreement")
        
        assert parsed.full_text == text
        assert len(parsed.party_names) > 0
        assert parsed.effective_date is not None
    
    def test_section_extraction(self):
        """Test section extraction from documents."""
        from src.pdf_parser import parse_text_content
        
        text = """
        PAYMENT TERMS
        Licensee shall pay within 30 days.
        
        CONFIDENTIALITY
        All information shall be kept confidential.
        
        TERMINATION
        Either party may terminate with notice.
        """
        
        parsed = parse_text_content(text)
        
        assert "payment" in parsed.sections
        assert "confidentiality" in parsed.sections
        assert "termination" in parsed.sections


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
