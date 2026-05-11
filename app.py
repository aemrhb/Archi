try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import pandas as pd
import tempfile
import os
import re
import json
from collections import Counter
import chromadb
from chromadb.utils import embedding_functions
from rag_utils import smart_chunk_pdf

# --- PAGE SETUP ---
st.set_page_config(page_title="IFC Element Viewer", layout="wide")

# --- AUTHENTICATION GATEWAY ---
if 'user_mode' not in st.session_state:
    st.session_state['user_mode'] = None

if st.session_state['user_mode'] is None:
    st.title("🏗️ Smart Building Compliance Checker")
    st.markdown("Please select how you would like to use the application:")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("User")
        st.markdown("Access the compliance checker to upload and evaluate your BIM models.")
        if st.button("Enter as User", type="primary", use_container_width=True):
            st.session_state['user_mode'] = 'user'
            st.rerun()
            
    with col2:
        st.subheader("Administrator")
        st.markdown("Configure compliance rules, manage AI settings, and ingest rulebook PDFs.")
        admin_password = st.text_input("Admin Password", type="password")
        if st.button("Login as Admin", use_container_width=True):
            if admin_password == "admin_99":
                st.session_state['user_mode'] = 'admin'
                st.rerun()
            elif admin_password:
                st.error("Incorrect password")
    
    # Stop execution here until a mode is selected
    st.stop()

# PDF and LLM imports
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.warning("pdfplumber not installed. Install with: pip install pdfplumber")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    # Fallback to requests for Ollama API
    try:
        import requests
        OLLAMA_AVAILABLE = True
        OLLAMA_USE_REQUESTS = True
    except:
        OLLAMA_AVAILABLE = False
        st.warning("Ollama not available. Install with: pip install ollama")

# Import property set extraction function
try:
    from ifcopenshell.util.element import get_psets
except ImportError:
    # Fallback if direct import doesn't work
    get_psets = ifcopenshell.util.element.get_psets

# Helper function to get quantities (QTOs) - quantities are often in property sets too
def get_qto(element):
    """Get quantity sets (QTOs) for an element"""
    try:
        # Try using get_pset with qtos_only parameter if available
        if hasattr(ifcopenshell.util.element, 'get_pset'):
            # Some versions use get_pset with qtos_only=True
            psets = ifcopenshell.util.element.get_psets(element)
            # Filter for quantity sets (usually start with Qto_)
            qtos = {}
            for pset_name, pset_props in psets.items():
                if pset_name.startswith('Qto_') or 'Quantity' in pset_name:
                    qtos[pset_name] = pset_props
            return qtos
        else:
            # Fallback: get_psets might include quantities
            psets = get_psets(element)
            qtos = {}
            for pset_name, pset_props in psets.items():
                if pset_name.startswith('Qto_') or 'Quantity' in pset_name:
                    qtos[pset_name] = pset_props
            return qtos
    except:
        return {}

# Helper function to get available Ollama models
def get_available_ollama_models(base_url="http://localhost:11434"):
    """Get list of available Ollama models"""
    try:
        import requests
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [m['name'] for m in models]
        return []
    except:
        return []

# Helper functions for PDF and LLM processing
def extract_text_from_pdf(pdf_file, keyword_prioritize=True, deep_scan=False):
    """
    Extract text and tables from PDF file with structure awareness.
    If deep_scan is True, it bypasses keyword filtering.
    If keyword_prioritize is True and deep_scan is False, it looks for pages containing dimensional keywords.
    """
    if not PDF_AVAILABLE:
        return None
    
    # Expanded keywords to include qualitative rules and DIN standards
    keywords = [
        "maße", "abmessungen", "mindest", "breite", "höhe", "fläche", "stärke", "dicke", "abstand", "m²", "cm", "mm",
        "din", "norm", "anforderung", "standard", "sicherheit", "allgemein", "bauaufsichtlich", "brandschutz"
    ]
    
    important_content = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                
                # Check if page is likely to contain dimensional or regulatory rules
                is_important = any(kw in page_text.lower() for kw in keywords)
                
                if deep_scan or is_important or not keyword_prioritize:
                    # 1. Extract tables as structured text
                    tables = page.extract_tables()
                    table_text = ""
                    for table in tables:
                        for row in table:
                            # Filter out None and join with pipes to preserve row structure
                            clean_row = [str(cell).replace('\n', ' ') for cell in row if cell is not None]
                            if clean_row:
                                table_text += "| " + " | ".join(clean_row) + " |\n"
                    
                    # 2. Combine clean text and table text
                    # We remove potential headers/footers by skipping very short lines at start/end
                    lines = page_text.split('\n')
                    clean_lines = [l for l in lines if len(l.strip()) > 3] # Filter out tiny noise lines
                    
                    page_content = f"--- PAGE {i+1} ---\n"
                    if table_text:
                        page_content += f"TABLE DATA:\n{table_text}\n"
                    page_content += "\n".join(clean_lines)
                    
                    important_content.append(page_content)
                    
            # Join everything back together
            if not important_content:
                # Fallback if no keywords found: take first few pages
                return "\n".join([(p.extract_text() or "") for p in pdf.pages[:10]])
                
            return "\n\n".join(important_content)
    except Exception as e:
        st.error(f"Error extracting structured text from PDF: {e}")
        return None

