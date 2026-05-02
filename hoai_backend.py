import os
import re
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfplumber
import requests
import chromadb
from chromadb.utils import embedding_functions

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hoai-auditor")

app = FastAPI(title="HOAI Contract Auditor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("HOAI_MODEL", "mistral")

# --- DATABASE ---
chroma_client = chromadb.PersistentClient(path="./hoai_db")
default_ef = embedding_functions.DefaultEmbeddingFunction()
def get_hoai_collection():
    return chroma_client.get_or_create_collection(
        name="hoai_reference", 
        embedding_function=default_ef
    )

# --- MODELS ---
class ExtractionRequest(BaseModel):
    text: str
    model: Optional[str] = "mistral"

class ChatRequest(BaseModel):
    message: str
    contract_text: Optional[str] = ""
    audit_report: Optional[str] = ""
    history: List[Dict[str, str]] = []
    model: Optional[str] = "mistral"

class AuditResponse(BaseModel):
    phase: str
    status: str
    data: Any
    reasoning: str

# --- UTILS ---
def fix_json_syntax(json_str: str) -> str:
    """Attempt to fix common LLM JSON errors like missing commas between fields"""
    # Fix missing comma between ] and "
    json_str = re.sub(r'\]\s*\"', '], "', json_str)
    # Fix missing comma between } and "
    json_str = re.sub(r'\}\s*\"', '}, "', json_str)
    # Fix missing comma between " and " (if they are on different lines/fields)
    # This is trickier, only do it if we see property-like patterns
    json_str = re.sub(r'\"\s*\"(\w+)\"\s*:', r'", "\1":', json_str)
    return json_str

# --- SMART CHUNKING ---
from rag_utils import smart_chunk_pdf, CHUNK_SIZE, CHUNK_OVERLAP

def call_ollama(prompt: str, system_prompt: str = "", model_name: str = "mistral") -> str:
    try:
        # Use /api/generate for better stability across models like Qwen 3.5
        full_prompt = f"[SYSTEM: {system_prompt}]\n\n{prompt}" if system_prompt else prompt
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": full_prompt,
                "options": {
                    "num_ctx": 8192,
                    "num_predict": 2048,
                    "temperature": 0.2
                },
                "stream": False
            },
            timeout=600
        )
        if response.status_code == 200:
            return response.json().get('response', '')
        return f"Error: {response.status_code}"
    except Exception as e:
        return f"Exception: {str(e)}"

# --- ENDPOINTS ---
@app.get("/models")
async def list_models():
    """Get list of available Ollama models"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [m['name'] for m in models]
        return ["mistral"]
    except:
        return ["mistral"]

@app.post("/upload/hoai")
async def upload_hoai(file: UploadFile = File(...)):
    """Ingest the HOAI PDF and index it into ChromaDB using smart chunking"""
    try:
        content = await file.read()
        logger.info(f"Received file: {file.filename}, size: {len(content)} bytes")
        temp_path = f"temp_hoai_{uuid.uuid4().hex}.pdf"
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Smart chunking: tables + sections + sliding window
        logger.info(f"Smart chunking PDF: {temp_path}")
        text_chunks = smart_chunk_pdf(temp_path, file.filename)

        if not text_chunks:
            logger.error(f"No text extracted from {file.filename}")
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            raise HTTPException(status_code=422, detail="No readable text found in PDF. Is it a scanned image?")

        logger.info(f"Smart chunking produced {len(text_chunks)} chunks. Vectorizing...")
        
        # Upsert to Chroma
        try:
            logger.info("Clearing old collection...")
            chroma_client.delete_collection(name="hoai_reference")
        except Exception as e:
            logger.warning(f"Note: Could not delete collection: {e}")
            
        coll = chroma_client.get_or_create_collection(
            name="hoai_reference", 
            embedding_function=default_ef
        )
        
        coll.add(
            ids=[c["id"] for c in text_chunks],
            documents=[c["text"] for c in text_chunks],
            metadatas=[c["metadata"] for c in text_chunks]
        )
        
        logger.info("Ingestion successful.")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Return chunk breakdown
        breakdown = {
            "tables": sum(1 for c in text_chunks if c['metadata']['chunk_type'] == 'table'),
            "sections": sum(1 for c in text_chunks if c['metadata']['chunk_type'] == 'section'),
            "text": sum(1 for c in text_chunks if c['metadata']['chunk_type'] == 'text'),
        }
        return {"status": "success", "chunks": len(text_chunks), "breakdown": breakdown}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during HOAI upload")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/hoai")
async def get_hoai_status():
    """Check if HOAI is already indexed"""
    try:
        count = get_hoai_collection().count()
        return {"status": "success", "count": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/upload/contract")
async def upload_contract(file: UploadFile = File(...)):
    """Extract text from the contract PDF"""
    try:
        content = await file.read()
        temp_path = f"temp_contract_{uuid.uuid4().hex}.pdf"
        with open(temp_path, "wb") as f:
            f.write(content)
            
        full_text = ""
        try:
            with pdfplumber.open(temp_path) as pdf:
                for page in pdf.pages:
                    full_text += (page.extract_text() or "") + "\n"
        finally:
            # Ensure file handle is closed
            pass
        
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        return {"status": "success", "text": full_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-parameters")
async def extract_parameters(req: ExtractionRequest):
    """Phase 2 & 3: Semantic Extraction & Reasoning"""
    system_prompt = """You are an expert HOAI auditor. Your goal is to extract key billing parameters from architectural contracts.
