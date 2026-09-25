"""
Document Drafter Agent - Precision legal document generation.
"""
import logging
import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.models import (
    DocumentDrafterInput,
    DraftResult,
    AttorneyNote,
    MatterInfo,
)
from src.config import get_settings

logger = logging.getLogger(__name__)


class DocumentDrafterAgent:
    """
    AI agent for legal document drafting.
    Generates first-draft contracts, pleadings, letters, and clauses.
    
    CRITICAL: All output is FIRST DRAFT only - requires attorney review.
    """
    
    LEGAL_DISCLAIMER = (
        "This document is an AI-generated first draft for attorney review only. It does "
        "not constitute legal advice and must not be executed, filed, or used in any "
        "legal matter until reviewed and approved by a licensed attorney."
    )
    
    # Supported document templates
    SUPPORTED_DOCUMENTS = {
        "NDA": "Non-Disclosure Agreement (Mutual or One-Way)",
        "MSA": "Master Service Agreement",
        "SOW": "Statement of Work",
        "EMPLOYMENT": "Employment Agreement",
        "INDEPENDENT_CONTRACTOR": "Independent Contractor Agreement",
        "CONSULTING": "Consulting Agreement",
        "SAAS": "SaaS Subscription Agreement",
        "VENDOR": "Vendor Agreement",
        "LOI": "Letter of Intent",
        "TERM_SHEET": "Term Sheet",
        "DEMAND_LETTER": "Demand Letter",
        "CEASE_DESIST": "Cease and Desist Letter",
        "SETTLEMENT": "Settlement Agreement and Release",
        "BOARD_RESOLUTION": "Board Resolution",
        "IP_ASSIGNMENT": "IP Assignment Agreement",
    }
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize Document Drafter agent.
        
        Args:
            model: Model to use (defaults to Claude 3.5 Sonnet)
        """
        settings = get_settings()
        self.model_name = model or settings.document_drafter_model
        
        # Use Claude for best structured writing
        if "claude" in self.model_name.lower():
            self.llm = ChatAnthropic(
                model=self.model_name,
                api_key=settings.anthropic_api_key,
                temperature=0.2,
                max_tokens=8192,
            )
        else:
            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=settings.openai_api_key,
                temperature=0.2,
                max_tokens=8192,
            )
        
        self.prompt = self._build_prompt()
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the document drafting prompt."""
        system_prompt = """
You are DocumentDrafter — a precision legal writing engine.
Generate first-draft legal documents based on attorney instructions.

CRITICAL: Every document you produce is a FIRST DRAFT only.
It must be reviewed, modified, and approved by a licensed attorney.

DRAFTING STYLE RULES:

ALWAYS:
- Use plain, precise language — avoid unnecessary legalese
- Define every term you use more than once
- Use active voice where possible
- Number all sections and subsections consistently
- Include a complete definitions section
- Use "shall" for mandatory obligations, "may" for discretionary
- Use "will" only for future-tense factual statements

NEVER:
- Use ambiguous pronouns (always use defined party names)
- Use "and/or" (choose "and" or "or" — be precise)
- Use "reasonable" without defining what it means
- Leave any bracketed placeholder unfilled without flagging
- Use archaic terms (witnesseth, hereinafter, heretofore) unless required

DOCUMENT STRUCTURE:
Every legal document should include (as applicable):
1. Title and preamble
2. Parties and recitals
3. Definitions section
4. Operative provisions
5. Representations and warranties
6. Covenants
7. Conditions precedent
8. Termination provisions
9. General provisions (governing law, dispute resolution, etc.)
10. Signature blocks

ATTORNEY NOTES:
Use inline notes for issues requiring attorney attention:
[NOTE: {{issue or question for attorney}}]

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{{
  "draft_id": "unique-id",
  "matter_id": "matter-id",
  "document_type": "document type",
  "document_title": "document title",
  "jurisdiction": "jurisdiction",
  "parties": {{}},
  "effective_date": "date or null",
  "draft_version": "v0.1 - First Draft for Attorney Review",
  "full_document_text": "complete document text",
  "docx_file_path": null,
  "attorney_notes": [
    {{"section": "section name", "note": "note", "priority": "HIGH|MEDIUM|LOW"}}
  ],
  "unfilled_placeholders": [],
  "jurisdiction_flags": [],
  "consistency_issues": [],
  "clause_library_suggestions": [],
  "word_count": 0,
  "estimated_review_time_minutes": 0,
  "attorney_review_required": true,
  "legal_disclaimer": "{disclaimer}"
}}

DRAFTING REQUEST:
Document Type: {document_type}
Jurisdiction: {jurisdiction}
Party Details: {party_details}
Key Terms: {key_terms}
Special Instructions: {special_instructions}
"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
        ])
    
    async def draft(self, input_data: DocumentDrafterInput) -> DraftResult:
        """
        Draft a legal document.
        
        Args:
            input_data: Drafting input
            
        Returns:
            DraftResult with document
        """
        try:
            logger.info(f"Starting document drafting: {input_data.document_type}")
            
            # Validate document type
            doc_type_upper = input_data.document_type.upper()
            if doc_type_upper not in self.SUPPORTED_DOCUMENTS:
                logger.warning(
                    f"Document type '{input_data.document_type}' not in standard library. "
                    f"Proceeding with generic template."
                )
            
            # Build the chain
            chain = self.prompt | self.llm | JsonOutputParser()
            
            # Execute drafting
            response = await chain.ainvoke({
                "document_type": input_data.document_type,
                "jurisdiction": input_data.jurisdiction,
                "party_details": json.dumps(input_data.party_details, indent=2),
                "key_terms": json.dumps(input_data.key_terms, indent=2),
                "special_instructions": input_data.special_instructions or "None",
                "disclaimer": self.LEGAL_DISCLAIMER,
            })
            
            # Parse and validate response
            result = self._parse_result(response, input_data)
            
            logger.info(
                f"Document drafting complete: {result.word_count} words, "
                f"{len(result.attorney_notes)} attorney notes"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Document drafting failed: {e}")
            raise
    
    def _parse_result(
        self,
        response: dict,
        input_data: DocumentDrafterInput,
    ) -> DraftResult:
        """Parse and validate the LLM response."""
        # Parse attorney notes
        attorney_notes = []
        for note in response.get("attorney_notes", []):
            if isinstance(note, str):
                attorney_notes.append(AttorneyNote(
                    section="General",
                    note=note,
                    priority="MEDIUM",
                ))
            elif isinstance(note, dict):
                attorney_notes.append(AttorneyNote(
                    section=note.get("section", "General"),
                    note=note.get("note", ""),
                    priority=note.get("priority", "MEDIUM"),
                ))
        
        # Calculate word count
        full_text = response.get("full_document_text", "")
        word_count = len(full_text.split())
        
        # Estimate review time (roughly 1 minute per 500 words for legal docs)
        estimated_review_time = max(15, word_count // 500)
        
        return DraftResult(
            draft_id=response.get("draft_id", str(uuid.uuid4())[:8]),
            matter_id=input_data.matter_info.matter_id,
            document_type=input_data.document_type,
            document_title=response.get("document_title", f"{input_data.document_type} Agreement"),
            jurisdiction=input_data.jurisdiction,
            parties=response.get("parties", input_data.party_details),
            effective_date=response.get("effective_date"),
            draft_version=response.get("draft_version", "v0.1 - First Draft for Attorney Review"),
            full_document_text=full_text,
            docx_file_path=response.get("docx_file_path"),
            attorney_notes=attorney_notes,
            unfilled_placeholders=response.get("unfilled_placeholders", []),
            jurisdiction_flags=response.get("jurisdiction_flags", []),
            consistency_issues=response.get("consistency_issues", []),
            clause_library_suggestions=response.get("clause_library_suggestions", []),
            word_count=word_count,
            estimated_review_time_minutes=estimated_review_time,
            attorney_review_required=True,
            legal_disclaimer=self.LEGAL_DISCLAIMER,
        )
    
    def draft_sync(self, input_data: DocumentDrafterInput) -> DraftResult:
        """
        Synchronous version of document drafting.
        
        Args:
            input_data: Drafting input
            
        Returns:
            DraftResult with document
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.draft(input_data))
    
    def get_template_info(self, document_type: str) -> Dict[str, Any]:
        """
        Get information about a document template.
        
        Args:
            document_type: Type of document
            
        Returns:
            Template information
        """
        doc_type_upper = document_type.upper()
        
        if doc_type_upper in self.SUPPORTED_DOCUMENTS:
            return {
                "type": doc_type_upper,
                "description": self.SUPPORTED_DOCUMENTS[doc_type_upper],
                "supported": True,
            }
        
        return {
            "type": document_type,
            "description": "Custom document type",
            "supported": False,
            "note": "Will use generic template structure",
        }
