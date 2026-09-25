"""
MCP Server implementation for Legal Assistant.
Exposes specialist legal AI tools via MCP protocol.
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.config import get_settings
from src.models import (
    ContractReviewerInput,
    CaseResearcherInput,
    DocumentDrafterInput,
    DeadlineTrackerInput,
    BillingCalculatorInput,
    MatterInfo,
    FirmProfile,
)
from src.pdf_parser import parse_text_content

logger = logging.getLogger(__name__)


def create_mcp_server() -> Server:
    """
    Create and configure the MCP Legal Assistant server.
    
    Returns:
        Configured MCP Server instance
    """
    server = Server("mcp-legal-assistant")
    
    # Register available tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available legal assistant tools."""
        return [
            Tool(
                name="contract_reviewer",
                description="Review contracts and legal agreements for risk clauses, missing protections, and unfavorable terms. Returns detailed risk analysis with suggested revisions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_text": {
                            "type": "string",
                            "description": "Full text of the contract or agreement to review"
                        },
                        "document_name": {
                            "type": "string",
                            "description": "Name/identifier for the document"
                        },
                        "matter_id": {
                            "type": "string",
                            "description": "Matter ID associated with this contract"
                        },
                        "client_name": {
                            "type": "string",
                            "description": "Client name"
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Governing law jurisdiction"
                        },
                        "firm_profile": {
                            "type": "object",
                            "description": "Optional law firm profile with preferences"
                        }
                    },
                    "required": ["document_text", "document_name", "matter_id", "client_name", "jurisdiction"]
                }
            ),
            Tool(
                name="case_researcher",
                description="Conduct comprehensive legal research across case law, statutes, and regulations. Returns structured research memo with verified citations.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "legal_question": {
                            "type": "string",
                            "description": "The legal question or issue to research"
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Legal jurisdiction (e.g., 'Texas', 'Federal', '9th Circuit')"
                        },
                        "practice_area": {
                            "type": "string",
                            "description": "Practice area (e.g., 'Contract', 'Employment', 'IP')"
                        },
                        "matter_id": {
                            "type": "string",
                            "description": "Matter ID for this research"
                        },
                        "client_name": {
                            "type": "string",
                            "description": "Client name"
                        },
                        "favorable_research": {
                            "type": "boolean",
                            "description": "Whether to focus on research favorable to client position"
                        }
                    },
                    "required": ["legal_question", "jurisdiction", "practice_area", "matter_id", "client_name"]
                }
            ),
            Tool(
                name="document_drafter",
                description="Draft legal documents, contracts, pleadings, and clauses. Returns first-draft documents ready for attorney review.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_type": {
                            "type": "string",
                            "description": "Type of document to draft (e.g., 'NDA', 'MSA', 'Demand Letter')"
                        },
                        "party_details": {
                            "type": "object",
                            "description": "Details about parties involved"
                        },
                        "key_terms": {
                            "type": "object",
                            "description": "Key business terms and provisions"
                        },
                        "jurisdiction": {
                            "type": "string",
                            "description": "Governing law jurisdiction"
                        },
                        "matter_id": {
                            "type": "string",
                            "description": "Matter ID"
                        },
                        "client_name": {
                            "type": "string",
                            "description": "Client name"
                        },
                        "special_instructions": {
                            "type": "string",
                            "description": "Any special instructions or requirements"
                        }
                    },
                    "required": ["document_type", "party_details", "jurisdiction", "matter_id", "client_name"]
                }
            ),
            Tool(
                name="deadline_tracker",
                description="Track and manage legal deadlines, court dates, and filing deadlines. Returns daily docket report with urgency alerts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "firm_id": {
                            "type": "string",
                            "description": "Law firm ID"
                        },
                        "matter_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of matter IDs to filter"
                        },
                        "generate_report": {
                            "type": "boolean",
                            "description": "Whether to generate full daily report"
                        }
                    },
                    "required": ["firm_id"]
                }
            ),
            Tool(
                name="billing_calculator",
                description="Calculate legal fees, process time entries, and generate invoices. Returns detailed billing summary and invoice.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "matter_id": {
                            "type": "string",
                            "description": "Matter ID to bill"
                        },
                        "billing_period_start": {
                            "type": "string",
                            "format": "date",
                            "description": "Start date of billing period (YYYY-MM-DD)"
                        },
                        "billing_period_end": {
                            "type": "string",
                            "format": "date",
                            "description": "End date of billing period (YYYY-MM-DD)"
                        },
                        "client_name": {
                            "type": "string",
                            "description": "Client name"
                        },
                        "include_expenses": {
                            "type": "boolean",
                            "description": "Whether to include expenses"
                        },
                        "generate_invoice": {
                            "type": "boolean",
                            "description": "Whether to generate invoice document"
                        }
                    },
                    "required": ["matter_id", "billing_period_start", "billing_period_end", "client_name"]
                }
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute a legal assistant tool.
        
        Args:
            name: Tool name to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution results
        """
        try:
            if name == "contract_reviewer":
                result = await _execute_contract_reviewer(arguments)
            elif name == "case_researcher":
                result = await _execute_case_researcher(arguments)
            elif name == "document_drafter":
                result = await _execute_document_drafter(arguments)
            elif name == "deadline_tracker":
                result = await _execute_deadline_tracker(arguments)
            elif name == "billing_calculator":
                result = await _execute_billing_calculator(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            
        except Exception as e:
            logger.error(f"Tool execution error for {name}: {e}")
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
    
    return server


async def _execute_contract_reviewer(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute contract review tool."""
    from ..agents.contract_reviewer import ContractReviewerAgent
    
    # Build input model
    matter_info = MatterInfo(
        matter_id=arguments["matter_id"],
        client_name=arguments["client_name"],
        matter_type="Contract Review",
        jurisdiction=arguments.get("jurisdiction", "Texas"),
        responsible_attorney="TBD",
    )
    
    firm_profile = None
    if arguments.get("firm_profile"):
        firm_profile = FirmProfile(**arguments["firm_profile"])
    
    input_model = ContractReviewerInput(
        document_text=arguments["document_text"],
        document_name=arguments["document_name"],
        matter_info=matter_info,
        firm_profile=firm_profile,
    )
    
    # Execute agent
    agent = ContractReviewerAgent()
    result = await agent.review(input_model)
    
    return result.model_dump()