IMPORTANT: All the text you need to analyze is provided directly below. You MUST extract values from this text. 
NEVER say you cannot access the data — it is given to you in this prompt."""
    prompt = f"""Extract the following parameters FROM THE GERMAN TEXT PROVIDED BELOW. 
BEWARE: Financial numbers often use '.' as thousands separator and ',' as decimal separator in German.

1. "Anrechenbare Kosten" (Chargeable Costs): The main construction budget.
2. "Honorar" / "Pauschalhonorar" (Agreed Fee): The specific fee agreed for the architect. 
3. "Leistungsphasen" (Service Phases): List which ones (1-9) are mentioned.
4. Difficulty: Any mention of "Honorarzone", "Denkmalschutz", "Hanglage", or "Schwierig".

TEXT TO ANALYZE:
{req.text} 

OUTPUT ONLY VALID JSON:
{{
  "costs": float,
  "contract_fee": float or null,
  "service_phases": [int],
  "complexity_clues": [string],
  "reasoning": "Explain exactly where you found the costs and the contract_fee"
}}
"""
    model_to_use = req.model or MODEL_NAME
    result = call_ollama(prompt, system_prompt, model_to_use)
    
    # Debug log
    logger.info(f"Raw Ollama output from {model_to_use}: {result[:500]}...")

    try:
        # Clean potential markdown or prefix text
        json_str = result.strip()
        
        # Remove DeepSeek/Qwen thinking blocks if present
        if "<think>" in json_str:
            json_str = json_str.split("</think>")[-1].strip()
        
        # Look for JSON block
        if "```json" in json_str:
            json_str = json_str.split("```json")[-1].split("```")[0].strip()
        elif "```" in json_str:
            # Check if it looks like a code block
            parts = json_str.split("```")
            if len(parts) >= 3:
                json_str = parts[1].strip()
            
        # Try to find the first '{' and last '}' to isolate JSON
        start = json_str.find('{')
        end = json_str.rfind('}')
        if start != -1 and end != -1:
            json_str = json_str[start:end+1]
        else:
            # If no JSON braces found, it might be an error or purely text
            if result.startswith("Exception:") or result.startswith("Error:"):
                 raise ValueError(f"Ollama Error: {result}")
            raise ValueError("No JSON structure found in LLM response.")
            
        # Apply syntax fixes
        json_str = fix_json_syntax(json_str)
            
        data = json.loads(json_str)
        return {"status": "success", "data": data, "raw_reasoning": result}
    except Exception as e:
        return {"status": "partial", "raw_output": result, "error": str(e)}

@app.post("/audit")
async def perform_audit(data: Dict[str, Any]):
    """Phase 4 & 5: RAG Audit and Comparison"""
    # 1. Retrieve relevant HOAI snippets
    query = f"Fee table for costs {data.get('costs')} and complexity related to {', '.join(data.get('complexity_clues', []))}"
    results = get_hoai_collection().query(query_texts=[query], n_results=6)
    
    # Enrich context with metadata (Page numbers + chunk type)
    context_parts = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        chunk_type = meta.get('chunk_type', 'text').upper()
        section = meta.get('section', '')
        section_str = f" | SECTION: {section}" if section else ""
        context_parts.append(f"[{chunk_type} | SOURCE: {meta.get('source')} | PAGE: {meta.get('page')}{section_str}]\n{doc}")
    context = "\n---\n".join(context_parts)
    
    # 2. Query LLM for calculation based on context
    model_to_use = data.get('model', MODEL_NAME)
    system_prompt = """You are a legal HOAI calculation bot. 
CRITICAL RULES:
- The HOAI reference text is PROVIDED DIRECTLY BELOW in this prompt. You HAVE full access to it.
- NEVER say "I don't have access to the HOAI tables" — the tables ARE provided below.
- You MUST use ONLY the provided HOAI text to find fee values and perform calculations.
- If the exact value is not in the provided text, interpolate or estimate based on what IS provided.
- Always show your calculation step by step."""
    contract_fee = data.get('contract_fee')
    prompt = f"""You are a Mathematical Audit Engine.

