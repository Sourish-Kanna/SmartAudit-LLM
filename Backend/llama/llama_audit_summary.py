from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage # Corrected import
from dotenv import load_dotenv
import json
import os
import logging # <-- NEW: Import logging module

# Get the existing logger instance for consistency
logger = logging.getLogger("AuditApp") 

class LlamaAuditSummarizer:
    def __init__(self, model: str = "llama-3.1-8b-instant", temperature: float = 0.5):
        load_dotenv()
        self.chat_model = ChatGroq(
            model=model,
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY")  # type: ignore
        )  # type: ignore

        self.system_prompt = """
You are a Senior Financial Auditor AI.

Your task is to analyze structured audit data, including pre-computed analytical insights, and generate three concise, actionable summaries for different stakeholders. Use professional judgment to interpret the data and insights, focusing on risks, compliance issues, and actionable recommendations.

Begin your response directly with the "Legal Summary" heading.

---

## Legal Summary
- **Compliance & Legal Fields:** Flag any missing, incomplete, or malformed legal identifiers (e.g., GSTIN, PAN, registered address). Note any invalid or out-of-sequence invoice dates.
- **Vendor & Transaction Risk:** Identify vendors with potential compliance risks or transactions that fall outside of standard business scope. Use insights to highlight single-invoice or unverified vendors.
- **Recommendations:** Suggest concrete steps to ensure regulatory and tax compliance (e.g., "Request updated GSTIN from Vendor X," "Implement date validation checks").

## Manager Summary
- **Vendor Management:** Summarize vendor-related risks, such as over-reliance on a single supplier, unusual transaction volumes, or a high number of one-time vendors.
- **Spend Analysis:** Comment on patterns in high-volume or high-value item purchases. Use insights to question suspicious quantities or unusual item combinations that could impact inventory or project budgets.
- **Recommendations:** Propose managerial actions to mitigate risks (e.g., "Initiate a review of the top 5 vendors by spend," "Diversify suppliers for critical items," "Investigate the high quantity of 'Item Y' on PO-987").

## Accountant Summary
- **Data Integrity:** Verify that line item totals correctly match `quantity × unit_price`. Explicitly point out any discrepancies, invalid numerical values (e.g., zero quantity with a non-zero price, negative amounts), or potential rounding errors.
- **Record Clarity:** Flag vague line item descriptions, inconsistencies, or items billed with zero value that could complicate reconciliation and bookkeeping.
- **Recommendations:** Provide clear instructions for correction to ensure accurate financial records (e.g., "Correct calculation for item #3 on INV-123," "Request a revised invoice from 'ABC Corp' to clarify the zero-billed 'Service Fee'").

## Formatting and Style Guidelines
- The entire output must be in **Markdown**.
- Use bullet points (`-`) for all points within each section.
- Use the Indian Rupee symbol (`₹`) for all currency values.
- Maintain a clear, professional, and direct tone.
- Do not include any preamble, introduction, disclaimer, or concluding remarks.
- Summarize intelligently; do not repeat the raw input JSON.
"""

    def summarize(self, audit_data: dict) -> str:
        """Send audit JSON to LLaMA 3 and return structured markdown summary."""
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"{json.dumps(audit_data, indent=2)}")
        ]
        response = self.chat_model.invoke(messages)
        return response.content  # type: ignore
    
    def chat(self, messages_text: str) -> str:
        """Send a chat message to the LLaMA model and return the response."""
        logger.info(f"Delegated chat message: {messages_text[:100]}...") # <-- REPLACED logger.info
        response = self.chat_model.invoke([HumanMessage(content=messages_text)])
        return response.content

# ✅ Usage Example
if __name__ == "__main__":
    from rich.console import Console
    from rich.markdown import Markdown

    # Note: Added basic logging setup for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    audit_json = {
        "summary": {
            "total_invoices": 2,
            "vendors": 2,
            "date_range": {"start": "2025-06-01", "end": "2025-07-15"}
        },
        "issues": [
            {
                "invoice_id": "INV-1001",
                "vendor": "ABC Traders",
                "issue_type": "total_mismatch",
                "description": "Total does not match quantity × unit_price",
                "severity": "high"
            }
        ],
        "compliance_flags": {
            "future_dates": [{"invoice_id": "INV-1008", "date": "2026-01-01"}],
            "missing_fields": [{"invoice_id": "INV-1001", "field": "GSTIN"}],
            "invalid_gstin": [{"invoice_id": "INV-1002", "gstin": "123INVALIDGST"}]
        },
        "vendor_summary": [
            {"vendor": "ABC Traders", "invoice_count": 10, "total_billed": 500000}
        ],
        "invoice_patterns": {
            "duplicate_amounts": [
                {"amount": 5000, "invoice_ids": ["INV-1005", "INV-1010"]}
            ],
            "repeated_items": [
                {"item": "Widget A", "occurrences": 5}
            ]
        }
    }

    summarizer = LlamaAuditSummarizer()
    markdown_summary = summarizer.summarize(audit_json)
    
    console = Console()
    markdown = Markdown(markdown_summary)
    console.print(markdown)