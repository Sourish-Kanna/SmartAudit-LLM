from openai import chat
from parsers.csv_parser import csv_parser
from parsers.pdf_parser import pdf_parser
from llama.llama_audit_summary import LlamaAuditSummarizer
from mistral.mistral_audit_agent import InvoiceAuditAgent
from ChatSession.chat_session import ChatSession
from rich import print
from rich.console import Console
from rich.markdown import Markdown
import json

def print_and_summarize(raw_invoices, parser_name):
    # print(f"\n--- {parser_name} Parsed Output ---")
    # for inv in raw_invoices:
    #     print(json.dumps(inv, indent=2, ensure_ascii=False))

    if raw_invoices:
        # 🧠 Run through Mistral Agent first
        mistral_agent = InvoiceAuditAgent()
        audit_output = mistral_agent.audit(raw_invoices)
        # print(f"{[audit_output]}")

        # print(f"\n--- Mistral Agent Audit Output ---")
        # print(json.dumps(audit_output, indent=2, ensure_ascii=False))

        # 🦙 Then summarize with LLaMA
        summarizer = LlamaAuditSummarizer()
        summary = summarizer.summarize({"audit_json": audit_output})

        console = Console()
        print(f"\n--- LLaMA Summary for {parser_name} ---\n")
        markdown_summary = f"{summary}"
        markdown = Markdown(markdown_summary)
        console.print(markdown)


        chat_session = ChatSession(system_prompt=f"{summary}\n{json.dumps(audit_output, indent=2)}", model=summarizer.chat_model)
        insights = chat_session.user_chat("What are the key insights from this audit?")
        print(f"\n--- LLaMA Insights for {parser_name} ---\n")
        markdown_summary = f"{insights}"
        markdown = Markdown(markdown_summary)
        console.print(markdown)

        while True:
            user_input = input("\nEnter your question (or type 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            response = chat_session.user_chat(user_input)
            print(f"\n--- Response ---\n")
            markdown_response = f"{response}"
            markdown = Markdown(markdown_response)
            console.print(markdown)


if __name__ == "__main__":
    csv_invoices = csv_parser('./sample_data/test1.csv')
    print_and_summarize(csv_invoices, "CSV Parser")

    # Uncomment to test PDF
    pdf_invoices = pdf_parser('./sample_data/mul_1.pdf')
    # print_and_summarize(pdf_invoices, "PDF Parser")

    list_invoices = csv_invoices + pdf_invoices
    # print_and_summarize(list_invoices, "Combined CSV and PDF Parser")