async def _execute_case_researcher(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute case research tool."""
    from ..agents.case_researcher import CaseResearcherAgent
    
    matter_info = MatterInfo(
        matter_id=arguments["matter_id"],
        client_name=arguments["client_name"],
        matter_type="Legal Research",
        jurisdiction=arguments["jurisdiction"],
        responsible_attorney="TBD",
    )
    
    input_model = CaseResearcherInput(
        legal_question=arguments["legal_question"],
        jurisdiction=arguments["jurisdiction"],
        practice_area=arguments["practice_area"],
        matter_info=matter_info,
        favorable_research=arguments.get("favorable_research", True),
    )
    
    agent = CaseResearcherAgent()
    result = await agent.research(input_model)
    
    return result.model_dump()


async def _execute_document_drafter(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute document drafting tool."""
    from ..agents.document_drafter import DocumentDrafterAgent
    
    matter_info = MatterInfo(
        matter_id=arguments["matter_id"],
        client_name=arguments["client_name"],
        matter_type="Document Drafting",
        jurisdiction=arguments["jurisdiction"],
        responsible_attorney="TBD",
    )
    
    input_model = DocumentDrafterInput(
        document_type=arguments["document_type"],
        party_details=arguments["party_details"],
        key_terms=arguments.get("key_terms", {}),
        jurisdiction=arguments["jurisdiction"],
        matter_info=matter_info,
        client_name=arguments["client_name"],
        special_instructions=arguments.get("special_instructions"),
    )
    
    agent = DocumentDrafterAgent()
    result = await agent.draft(input_model)
    
    return result.model_dump()


async def _execute_deadline_tracker(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute deadline tracking tool."""
    from ..agents.deadline_tracker import DeadlineTrackerAgent
    
    input_model = DeadlineTrackerInput(
        firm_id=arguments["firm_id"],
        matter_ids=arguments.get("matter_ids"),
        generate_report=arguments.get("generate_report", True),
    )
    
    agent = DeadlineTrackerAgent()
    result = await agent.get_deadlines(input_model)
    
    return result.model_dump()


async def _execute_billing_calculator(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute billing calculation tool."""
    from ..agents.billing_calculator import BillingCalculatorAgent
    
    from datetime import datetime
    
    input_model = BillingCalculatorInput(
        matter_id=arguments["matter_id"],
        billing_period_start=datetime.strptime(arguments["billing_period_start"], "%Y-%m-%d").date(),
        billing_period_end=datetime.strptime(arguments["billing_period_end"], "%Y-%m-%d").date(),
        client_name=arguments["client_name"],
        include_expenses=arguments.get("include_expenses", True),
        generate_invoice=arguments.get("generate_invoice", True),
    )
    
    agent = BillingCalculatorAgent()
    result = await agent.calculate_billing(input_model)
    
    return result.model_dump()


async def run_mcp_server():
    """Run the MCP server using stdio transport."""
    server = create_mcp_server()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


# ============================================================
# Main entry point
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_mcp_server())
