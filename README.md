<div align="center">

# ⚖LexMind Legal




**AI-Powered Legal Intelligence for Modern Law Firms**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.0+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0.0+-orange.svg)](https://modelcontextprotocol.io)

> Automate 80% of legal grunt work. Focus on winning cases.

[Quick Start](#-quick-start) • [Features](#-features) • [API Docs](#-api-reference) • [Examples](#-examples)

</div>

---

## 🚀 The Problem

Lawyers spend **4–6 hours reviewing a single contract** and **8+ hours on legal research** that AI can do in minutes. LexPilot changes that.

| Task | Without LexPilot | With LexPilot |
|------|------------------|---------------|
| Contract Review | 4–6 hours | **15 minutes** |
| Legal Research | 8–12 hours | **30 minutes** |
| Document Drafting | 2–3 hours | **2 minutes** |
| Invoice Generation | 1–2 hours | **30 seconds** |

---

## ✨ What It Does

### 📄 Contract Intelligence
Upload any agreement. Get instant risk analysis with redline suggestions.
- 🔴 High-risk clause detection
- 🟡 Missing protections flagged
- 📝 Suggested revisions ready for negotiation
- ⚖️ Jurisdiction-aware enforceability checks

### ⚖️ Legal Research Engine
Ask complex questions. Get structured memos with verified citations.
- ✅ Binding authority only (no hallucinations)
- 📊 Circuit split analysis
- ⚠️ Adverse authority disclosure (ethics-compliant)
- 🎯 Confidence scores on every conclusion

### 📝 Document Drafting
Generate first drafts in seconds across 20+ document types.
- NDAs, MSAs, SOWs, Employment Agreements
- Jurisdiction-specific clauses
- Inline attorney notes for review points
- Consistency checks across defined terms

### 📅 Deadline Management
Never miss a critical date again.
- Statute of limitations tracking
- Court rule calculations (FRCP, state rules)
- Escalating alerts (90d → 30d → 14d → 7d → 3d → 1d)
- Daily docket reports at 7 AM

### 💰 Billing Automation
Turn time entries into professional invoices.
- Block billing detection (ethics compliance)
- Trust account tracking
- Budget burn rate monitoring
- PDF/HTML invoice generation

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────┐
│         Your App (Web / Mobile / CLI)          │
└────────────────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│              FastAPI + MCP Gateway             │
│         REST API • Model Context Protocol      │
└────────────────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│           LangGraph Orchestrator               │
│      Task Classification • Agent Routing       │
└────────────────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐   ┌─────────────┐   ┌───────────┐
│Contract │   │   Case      │   │ Document  │
│Reviewer │   │ Researcher  │   │ Drafter   │
│(Claude) │   │  (GPT-4o)   │   │ (Claude)  │
└─────────┘   └─────────────┘   └───────────┘
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐   ┌─────────────┐   ┌───────────┐
│Deadline │   │   Billing   │   │ Pinecone  │
│Tracker  │   │ Calculator  │   │ Vector DB │
│(GPT-4o) │   │  (GPT-4o)   │   │           │
└─────────┘   └─────────────┘   └───────────┘
```



### First API Call

```bash
# Review a contract
curl -X POST http://localhost:8000/api/v1/contract/review \
  -H "Content-Type: application/json" \
  -d '{
    "document_text": "YOUR_CONTRACT_TEXT",
    "document_name": "NDA.pdf",
    "matter_id": "MATTER-001",
    "client_name": "Acme Corp",
    "jurisdiction": "Delaware"
  }'
```

### CLI Usage

```bash
# Review a contract PDF
python main.py review-contract \
  --contract agreement.pdf \
  --matter-id M-001 \
  --client "Acme Corp" \
  --jurisdiction Delaware

# Draft an NDA
python main.py draft \
  --type NDA \
  --matter-id M-002 \
  --client "StartupXYZ" \
  --jurisdiction California

# Legal research
python main.py research \
  --question "What is the statute of limitations for breach of contract?" \
  --jurisdiction Texas \
  --practice-area Contract \
  --matter-id M-003 \
  --client "Test Client"
```

---

## 📖 Core Concepts

### Matters

Every action in LexPilot is tied to a **matter** (a legal case or transaction).

```python
matter_info = MatterInfo(
    matter_id="MATTER-001",
    client_name="Acme Corporation",
    matter_type="Contract Review",
    jurisdiction="Delaware",
    responsible_attorney="Jane Doe",
)
```

### Agents

Specialist AI agents handle specific tasks:

| Agent | Model | Purpose |
|-------|-------|---------|
| ContractReviewer | GROQ | Risk analysis, redlining |
| CaseResearcher | GPT-4o | Legal research, citations |
| DocumentDrafter | GROQ | Document generation |
| DeadlineTracker | GPT-4o | Deadline management |
| BillingCalculator | GPT-4o | Invoice generation |


---
# 📸 Application Preview

## 🚀 API Endpoint Demonstrations

## Contract Review 

> ![Contract Review](./app%20preview/contract%20review.png)

```
```
## Case Research 

> ![Case Research](./app%20preview/case%20research.png)


```

```
## Documents Drafting

> ![Documents Drafting](./app%20preview/documents%20drafting.png)

```

```


## 🔌 API Reference

### Contract Review

> ![Contract Review](./app%20preview/contract%20review.png)

```http
POST /api/v1/contract/review
Content-Type: application/json
```

**Request:**
```json
{
  "document_text": "string (required)",
  "document_name": "string (required)",
  "matter_id": "string (required)",
  "client_name": "string (required)",
  "jurisdiction": "string (required)",
  "firm_profile": "object (optional)"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "review_id": "REV-123",
    "document_name": "Employment Agreement",
    "overall_risk_level": "MEDIUM",
    "risk_score": 45,
    "risk_flags": [
      {
        "risk_level": "HIGH",
        "section": "Non-Compete",
        "issue_description": "Duration exceeds 2 years",
        "suggested_revision": "Reduce to 12 months"
      }
    ],
    "missing_clauses": ["Arbitration", "Severability"],
    "attorney_review_required": true
  }
}
```

### Case Research

```http
POST /api/v1/case/research
Content-Type: application/json

