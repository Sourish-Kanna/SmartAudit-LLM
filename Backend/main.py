import uuid 
import json 
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import os
import shutil
import logging 
from dotenv import load_dotenv

load_dotenv()

# --- Configure Basic Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(message)s'
)
logger = logging.getLogger("AuditApp") # Logger instance for the application

# --- Existing Imports ---
from llama.llama_audit_summary import LlamaAuditSummarizer
from mistral.mistral_audit_agent import InvoiceAuditAgent
from parsers.csv_parser import csv_parser
from parsers.pdf_parser import pdf_parser
from chat_session.chat_session import ChatSession # NEW: Import ChatSession

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
CHAT_SESSIONS: Dict[str, ChatSession] = {} 

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
    Processes uploaded financial documents, performs audit, and starts a stateful chat session.
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
            # Stateless Fallback (No documents uploaded)
            logger.info(f"No documents uploaded. Routing message to Llama chat agent (Stateless).")
            res = llama_summarizer.chat(message)
            return JSONResponse(content={"response": res, "session_id": None})

        # Step 1: Run through InvoiceAuditAgent
        logger.info(f"Starting InvoiceAuditAgent for {len(raw_invoices)} total parsed items.")
        audit_output = mistral_audit_agent.audit(raw_invoices)
        logger.info("InvoiceAuditAgent completed successfully.")
        
        # Step 2: Summarize with LlamaAuditSummarizer
        logger.info("Summarizing audit data with LlamaAuditSummarizer...")
        final_summary_markdown = llama_summarizer.summarize(audit_output)
        logger.info("LlamaAuditSummarizer completed. Response generated.")

        # --- NEW STATEFUL CHAT INITIATION ---
        session_id = str(uuid.uuid4())
        
        # 1. Prepare the full context for the LLM
        system_context = f"You are an expert auditor. The following is the document audit summary and raw data. Use this information to answer follow-up questions.\n\n--SUMMARY--\n{final_summary_markdown}\n\n--RAW DATA--\n{json.dumps(audit_output, indent=2)}"
        
        # 2. Initialize the chat session
        new_session = ChatSession(
            system_prompt=system_context, 
            model=llama_summarizer.chat_model 
        )
        
        # 3. Process the initial user message within the new, stateful session
        initial_chat_response = new_session.user_chat(message)
        
        # 4. Store the active session
        CHAT_SESSIONS[session_id] = new_session
        logger.info(f"New ChatSession initialized and stored with ID: {session_id}")

        # 5. Return the audit summary, the initial chat response, and the new session ID
        return JSONResponse(content={
            "response": final_summary_markdown, 
            "session_id": session_id,          
            "initial_chat_response": initial_chat_response 
        })

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

# NEW: Endpoint for follow-up chat messages
@app.post("/chat/{session_id}")
async def continue_chat(session_id: str, message: Dict[str, str]):
    """
    Continues a stateful chat session based on the provided audit context.
    The message must be sent in the request body as {"message": "..."}.
    """
    user_message = message.get("message")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message content is required.")
    
    # Check if session exists
    chat_session = CHAT_SESSIONS.get(session_id)
    
    if not chat_session:
        logger.warning(f"Attempted access to missing session ID: {session_id}")
        raise HTTPException(status_code=404, detail="Chat session not found or expired. Please re-upload documents to start a new audit.")

    try:
        # Use the stored ChatSession object to continue the conversation
        response = chat_session.user_chat(user_message)
        logger.info(f"Chat turn processed for session {session_id}.")
        return JSONResponse(content={"response": response})
    except Exception as e:
        logger.error(f"Error during chat turn for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal chat error.")

@app.get("/")
def home():
    return {"message": "Welcome to the Financial Audit AI Backend!"}