def call_local_llm(prompt, model_name="llama3", base_url="http://localhost:11434"):
    """Call local LLM (Ollama) or Cloud (Groq) to process the prompt"""
    import requests
    
    provider = st.session_state.get('llm_provider', 'Ollama (Local)')
    
    if provider == "Groq (Cloud Fast)":
        api_key = st.session_state.get('groq_api_key', '')
        if not api_key:
            st.error("Groq API Key is missing!")
            return None
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                st.error(f"Groq API Error: {response.text}")
                return None
        except Exception as e:
            st.error(f"Error calling Groq API: {e}")
            return None
            
    # --- Otherwise, Ollama logic ---
    if not OLLAMA_AVAILABLE:
        return None
    
    try:
        # Try using ollama library first (if available)
        try:
            if 'ollama' in globals() and hasattr(ollama, 'chat'):
                response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
                return response['message']['content']
        except Exception as e:
            st.warning(f"Ollama library failed, trying HTTP API: {e}")
        
        # Use requests with /api/chat endpoint (correct endpoint for chat models)
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('message', {}).get('content', '')
        elif response.status_code == 404:
            # Model might not exist, try to list available models and suggest fallback
            try:
                models_response = requests.get(f"{base_url}/api/tags", timeout=10)
                if models_response.status_code == 200:
                    available_models = [m['name'] for m in models_response.json().get('models', [])]
                    st.error(f"❌ Model '{model_name}' not found.")
                    
                    if available_models:
                        st.warning(f"Available models: {', '.join(available_models)}")
                        st.info(f"💡 **Solution 1**: Select one of the available models from the dropdown above")
                        st.info(f"💡 **Solution 2**: Pull the model with: `ollama pull {model_name}`")
                        
                        # Try to use first available model as fallback
                        fallback_model = available_models[0]
                        if st.button(f"🔄 Try with available model: {fallback_model}", key="fallback_model"):
                            st.info(f"Retrying with {fallback_model}...")
                            # Retry with fallback model
                            fallback_response = requests.post(
                                f"{base_url}/api/chat",
                                json={
                                    "model": fallback_model,
                                    "messages": [{"role": "user", "content": prompt}],
                                    "stream": False
                                },
                                timeout=300
                            )
                            if fallback_response.status_code == 200:
                                result = fallback_response.json()
                                return result.get('message', {}).get('content', '')
                    else:
                        st.error("No models available in Ollama!")
                        st.info(f"Pull a model first: ollama pull {model_name}")
                else:
                    st.error(f"Ollama API 404 error. Model '{model_name}' may not exist.")
                    st.info(f"Check if Ollama is running and pull the model: ollama pull {model_name}")
            except Exception as e:
                st.error(f"Ollama API 404 error. Model '{model_name}' may not exist.")
                st.info(f"Check if Ollama is running and pull the model: ollama pull {model_name}")
            return None
        else:
            error_msg = response.text if hasattr(response, 'text') else f"Status {response.status_code}"
            st.error(f"Ollama API error: {response.status_code} - {error_msg}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to Ollama. Make sure Ollama is running locally.")
        st.info("Install Ollama from: https://ollama.ai")
        st.info(f"Then start it and pull a model: ollama pull {model_name}")
        return None
    except Exception as e:
        st.error(f"Error calling LLM: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def agentic_evaluate_compliance(rules_text, elements_df, element_type, llm_model, ollama_url):
    import json
    import requests
    import streamlit as st
    
    provider = st.session_state.get('llm_provider', 'Ollama (Local)')
    columns_list = elements_df.columns.tolist()
    
    pdf_language = st.session_state.get('pdf_language', 'German')
    
    system_prompt = f"""You are an expert Building Code Compliance Agent. The rulebook text is written in {pdf_language}.
Your task is to read the building regulations and evaluate if the BIM elements comply.

AVAILABLE RULES EXTRACTED FROM PDF:
=============================================
{rules_text}
=============================================

BIM ELEMENT TYPE: {element_type}
AVAILABLE COLUMNS IN DATASET: {columns_list}
TOTAL ELEMENTS: {len(elements_df)}

INSTRUCTIONS:
1. Read the rules and determine the exact geometric requirement (e.g. min width, max area).
2. Use the 'evaluate_geometric_compliance' tool to execute a pandas query that finds the FAILED elements.
   - For column names with spaces or special characters, you MUST wrap them in backticks in the query string.
   - Example valid queries: `\`Width (mm)\` < 900` or `\`Area (m²)\` > 12.5`
3. After receiving the tool's result, write a beautifully formatted Markdown compliance report summarizing the findings. Include the IDs of the failing elements.
   - If no relevant geometric rules exist for {element_type}, do not call the tool. Just state that no rules apply.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please evaluate all {element_type} elements for compliance."}
    ]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "evaluate_geometric_compliance",
                "description": "Execute a pandas query to filter the BIM dataset for elements that FAIL compliance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pandas_query": {
                            "type": "string",
                            "description": "A valid pandas query string. Example: `\`Width (mm)\` < 900`. Returns the number of failing elements and their GlobalIds."
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Explanation of why this condition was chosen based on the rules."
                        }
                    },
                    "required": ["pandas_query", "reasoning"]
                }
            }
        }
    ]
    
    def execute_tool(tool_call):
        try:
            args = json.loads(tool_call["function"]["arguments"])
            query_str = args.get("pandas_query", "")
            reasoning = args.get("reasoning", "")
            
            # Execute query safely
            failed_df = elements_df.query(query_str)
            if failed_df.empty:
                return f"Tool Execution Success. Reasoning: {reasoning}. Result: 0 elements failed compliance."
            else:
                ids = failed_df['GlobalId'].tolist()
                return f"Tool Execution Success. Reasoning: {reasoning}. Result: {len(failed_df)} elements FAILED compliance. Failing IDs: {ids[:50]} {'... (truncated)' if len(ids)>50 else ''}"
        except Exception as e:
            return f"Error executing pandas query '{query_str}': {e}. Please refine your query string and ensure you use backticks for column names with spaces."

    if provider == "Groq (Cloud Fast)":
        api_key = st.session_state.get('groq_api_key', '')
        if not api_key:
            return "❌ Groq API Key is missing! Please configure it in the sidebar or Streamlit Secrets."
            
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # Max 5 turns to prevent infinite loops
        for turn in range(5):
            data = {"model": llm_model, "messages": messages, "tools": tools, "tool_choice": "auto", "temperature": 0.1}
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=60)
            if response.status_code != 200:
                return f"❌ Groq API Error: {response.text}"
                
            response_json = response.json()
            message = response_json['choices'][0]['message']
            messages.append(message)
            
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    if tool_call["function"]["name"] == "evaluate_geometric_compliance":
                        result_str = execute_tool(tool_call)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": "evaluate_geometric_compliance",
                            "content": result_str
                        })
            else:
                return message["content"]
                
        debug_log = "\\n\\n**Debug Logs:**\\n"
        for m in messages:
            debug_log += f"- **{m['role']}**: {m.get('content') or m.get('tool_calls')}\\n"
        return "❌ Agent exceeded maximum turns without returning a final answer." + debug_log

    else:
        # Ollama logic
        try:
            for turn in range(5):
                data = {"model": llm_model, "messages": messages, "tools": tools, "stream": False}
                response = requests.post(f"{ollama_url}/api/chat", json=data, timeout=120)
                if response.status_code != 200:
                    return f"❌ Ollama API Error: {response.text}"
                    
                response_json = response.json()
                message = response_json.get('message', {})
                messages.append(message)
                
                if message.get("tool_calls"):
                    for tool_call in message["tool_calls"]:
                        if tool_call["function"]["name"] == "evaluate_geometric_compliance":
                            result_str = execute_tool(tool_call)
                            messages.append({
                                "role": "tool",
                                "name": "evaluate_geometric_compliance",
                                "content": result_str
                            })
                else:
                    return message.get("content", "No output generated.")
                    
            debug_log = "\\n\\n**Debug Logs:**\\n"
            for m in messages:
                debug_log += f"- **{m['role']}**: {m.get('content') or m.get('tool_calls')}\\n"
            return "❌ Agent exceeded maximum turns without returning a final answer." + debug_log
        except Exception as e:
            return f"❌ Error communicating with Ollama: {e}"


def extract_rules_from_pdf(pdf_text, model_name="llama3", base_url="http://localhost:11434"):
    """
    Use LLM to extract building code rules from PDF text.
    Processes text in CHUNKS to handle large documents.
    """
    if not pdf_text:
        return None
    
    # Split text into chunks of ~30,000 characters (approx 10-15 pages)
    chunk_size = 30000
    chunks = [pdf_text[i:i + chunk_size] for i in range(0, len(pdf_text), chunk_size)]
    
    all_valid_rules = []
    
    # Progress bar for extraction
    progress_bar = st.progress(0, text="🤖 Starting AI Analysis...")
    
    for i, chunk in enumerate(chunks):
        progress_text = f"🤖 AI is analyzing part {i+1} of {len(chunks)}... ({len(all_valid_rules)} rules found so far)"
        progress_bar.progress((i + 1) / len(chunks), text=progress_text)
        
        prompt = f"""You are a precise building code extraction system. 
The input text contains structured page data and tables from a Building Code Document.

GOAL: Extract THREE types of rules from the text:
1. DIMENSIONAL: Specific numeric requirements (e.g., "900 mm").
2. REGULATORY: References to standards or DIN norms (e.g., "Must comply with DIN 18101").
3. GENERAL: Qualitative rules or provisions (e.g., "Non-built areas must not be unsightly").

CRITICAL INSTRUCTIONS:
- TABLES: Look for rows in 'TABLE DATA' sections for dimensions.
- RULE TYPE: Assign "dimensional" if there is a number/limit, otherwise "general".
- LANGUAGE: Input is German, but 'rule_description' must be in English.
- CONVERSION: For dimensional rules, convert to m, mm, or m².

SCHEMA:
[
  {{
    "element_type": "door" | "window" | "room" | "wall" | "stair" | "slab" | "general",
    "rule_type": "dimensional" | "general",
    "property": "width" | "height" | "area" | "thickness" | "clearance" | "provision",
    "rule_description": "English description of the requirement",
    "min_value": <float or null>,
    "max_value": <float or null>,
    "unit": "mm" | "m" | "m2" | null,
    "reference": "Section/Page label"
  }}
]

INPUT TEXT (PART {i+1}):
{chunk}

OUTPUT ONLY THE JSON ARRAY. DO NOT INCLUDE ANY EXPLANATORY TEXT BEFORE OR AFTER THE JSON."""

        response = call_local_llm(prompt, model_name, base_url)
        if not response:
            continue
            
        try:
            # More robust JSON extraction
            clean_response = response.strip()
            
            # 1. Remove markdown backticks if present
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_response:
                # Find the largest block between backticks
                blocks = re.findall(r'```(?:json)?\s*(.*?)```', clean_response, re.DOTALL)
                if blocks:
                    clean_response = max(blocks, key=len).strip()
                else:
                    clean_response = clean_response.split("```")[1].strip()
            
            # 2. Use regex to find the [ ... ] or { ... } block if it's still buried in text
            json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', clean_response)
            if json_match:
                clean_response = json_match.group(0)
            
            # 3. Last-ditch cleaning for common LLM malformations
            # Replace common invalid characters or trailing commas that break standard json.loads
            clean_response = clean_response.replace('’', "'").replace('‘', "'").replace('”', '"').replace('“', '"')
            # Remove trailing commas before closing brackets
            clean_response = re.sub(r',\s*\]', ']', clean_response)
            clean_response = re.sub(r',\s*\}', '}', clean_response)

            chunk_rules = json.loads(clean_response)

            if isinstance(chunk_rules, dict):
                # Check for dict-as-list
                if all(str(k).isdigit() for k in chunk_rules.keys()) and chunk_rules:
                    chunk_rules = [chunk_rules[k] for k in sorted(chunk_rules.keys(), key=lambda x: int(x))]
                else:
                    # Check for nested list or single object
                    found_list = False
                    for val in chunk_rules.values():
                        if isinstance(val, list):
                            chunk_rules = val
                            found_list = True
                            break
                    if not found_list:
                        chunk_rules = [chunk_rules]

            if isinstance(chunk_rules, list):
                for rule in chunk_rules:
                    # Very permissive validation
                    desc = rule.get('rule_description', '') or rule.get('provision', '')
                    if not desc or len(desc) < 5:
                        continue
                        
                    # Normalize fields
                    rule['rule_description'] = desc
                    rule['rule_type'] = rule.get('rule_type', 'dimensional').lower()
                    
                    # Ensure element_type exists
                    if not rule.get('element_type'):
                        rule['element_type'] = 'general'
                        
                    all_valid_rules.append(rule)
                    
        except Exception as e:
            st.error(f"Error parsing AI response for part {i+1}: {e}")
            continue
            
    # Remove progress bar when done
    progress_bar.empty()
    
    if not all_valid_rules:
        return []
        
    return all_valid_rules


# --- SIDEBAR: RULE CONFIGURATION ---
with st.sidebar:
    st.header("📋 Building Code Compliance")
    st.markdown("Configure global building code rules to automatically check your BIM models.")
    
    if st.button("Log Out", use_container_width=True):
        st.session_state["user_mode"] = None
        st.rerun()
    
    # --- GLOBAL LLM CONFIGURATION ---
    st.markdown("---")
    st.subheader("🤖 AI Agent Configuration")
    
    if st.session_state.get("user_mode") == "admin":
        llm_provider = st.selectbox("Inference Provider", ["Groq (Cloud Fast)", "Ollama (Local)"])
        st.session_state["llm_provider"] = llm_provider
        
        if llm_provider == "Groq (Cloud Fast)":
            groq_api_key = st.text_input("Groq API Key", type="password", value="")
            st.session_state["groq_api_key"] = groq_api_key
            llm_model = st.selectbox("Groq Model", ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "qwen/qwen3-32b"], index=0)
            ollama_url = ""
        else:
            ollama_url = st.text_input("Ollama URL", value="http://localhost:11434", help="Default: http://localhost:11434")
            llm_model = "mistral"
            if not OLLAMA_AVAILABLE:
                st.error("⚠️ Ollama API not available via python.")
            else:
                available_models = get_available_ollama_models(ollama_url)
                if available_models:
                    default_index = 0
                    for preferred in ["llama3", "llama3.1", "mistral", "qwen3.5", "phi4"]:
                        if preferred in available_models:
                            default_index = available_models.index(preferred)
                            break
                    llm_model = st.selectbox("LLM Model (Ollama)", available_models, index=default_index)
                else:
                    st.error("⚠️ No models found in Ollama!")
                    st.info("Pull a model first: ollama pull mistral")
    else:
        user_ai_choice = st.selectbox("AI Model / Mode", [
            "Auto (Standard Reasoning - Fast)", 
            "Advanced (Agentic Tool Calling - Accurate Math)",
            "Claude 3.5 Sonnet (Placeholder)", 
            "GPT-4o (Placeholder)"
        ])
        
        # Set evaluation mode based on user's choice
        if user_ai_choice.startswith("Advanced"):
            st.session_state["eval_mode"] = "Advanced"
        else:
            st.session_state["eval_mode"] = "Standard"
            
        llm_provider = "Groq (Cloud Fast)"
        groq_api_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
        st.session_state["groq_api_key"] = groq_api_key
        st.session_state["llm_provider"] = llm_provider
        llm_model = "llama-3.1-8b-instant"
        ollama_url = ""
    
    # Only show the explicit radio button to Admins
    if st.session_state.get("user_mode") == "admin":
        st.markdown("---")
        st.subheader("⚙️ Evaluation Mode")
        eval_mode = st.radio(
            "Select Agent Behavior",
            ["Standard (Fast & Low Token)", "Advanced (Agentic Python Reasoning)"],
            help="Standard mode uses pure LLM reasoning. Advanced mode writes and executes Python code for 100% mathematical accuracy."
        )
        st.session_state["eval_mode"] = eval_mode
    
    st.markdown("---")
    # Rule source selection
    rule_source = st.radio(
        "Rule Source",
        ["Upload PDF Rule Book (Smart RAG Ingestion)", "Manual Configuration"],
        help="Choose to upload a PDF and index it with Smart RAG, or configure manually"
    )
    
    # Enable/disable compliance checking
    enable_compliance = st.checkbox("Enable Compliance Checking", value=True)
    
    if enable_compliance:
        compliance_rules = None
    
        if rule_source == "Upload PDF Rule Book (Smart RAG Ingestion)":
            st.markdown("---")
            st.subheader("📄 Upload Rule Book PDF")
        
            if not PDF_AVAILABLE:
                st.error("⚠️ PDF processing not available. Install with: pip install pdfplumber")
            else:
                pdf_language = st.selectbox(
                    "Rule Book Language", 
                    ["German", "English", "French", "Spanish", "Dutch", "Italian"],
                    index=0,
                    help="Select the language of the uploaded PDF to optimize AI retrieval."
                )
                st.session_state["pdf_language"] = pdf_language
                
                uploaded_pdf = st.file_uploader(
                    "Upload Rule Book PDF",
                    type=["pdf"],
                    help="Upload any building code rule book or standard in PDF format"
                )
            
                if uploaded_pdf is not None:
                    # RAG Database initialization function
                    def get_rulebook_collection():
                        chroma_client = chromadb.PersistentClient(path="./rules_db")
                        default_ef = embedding_functions.DefaultEmbeddingFunction()
                        return chroma_client.get_or_create_collection(name="rulebook_reference", embedding_function=default_ef), chroma_client
                    
                    if st.button("🧠 Ingest", type="primary", key="ingest_rag_btn"):
                        with st.spinner("Processing PDF with Smart Chunking..."):
                            # Save temp file
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(uploaded_pdf.getvalue())
                                tmp_path = tmp.name
                            
                            try:
                                chunks = smart_chunk_pdf(tmp_path, source_name=uploaded_pdf.name)
                            
                                if chunks:
                                    if st.session_state.get("user_mode") == "admin":
                                        st.info(f"Generated {len(chunks)} smart chunks. Vectorizing...")
                                    coll, client = get_rulebook_collection()
                                
                                    # Clear old collection
                                    try:
                                        client.delete_collection(name="rulebook_reference")
                                        coll, _ = get_rulebook_collection()
                                    except: pass
                                
                                    ids = [c["id"] for c in chunks]
                                    docs = [c["text"] for c in chunks]
                                    metas = [c["metadata"] for c in chunks]
                                
                                    # Batch add
                                    batch_size = 100
                                    for i in range(0, len(ids), batch_size):
                                        coll.add(
                                            ids=ids[i:i+batch_size],
                                            documents=docs[i:i+batch_size],
                                            metadatas=metas[i:i+batch_size]
                                        )
                                    if st.session_state.get("user_mode") == "admin":
                                        st.success("✅ RAG Database updated successfully! You can now use the Agent to check elements.")
                                    else:
                                        st.success("✅ Database updated")
                                    st.session_state['rag_ingested'] = True
                                else:
                                    st.error("No chunks extracted from PDF.")
                            finally:
                                os.remove(tmp_path)
                        
                    try:
                        coll, _ = get_rulebook_collection()
                        if coll.count() > 0:
                            if st.session_state.get("user_mode") == "admin":
                                st.success(f"📚 RAG DB active ({coll.count()} chunks stored).")
                    except Exception:
                        pass
    
        elif rule_source == "Manual Configuration":
            st.markdown("---")
            st.subheader("Manual Rule Configuration")
        
            st.markdown("---")
            st.subheader("Door Requirements")
        
            # Minimum door width for barrier-free access
            min_door_width = st.number_input(
                "Minimum Door Width (mm)",
                min_value=0,
                max_value=5000,
                value=900,
                step=50,
                help="Set to minimum required (e.g. 900 mm for barrier-free access)"
            )
        
            # Minimum door height
            min_door_height = st.number_input(
                "Minimum Door Height (mm)",
                min_value=0,
                max_value=5000,
                value=2000,
                step=50,
                help="Standard minimum door height"
            )
        
            st.markdown("---")
            st.subheader("Window Requirements")
        
            # Minimum window dimensions
            min_window_width = st.number_input(
                "Minimum Window Width (mm)",
                min_value=0,
                max_value=5000,
                value=0,
                step=50,
                help="Set to 0 to disable window width checking"
            )
        
            min_window_height = st.number_input(
                "Minimum Window Height (mm)",
                min_value=0,
                max_value=5000,
                value=0,
                step=50,
                help="Set to 0 to disable window height checking"
            )
        
            st.markdown("---")
            st.subheader("Space/Room Requirements")
        
            # Minimum room area
            min_room_area = st.number_input(
                "Minimum Room Area (m²)",
                min_value=0.0,
                max_value=1000.0,
                value=0.0,
                step=0.5,
                help="Set to 0 to disable room area checking"
            )
        
            # Minimum room height
            min_room_height = st.number_input(
                "Minimum Room Height (m)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.1,
                help="Set to 0 to disable room height checking"
            )
        
            st.markdown("---")
            st.subheader("Wall Requirements")
        
            # Minimum wall thickness
            min_wall_thickness = st.number_input(
                "Minimum Wall Thickness (mm)",
                min_value=0,
                max_value=1000,
                value=0,
                step=10,
                help="Set to 0 to disable wall thickness checking"
            )
        
            # Store rules in session state
            compliance_rules = {
                'min_door_width': min_door_width,
                'min_door_height': min_door_height,
                'min_window_width': min_window_width,
                'min_window_height': min_window_height,
                'min_room_area': min_room_area,
                'min_room_height': min_room_height,
                'min_wall_thickness': min_wall_thickness
            }
    
        # Use extracted rules if available, otherwise use manual rules
        if compliance_rules is None and 'extracted_rules' in st.session_state:
            compliance_rules = st.session_state['extracted_rules']
    else:
        compliance_rules = None

st.title("🏗️ Smart Building Compliance Checker")
st.markdown("##### Upload your **IFC file** to automatically view its elements, evaluate compliance rules, and query the AI agent.")
st.divider()

# --- UPLOAD SECTION ---
uploaded_file = st.file_uploader("Upload your IFC model (.ifc)", type=["ifc"])

if uploaded_file is not None:
    # Save the uploaded file to a temp file to pass it to ifcopenshell
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    st.success(f"✅ Model loaded successfully! Analyzing elements...")

    # --- PROCESSING ---
    try:
        # Step 1: Open and parse the IFC file using ifcopenshell
        model = ifcopenshell.open(tmp_path)
        
        # Step 2: Extract ALL product elements from the model
        # IfcProduct is the base class for all physical building elements
        # This gets walls, doors, slabs, beams, columns, spaces, etc.
        all_products = model.by_type("IfcProduct")
        st.info(f"Found {len(all_products)} product elements in the project.")

        # --- STATISTICS ---
        # Step 3: Get the actual type of each element (e.g., "IfcWall", "IfcDoor")
        # is_a() returns the IFC class name
        element_types = [product.is_a() for product in all_products]
        # Step 4: Count how many of each type we have
        type_counts = Counter(element_types)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Elements", len(all_products))
        with col2:
            st.metric("Element Types", len(type_counts))
        with col3:
            most_common_type, most_common_count = type_counts.most_common(1)[0]
            st.metric("Most Common Type", f"{most_common_type} ({most_common_count})")

        # --- ELEMENT DETAILS ---
        st.markdown("---")
        st.subheader("📋 All Elements")
        
        # Search/filter
        search_term = st.text_input("🔍 Search elements by type or name", "", key="search_elements_input")
        
        # Helper function to search for a value in multiple sources
        def find_property_value(product, prop_names, multiplier=1.0, unit_suffix=""):
            """
            Search for a property value in 3 places (in order of priority):
            1. Geometry (direct attributes)
            2. Property Sets (Psets)
            3. Quantities (Qto)
            
            Returns the first found value, or None
            """
            # 1. Try Geometry (direct attributes)
            for prop_name in prop_names:
                if hasattr(product, prop_name):
                    value = getattr(product, prop_name, None)
                    if value is not None:
                        try:
                            return float(value) * multiplier
                        except:
                            pass
            
            # 2. Try Property Sets (Psets)
            try:
                psets = get_psets(product)
                for pset_name, pset_props in psets.items():
                    for prop_name in prop_names:
                        if prop_name in pset_props:
                            value = pset_props[prop_name]
                            if value is not None:
                                try:
                                    return float(value) * multiplier
                                except:
                                    pass
            except:
                pass
            
            # 3. Try Quantities (Qto) - quantities are often in property sets starting with Qto_
            try:
                qtos = get_qto(product)
                if qtos:  # Only proceed if we got quantities
                    for qto_name, qto_props in qtos.items():
                        for prop_name in prop_names:
                            if prop_name in qto_props:
                                value = qto_props[prop_name]
                                if value is not None:
                                    try:
                                        return float(value) * multiplier
                                    except:
                                        pass
            except:
                pass
            
            return None
        
        # Helper function to extract geometric properties
        def _get_geometric_properties(product, element_type):
            """
            Extract geometric information based on element type.
            Searches in 3 places: Geometry → Psets → Quantities
            """
            geom = {}
            
            # DOOR properties
            if "IfcDoor" in element_type:
                width = find_property_value(product, ['OverallWidth', 'Width', 'NominalWidth'], 1000.0)
                if width:
                    geom['Width (mm)'] = f"{width:.0f}"
                
                height = find_property_value(product, ['OverallHeight', 'Height', 'NominalHeight'], 1000.0)
                if height:
                    geom['Height (mm)'] = f"{height:.0f}"
            
            # WINDOW properties
            elif "IfcWindow" in element_type:
                width = find_property_value(product, ['OverallWidth', 'Width', 'NominalWidth'], 1000.0)
                if width:
                    geom['Width (mm)'] = f"{width:.0f}"
                
                height = find_property_value(product, ['OverallHeight', 'Height', 'NominalHeight'], 1000.0)
                if height:
                    geom['Height (mm)'] = f"{height:.0f}"
            
            # SPACE/ROOM properties (Area and Volume)
            elif "IfcSpace" in element_type:
                # Try multiple area property names
                area = find_property_value(product, [
                    'GrossFloorArea', 'NetFloorArea', 'Area', 'FloorArea',
                    'GrossArea', 'NetArea', 'BaseArea'
                ], 1.0)
                if area:
                    geom['Area (m²)'] = f"{area:.2f}"
                
                # Try multiple volume property names
                volume = find_property_value(product, [
                    'GrossVolume', 'NetVolume', 'Volume', 'EnclosedVolume',
                    'GrossVolume', 'NetVolume'
                ], 1.0)
                if volume:
                    geom['Volume (m³)'] = f"{volume:.2f}"
            
            # WALL properties (Thickness, Length, Height)
            elif "IfcWall" in element_type:
                thickness = find_property_value(product, [
                    'Thickness', 'WallThickness', 'NominalThickness', 'Width'
                ], 1000.0)
                if thickness:
                    geom['Thickness (mm)'] = f"{thickness:.0f}"
                
                length = find_property_value(product, [
                    'Length', 'WallLength', 'NominalLength'
                ], 1.0)
                if length:
                    geom['Length (m)'] = f"{length:.2f}"
                
                height = find_property_value(product, [
                    'Height', 'WallHeight', 'NominalHeight'
                ], 1.0)
                if height:
                    geom['Height (m)'] = f"{height:.2f}"
            
            # SLAB properties (Thickness, Area, Length, Width)
            elif "IfcSlab" in element_type:
                thickness = find_property_value(product, [
                    'Thickness', 'SlabThickness', 'NominalThickness', 'Depth'
                ], 1000.0)
                if thickness:
                    geom['Thickness (mm)'] = f"{thickness:.0f}"
                
                area = find_property_value(product, [
                    'Area', 'SlabArea', 'GrossArea', 'NetArea', 'BaseArea'
                ], 1.0)
                if area:
                    geom['Area (m²)'] = f"{area:.2f}"
                
                length = find_property_value(product, [
                    'Length', 'SlabLength', 'NominalLength'
                ], 1.0)
                if length:
                    geom['Length (m)'] = f"{length:.2f}"
                
                width = find_property_value(product, [
                    'Width', 'SlabWidth', 'NominalWidth'
                ], 1.0)
                if width:
                    geom['Width (m)'] = f"{width:.2f}"
            
            # BEAM properties (Length, Width, Height, Depth)
            elif "IfcBeam" in element_type:
                length = find_property_value(product, [
                    'Length', 'BeamLength', 'NominalLength'
                ], 1.0)
                if length:
                    geom['Length (m)'] = f"{length:.2f}"
                
                width = find_property_value(product, [
                    'Width', 'BeamWidth', 'NominalWidth', 'FlangeWidth'
                ], 1000.0)
                if width:
                    geom['Width (mm)'] = f"{width:.0f}"
                
                height = find_property_value(product, [
                    'Height', 'BeamHeight', 'NominalHeight', 'Depth', 'FlangeThickness'
                ], 1000.0)
                if height:
                    geom['Height (mm)'] = f"{height:.0f}"
            
            # COLUMN properties (Width, Height, Depth, CrossSectionArea)
            elif "IfcColumn" in element_type:
                width = find_property_value(product, [
                    'Width', 'ColumnWidth', 'NominalWidth', 'Diameter', 'CrossSectionWidth'
                ], 1000.0)
                if width:
                    geom['Width (mm)'] = f"{width:.0f}"
                
                height = find_property_value(product, [
                    'Height', 'ColumnHeight', 'NominalHeight', 'Length'
                ], 1.0)
                if height:
                    geom['Height (m)'] = f"{height:.2f}"
                
                depth = find_property_value(product, [
                    'Depth', 'ColumnDepth', 'NominalDepth', 'CrossSectionDepth'
                ], 1000.0)
                if depth:
                    geom['Depth (mm)'] = f"{depth:.0f}"
                
                area = find_property_value(product, [
                    'CrossSectionArea', 'Area', 'BaseArea'
                ], 1.0)
                if area:
                    geom['CrossSection Area (m²)'] = f"{area:.4f}"
            
            # STAIR properties
            elif "IfcStair" in element_type or "IfcStairFlight" in element_type:
                width = find_property_value(product, [
                    'Width', 'StairWidth', 'NominalWidth'
                ], 1.0)
                if width:
                    geom['Width (m)'] = f"{width:.2f}"
                
                height = find_property_value(product, [
                    'Height', 'RiseHeight', 'TotalRiseHeight'
                ], 1.0)
                if height:
                    geom['Height (m)'] = f"{height:.2f}"
                
                length = find_property_value(product, [
                    'Length', 'StairLength', 'NominalLength', 'RunLength'
                ], 1.0)
                if length:
                    geom['Length (m)'] = f"{length:.2f}"
            
            # ROOF properties
            elif "IfcRoof" in element_type:
                area = find_property_value(product, [
                    'Area', 'RoofArea', 'GrossArea', 'NetArea'
                ], 1.0)
                if area:
                    geom['Area (m²)'] = f"{area:.2f}"
            
            return geom
            
        def get_all_properties(product, element_type):
            """Extracts base geometric properties, then dynamically appends all Pset/Qto properties."""
            geom = _get_geometric_properties(product, element_type)
            
            # Extract arbitrary properties from Psets
            try:
                psets = get_psets(product)
                for pset_name, pset_props in psets.items():
                    for prop_name, value in pset_props.items():
                        if value is not None and str(value).strip() != "":
                            # Avoid overwriting standardized geometric properties
                            if prop_name not in geom and not any(prop_name in k for k in geom.keys()):
                                # Filter out some internal IFC garbage properties
                                if prop_name.lower() not in ['id', 'globalid', 'ownerhistory', 'objectplacement', 'representation']:
                                    geom[prop_name] = str(value)
            except:
                pass
                
            # Extract arbitrary quantities from Qto
            try:
                qtos = get_qto(product)
                if qtos:
                    for qto_name, qto_props in qtos.items():
                        for prop_name, value in qto_props.items():
                            if value is not None and str(value).strip() != "":
                                if prop_name not in geom and not any(prop_name in k for k in geom.keys()):
                                    geom[prop_name] = str(value)
            except:
                pass
                
            return geom
        
        # Helper function to extract numeric value from formatted string
        def extract_numeric_value(formatted_str):
            """Extract numeric value from formatted string like '900.0' or '25.50 m²'"""
            if not formatted_str or formatted_str == "-":
                return None
            try:
                # Remove units and extract number - match number (with optional decimal)
                match = re.search(r'([\d.]+)', str(formatted_str))
                if match:
                    return float(match.group(1))
            except:
                pass
            return None
        
        # Helper function to check compliance with NBauO rules
        def check_compliance(element_data, element_type, geometric_props, rules):
            """Check if element complies with configured building code rules"""
            violations = []
            status = "✅ Pass"
            
            if not rules:
                return status, violations
            
            # Handle both old format (dict) and new format (list of rule objects)
            if isinstance(rules, dict):
                # Old format - convert to new format for processing
                rules_list = []
                if 'min_door_width' in rules:
                    rules_list.append({
                        'element_type': 'door',
                        'property': 'width',
                        'min_value': rules.get('min_door_width'),
                        'unit': 'mm'
                    })
                if 'min_door_height' in rules:
                    rules_list.append({
                        'element_type': 'door',
                        'property': 'height',
                        'min_value': rules.get('min_door_height'),
                        'unit': 'mm'
                    })
                # Add other old format rules...
                rules = rules_list
            elif not isinstance(rules, list):
                return status, violations
            
            # Map IFC element types to rule element types
            element_type_map = {
                'IfcDoor': 'door',
                'IfcWindow': 'window',
                'IfcSpace': 'room',
                'IfcWall': 'wall',
                'IfcStair': 'stair',
                'IfcStairFlight': 'stair',
                'IfcCorridor': 'corridor'
            }
            
            # Get the rule element type for this IFC element
            rule_elem_type = None
            for ifc_type, rule_type in element_type_map.items():
                if ifc_type in element_type:
                    rule_elem_type = rule_type
                    break
            
            if not rule_elem_type:
                return status, violations  # No matching rule type
            
            # Check all applicable rules
            for rule in rules:
                rule_elem = rule.get('element_type', '').lower()
                rule_prop = rule.get('property', '').lower()
                
                # Check if this rule applies to this element type
                if rule_elem != rule_elem_type:
                    continue
                
                # Map property names to geometric property keys
                prop_mapping = {
                    'width': ['Width (mm)', 'Width (m)'],
                    'height': ['Height (mm)', 'Height (m)'],
                    'area': ['Area (m²)'],
                    'thickness': ['Thickness (mm)'],
                    'length': ['Length (m)'],
                    'volume': ['Volume (m³)']
                }
                
                # Get the geometric property key for this rule property
                geom_keys = prop_mapping.get(rule_prop, [])
                if not geom_keys:
                    continue  # Unknown property type
                
                # Find the value in geometric properties
                element_value = None
                for key in geom_keys:
                    if key in geometric_props:
                        element_value = extract_numeric_value(geometric_props[key])
                        if element_value is not None:
                            break
                
                if element_value is None:
                    continue  # No value found for this property
                
                # Convert units if needed
                rule_unit = rule.get('unit', '').lower()
                rule_min = rule.get('min_value')
                rule_max = rule.get('max_value')
                
                # Convert element value to rule unit if needed
                if rule_unit == 'mm' and 'm)' in str(geom_keys[0]):
                    element_value = element_value * 1000  # Convert m to mm
                elif rule_unit in ['m', 'm²', 'm³'] and 'mm' in str(geom_keys[0]):
                    element_value = element_value / 1000  # Convert mm to m
                
                # Check minimum value
                if rule_min is not None:
                    if element_value < rule_min:
                        rule_desc = rule.get('rule_description', f"{rule_prop} requirement")
                        violations.append(f"{rule_desc}: {element_value:.2f} {rule_unit} < minimum {rule_min} {rule_unit}")
                        status = "❌ VIOLATION"
                
                # Check maximum value
                if rule_max is not None:
                    if element_value > rule_max:
                        rule_desc = rule.get('rule_description', f"{rule_prop} requirement")
                        violations.append(f"{rule_desc}: {element_value:.2f} {rule_unit} > maximum {rule_max} {rule_unit}")
                        status = "❌ VIOLATION"
            
            return status, violations
        
        # Step 5: Extract properties from each element
        results = []
        for product in all_products:
            # Get the IFC class type (e.g., "IfcWall", "IfcDoor", "IfcSlab")
            element_type = product.is_a()
            
            # Extract Name property (human-readable identifier)
            name = product.Name if hasattr(product, 'Name') and product.Name else "Unnamed"
            
            # Extract GlobalId (unique GUID identifier)
            global_id = product.GlobalId if hasattr(product, 'GlobalId') else ""
            
            # Extract Tag (optional identifier/label)
            tag = ""
            if hasattr(product, 'Tag') and product.Tag:
                tag = product.Tag
            
            # Extract Level/Storey (which floor the element is on)
            # This uses the ContainedInStructure relationship
            level = "Unknown"
            try:
                if hasattr(product, 'ContainedInStructure') and product.ContainedInStructure:
                    # Navigate the relationship to get the building storey name
                    level = product.ContainedInStructure[0].RelatingStructure.Name
            except:
                pass
            
            # Step 6: Extract ALL properties (geometric + dynamic Psets/Qtos)
            geometric_props = get_all_properties(product, element_type)
            
            # Step 7: Check compliance with NBauO rules (if enabled)
            compliance_status = "N/A"
            compliance_violations = []
            if enable_compliance and compliance_rules:
                compliance_status, compliance_violations = check_compliance(
                    None, element_type, geometric_props, compliance_rules
                )
            
            # Step 8: Apply search filter (if user entered search term)
            if search_term:
                search_lower = search_term.lower()
                # Skip element if search term doesn't match type, name, or globalId
                if (search_lower not in element_type.lower() and 
                    search_lower not in name.lower() and
                    search_lower not in global_id.lower()):
                    continue  # Skip this element
            
            # Step 9: Add element data to results list
            element_data = {
                "Type": element_type,
                "Name": name,
                "GlobalId": global_id,
                "Tag": tag if tag else "-",
                "Level": level
            }
            
            # Add geometric properties to the element data
            element_data.update(geometric_props)
            
            # Add compliance information
            if enable_compliance and compliance_rules:
                element_data["Compliance Status"] = compliance_status
                if compliance_violations:
                    element_data["Violations"] = "; ".join(compliance_violations)
            
            results.append(element_data)

        # Step 10: Convert results list to pandas DataFrame for easy manipulation
        if results:
            df = pd.DataFrame(results)
            
            # Show compliance summary if enabled and rules exist
            if enable_compliance and 'Compliance Status' in df.columns and compliance_rules:
                violations_df = df[df['Compliance Status'] == '❌ VIOLATION']
                if len(violations_df) > 0:
                    st.error(f"⚠️ **{len(violations_df)} Compliance Violations Found**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(
                            violations_df[['Type', 'Name', 'Level', 'Compliance Status', 'Violations']],
                            use_container_width=True,
                            hide_index=True
                        )
                    with col2:
                        # Violations by type
                        violation_types = violations_df['Type'].value_counts()
                        st.write("**Violations by Element Type:**")
                        for vtype, count in violation_types.items():
                            st.write(f"- {vtype}: {count}")
                else:
                    st.success("✅ **All elements comply with configured manual rules!**")
                st.markdown("---")
            elif rule_source == "Upload PDF Rule Book (Smart RAG Ingestion)":
                st.info("💡 **Smart RAG Mode Active:** Expand the element groups below and use the '🔍 Agent: DB Search' buttons to evaluate elements directly against the building code.")
                st.markdown("---")
            
            # Step 11: Group elements by type and display
            st.markdown(f"**Showing {len(results)} elements** (filtered from {len(all_products)} total)")
            
            # Get all unique element types and sort them alphabetically
            # Then for each type, filter the DataFrame and display in an expandable section
            for element_type in sorted(df["Type"].unique()):
                # Filter DataFrame to show only elements of this type
                # Example: type_df contains only "IfcDoor" elements
                type_df = df[df["Type"] == element_type]
                type_df = type_df.dropna(axis=1, how='all')
                
                    # Display in a collapsible expander section
                with st.expander(f"🔹 {element_type} ({len(type_df)} elements)", expanded=False):
                    # Reorder columns to show geometric info prominently
                    base_cols = ["Type", "Name", "GlobalId", "Tag", "Level"]
                    if enable_compliance and 'Compliance Status' in type_df.columns:
                        base_cols.append("Compliance Status")
                    if enable_compliance and 'Violations' in type_df.columns:
                        base_cols.append("Violations")
                    geom_cols = [col for col in type_df.columns if col not in base_cols]
                    display_cols = base_cols + geom_cols
                    display_cols = [col for col in display_cols if col in type_df.columns]
                    
                    # Highlight violations in the dataframe
                    if enable_compliance and 'Compliance Status' in type_df.columns:
                        # Show violations first
                        violations_in_type = type_df[type_df['Compliance Status'] == '❌ VIOLATION']
                        if len(violations_in_type) > 0:
                            st.warning(f"⚠️ {len(violations_in_type)} violation(s) in this type")
                            st.dataframe(
                                violations_in_type[display_cols],
                                use_container_width=True,
                                hide_index=True
                            )
                            st.markdown("**All elements:**")
                    
                    st.dataframe(
                        type_df[display_cols],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # --- NEW DYNAMIC RAG EVALUATION ---
                    st.markdown("---")
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        rag_btn = st.button(f"🔍 Agent: DB Search", key=f"rag_search_{element_type}", help=f"Search database for {element_type} rules")
                    
                    if rag_btn or st.session_state.get(f"rag_visible_{element_type}", False):
                        st.session_state[f"rag_visible_{element_type}"] = True
                        
                        try:
                            # 1. Direct fetch from ChromaDB
                            chroma_client = chromadb.PersistentClient(path="./rules_db")
                            default_ef = embedding_functions.DefaultEmbeddingFunction()
                            coll = chroma_client.get_collection(name="rulebook_reference", embedding_function=default_ef)
                            
                            # --- AGENTIC QUERY GENERATION ---
                            if f"rag_query_{element_type}" not in st.session_state:
                                with st.spinner("Agent is generating optimal search query..."):
                                    pdf_lang = st.session_state.get('pdf_language', 'German')
                                    query_prompt = f"I need to search a {pdf_lang} building code document for regulations applying to the BIM element type '{element_type}'. Please generate a highly enriched search query string in {pdf_lang} containing architectural synonyms and regulatory concepts that apply to this element. Provide ONLY the search string in {pdf_lang}, nothing else."
                                    generated_query = call_local_llm(query_prompt, llm_model, ollama_url).strip()
                                    
                                    # Fallback if LLM fails
                                    if not generated_query or len(generated_query) < 5:
                                        if pdf_lang == "German":
                                            generated_query = f"Anforderungen, Abmessungen, Maße, Regeln, Brandschutz für {element_type.replace('Ifc', '')}"
                                        else:
                                            generated_query = f"Requirements, dimensions, rules, fire safety for {element_type.replace('Ifc', '')}"
                                        
                                    st.session_state[f"rag_query_{element_type}"] = generated_query
                            
                            query_str = st.session_state[f"rag_query_{element_type}"]
                            if st.session_state.get("user_mode") == "admin":
                                st.caption(f"🧠 *Agent Query:* `{query_str}`")
                            
                            results = coll.query(query_texts=[query_str], n_results=4)
                            
                            st.markdown(f"**📖 Found top 4 references for {element_type} in Rule Book:**")
                            for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                                with st.container(border=True):
                                    st.caption(f"**[{meta.get('chunk_type', '?').upper()}]** Page {meta.get('page', '?')}")
                                    st.markdown(doc)
                                    
                            if st.button(f"🧠 AI Evaluate {len(type_df)} {element_type}(s)", key=f"rag_eval_{element_type}", type="primary"):
                                with st.spinner("Agent is evaluating rules against your IFC geometry..."):
                                    # Create the massive string for the prompt
                                    rules_text = "\n\n".join(results['documents'][0])
                                    
                                    if st.session_state.get("eval_mode", "").startswith("Advanced"):
                                        response = agentic_evaluate_compliance(rules_text, type_df, element_type, llm_model, ollama_url)
                                    else:
                                        elements_csv = type_df[display_cols].to_csv(index=False)
                                        prompt = f"""You are a Building Code Compliance Engineer.
Evaluate if the following {element_type} element complies with the building code.
AVAILABLE RULES EXTRACTED FROM PDF:
=============================================
{rules_text}
=============================================

IFC ELEMENTS FROM BIM MODEL ({element_type}):
=============================================
{elements_csv}
=============================================

YOUR TASK:
1. Examine the available rules specifically looking for geometric limits. If there are NO relevant rules, clearly state "No rules found."
2. Evaluate each IFC element against the rules.
3. List the elements that FAIL compliance.
4. Be mathematically precise.

Respond with a beautifully formatted Markdown compliance report."""
                                        response = call_local_llm(prompt, llm_model, ollama_url)
                                        
                                    if response:
                                        st.session_state[f"rag_report_{element_type}"] = response
                                        st.success("Evaluation complete.")
                        except Exception as e:
                            st.warning(f"Could not connect to or query RAG database. Please ingest the PDF first. ({e})")
                            
                    # Show report if it exists
                    if st.session_state.get(f"rag_report_{element_type}"):
                        st.info("🤖 **Agent Evaluation Report:**")
                        st.markdown(st.session_state[f"rag_report_{element_type}"])
            
            # Also show full table option
            st.markdown("---")
            st.subheader("📊 Complete Element List")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Show geometric summary for specific element types
            st.markdown("---")
            st.subheader("📐 Geometric Summary")
            
            # Door dimensions summary
            if "IfcDoor" in df["Type"].values:
                doors_df = df[df["Type"].str.contains("IfcDoor", na=False)]
                if "Width (mm)" in doors_df.columns:
                    door_widths = doors_df["Width (mm)"].dropna()
                    door_widths = door_widths[door_widths != "-"]
                    if len(door_widths) > 0:
                        # Extract numeric values (remove " mm" if present)
                        widths_numeric = []
                        for w in door_widths:
                            try:
                                w_clean = str(w).replace(" mm", "").strip()
                                widths_numeric.append(float(w_clean))
                            except:
                                pass
                        
                        if widths_numeric:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Doors with Width", len(widths_numeric))
                            with col2:
                                avg_width = sum(widths_numeric) / len(widths_numeric)
                                st.metric("Avg Door Width", f"{avg_width:.0f} mm")
                            with col3:
                                min_width = min(widths_numeric)
                                max_width = max(widths_numeric)
                                st.metric("Width Range", f"{min_width:.0f} - {max_width:.0f} mm")
            
            # Space/Room area summary
            if "IfcSpace" in df["Type"].values:
                spaces_df = df[df["Type"].str.contains("IfcSpace", na=False)]
                if "Area (m²)" in spaces_df.columns:
                    areas = spaces_df["Area (m²)"].dropna()
                    areas = areas[areas != "-"]
                    if len(areas) > 0:
                        # Extract numeric values (remove " m²" if present)
                        areas_numeric = []
                        for a in areas:
                            try:
                                a_clean = str(a).replace(" m²", "").strip()
                                areas_numeric.append(float(a_clean))
                            except:
                                pass
                        
                        if areas_numeric:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Spaces with Area", len(areas_numeric))
                            with col2:
                                total_area = sum(areas_numeric)
                                st.metric("Total Area", f"{total_area:.2f} m²")
                            with col3:
                                avg_area = sum(areas_numeric) / len(areas_numeric)
                                st.metric("Avg Space Area", f"{avg_area:.2f} m²")
        else:
            st.warning("No elements found matching your search criteria.")

        # --- TYPE SUMMARY ---
        st.markdown("---")
        st.subheader("📈 Element Type Summary")
        type_summary = pd.DataFrame([
            {"Type": k, "Count": v} 
            for k, v in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        ])
        st.dataframe(type_summary, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Error reading IFC file: {str(e)}")
        st.exception(e)
    
    finally:
        # Cleanup temp file
        try:
            os.remove(tmp_path)
        except:
            pass

        # --- NEW CONTEXT AWARE CHAT UI ---
        st.markdown("---")
        st.subheader("💬 Building Code Compliance Agent Chat")
        st.markdown("Ask contextual questions about your evaluated elements or the building code!")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
        # Accept user input
        if prompt := st.chat_input("E.g., Why did my doors fail the width check?"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Show user message
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Agent processes the prompt
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🧠 Thinking and gathering context...")
                
                # 1. Gather Context from Active BIM Reports
                active_reports = []
                for key in st.session_state.keys():
                    if key.startswith("rag_report_"):
                        elem = key.replace("rag_report_", "")
                        active_reports.append(f"Report for {elem}:\n{st.session_state[key]}")
                
                reports_context = "\n\n".join(active_reports) if active_reports else "No active elements evaluated yet."
                
                # 2. Gather Context from Building Code Database via RAG
                rag_context = "No building code available. Did you ingest the PDF?"
                try:
                    import chromadb
                    from chromadb.utils import embedding_functions
                    chroma_client = chromadb.PersistentClient(path="./rules_db")
                    default_ef = embedding_functions.DefaultEmbeddingFunction()
                    coll = chroma_client.get_collection(name="rulebook_reference", embedding_function=default_ef)
                    results = coll.query(query_texts=[prompt], n_results=3)
                    if results and results['documents'] and results['documents'][0]:
                        rag_context = "\n\n".join(results['documents'][0])
                except Exception:
                    pass
                
                # 3. Build the sophisticated system prompt
                import requests
                
                pdf_lang = st.session_state.get('pdf_language', 'German')
                system_prompt = f"""You are a {pdf_lang} Building Code Expert & BIM Consultant.
You are helping the user understand their building model compliance according to the rule book.

--- CONTEXT 1: CURRENT BIM EVALUATION REPORTS ---
The user has evaluated some elements in their model. Here are the active reports:
{reports_context}

--- CONTEXT 2: RELEVANT BUILDING CODE SECTIONS ---
Here are sections from the rule book relevant to the user's question:
{rag_context}
--------------------------------------------------

Answer the user's question directly and concisely without sounding robotic. Reference the building code exact values and elements from the context."""

                # Format payload for Ollama
                messages = [{"role": "system", "content": system_prompt}]
                # Inject full chat history
                messages.extend([m for m in st.session_state.messages if m["role"] != "system"])
                
                payload = {
                    "model": llm_model,
                    "messages": messages,
                    "stream": False
                }
                
                try:
                    if st.session_state.get('llm_provider') == "Groq (Cloud Fast)":
                        headers = {
                            "Authorization": f"Bearer {st.session_state.get('groq_api_key', '')}",
                            "Content-Type": "application/json"
                        }
                        res = requests.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers=headers,
                            json={"model": llm_model, "messages": messages, "temperature": 0.3},
                            timeout=60
                        )
                        if res.status_code == 200:
                            full_response = res.json()['choices'][0]['message']['content']
                            message_placeholder.markdown(full_response)
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                        else:
                            error_msg = f"Groq API Error {res.status_code}: {res.text}"
                            message_placeholder.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    else:
                        res = requests.post(f"{ollama_url}/api/chat", json=payload)
                        if res.status_code == 200:
                            full_response = res.json().get("message", {}).get("content", "Error: No content returned")
                            message_placeholder.markdown(full_response)
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                        else:
                            error_msg = f"API Error {res.status_code}: {res.text}"
                            message_placeholder.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    error_msg = f"Connection Error: {e}"
                    message_placeholder.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

else:
    st.info("👆 Please upload an IFC file to get started...")

