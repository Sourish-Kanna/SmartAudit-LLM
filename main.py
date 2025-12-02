from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import os
import shutil
from dotenv import load_dotenv
from dotenv import load_dotenv

load_dotenv()

# Import LlamaAuditSummarizer
from llama.llama_audit_summary import LlamaAuditSummarizer

# Import Mistral Audit Components
from mistral.mistral_audit_agent import InvoiceAuditAgent

# Import parsers
from parsers.csv_parser import csv_parser
from parsers.pdf_parser import pdf_parser

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Financial Audit AI Backend",
    description="API for processing financial documents and generating audit summaries.",
    version="1.0.0"
)

# Configure CORS to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Initialize LLM agents globally to avoid re-initialization on each request
llama_summarizer = LlamaAuditSummarizer()
mistral_audit_agent = InvoiceAuditAgent() # Note: InvoiceAuditAgent will use MistralAuditLogic internally

# Directory to temporarily store uploaded files
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/audit")
async def perform_audit(
    message: str = Form(...), # User's chat message
    csv_file: Optional[UploadFile] = File(None), # Optional CSV file upload
    pdf_file: Optional[UploadFile] = File(None)  # Optional PDF file upload
):
    """
    Processes uploaded financial documents (CSV and/or PDF) and a user query
    to generate a comprehensive financial audit summary.

    Args:
        message (str): The user's query or instruction for the audit.
        csv_file (Optional[UploadFile]): An optional CSV file containing financial data.
        pdf_file (Optional[UploadFile]): An optional PDF file containing financial data.

    Returns:
        JSONResponse: A JSON object containing the markdown audit summary.
    """
    raw_invoices: List[Dict[str, Any]] = []
    temp_file_paths = []

    try:
        # Process CSV file if provided
        if csv_file:
            csv_path = os.path.join(UPLOAD_DIR, csv_file.filename)
            temp_file_paths.append(csv_path)
            with open(csv_path, "wb") as buffer:
                shutil.copyfileobj(csv_file.file, buffer)
            print(f"CSV file saved to {csv_path}")
            parsed_csv_invoices = csv_parser(csv_path)
            raw_invoices.extend(parsed_csv_invoices)
            print(f"Parsed {len(parsed_csv_invoices)} invoices from CSV.")

        # Process PDF file if provided
        if pdf_file:
            pdf_path = os.path.join(UPLOAD_DIR, pdf_file.filename)
            temp_file_paths.append(pdf_path)
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(pdf_file.file, buffer)
            print(f"PDF file saved to {pdf_path}")
            parsed_pdf_invoices = pdf_parser(pdf_path)
            raw_invoices.extend(parsed_pdf_invoices)
            print(f"Parsed {len(parsed_pdf_invoices)} invoices from PDF.")

        if not raw_invoices:
            # If no files were uploaded or parsed, return an error
            print(message)
            res = llama_summarizer.chat(message)
            return JSONResponse(content={"response": res})

            # raise HTTPException(status_code=400, detail="No valid invoice data found. Please upload CSV or PDF files.")

        # Step 1: Run through InvoiceAuditAgent (which includes MistralAuditLogic)
        # This generates the structured audit_json with fuzzy insights
        print("Running InvoiceAuditAgent to get initial audit data and fuzzy insights...")
        audit_output = mistral_audit_agent.audit(raw_invoices)
        print("InvoiceAuditAgent completed.")
        
        # Step 2: Summarize with LlamaAuditSummarizer
        # The LlamaSummarizer expects the entire audit_json as its input
        print("Summarizing audit data with LlamaAuditSummarizer...")
        final_summary_markdown = llama_summarizer.summarize(audit_output)
        # print(f"Final summary generated:\n{final_summary_markdown}")
        print("LlamaAuditSummarizer completed.")

        return JSONResponse(content={"response": final_summary_markdown})

    except HTTPException as e:
        # Re-raise HTTPExceptions for proper FastAPI error handling
        raise e
    except Exception as e:
        print(f"An error occurred during audit: {e}")
        # Return a generic error message for other exceptions
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        # Clean up temporary files
        for path in temp_file_paths:
            if os.path.exists(path):
                os.remove(path)
                print(f"Cleaned up temporary file: {path}")
