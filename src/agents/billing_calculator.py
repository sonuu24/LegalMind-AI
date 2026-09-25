"""
Billing Calculator Agent - Legal fee calculation and invoice generation.
"""
import logging
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.models import (
    BillingCalculatorInput,
    BillingResult,
    TimeEntry,
    ExpenseEntry,
    TrustAccount,
    MatterBudget,
)
from src.config import get_settings

logger = logging.getLogger(__name__)


class BillingCalculatorAgent:
    """
    AI agent for legal billing operations.
    Processes time entries, calculates fees, and generates invoices.
    
    Legal billing requires precision - every dollar must be properly attributed.
    """
    
    # Standard billing increments
    BILLING_INCREMENTS = {
        0.1: "6 minutes",
        0.25: "15 minutes",
        0.5: "30 minutes",
    }
    
    # Ethics compliance rules
    ETHICS_FLAGS = {
        "overbilling": "More than 24 hours billed in a single day",
        "duplicate": "Same task billed to multiple clients",
        "administrative": "Administrative tasks billed at attorney rates",
        "contingency": "Contingency fee matter - verify fee agreement",
        "fee_splitting": "Fee splitting with non-lawyers detected",
        "interest": "Interest/late fees - verify fee agreement authorizes",
    }
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize Billing Calculator agent.
        
        Args:
            model: Model to use (defaults to GPT-4o)
        """
        settings = get_settings()
        self.model_name = model or settings.billing_calculator_model
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=settings.openai_api_key,
            temperature=0.1,
            max_tokens=4096,
        )
        
        self.prompt = self._build_prompt()
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the billing calculation prompt."""
        system_prompt = """
You are BillingCalculator — a legal financial operations engine.
Process time entries, calculate fees, and generate professional invoices.

LEGAL BILLING RULES:

TIME ENTRY INCREMENTS:
- Standard increment: 0.1 hours (6 minutes)
- Some firms use 0.25 hours (15 minutes)
- Always round UP to nearest increment

TIME DESCRIPTION QUALITY:
REJECT vague descriptions like:
- "Worked on case"
- "Research"
- "Phone call"

ACCEPT specific descriptions like:
- "Reviewed plaintiff's motion for summary judgment; identified three grounds for opposition"
- "Telephone conference with client J. Smith re: settlement strategy"

BLOCK BILLING DETECTION:
Flag entries where multiple tasks are grouped:
- "Drafted motion, reviewed discovery, called client - 3.5 hrs"
Block billing may be disputed by clients and disallowed by courts.

ETHICS COMPLIANCE:
Flag for attorney review:
- > 24 hours billed in a single day (overbilling)
- Same task billed to multiple clients (duplicate)
- Administrative tasks at attorney rates (filing, copying)
- Contingency fee matters without agreement
- Fee splitting with non-lawyers (ethical violation)

INVOICE STRUCTURE:
1. Header: Firm info, client info, invoice number, dates
2. Time Detail: Date | Timekeeper | Description | Hours | Rate | Amount
3. Expenses: Date | Description | Amount
4. Summary: Prior balance, current fees, expenses, taxes, payments, total due
5. Trust Account: Retainer balance, applied, remaining

OUTPUT FORMAT:
Return a JSON object with this structure:
{{
  "billing_id": "unique-id",
  "matter_id": "matter-id",
  "client_name": "client name",
  "billing_period": {{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}},
  "invoice_number": "INV-0001",
  "time_entries_processed": 0,
  "time_entries_flagged": [],
  "block_billing_detected": [],
  "total_hours": 0.0,
  "total_fees": "$0.00",
  "total_expenses": "$0.00",
  "total_invoice_amount": "$0.00",
  "invoice_html": "HTML invoice or null",
  "invoice_pdf_path": null,
  "trust_account": {{
    "balance_before": 0.0,
    "applied_to_invoice": 0.0,
    "balance_after": 0.0,
    "replenishment_requested": false
  }},
  "ethics_flags": [],
  "matter_budget": {{
    "total_budget": 0.0,
    "total_billed_to_date": 0.0,
    "percent_consumed": 0.0,
    "projected_at_completion": 0.0,
    "over_budget_flag": false
  }},
  "ready_to_send": false,
  "requires_attorney_approval": true
}}

BILLING DATA:
Time Entries: {time_entries}
Expenses: {expenses}
Matter Info: {matter_info}
Billing Period: {billing_period}
"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
        ])
    
    async def calculate_billing(self, input_data: BillingCalculatorInput) -> BillingResult:
        """
        Calculate billing and generate invoice.
        
        Args:
            input_data: Billing input
            
        Returns:
            BillingResult with invoice
        """
        try:
            logger.info(
                f"Calculating billing for matter {input_data.matter_id}: "
                f"{input_data.billing_period_start} to {input_data.billing_period_end}"
            )
            
            # Get time entries and expenses (from database in production)
            time_entries = self._get_time_entries(input_data)
            expenses = self._get_expenses(input_data) if input_data.include_expenses else []
            
            # Get matter info
            matter_info = self._get_matter_info(input_data.matter_id)
            
            # Build the chain
            chain = self.prompt | self.llm | JsonOutputParser()
            
            # Execute billing calculation
            response = await chain.ainvoke({
                "time_entries": self._format_time_entries(time_entries),
                "expenses": self._format_expenses(expenses),
                "matter_info": json.dumps(matter_info, indent=2),
                "billing_period": f"{input_data.billing_period_start} to {input_data.billing_period_end}",
            })
            
            # Parse and validate response
            result = self._parse_result(response, input_data, time_entries, expenses)
            
            logger.info(
                f"Billing complete: {result.total_hours} hours, "
                f"{result.total_fees} fees, {result.total_invoice_amount} total"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Billing calculation failed: {e}")
            raise
    
    def _get_time_entries(self, input_data: BillingCalculatorInput) -> List[TimeEntry]:
        """
        Get time entries from database.
        In production, this queries PostgreSQL.
        """
        # TODO: Implement database query
        return [
            TimeEntry(
                entry_id=str(uuid.uuid4())[:8],
                date=date.today() - timedelta(days=5),
                timekeeper_id="ATT001",
                timekeeper_name="John Doe",
                matter_id=input_data.matter_id,
                hours=2.5,
                description="Reviewed and analyzed plaintiff's motion for summary judgment; "
                           "prepared outline for response; researched applicable case law",
                billing_code="LIT-001",
                billable=True,
                rate=450.0,
            ),
            TimeEntry(
                entry_id=str(uuid.uuid4())[:8],
                date=date.today() - timedelta(days=3),
                timekeeper_id="ATT002",
                timekeeper_name="Jane Smith",
                matter_id=input_data.matter_id,
                hours=1.5,
                description="Telephone conference with client re: settlement parameters; "
                           "discussed negotiation strategy and authority",
                billing_code="LIT-002",
                billable=True,
                rate=350.0,
            ),
        ]
    
    def _get_expenses(self, input_data: BillingCalculatorInput) -> List[ExpenseEntry]:
        """
        Get expenses from database.
        In production, this queries PostgreSQL.
        """
        # TODO: Implement database query
        return [
            ExpenseEntry(
                expense_id=str(uuid.uuid4())[:8],
                date=date.today() - timedelta(days=10),
                description="Court filing fees",
                amount=400.0,
                matter_id=input_data.matter_id,
            ),
            ExpenseEntry(
                expense_id=str(uuid.uuid4())[:8],
                date=date.today() - timedelta(days=7),
                description="Process server - service of process",
                amount=75.0,
                matter_id=input_data.matter_id,
            ),
        ]
    
    def _get_matter_info(self, matter_id: str) -> Dict[str, Any]:
        """
        Get matter information from database.
        In production, this queries PostgreSQL.
        """
        # TODO: Implement database query
        return {
            "matter_id": matter_id,
            "client_name": "Sample Client",
            "matter_type": "Litigation",
            "responsible_attorney": "John Doe",
            "billing_type": "hourly",
            "attorney_rates": {
                "partner": 450.0,
                "associate": 350.0,
                "paralegal": 200.0,
            },
            "retainer_balance": 5000.0,
            "budget": 50000.0,
            "billed_to_date": 15000.0,
        }
    
    def _format_time_entries(self, entries: List[TimeEntry]) -> str:
        """Format time entries for the prompt."""
        return json.dumps([e.model_dump() for e in entries], indent=2, default=str)
    
    def _format_expenses(self, entries: List[ExpenseEntry]) -> str:
        """Format expenses for the prompt."""
        return json.dumps([e.model_dump() for e in entries], indent=2, default=str)
    
    def _parse_result(
        self,
        response: dict,
        input_data: BillingCalculatorInput,
        time_entries: List[TimeEntry],
        expenses: List[ExpenseEntry],
    ) -> BillingResult:
        """Parse and validate the LLM response."""
        # Parse trust account
        trust_data = response.get("trust_account", {})
        trust_account = None
        if trust_data:
            trust_account = TrustAccount(
                balance_before=float(trust_data.get("balance_before", 0)),
                applied_to_invoice=float(trust_data.get("applied_to_invoice", 0)),
                balance_after=float(trust_data.get("balance_after", 0)),
                replenishment_requested=trust_data.get("replenishment_requested", False),
            )
        
        # Parse matter budget
        budget_data = response.get("matter_budget", {})
        matter_budget = None
        if budget_data:
            matter_budget = MatterBudget(
                total_budget=budget_data.get("total_budget"),
                total_billed_to_date=float(budget_data.get("total_billed_to_date", 0)),
                percent_consumed=float(budget_data.get("percent_consumed", 0)),
                projected_at_completion=budget_data.get("projected_at_completion"),
                over_budget_flag=budget_data.get("over_budget_flag", False),
            )
        
        return BillingResult(
            billing_id=response.get("billing_id", str(uuid.uuid4())[:8]),
            matter_id=input_data.matter_id,
            client_name=response.get("client_name", input_data.client_name),
            billing_period={
                "from": input_data.billing_period_start,
                "to": input_data.billing_period_end,
            },
            invoice_number=response.get("invoice_number", f"INV-{uuid.uuid4().hex[:8].upper()}"),
            time_entries_processed=len(time_entries),
            time_entries_flagged=response.get("time_entries_flagged", []),
            block_billing_detected=response.get("block_billing_detected", []),
            total_hours=float(response.get("total_hours", 0)),
            total_fees=response.get("total_fees", "$0.00"),
            total_expenses=response.get("total_expenses", "$0.00"),
            total_invoice_amount=response.get("total_invoice_amount", "$0.00"),
            invoice_html=response.get("invoice_html"),
            invoice_pdf_path=response.get("invoice_pdf_path"),
            trust_account=trust_account,
            ethics_flags=response.get("ethics_flags", []),
            matter_budget=matter_budget,
            ready_to_send=response.get("ready_to_send", False),
            requires_attorney_approval=True,
        )
    
    def _generate_invoice_html(
        self,
        result: BillingResult,
        time_entries: List[TimeEntry],
        expenses: List[ExpenseEntry],
    ) -> str:
        """
        Generate HTML invoice.
        
        Args:
            result: Billing result
            time_entries: Time entries
            expenses: Expenses
            
        Returns:
            HTML invoice string
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Invoice {result.invoice_number}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ margin-bottom: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .total {{ font-weight: bold; font-size: 1.2em; }}
        .footer {{ margin-top: 40px; font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>INVOICE</h1>
        <p><strong>Invoice Number:</strong> {result.invoice_number}</p>
        <p><strong>Matter:</strong> {result.matter_id}</p>
        <p><strong>Client:</strong> {result.client_name}</p>
        <p><strong>Billing Period:</strong> {result.billing_period['from']} to {result.billing_period['to']}</p>
    </div>
    
    <h2>Time Entries</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>Timekeeper</th>
            <th>Description</th>
            <th>Hours</th>
            <th>Rate</th>
            <th>Amount</th>
        </tr>
"""
        
        for entry in time_entries:
            amount = entry.hours * (entry.rate or 0)
            html += f"""
        <tr>
            <td>{entry.date}</td>
            <td>{entry.timekeeper_name}</td>
            <td>{entry.description}</td>
            <td>{entry.hours}</td>
            <td>${entry.rate or 0:.2f}</td>
            <td>${amount:.2f}</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>Expenses</h2>
    <table>
        <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Amount</th>
        </tr>
"""
        
        for expense in expenses:
            html += f"""
        <tr>
            <td>{expense.date}</td>
            <td>{expense.description}</td>
            <td>${expense.amount:.2f}</td>
        </tr>
"""
        
        html += f"""
    </table>
    
    <div class="total">
        <p><strong>Total Fees:</strong> {result.total_fees}</p>
        <p><strong>Total Expenses:</strong> {result.total_expenses}</p>
        <p><strong>Total Amount Due:</strong> {result.total_invoice_amount}</p>
    </div>
    
    <div class="footer">
        <p>Payment terms: Net 30 days</p>
        <p>Please make checks payable to: [Firm Name]</p>
        <p>This invoice is subject to attorney review before sending.</p>
    </div>
</body>
</html>
"""
        
        return html
    
    def calculate_billing_sync(
        self,
        input_data: BillingCalculatorInput,
    ) -> BillingResult:
        """
        Synchronous version of billing calculation.
        
        Args:
            input_data: Billing input
            
        Returns:
            BillingResult with invoice
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.calculate_billing(input_data))
    
    def round_to_increment(self, hours: float, increment: float = 0.1) -> float:
        """
        Round time to billing increment.
        
        Args:
            hours: Time in hours
            increment: Billing increment (default 0.1 = 6 minutes)
            
        Returns:
            Rounded hours
        """
        import math
        return math.ceil(hours / increment) * increment
    
    def validate_time_description(self, description: str) -> Dict[str, Any]:
        """
        Validate time entry description quality.
        
        Args:
            description: Time entry description
            
        Returns:
            Validation result
        """
        vague_patterns = [
            r"^\s*worked\s+",
            r"^\s*research\s*$",
            r"^\s*phone\s+call\s*$",
            r"^\s*review\s+documents\s*$",
            r"^\s*emails?\s*$",
        ]
        
        import re
        
        is_vague = False
        for pattern in vague_patterns:
            if re.match(pattern, description.lower()):
                is_vague = True
                break
        
        # Check for block billing (multiple activities)
        activities = description.count(";") + description.count(",")
        is_block_billing = activities >= 2 and len(description) > 100
        
        return {
            "is_vague": is_vague,
            "is_block_billing": is_block_billing,
            "quality_score": 0.3 if is_vague else (0.7 if is_block_billing else 0.9),
            "suggestions": [
                "Be more specific about the task performed",
                "Include the purpose or outcome of the work",
                "Identify the specific documents or parties involved",
            ] if is_vague else [],
        }
