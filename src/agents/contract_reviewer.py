"""
Contract Reviewer Agent - Precision contract analysis for risk detection.
"""

import logging
import uuid
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.models import (
    ContractReviewerInput,
    ContractReviewResult,
    RiskFlag,
    RiskLevel,
)
from src.pdf_parser import parse_text_content
from src.config import get_settings

logger = logging.getLogger(__name__)


class ContractReviewerAgent:
    """
    AI agent for contract review and risk analysis.
    Identifies risk clauses, missing protections, and unfavorable terms.
    """

    LEGAL_DISCLAIMER = (
        "This contract review is AI-assisted analysis only. It does not constitute "
        "legal advice. All findings must be reviewed and validated by a licensed "
        "attorney before any action is taken."
    )

    def __init__(self, model: Optional[str] = None):
        """
        Initialize Contract Reviewer agent.

        Args:
            model: Model to use. Defaults to the configured contract reviewer model.
        """

        settings = get_settings()

        self.model_name = model or settings.contract_reviewer_model

        # ---------------------------------------------------------
        # LLM PROVIDER SELECTION
        # ---------------------------------------------------------
        #
        # Groq models currently use provider-specific model IDs such
        # as "openai/gpt-oss-120b". The "openai/" prefix here refers
        # to the model family, NOT the API provider.
        #
        # Therefore, these models must go through ChatGroq.
        # ---------------------------------------------------------

        if (
            self.model_name.startswith("openai/")
            or self.model_name.startswith("qwen/")
            or self.model_name.startswith("allam-")
            or self.model_name.startswith("meta-llama/")
        ):
            logger.info(
                f"Using Groq provider with model: {self.model_name}"
            )

            self.llm = ChatGroq(
                model=self.model_name,
                api_key=settings.groq_api_key,
                temperature=0.1,
                max_tokens=8192,
            )

        elif "claude" in self.model_name.lower():
            logger.info(
                f"Using Anthropic provider with model: {self.model_name}"
            )

            self.llm = ChatAnthropic(
                model=self.model_name,
                api_key=settings.anthropic_api_key,
                temperature=0.1,
                max_tokens=8192,
            )

        else:
            logger.info(
                f"Using OpenAI provider with model: {self.model_name}"
            )

            self.llm = ChatOpenAI(
                model=self.model_name,
                api_key=settings.openai_api_key,
                temperature=0.1,
                max_tokens=8192,
            )

        self.prompt = self._build_prompt()

    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the contract review prompt."""

        system_prompt = """
You are ContractReviewer — a precision contract analysis engine.

Review the contract and identify risk clauses, missing protections, and unfavorable terms.

CRITICAL:
You identify and flag — you do NOT advise.
You never tell a client what to do.
You surface issues for the reviewing attorney.

Analyze the contract on these dimensions:

RISK LEVELS:
- HIGH: Requires immediate attorney review before signing
- MEDIUM: Requires attorney clarification or negotiation
- LOW: Standard clause, acceptable with modifications
- NEUTRAL: Informational only

RISK CATEGORIES TO ANALYZE:
1. PAYMENT & FINANCIAL
   - Look for unlimited obligations
   - Auto-renewal traps
   - Hidden fees
   - Unilateral payment withholding

2. INTELLECTUAL PROPERTY
   - Watch for overbroad IP assignment
   - Vague ownership
   - Assignment without additional compensation

3. LIABILITY & INDEMNIFICATION
   - Flag unlimited liability
   - One-sided indemnity
   - Broad damage exposure

4. CONFIDENTIALITY
   - Identify overly broad definitions
   - Missing carve-outs
   - Missing duration limitations

5. TERMINATION
   - Note one-sided termination
   - Insufficient notice periods
   - Asymmetric termination rights

6. GOVERNING LAW & DISPUTE
   - Flag unfavorable jurisdictions
   - Mandatory arbitration
   - Missing dispute resolution mechanism

7. NON-COMPETE
   - Identify overbroad scope
   - Excessive duration
   - Restrictions on future business activity

MISSING CLAUSE DETECTION:

Check for:
- Force Majeure
- Liability Cap
- Mutual Indemnification
- Dispute Resolution
- Governing Law
- Assignment Restrictions
- Amendment Procedure
- Merger Clause
- Severability

OUTPUT REQUIREMENTS:

Return ONLY a valid JSON object.

Use this exact structure:

{{
  "review_id": "unique-id",
  "document_name": "document name",
  "document_type": "NDA|SaaS Agreement|Employment|Service|Other",
  "parties": {{
    "party_a": "name",
    "party_b": "name"
  }},
  "effective_date": "date or null",
  "governing_law": "jurisdiction or null",
  "contract_value": "value or null",
  "overall_risk_level": "HIGH|MEDIUM|LOW",
  "risk_score": 0,
  "executive_summary": "2-3 sentence summary",
  "risk_flags": [
    {{
      "flag_id": "id",
      "section": "section name",
      "clause_number": "number or null",
      "risk_level": "HIGH|MEDIUM|LOW",
      "risk_category": "category",
      "issue_description": "description",
      "original_text": "exact text",
      "suggested_revision": "revision or null",
      "attorney_action": "required action"
    }}
  ],
  "missing_clauses": [
    "list of missing clauses"
  ],
  "defined_terms_issues": [
    "list of issues"
  ],
  "total_high_risks": 0,
  "total_medium_risks": 0,
  "total_low_risks": 0,
  "recommended_negotiation_points": [
    "points"
  ],
  "attorney_review_required": true,
  "legal_disclaimer": "{disclaimer}"
}}

