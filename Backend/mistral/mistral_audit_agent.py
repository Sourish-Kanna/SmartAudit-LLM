import json
import json5
import re
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from mistral.audit_logic import MistralAuditLogic
import logging # <-- NEW: Import logging module

# Get the existing logger instance for consistency
logger = logging.getLogger("AuditApp") 


class InvoiceAuditAgent:
    def __init__(self, model: str = "llama-3.3-70b-versatile", temperature: float = 0.2):
        load_dotenv()
        self.chat = ChatGroq(
            model=model,
            temperature=temperature,
        )
        self.prompt_template = PromptTemplate(
            input_variables=["audit_json"],
            template=self._load_template(),
        )
        self.chain = self.prompt_template | self.chat

    def _load_template(self) -> str:
        return ("""
You are a specialized AI agent for financial data analysis. Your only function is to generate a JSON object containing analytical insights.

Analyze the provided invoice audit JSON based on the following detection rules to identify potential anomalies and patterns:
1.  **Unusual Item Mix:** Are there strange combinations of items on a single invoice (e.g., office supplies and heavy machinery)?
2.  **Suspicious Quantities:** Are the quantities unusually high or low for the item type (e.g., 1000 laptops, 0.5 chairs)?
3.  **Single-Invoice Vendors:** Does a vendor appear only once in the entire dataset? This can sometimes indicate a one-off, potentially risky transaction.
4.  **Zero Value Items:** Are any line items listed with a quantity or billed amount of zero?
5.  **Pattern Recognition:** Are there frequently repeated, non-round amounts or items that suggest automated billing or potential duplication?

## JSON Output Requirements
- Your entire response must be a single, valid JSON object.
- The root object must contain ONLY one key: `"fuzzy_insights"`.
- The value of `"fuzzy_insights"` must be an array of insight objects.
- Each insight object must have two keys: `"type"` (a string) and `"description"` (a string).
- Do NOT include markdown, code fences (` ``` `), or any explanatory text outside of the JSON structure.

## Example Output
```json
{{
  "fuzzy_insights": [
    {{
      "type": "suspicious_quantity",
      "description": "Invoice INV-123 contains an unusually high quantity of 500 keyboards for a small-medium enterprise."
    }},
    {{
      "type": "single_invoice_vendor",
      "description": "Vendor 'Global Tech Solutions' has only one invoice in this batch, which may warrant further review."
    }},
    {{
      "type": "zero_value_item",
      "description": "Line item 'Promotional Pens' on invoice INV-456 has a quantity of 200 but a billed amount of zero."
    }}
  ]
}}
# Input JSON:
# {{ audit_json }}
""")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extracts JSON from text, tolerating minor LLM formatting issues."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON object found in the response.")
        raw_json = match.group()

        try:
            # First try strict parsing
            return json.loads(raw_json)
        except json.JSONDecodeError:
            # Fall back to tolerant parsing with json5
            return json5.loads(raw_json)

    def audit(self, invoice_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        mistral_logic = MistralAuditLogic(invoice_data)
        audit_json = mistral_logic.run_audit()

        try:
            input_for_llm = json.dumps(audit_json, indent=2)
            response = self.chain.invoke({"audit_json": input_for_llm})
            fuzzy = self._extract_json(response.content)
            audit_json.update({"fuzzy_insights": fuzzy.get("fuzzy_insights", [])})

        except Exception as e:
            logger.error(f"❌ Failed to get or parse fuzzy insights: {e}")
            audit_json.update({
                "fuzzy_insights_error": "Failed to generate or parse insights from the model.",
            })

        return audit_json
