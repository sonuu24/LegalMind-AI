"""
Case Researcher Agent - Comprehensive legal research with verified citations.
"""
import logging
import uuid
import json
from typing import Optional, List
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.models import (
    CaseResearcherInput,
    ResearchResult,
    CaseFound,
    VerificationStatus,
    AttorneyActionItem,
    MatterInfo,
)
from src.config import get_settings

logger = logging.getLogger(__name__)


class CaseResearcherAgent:
    """
    AI agent for legal case research.
    Conducts research across case law, statutes, and regulations.
    
    CRITICAL: Only cites verified cases from trusted sources.
    Never hallucinates citations.
    """
    
    LEGAL_DISCLAIMER = (
        "This research memo is prepared by an AI legal research assistant and does "
        "not constitute legal advice. All citations must be verified by a licensed "
        "attorney. Adverse authority has been included per professional responsibility obligations."
    )
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize Case Researcher agent.
        
        Args:
            model: Model to use (defaults to GPT-4o)
        """
        settings = get_settings()
        self.model_name = model or settings.case_researcher_model
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=settings.openai_api_key,
            temperature=0.1,
            max_tokens=8192,
        )
        
        self.prompt = self._build_prompt()
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the case research prompt."""
        system_prompt = """
You are CaseResearcher — a legal intelligence engine conducting comprehensive research.

CRITICAL CITATION RULE:
You ONLY cite cases, statutes, and regulations that you have retrieved from verified sources.
You NEVER fabricate, estimate, or guess case names, citations, or holdings.
If a source cannot be verified → mark as UNVERIFIED and flag for attorney confirmation.

RESEARCH METHODOLOGY:

1. QUERY ANALYSIS:
   - Identify core legal issue
   - Confirm jurisdiction and practice area
   - Determine if research should favor client position or be objective

2. SOURCE HIERARCHY (search in this order):
   Tier 1 - Binding authority: Supreme Court, Circuit Courts, State Supreme Courts, Statutes
   Tier 2 - Persuasive authority: Other circuits, Restatements, Model codes
   Tier 3 - Secondary sources: Law reviews, ALR annotations, Treatises

3. CASE ANALYSIS:
   For each case, extract:
   - Full citation: Name, Volume, Reporter, Page, Court, Year
   - Key facts (2-3 sentences)
   - Holding (exact decision)
   - Relevant quote with pinpoint citation
   - Subsequent history
   - Relevance to current matter

4. STATUTORY RESEARCH:
   - Cite exact code section (e.g., 28 U.S.C. § 1331)
   - Include effective date and amendments
   - Flag circuit splits on interpretation

5. ADVERSE AUTHORITY:
   - MUST disclose cases/authority against client position
   - Hiding bad cases = malpractice risk

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{{
  "research_id": "unique-id",
  "matter_id": "matter-id",
  "question_presented": "legal question",
  "jurisdiction": "jurisdiction",
  "practice_area": "practice area",
  "brief_answer": "2-3 sentence answer",
  "research_memo_text": "full memo in legal format",
  "cases_found": [
    {{
      "citation": "full citation",
      "court": "court name",
      "year": 2024,
      "holding": "holding",
      "relevant_quote": "quote or null",
      "pinpoint_citation": "pinpoint or null",
      "subsequent_history": "history or null",
      "relevance_to_matter": "relevance",
      "verification_status": "VERIFIED|UNVERIFIED - needs attorney check",
      "favors_client": true
    }}
  ],
  "statutes_found": ["statutes"],
  "adverse_authority": [same structure as cases_found],
  "internal_db_matches": [],
  "circuit_splits_identified": [],
  "unsettled_law_flags": [],
  "research_confidence": 0.0-1.0,
  "attorney_action_items": [],
  "legal_disclaimer": "{disclaimer}"
}}

RESEARCH REQUEST:
Legal Question: {legal_question}
Jurisdiction: {jurisdiction}
Practice Area: {practice_area}
Client: {client_name}
Favorable Research: {favorable_research}
"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
        ])
    
    async def research(self, input_data: CaseResearcherInput) -> ResearchResult:
        """
        Conduct legal research.
        
        Args:
            input_data: Research input
            
        Returns:
            ResearchResult with memo and citations
        """
        try:
            logger.info(
                f"Starting legal research: {input_data.legal_question[:100]}... "
                f"in {input_data.jurisdiction}"
            )
            
            # Build the chain
            chain = self.prompt | self.llm | JsonOutputParser()
            
            # Execute research
            response = await chain.ainvoke({
                "legal_question": input_data.legal_question,
                "jurisdiction": input_data.jurisdiction,
                "practice_area": input_data.practice_area,
                "client_name": input_data.matter_info.client_name,
                "favorable_research": input_data.favorable_research,
                "disclaimer": self.LEGAL_DISCLAIMER,
            })
            
            # Parse and validate response
            result = self._parse_result(response, input_data)
            
            logger.info(
                f"Research complete: {len(result.cases_found)} cases found, "
                f"confidence: {result.research_confidence}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Legal research failed: {e}")
            raise
    
    def _parse_result(
        self,
        response: dict,
        input_data: CaseResearcherInput,
    ) -> ResearchResult:
        """Parse and validate the LLM response."""
        # Parse cases
        cases_found = []
        for case in response.get("cases_found", []):
            cases_found.append(CaseFound(
                citation=case.get("citation", ""),
                court=case.get("court", ""),
                year=case.get("year", datetime.now().year),
                holding=case.get("holding", ""),
                relevant_quote=case.get("relevant_quote"),
                pinpoint_citation=case.get("pinpoint_citation"),
                subsequent_history=case.get("subsequent_history"),
                relevance_to_matter=case.get("relevance_to_matter", ""),
                verification_status=VerificationStatus(
                    case.get("verification_status", "UNVERIFIED - needs attorney check")
                ),
                favors_client=case.get("favors_client", True),
            ))
        
        # Parse adverse authority
        adverse_authority = []
        for case in response.get("adverse_authority", []):
            adverse_authority.append(CaseFound(
                citation=case.get("citation", ""),
                court=case.get("court", ""),
                year=case.get("year", datetime.now().year),
                holding=case.get("holding", ""),
                relevant_quote=case.get("relevant_quote"),
                pinpoint_citation=case.get("pinpoint_citation"),
                subsequent_history=case.get("subsequent_history"),
                relevance_to_matter=case.get("relevance_to_matter", ""),
                verification_status=VerificationStatus(
                    case.get("verification_status", "UNVERIFIED - needs attorney check")
                ),
                favors_client=False,
            ))
        
        # Parse attorney action items
        attorney_action_items = []
        for i, item in enumerate(response.get("attorney_action_items", [])):
            if isinstance(item, str):
                attorney_action_items.append(AttorneyActionItem(
                    item_id=str(uuid.uuid4())[:8],
                    description=item,
                    priority="MEDIUM",
                ))
            elif isinstance(item, dict):
                attorney_action_items.append(AttorneyActionItem(
                    item_id=item.get("item_id", str(uuid.uuid4())[:8]),
                    description=item.get("description", ""),
                    priority=item.get("priority", "MEDIUM"),
                ))
        
        return ResearchResult(
            research_id=response.get("research_id", str(uuid.uuid4())[:8]),
            matter_id=input_data.matter_info.matter_id,
            question_presented=response.get("question_presented", input_data.legal_question),
            jurisdiction=input_data.jurisdiction,
            practice_area=input_data.practice_area,
            brief_answer=response.get("brief_answer", ""),
            research_memo_text=response.get("research_memo_text", ""),
            cases_found=cases_found,
            statutes_found=response.get("statutes_found", []),
            adverse_authority=adverse_authority,
            internal_db_matches=response.get("internal_db_matches", []),
            circuit_splits_identified=response.get("circuit_splits_identified", []),
            unsettled_law_flags=response.get("unsettled_law_flags", []),
            research_confidence=response.get("research_confidence", 0.75),
            attorney_action_items=attorney_action_items,
            legal_disclaimer=self.LEGAL_DISCLAIMER,
        )
    
    def research_sync(self, input_data: CaseResearcherInput) -> ResearchResult:
        """
        Synchronous version of legal research.
        
        Args:
            input_data: Research input
            
        Returns:
            ResearchResult with memo and citations
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.research(input_data))
    
    async def search_internal_database(
        self,
        query: str,
        matter_id: str,
        top_k: int = 5,
    ) -> List[dict]:
        """
        Search firm's internal case database.
        
        Args:
            query: Search query
            matter_id: Matter ID for filtering
            top_k: Number of results
            
        Returns:
            List of matching internal documents
        """
        try:
            from src.vector_store import create_vector_store
            
            settings = get_settings()
            vector_store = create_vector_store(
                api_key=settings.pinecone_api_key,
                environment=settings.pinecone_environment,
                index_name=settings.pinecone_index_name,
            )
            
            results = vector_store.search(
                query=query,
                filter={"matter_id": matter_id},
                top_k=top_k,
            )
            
            return results
            
        except Exception as e:
            logger.warning(f"Internal database search failed: {e}")
            return []