IMPORTANT:
- Return valid JSON only.
- Do not wrap JSON in markdown.
- Do not include ```json.
- Keep risk_level values exactly HIGH, MEDIUM, or LOW.
- Use null when information is unavailable.
- Use the exact contract wording in original_text where possible.

Contract to review:

{contract_text}

Jurisdiction: {jurisdiction}

Client: {client_name}

Legal disclaimer:
{disclaimer}
"""

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
            ]
        )

    async def review(
        self,
        input_data: ContractReviewerInput,
    ) -> ContractReviewResult:
        """
        Review a contract and return risk analysis.

        Args:
            input_data: Contract review input.

        Returns:
            ContractReviewResult with analysis.
        """

        try:
            logger.info(
                f"Starting contract review: {input_data.document_name}"
            )

            # Parse the document
            parse_text_content(
                input_data.document_text,
                input_data.document_name,
            )

            # Build the chain
            chain = self.prompt | self.llm | JsonOutputParser()

            # Execute review
            response = await chain.ainvoke(
                {
                    "contract_text": input_data.document_text[:50000],
                    "jurisdiction": input_data.matter_info.jurisdiction,
                    "client_name": input_data.matter_info.client_name,
                    "disclaimer": self.LEGAL_DISCLAIMER,
                }
            )

            # Parse and validate response
            result = self._parse_result(
                response,
                input_data,
            )

            logger.info(
                f"Contract review complete: "
                f"{result.total_high_risks} high, "
                f"{result.total_medium_risks} medium, "
                f"{result.total_low_risks} low risks"
            )

            return result

        except Exception as e:
            logger.error(
                f"Contract review failed: {e}"
            )
            raise

    def _parse_result(
        self,
        response: dict,
        input_data: ContractReviewerInput,
    ) -> ContractReviewResult:
        """Parse and validate the LLM response."""

        # Count risks
        risk_flags = []

        for flag in response.get("risk_flags", []):
            risk_flags.append(
                RiskFlag(
                    flag_id=flag.get(
                        "flag_id",
                        str(uuid.uuid4())[:8],
                    ),
                    section=flag.get(
                        "section",
                        "Unknown",
                    ),
                    clause_number=flag.get(
                        "clause_number"
                    ),
                    risk_level=RiskLevel(
                        flag.get(
                            "risk_level",
                            "MEDIUM",
                        )
                    ),
                    risk_category=flag.get(
                        "risk_category",
                        "General",
                    ),
                    issue_description=flag.get(
                        "issue_description",
                        "",
                    ),
                    original_text=flag.get(
                        "original_text",
                        "",
                    ),
                    suggested_revision=flag.get(
                        "suggested_revision"
                    ),
                    attorney_action=flag.get(
                        "attorney_action",
                        "",
                    ),
                )
            )

        # Auto-count risks if the model doesn't provide counts
        total_high = response.get(
            "total_high_risks",
            0,
        ) or len(
            [
                f
                for f in risk_flags
                if f.risk_level == RiskLevel.HIGH
            ]
        )

        total_medium = response.get(
            "total_medium_risks",
            0,
        ) or len(
            [
                f
                for f in risk_flags
                if f.risk_level == RiskLevel.MEDIUM
            ]
        )

        total_low = response.get(
            "total_low_risks",
            0,
        ) or len(
            [
                f
                for f in risk_flags
                if f.risk_level == RiskLevel.LOW
            ]
        )

        # Determine overall risk level
        if total_high > 0:
            overall_risk = RiskLevel.HIGH
        elif total_medium > 2:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        # Calculate risk score
        risk_score = min(
            100,
            (total_high * 20)
            + (total_medium * 10)
            + (total_low * 3),
        )

        return ContractReviewResult(
            review_id=response.get(
                "review_id",
                str(uuid.uuid4())[:8],
            ),
            document_name=input_data.document_name,
            document_type=response.get(
                "document_type",
                "Other",
            ),
            parties=response.get(
                "parties",
                {},
            ),
            effective_date=response.get(
                "effective_date"
            ),
            governing_law=response.get(
                "governing_law"
            ),
            contract_value=response.get(
                "contract_value"
            ),
            overall_risk_level=overall_risk,
            risk_score=risk_score,
            executive_summary=response.get(
                "executive_summary",
                "",
            ),
            risk_flags=risk_flags,
            missing_clauses=response.get(
                "missing_clauses",
                [],
            ),
            defined_terms_issues=response.get(
                "defined_terms_issues",
                [],
            ),
            total_high_risks=total_high,
            total_medium_risks=total_medium,
            total_low_risks=total_low,
            recommended_negotiation_points=response.get(
                "recommended_negotiation_points",
                [],
            ),
            attorney_review_required=True,
            legal_disclaimer=self.LEGAL_DISCLAIMER,
        )

    def review_sync(
        self,
        input_data: ContractReviewerInput,
    ) -> ContractReviewResult:
        """
        Synchronous version of contract review.

        Args:
            input_data: Contract review input.

        Returns:
            ContractReviewResult with analysis.
        """

        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.review(input_data)
        )