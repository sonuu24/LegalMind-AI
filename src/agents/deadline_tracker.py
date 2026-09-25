"""
Deadline Tracker Agent - Critical deadline management for legal matters.
"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.models import (
    DeadlineTrackerInput,
    DeadlineReport,
    DeadlineInfo,
    MatterDeadlines,
    UrgencyLevel,
    AlertStatus,
)
from src.config import get_settings

logger = logging.getLogger(__name__)


class DeadlineTrackerAgent:
    """
    AI agent for legal deadline tracking and management.
    Monitors court dates, filing deadlines, and statute of limitations.
    
    ZERO TOLERANCE: A missed legal deadline can result in malpractice liability.
    """
    
    # Common statute of limitations periods (in years) - varies by jurisdiction
    SOL_PERIODS = {
        "contract": {"default": 4, "oral": 2, "written": 6},
        "personal_injury": {"default": 2, "medical_malpractice": 3},
        "employment_discrimination": {"eeoc": 0.5, "state": 2},
        "federal_civil_rights": {"default": 2},
        "ip_infringement": {"copyright": 3, "patent": 6, "trademark": 4},
        "property_damage": {"default": 3},
        "fraud": {"default": 4, "discovery_rule": True},
    }
    
    # Court rule calculations
    COURT_RULES = {
        "federal": {
            "name": "Federal Rules of Civil Procedure",
            "computation": "calendar_days",
            "exclude_trigger_day": True,
            "include_last_day": True,
            "weekend_holiday_extension": True,
        },
        "texas": {
            "name": "Texas Rules of Civil Procedure",
            "computation": "calendar_days",
            "exclude_trigger_day": True,
            "include_last_day": True,
            "weekend_holiday_extension": True,
        },
        "california": {
            "name": "California Code of Civil Procedure",
            "computation": "calendar_days",
            "exclude_trigger_day": True,
            "include_last_day": False,
            "weekend_holiday_extension": True,
        },
        "new_york": {
            "name": "New York CPLR",
            "computation": "calendar_days",
            "exclude_trigger_day": True,
            "include_last_day": True,
            "weekend_holiday_extension": True,
        },
    }
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize Deadline Tracker agent.
        
        Args:
            model: Model to use (defaults to GPT-4o)
        """
        settings = get_settings()
        self.model_name = model or settings.deadline_tracker_model
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=settings.openai_api_key,
            temperature=0.1,
            max_tokens=4096,
        )
        
        self.prompt = self._build_prompt()
    
    def _build_prompt(self) -> ChatPromptTemplate:
        """Build the deadline tracking prompt."""
        system_prompt = """
You are DeadlineTracker — a critical deadline management engine for legal matters.

ZERO TOLERANCE POLICY:
A missed legal deadline can result in malpractice liability, case dismissal,
contempt of court, or bar discipline. Operate with military precision.

DEADLINE CATEGORIES:

🔴 CRITICAL (Hard deadlines - cannot be extended):
- Statute of Limitations expiration
- Court-ordered filing deadlines
- Response to complaint (Answer due dates)
- Appeal deadlines
- Discovery cutoff dates
- Trial dates, Hearing dates

🟡 IMPORTANT (Extendable with court permission):
- Motion briefing schedules
- Expert witness disclosure deadlines
- Deposition scheduling windows
- Settlement conference preparation

🟢 ADMINISTRATIVE (Internal firm deadlines):
- Client update communications
- Bill generation deadlines
- Conflict check completion

BUFFER ALERT SYSTEM:
- 90 days before: First advisory alert
- 30 days before: Warning alert
- 14 days before: Urgent alert + calendar block
- 7 days before: Critical alert + partner notification
- 3 days before: Emergency alert + confirmation required
- 1 day before: Final warning
- OVERDUE: Immediate escalation

URGENCY DETERMINATION:
- CRITICAL: Due within 7 days OR statute of limitations within 30 days
- IMPORTANT: Due within 30 days
- ADMINISTRATIVE: Due after 30 days

OUTPUT FORMAT:
Return a JSON object with this structure:
{{
  "docket_report_date": "YYYY-MM-DD",
  "firm_id": "firm-id",
  "deadlines_today": [],
  "deadlines_this_week": [],
  "deadlines_next_30_days": [],
  "sol_expiring_90_days": [],
  "overdue_deadlines": [],
  "alerts_sent": [],
  "matters": [
    {{
      "matter_id": "id",
      "client_name": "name",
      "matter_type": "type",
      "responsible_attorney": "attorney",
      "deadlines": [
        {{
          "deadline_id": "id",
          "description": "description",
          "due_date": "YYYY-MM-DD",
          "days_remaining": 0,
          "urgency": "CRITICAL|IMPORTANT|ADMINISTRATIVE",
          "category": "category",
          "court_rule_reference": "rule or null",
          "calculation_method": "method",
          "alert_status": "NOT_SENT|SENT|ACKNOWLEDGED|OVERDUE",
          "requires_attorney_confirmation": true
        }}
      ]
    }}
  ],
  "system_health": {{
    "total_active_matters": 0,
    "total_tracked_deadlines": 0,
    "deadlines_acknowledged_today": 0,
    "deadlines_pending_acknowledgment": 0
  }}
}}

MATTERS DATA:
{matters_data}

Generate the daily docket report for firm_id: {firm_id}
"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
        ])
    
    async def get_deadlines(self, input_data: DeadlineTrackerInput) -> DeadlineReport:
        """
        Get deadline report for firm/matters.
        
        Args:
            input_data: Deadline tracking input
            
        Returns:
            DeadlineReport with all deadlines
        """
        try:
            logger.info(f"Generating deadline report for firm: {input_data.firm_id}")
            
            # Get matters data (in production, this would come from database)
            matters_data = self._get_matters_data(input_data)
            
            # Build the chain
            chain = self.prompt | self.llm | JsonOutputParser()
            
            # Execute deadline calculation
            response = await chain.ainvoke({
                "firm_id": input_data.firm_id,
                "matters_data": self._format_matters_data(matters_data),
            })
            
            # Parse and validate response
            result = self._parse_result(response, input_data)
            
            # Generate alerts for critical deadlines
            await self._generate_alerts(result)
            
            logger.info(
                f"Deadline report complete: {len(result.deadlines_today)} today, "
                f"{len(result.overdue_deadlines)} overdue"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Deadline tracking failed: {e}")
            raise
    
    def _get_matters_data(self, input_data: DeadlineTrackerInput) -> List[Dict[str, Any]]:
        """
        Get matters data from database.
        In production, this queries the PostgreSQL database.
        
        For now, returns sample data structure.
        """
        # TODO: Implement database query
        return [
            {
                "matter_id": "SAMPLE-001",
                "client_name": "Sample Client",
                "matter_type": "Litigation",
                "responsible_attorney": "John Doe",
                "jurisdiction": "Texas",
                "open_date": date.today() - timedelta(days=90),
                "deadlines": [
                    {
                        "description": "Answer to Complaint due",
                        "due_date": date.today() + timedelta(days=5),
                        "category": "CRITICAL",
                        "court_rule": "FRCP 12(a)",
                    }
                ]
            }
        ]
    
    def _format_matters_data(self, matters_data: List[Dict[str, Any]]) -> str:
        """Format matters data for the prompt."""
        import json
        return json.dumps(matters_data, indent=2, default=str)
    
    def _parse_result(
        self,
        response: dict,
        input_data: DeadlineTrackerInput,
    ) -> DeadlineReport:
        """Parse and validate the LLM response."""
        today = date.today()
        
        # Parse deadlines
        def parse_deadlines(deadline_list: List[Dict]) -> List[DeadlineInfo]:
            deadlines = []
            for d in deadline_list:
                try:
                    due_date = datetime.strptime(d.get("due_date", ""), "%Y-%m-%d").date()
                except:
                    due_date = today
                
                days_remaining = (due_date - today).days
                
                deadlines.append(DeadlineInfo(
                    deadline_id=d.get("deadline_id", str(uuid.uuid4())[:8]),
                    description=d.get("description", ""),
                    due_date=due_date,
                    days_remaining=days_remaining,
                    urgency=UrgencyLevel(d.get("urgency", "IMPORTANT")),
                    category=d.get("category", ""),
                    court_rule_reference=d.get("court_rule_reference"),
                    calculation_method=d.get("calculation_method", ""),
                    alert_status=AlertStatus(d.get("alert_status", "NOT_SENT")),
                    requires_attorney_confirmation=d.get("requires_attorney_confirmation", True),
                ))
            return deadlines
        
        # Parse matters
        matters = []
        for m in response.get("matters", []):
            matter_deadlines = MatterDeadlines(
                matter_id=m.get("matter_id", ""),
                client_name=m.get("client_name", ""),
                matter_type=m.get("matter_type", ""),
                responsible_attorney=m.get("responsible_attorney", ""),
                deadlines=parse_deadlines(m.get("deadlines", [])),
            )
            matters.append(matter_deadlines)
        
        return DeadlineReport(
            docket_report_date=today,
            firm_id=input_data.firm_id,
            deadlines_today=parse_deadlines(response.get("deadlines_today", [])),
            deadlines_this_week=parse_deadlines(response.get("deadlines_this_week", [])),
            deadlines_next_30_days=parse_deadlines(response.get("deadlines_next_30_days", [])),
            sol_expiring_90_days=parse_deadlines(response.get("sol_expiring_90_days", [])),
            overdue_deadlines=parse_deadlines(response.get("overdue_deadlines", [])),
            alerts_sent=response.get("alerts_sent", []),
            matters=matters,
            system_health=response.get("system_health", {}),
        )
    
    async def _generate_alerts(self, report: DeadlineReport):
        """
        Generate and send alerts for critical deadlines.
        
        In production, this sends emails, SMS (Twilio), and Slack notifications.
        """
        alerts_to_send = []
        
        # Collect critical and overdue deadlines
        for deadline in report.overdue_deadlines:
            alerts_to_send.append({
                "deadline_id": deadline.deadline_id,
                "type": "OVERDUE",
                "description": deadline.description,
                "due_date": str(deadline.due_date),
                "urgency": "CRITICAL",
            })
        
        for deadline in report.deadlines_today:
            if deadline.urgency == UrgencyLevel.CRITICAL:
                alerts_to_send.append({
                    "deadline_id": deadline.deadline_id,
                    "type": "DUE_TODAY",
                    "description": deadline.description,
                    "urgency": "CRITICAL",
                })
        
        # TODO: Implement actual alert sending (email, SMS, Slack)
        if alerts_to_send:
            logger.warning(f"Generated {len(alerts_to_send)} critical alerts")
            report.alerts_sent = alerts_to_send
    
    def calculate_deadline(
        self,
        trigger_date: date,
        days: int,
        jurisdiction: str = "federal",
        business_days: bool = False,
    ) -> date:
        """
        Calculate a deadline based on court rules.
        
        Args:
            trigger_date: Date that triggers the deadline
            days: Number of days for deadline
            jurisdiction: Court jurisdiction (federal, texas, california, new_york)
            business_days: Whether to count business days only
            
        Returns:
            Calculated deadline date
        """
        rules = self.COURT_RULES.get(jurisdiction.lower(), self.COURT_RULES["federal"])
        
        # Start calculation
        if rules["exclude_trigger_day"]:
            calculated_date = trigger_date + timedelta(days=1)
        else:
            calculated_date = trigger_date
        
        # Add the specified days
        if business_days:
            days_added = 0
            current = calculated_date
            while days_added < days:
                current += timedelta(days=1)
                if current.weekday() < 5:  # Monday = 0, Friday = 4
                    days_added += 1
            calculated_date = current
        else:
            calculated_date = trigger_date + timedelta(days=days)
        
        # Apply weekend/holiday extension
        if rules.get("weekend_holiday_extension"):
            while calculated_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                calculated_date += timedelta(days=1)
        
        return calculated_date
    
    def get_sol_period(
        self,
        claim_type: str,
        jurisdiction: str,
        sub_type: Optional[str] = None,
    ) -> int:
        """
        Get statute of limitations period in years.
        
        Args:
            claim_type: Type of claim (contract, personal_injury, etc.)
            jurisdiction: State or federal jurisdiction
            sub_type: Sub-type of claim (optional)
            
        Returns:
            SOL period in years
        """
        claim_key = claim_type.lower().replace(" ", "_")
        
        if claim_key not in self.SOL_PERIODS:
            logger.warning(f"Unknown claim type: {claim_type}")
            return 2  # Default
        
        periods = self.SOL_PERIODS[claim_key]
        
        if sub_type and sub_type in periods:
            return periods[sub_type]
        
        return periods.get("default", 2)
    
    def get_deadlines_sync(self, input_data: DeadlineTrackerInput) -> DeadlineReport:
        """
        Synchronous version of deadline tracking.
        
        Args:
            input_data: Deadline tracking input
            
        Returns:
            DeadlineReport with all deadlines
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.get_deadlines(input_data))
