"""
MCP Legal Assistant - Main Entry Point
"""
import sys
import asyncio
import click
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """MCP Legal Assistant - AI-powered legal research and drafting."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host, port, reload):
    """Start the FastAPI server."""
    from src.server.server import run_server
    run_server(host=host, port=port, reload=reload)


@cli.command()
def mcp():
    """Start the MCP server."""
    from src.mcp.server import run_mcp_server
    asyncio.run(run_mcp_server())


@cli.command()
@click.option("--contract", help="Path to contract PDF/text file")
@click.option("--matter-id", required=True, help="Matter ID")
@click.option("--client", required=True, help="Client name")
@click.option("--jurisdiction", default="Texas", help="Governing jurisdiction")
def review_contract(contract, matter_id, client, jurisdiction):
    """Review a contract for risks."""
    from src.agents import ContractReviewerAgent
    from src.models import ContractReviewerInput, MatterInfo
    from src.pdf_parser import parse_document
    
    # Parse contract
    if not contract:
        click.echo("Error: --contract is required", err=True)
        return
    
    parsed = parse_document(contract)
    
    # Create agent and input
    agent = ContractReviewerAgent()
    input_data = ContractReviewerInput(
        document_text=parsed.full_text,
        document_name=Path(contract).name,
        matter_info=MatterInfo(
            matter_id=matter_id,
            client_name=client,
            matter_type="Contract Review",
            jurisdiction=jurisdiction,
            responsible_attorney="TBD",
        ),
    )
    
    # Review
    click.echo("Reviewing contract...")
    result = agent.review_sync(input_data)
    
    # Display results
    click.echo(f"\n{'='*60}")
    click.echo(f"CONTRACT REVIEW RESULTS")
    click.echo(f"{'='*60}")
    click.echo(f"Document: {result.document_name}")
    click.echo(f"Risk Score: {result.risk_score}/100")
    click.echo(f"Overall Risk: {result.overall_risk_level.value}")
    click.echo(f"\nHigh Risks: {result.total_high_risks}")
    click.echo(f"Medium Risks: {result.total_medium_risks}")
    click.echo(f"Low Risks: {result.total_low_risks}")
    click.echo(f"\nExecutive Summary:")
    click.echo(f"{result.executive_summary}")
    
    if result.risk_flags:
        click.echo(f"\nRisk Flags:")
        for flag in result.risk_flags[:5]:  # Show first 5
            click.echo(f"  [{flag.risk_level.value}] {flag.section}: {flag.issue_description}")
    
    if result.missing_clauses:
        click.echo(f"\nMissing Clauses:")
        for clause in result.missing_clauses:
            click.echo(f"  - {clause}")
    
    click.echo(f"\n{'='*60}")
    click.echo("DISCLAIMER:")
    click.echo(result.legal_disclaimer)
    click.echo(f"{'='*60}")


@cli.command()
@click.option("--question", required=True, help="Legal question to research")
@click.option("--jurisdiction", required=True, help="Legal jurisdiction")
@click.option("--practice-area", required=True, help="Practice area")
@click.option("--matter-id", required=True, help="Matter ID")
@click.option("--client", required=True, help="Client name")
def research(question, jurisdiction, practice_area, matter_id, client):
    """Conduct legal research."""
    from src.agents import CaseResearcherAgent
    from src.models import CaseResearcherInput, MatterInfo
    
    # Create agent and input
    agent = CaseResearcherAgent()
    input_data = CaseResearcherInput(
        legal_question=question,
        jurisdiction=jurisdiction,
        practice_area=practice_area,
        matter_info=MatterInfo(
            matter_id=matter_id,
            client_name=client,
            matter_type="Legal Research",
            jurisdiction=jurisdiction,
            responsible_attorney="TBD",
        ),
        favorable_research=True,
    )
    
    # Research
    click.echo("Conducting legal research...")
    result = agent.research_sync(input_data)
    
    # Display results
    click.echo(f"\n{'='*60}")
    click.echo(f"LEGAL RESEARCH MEMO")
    click.echo(f"{'='*60}")
    click.echo(f"Question: {result.question_presented}")
    click.echo(f"Jurisdiction: {result.jurisdiction}")
    click.echo(f"\nBrief Answer:")
    click.echo(f"{result.brief_answer}")
    click.echo(f"\nCases Found: {len(result.cases_found)}")
    click.echo(f"Adverse Authority: {len(result.adverse_authority)}")
    click.echo(f"Confidence: {result.research_confidence:.0%}")
    
    if result.cases_found:
        click.echo(f"\nKey Cases:")
        for case in result.cases_found[:3]:  # Show first 3
            click.echo(f"  - {case.citation} ({case.court}, {case.year})")
    
    click.echo(f"\n{'='*60}")
    click.echo("DISCLAIMER:")
    click.echo(result.legal_disclaimer)
    click.echo(f"{'='*60}")


@cli.command()
@click.option("--type", "doc_type", required=True, help="Document type to draft")
@click.option("--matter-id", required=True, help="Matter ID")
@click.option("--client", required=True, help="Client name")
@click.option("--jurisdiction", default="Texas", help="Governing jurisdiction")
@click.option("--output", "-o", help="Output file path")
def draft(doc_type, matter_id, client, jurisdiction, output):
    """Draft a legal document."""
    from src.agents import DocumentDrafterAgent
    from src.models import DocumentDrafterInput, MatterInfo
    
    # Create agent and input
    agent = DocumentDrafterAgent()
    input_data = DocumentDrafterInput(
        document_type=doc_type,
        party_details={
            "party_a": f"{client}",
            "party_b": "Counterparty",
        },
        key_terms={},
        jurisdiction=jurisdiction,
        matter_info=MatterInfo(
            matter_id=matter_id,
            client_name=client,
            matter_type="Document Drafting",
            jurisdiction=jurisdiction,
            responsible_attorney="TBD",
        ),
        client_name=client,
    )
    
    # Draft
    click.echo(f"Drafting {doc_type}...")
    result = agent.draft_sync(input_data)
    
    # Save or display
    if output:
        with open(output, "w") as f:
            f.write(result.full_document_text)
        click.echo(f"Document saved to: {output}")
    else:
        click.echo(f"\n{'='*60}")
        click.echo(f"{result.document_title.upper()}")
        click.echo(f"{'='*60}")
        click.echo(result.full_document_text[:2000] + "...")  # Preview
        click.echo(f"\n\n[Full document is {result.word_count} words]")
        click.echo(f"Attorney Notes: {len(result.attorney_notes)}")
    
    click.echo(f"\n{'='*60}")
    click.echo("DISCLAIMER:")
    click.echo(result.legal_disclaimer)
    click.echo(f"{'='*60}")


@cli.command()
def templates():
    """List available document templates."""
    from src.agents import DocumentDrafterAgent
    
    agent = DocumentDrafterAgent()
    
    click.echo(f"\n{'='*60}")
    click.echo("AVAILABLE DOCUMENT TEMPLATES")
    click.echo(f"{'='*60}\n")
    
    for doc_type, description in agent.SUPPORTED_DOCUMENTS.items():
        click.echo(f"  {doc_type:25} - {description}")
    
    click.echo(f"\n{'='*60}")


if __name__ == "__main__":
    cli()
