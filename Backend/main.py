from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import os
import shutil
import logging 
from dotenv import load_dotenv

load_dotenv()

# --- NEW: Configure Basic Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AuditApp") # Logger instance for the application

# --- Existing Imports ---
from llama.llama_audit_summary import LlamaAuditSummarizer
from mistral.mistral_audit_agent import InvoiceAuditAgent
from parsers.csv_parser import csv_parser
from parsers.pdf_parser import pdf_parser

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Financial Audit AI Backend",
    description="API for processing financial documents and generating audit summaries.",
    version="1.0.0"
)

# Configure CORS (standard setup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM agents globally
logger.info("Initializing LLM Agents...")
llama_summarizer = LlamaAuditSummarizer()
mistral_audit_agent = InvoiceAuditAgent()
logger.info("LLM Agents initialized successfully.")

# Directory to temporarily store uploaded files
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info(f"Upload directory created/verified: {UPLOAD_DIR}")


@app.post("/audit")
async def perform_audit(
    message: str = Form(...),
    csv_file: Optional[UploadFile] = File(None),
    pdf_file: Optional[UploadFile] = File(None)
):
    """
    Processes uploaded financial documents and a user query to generate a summary.
    """
    
    # NEW: Log incoming request details
    logger.info(f"--- New Audit Request ---")
    logger.info(f"User Message: {message[:50]}...")
    logger.info(f"Files Received: CSV={csv_file.filename if csv_file else 'None'}, PDF={pdf_file.filename if pdf_file else 'None'}")
    
    raw_invoices: List[Dict[str, Any]] = []
    temp_file_paths = []

    try:
        # Process CSV file if provided
        if csv_file:
            csv_path = os.path.join(UPLOAD_DIR, csv_file.filename)
            temp_file_paths.append(csv_path)
            with open(csv_path, "wb") as buffer:
                shutil.copyfileobj(csv_file.file, buffer)
            logger.info(f"CSV file saved to {csv_path}")
            
            parsed_csv_invoices = csv_parser(csv_path)
            raw_invoices.extend(parsed_csv_invoices)
            logger.info(f"Parsed {len(parsed_csv_invoices)} invoices from CSV.")

        # Process PDF file if provided
        if pdf_file:
            pdf_path = os.path.join(UPLOAD_DIR, pdf_file.filename)
            temp_file_paths.append(pdf_path)
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(pdf_file.file, buffer)
            logger.info(f"PDF file saved to {pdf_path}")
            
            parsed_pdf_invoices = pdf_parser(pdf_path)
            raw_invoices.extend(parsed_pdf_invoices)
            logger.info(f"Parsed {len(parsed_pdf_invoices)} invoices from PDF.")

        if not raw_invoices:
            # If no files were uploaded, delegate to chat agent for a conversational response
            logger.info(f"No documents uploaded. Routing message to Llama chat agent.")
            res = llama_summarizer.chat(message)
            return JSONResponse(content={"response": res})

        # Step 1: Run through InvoiceAuditAgent
        logger.info(f"Starting InvoiceAuditAgent for {len(raw_invoices)} total parsed items.")
        audit_output = mistral_audit_agent.audit(raw_invoices)
        logger.info("InvoiceAuditAgent completed successfully.")
        
        # Step 2: Summarize with LlamaAuditSummarizer
        logger.info("Summarizing audit data with LlamaAuditSummarizer...")
        final_summary_markdown = llama_summarizer.summarize(audit_output)
        logger.info("LlamaAuditSummarizer completed. Response generated.")

        return JSONResponse(content={"response": final_summary_markdown})

    except HTTPException as e:
        logger.warning(f"Handled HTTP Exception: {e.detail}")
        raise e
    except Exception as e:
        # Log unexpected errors at the ERROR level
        logger.error(f"An unexpected error occurred during audit processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        # Clean up temporary files
        for path in temp_file_paths:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Cleaned up temporary file: {path}")