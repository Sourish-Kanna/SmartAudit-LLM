import re
from datetime import datetime
from typing import List, Dict, Any
import logging # <-- NEW: Import logging module

# Get the existing logger instance for consistency
logger = logging.getLogger("AuditApp") 


class MistralAuditLogic:
    def __init__(self, invoices: List[Dict[str, Any]]):
        self.invoices = invoices

    def clean_amount(self,amount):
        try:
            # If it's already a number, return as float
            if isinstance(amount, (int, float)):
                return float(amount)
            
            # If it's a string, extract the numeric part
            match = re.search(r"[\d,]+(?:\.\d{1,2})?", amount)
            if not match:
                raise ValueError("No valid amount found")
            return float(match.group().replace(",", ""))
        
        except Exception as e:
            logger.error(f"❌ Failed to clean amount: {amount} → {e}")
            return None

    def detect_total_mismatches(self) -> List[Dict[str, Any]]:
        issues = []
        for inv in self.invoices:
            for product in inv["products"]:
                try:
                    qty = float(product["quantity"])
                    unit_price = self.clean_amount(product["unit_price"])
                    expected_total = qty * unit_price
                    actual_total = self.clean_amount(product["total"])
                    if round(expected_total, 2) != round(actual_total, 2):
                        issues.append({
                            "invoice_id": inv["invoice_id"],
                            "vendor": inv["vendor"],
                            "issue_type": "total_mismatch",
                            "description": f"Total mismatch for item {product['name']}: expected {expected_total:.2f}, got {actual_total:.2f}",
                            "severity": "high"
                        })
                except Exception as e:
                    logger.error(f"Error in invoice {inv['invoice_id']}: {e}")
        return issues

    def detect_missing_fields(self) -> List[Dict[str, str]]:
        missing = []
        for inv in self.invoices:
            if not inv.get("vendor"):
                missing.append({"invoice_id": inv["invoice_id"], "field": "vendor"})
            for product in inv["products"]:
                for field in ["quantity", "unit_price", "total"]:
                    if not product.get(field):
                        missing.append({"invoice_id": inv["invoice_id"], "field": field})
        return missing

    def detect_future_dates(self) -> List[Dict[str, str]]:
        future_flags = []
        for inv in self.invoices:
            try:
                inv_date = datetime.strptime(inv["date"], "%Y-%m-%d").date()
                if inv_date > datetime.today().date():
                    future_flags.append({
                        "invoice_id": inv["invoice_id"],
                        "date": inv["date"]
                    })
            except ValueError:
                continue
        return future_flags

    def summarize_vendors(self) -> List[Dict[str, Any]]:
        summary = {}
        for inv in self.invoices:
            vendor = inv["vendor"]
            if not vendor:
                continue
            billed_total = sum(
                amt for p in inv["products"]
                if (amt := self.clean_amount(p["total"])) is not None
                )

            if vendor not in summary:
                summary[vendor] = {"invoice_count": 0, "total_billed": 0.0}
            summary[vendor]["invoice_count"] += 1
            summary[vendor]["total_billed"] += billed_total
        return [{"vendor": v, **summary[v]} for v in summary]

    def detect_duplicates_and_repeats(self) -> Dict[str, Any]:
        amount_map = {}
        item_counts = {}
        for inv in self.invoices:
            for product in inv["products"]:
                amt = self.clean_amount(product["total"])
                amount_map.setdefault(amt, []).append(inv["invoice_id"])
                item = product["name"]
                item_counts[item] = item_counts.get(item, 0) + 1

        duplicate_amounts = [
            {"amount": amt, "invoice_ids": ids}
            for amt, ids in amount_map.items() if len(ids) > 1
        ]
        repeated_items = [
            {"item": item, "occurrences": count}
            for item, count in item_counts.items() if count > 1
        ]
        return {"duplicate_amounts": duplicate_amounts, "repeated_items": repeated_items}

    def run_audit(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_invoices": len(self.invoices),
                "vendors": len({inv["vendor"] for inv in self.invoices if inv["vendor"]}),
                "date_range": {
                    "start": min(inv["date"] for inv in self.invoices),
                    "end": max(inv["date"] for inv in self.invoices),
                },
            },
            "issues": self.detect_total_mismatches(),
            "compliance_flags": {
                "missing_fields": self.detect_missing_fields(),
                "future_dates": self.detect_future_dates(),
                "invalid_gstin": []  # Optional: if GSTIN was part of input
            },
            "vendor_summary": self.summarize_vendors(),
            "invoice_patterns": self.detect_duplicates_and_repeats()
        }


# 🔬 Example usage and test
if __name__ == "__main__":
    test_data = [
        {
            "date": "2025-06-01",
            "invoice_id": "INV-1001",
            "products": [
                {"name": "Cement Bags", "quantity": "10", "total": "Rs. 5000.00", "unit_price": "Rs. 500.00"},
                {"name": "Steel Rods", "quantity": "5", "total": "Rs. 6000.00", "unit_price": "Rs. 1200.00"}
            ],
            "vendor": "ABC Traders"
        },
        {
            "date": "2025-08-12",
            "invoice_id": "INV-1002",
            "products": [
                {"name": "Bricks", "quantity": "1000", "total": "Rs. 10000.00", "unit_price": "Rs. 10.00"},
                {"name": "Sand Bags", "quantity": "50", "total": "Rs. 4000.00", "unit_price": "Rs. 80.00"}
            ],
            "vendor": "XYZ Construction Supplies"
        },
        {
            "date": "2025-06-20",
            "invoice_id": "INV-1003",
            "products": [
                {"name": "Pipes (PVC)", "quantity": "20", "total": "Rs. 6000.00", "unit_price": "Rs. 300.00"},
                {"name": "Valves", "quantity": "0", "total": "Rs. 0.00", "unit_price": "Rs. 150.00"}
            ],
            "vendor": ""
        },
        {
            "date": "2025-07-05",
            "invoice_id": "INV-1004",
            "products": [
                {"name": "Paint (White)", "quantity": "5", "total": "Rs. 4000.00", "unit_price": "Rs. 800.00"},
                {"name": "Brushes", "quantity": "20", "total": "Rs. 1000.00", "unit_price": "Rs. 50.00"},
                {"name": "Rollers", "quantity": "10", "total": "Rs. 750.00", "unit_price": "Rs. 75.00"}
            ],
            "vendor": "Building Solutions Inc."
        }
    ]

    audit = MistralAuditLogic(test_data)
    result = audit.run_audit()

    import json
    logger.info(json.dumps(result, indent=2))