{
  "legal_question": "string",
  "jurisdiction": "string",
  "practice_area": "string",
  "matter_id": "string",
  "client_name": "string",
  "favorable_research": "boolean (optional)"
}
```

### Document Drafting

```http
POST /api/v1/document/draft
Content-Type: application/json

{
  "document_type": "NDA|MSA|SOW|Employment|etc.",
  "party_details": {"party_a": "...", "party_b": "..."},
  "key_terms": {"confidentiality_period": "2 years"},
  "jurisdiction": "string",
  "matter_id": "string",
  "client_name": "string",
  "special_instructions": "string (optional)"
}
```

---


## 🔒 Security & Compliance

### Data Protection
- **Encryption:** AES-256 at rest, TLS 1.3 in transit
- **Access Control:** Role-based permissions
- **Audit Logs:** All actions timestamped and logged

### Ethics Compliance
- **No Legal Advice:** All output labeled as research assistance
- **Attorney Review Required:** Flagged on every output
- **Adverse Authority:** Disclosed per professional responsibility
- **Citation Verification:** Hallucination prevention protocols

### Human Escalation

Automatic attorney alert when:
- Contract value > $500,000
- Criminal matter detected
- Statute of limitations < 30 days
- Cross-border jurisdiction
- Confidence score < 0.75

---
🎯 Learning Objectives

This project demonstrates practical experience with:

- Generative AI & LLM Application Development
- AI-Powered Legal Document Analysis
-Retrieval-Augmented Generation (RAG)
- Semantic Search & Information Retrieval
- Vector Database Integration
- LangChain & LangGraph Workflows
- Agentic AI & Multi-Agent Orchestration
- LLM Tool Calling & Structured Outputs
- Groq API & Open-Source LLM Integration
- Production-Ready FastAPI Development
- REST API Design & Backend Architecture
- AI-Powered Contract Risk Analysis
- Automated Legal Document Drafting
- Enterprise AI Application Architecture



# 📄 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

## Sonu Yadav

**AI Automation Engineer | AI Agent Developer | GenAI Engineer**

### Tech Stack

- Python
- FastAPI
- LangGraph
- Next.js
- TypeScript
- PostgreSQL
- Qdrant
- Docker
- GROQ API
- Google Gemini
- MCP
- n8n Automation

---

<div align="center">
⭐ If you found this project useful, please consider giving it a Star.

</div>