IMPORTANT: The HOAI fee tables and legal text are PROVIDED BELOW. You MUST use them. Do NOT claim you lack access to HOAI data.

INPUT DATA:
- Building Type: Gebäude (§ 34)
- Chargeable Costs (Anrechenbare Kosten): {data.get('costs')} EUR
- Requested Phases: {data.get('service_phases')}

=== HOAI REFERENCE TEXT (PROVIDED — USE THIS) ===
{context}
=== END OF HOAI REFERENCE TEXT ===

---
STRICT CALCULATION RULES (DO NOT CHANGE THESE PERCENTAGES):
For standard Gebäude (§ 35):
- LPH 1 (Grundlagenermittlung): 2%
- LPH 2 (Vorplanung): 7%
- LPH 3 (Entwurfsplanung): 15%
- LPH 4 (Genehmigungsplanung): 3%
- LPH 5 (Ausführungsplanung): 25%
- LPH 6 (Vorbereitung Vergabe): 10%
- LPH 7 (Mitwirkung Vergabe): 4%
- LPH 8 (Objektüberwachung): 32%
- LPH 9 (Objektbetreuung): 2%

TOTAL PERCENTAGE for phases {data.get('service_phases')} is: (Sum of above percentages)%

MISSION:
1. Find the "Basishonorsatz" (lowest fee) for {data.get('costs')} EUR in the HOAI tables provided in the context.
2. If exact 2.5M is not in the table, linear interpolate between the nearest values if possible, or use the value for {data.get('costs')}.
3. Multiply [Base Fee] * [Total Percentage/100].

OUTPUT FORMAT:
1. LEGAL FEE: [Result] EUR
2. CALCULATION WAY: [Show the math CLEARLY: Base fee * sum of percentages]
3. CONTRACT FEE: {contract_fee if contract_fee else 'NOT FOUND'}
4. CITATION: [Specific HOAI Section/Page]
5. DISCREPANCY: [Legal Fee - Contract Fee]
"""
    audit_txt = call_ollama(prompt, system_prompt, model_to_use)
    return {
        "status": "success", 
        "audit_report": audit_txt, 
        "referenced_context": results['metadatas'][0],
        "referenced_texts": results['documents'][0]
    }

@app.post("/chat")
async def chat_with_context(req: ChatRequest):
    """Phase 6: Interactive Chat with RAG and Contract context"""
    # 1. Retrieve relevant HOAI snippets based on the user's message
    results = get_hoai_collection().query(query_texts=[req.message], n_results=6)
    
    context_parts = []
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        chunk_type = meta.get('chunk_type', 'text').upper()
        section = meta.get('section', '')
        section_str = f" | {section}" if section else ""
        context_parts.append(f"[HOAI REFERENCE | {chunk_type} | Page: {meta.get('page')}{section_str}]: {doc}")
    rag_context = "\n---\n".join(context_parts)
    
    # 2. Prepare the system prompt
    system_prompt = f"""You are a helpful HOAI Expert Assistant with FULL ACCESS to the project data.

CRITICAL: All HOAI legal text, the contract, and the audit report are PROVIDED DIRECTLY BELOW.
You MUST use this data to answer questions. NEVER say "I don't have access" or "I cannot access external documents" — everything you need is RIGHT HERE in this prompt.

=== PROJECT CONTRACT TEXT ===
{req.contract_text if req.contract_text else "No contract uploaded yet."}
=== END CONTRACT ===

=== RELEVANT HOAI LEGAL SNIPPETS (from vector database) ===
{rag_context}
=== END HOAI SNIPPETS ===

=== CURRENT AUDIT REPORT (Discrepancy Report) ===
{req.audit_report if req.audit_report else "No audit report generated yet."}
=== END AUDIT REPORT ===

MISSION:
1. Answer the user's question using the contract, HOAI snippets, and audit report PROVIDED ABOVE.
2. Always reference specific values, pages, or sections from the provided text.
3. IF the user asks you to change, improve, or update the Audit Report, provide the new version WRAPPED in [UPDATE_REPORT] tags like this:
   [UPDATE_REPORT]
   (Your new report content here)
   [/UPDATE_REPORT]
4. Be concise and professional. Base ALL answers on the provided data.
"""
    
    # 3. Build the prompt including history
    chat_history_str = ""
    for msg in req.history[-5:]: # Last 5 messages for context
        chat_history_str += f"{msg['role'].upper()}: {msg['content']}\n"
    
    full_prompt = f"{chat_history_str}USER: {req.message}\nASSISTANT:"
    
    model_to_use = req.model or MODEL_NAME
    response_txt = call_ollama(full_prompt, system_prompt, model_to_use)
    
    return {
        "status": "success",
        "response": response_txt,
        "referenced_context": results['metadatas'][0]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
