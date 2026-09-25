"""
Comprehensive tests for MCP Legal Assistant API.
"""
import pytest
import asyncio
from datetime import date, timedelta
from typing import Dict, Any

from fastapi.testclient import TestClient

from src.server.server import create_app
from src.models import (
    MatterInfo,
    FirmProfile,
    ContractReviewerInput,
    CaseResearcherInput,
    DocumentDrafterInput,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_matter() -> MatterInfo:
    """Sample matter for testing."""
    return MatterInfo(
        matter_id="TEST-001",
        client_name="Test Client Inc.",
        matter_type="Contract Review",
        jurisdiction="Delaware",
        responsible_attorney="Test Attorney",
    )


@pytest.fixture
def sample_firm() -> FirmProfile:
    """Sample firm profile for testing."""
    return FirmProfile(
        firm_name="Test Law Firm",
        jurisdiction="Delaware",
        practice_areas=["Corporate", "Contract"],
        billing_increment=0.1,
    )


# ============================================================
# HEALTH CHECK TESTS
# ============================================================

class TestHealthCheck:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "MCP Legal Assistant API" in data["data"]["name"]

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data


# ============================================================
# CONTRACT REVIEW TESTS
# ============================================================

class TestContractReview:
    """Test contract review functionality."""

    def test_review_contract_basic(self, client):
        """Test basic contract review."""
        contract_text = """
        EMPLOYMENT AGREEMENT
        
        This Agreement is between Test Corp ("Company") and John Doe ("Employee").
        
        1. NON-COMPETE: Employee agrees not to compete for 5 years after termination.
        2. CONFIDENTIALITY: Employee shall keep all information confidential indefinitely.
        3. TERMINATION: Company may terminate with 5 days notice.
        """

        response = client.post(
            "/api/v1/contract/review",
            json={
                "document_text": contract_text,
                "document_name": "Test Employment Agreement",
                "matter_id": "TEST-001",
                "client_name": "John Doe",
                "jurisdiction": "California",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_review_contract_missing_text(self, client):
        """Test contract review with missing document text."""
        response = client.post(
            "/api/v1/contract/review",
            json={
                "document_name": "Test Agreement",
                "matter_id": "TEST-001",
                "client_name": "Test Client",
                "jurisdiction": "Delaware",
            }
        )

        assert response.status_code == 422  # Validation error


# ============================================================
# CASE RESEARCH TESTS
# ============================================================

class TestCaseResearch:
    """Test case research functionality."""

    def test_research_basic(self, client):
        """Test basic legal research."""
        response = client.post(
            "/api/v1/case/research",
            json={
                "legal_question": "What is the statute of limitations for breach of contract in Delaware?",
                "jurisdiction": "Delaware",
                "practice_area": "Contract",
                "matter_id": "TEST-001",
                "client_name": "Test Client",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_research_missing_question(self, client):
        """Test research with missing legal question."""
        response = client.post(
            "/api/v1/case/research",
            json={
                "jurisdiction": "Delaware",
                "practice_area": "Contract",
                "matter_id": "TEST-001",
                "client_name": "Test Client",
            }
        )

        assert response.status_code == 422


# ============================================================
# DOCUMENT DRAFTING TESTS
# ============================================================

class TestDocumentDrafting:
    """Test document drafting functionality."""

    def test_draft_nda(self, client):
        """Test drafting an NDA."""
        response = client.post(
            "/api/v1/document/draft",
            json={
                "document_type": "NDA",
                "party_details": {
                    "party_a": "Test Corp",
                    "party_b": "Example Inc",
                },
                "key_terms": {
                    "confidentiality_period": "2 years",
                    "governing_law": "Delaware",
                },
                "jurisdiction": "Delaware",
                "matter_id": "TEST-001",
                "client_name": "Test Corp",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_draft_missing_type(self, client):
        """Test drafting with missing document type."""
        response = client.post(
            "/api/v1/document/draft",
            json={
                "party_details": {"party_a": "Test"},
                "jurisdiction": "Delaware",
                "matter_id": "TEST-001",
                "client_name": "Test Client",
            }
        )

        assert response.status_code == 422


# ============================================================
# DEADLINE TRACKING TESTS
# ============================================================

class TestDeadlineTracking:
    """Test deadline tracking functionality."""

    def test_check_deadlines(self, client):
        """Test deadline checking."""
        response = client.post(
            "/api/v1/deadlines/check",
            json={
                "firm_id": "TEST-FIRM",
                "matter_ids": ["TEST-001"],
                "generate_report": True,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============================================================
# BILLING TESTS
# ============================================================

class TestBilling:
    """Test billing functionality."""

    def test_calculate_billing(self, client):
        """Test billing calculation."""
        response = client.post(
            "/api/v1/billing/calculate",
            json={
                "matter_id": "TEST-001",
                "billing_period_start": (date.today() - timedelta(days=30)).isoformat(),
                "billing_period_end": date.today().isoformat(),
                "client_name": "Test Client",
                "include_expenses": True,
                "generate_invoice": True,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============================================================
# ORCHESTRATOR TESTS
# ============================================================

class TestOrchestrator:
    """Test orchestrator functionality."""

    def test_orchestrate_contract_review(self, client):
        """Test orchestrating contract review task."""
        response = client.post(
            "/api/v1/orchestrate",
            json={
                "task_description": "Review this employment contract for non-compete issues",
                "matter_id": "TEST-001",
                "client_name": "Test Client",
                "jurisdiction": "Delaware",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_orchestrate_legal_research(self, client):
        """Test orchestrating legal research task."""
        response = client.post(
            "/api/v1/orchestrate",
            json={
                "task_description": "Find cases about breach of contract statute of limitations",
                "matter_id": "TEST-002",
                "client_name": "Test Client",
                "jurisdiction": "Texas",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============================================================
# TEMPLATE TESTS
# ============================================================

class TestTemplates:
    """Test template listing."""

    def test_list_templates(self, client):
        """Test listing available templates."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "templates" in data["data"]


# ============================================================
# ERROR HANDLING TESTS
# ============================================================

class TestErrorHandling:
    """Test error handling."""

    def test_invalid_endpoint(self, client):
        """Test 404 for invalid endpoint."""
        response = client.get("/api/v1/invalid-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test 405 for wrong HTTP method."""
        response = client.get("/api/v1/contract/review")
        assert response.status_code == 405


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_contract_workflow(self, client):
        """Test complete contract review workflow."""
        # 1. Review contract
        contract_text = "SAMPLE CONTRACT TEXT FOR TESTING"
        review_response = client.post(
            "/api/v1/contract/review",
            json={
                "document_text": contract_text,
                "document_name": "Test Contract",
                "matter_id": "INT-001",
                "client_name": "Integration Test Client",
                "jurisdiction": "New York",
            }
        )
        assert review_response.status_code == 200

        # 2. Draft related document
        draft_response = client.post(
            "/api/v1/document/draft",
            json={
                "document_type": "NDA",
                "party_details": {"party_a": "Party A", "party_b": "Party B"},
                "jurisdiction": "New York",
                "matter_id": "INT-001",
                "client_name": "Integration Test Client",
            }
        )
        assert draft_response.status_code == 200

        # 3. Check deadlines
        deadline_response = client.post(
            "/api/v1/deadlines/check",
            json={
                "firm_id": "TEST-FIRM",
                "matter_ids": ["INT-001"],
            }
        )
        assert deadline_response.status_code == 200


# ============================================================
# PERFORMANCE TESTS
# ============================================================

class TestPerformance:
    """Performance tests."""

    def test_response_time_health(self, client):
        """Test health endpoint response time."""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond in under 1 second

    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]

        assert all(r.status_code == 200 for r in results)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=html"])
