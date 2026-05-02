import os
import chromadb
from chromadb.utils import embedding_functions
from rag_utils import smart_chunk_pdf
import requests

def call_local_llm(prompt: str, model_name: str = "mistral", base_url: str = "http://localhost:11434") -> str:
    try:
        response = requests.post(f"{base_url}/api/generate", json={
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        })
        return response.json().get('response', '')
    except Exception as e:
        return f"Error: {e}"

def test_rag_retrieval():
    pdf_path = r"E:\check-my\archi\files\BIM-Vorgaben-Anlage-A-V-3-0-data.pdf"
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
        
    print("2. Using existing temporary ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="./test_bim_db_tmp")
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    coll = chroma_client.get_collection(name="test_reference", embedding_function=default_ef)
    
    test_elements = ["IfcWall"]
    
    for element_type in test_elements:
        print(f"\n{'='*50}\nTESTING ELEMENT: {element_type}\n{'='*50}")
        print(f"3. Asking Agent to generate query for {element_type}...")
        query_prompt = f"I need to search a German building code document or catalog for rules applying to the BIM element type '{element_type}'. Please generate a highly enriched German search query string containing architectural synonyms and regulatory concepts (e.g., Brandschutz, Fluchtwege, Barrierefreiheit, Abmessungen, Wand, Wandbeläge, Anforderungen) that apply to this element. Provide ONLY the search string, nothing else."
        
        query_str = call_local_llm(query_prompt)
        query_str = query_str.strip().strip('"').strip("'")
        print(f"   -> Agent Generated Query: {query_str}")
        
        print("\n4. Running DB Search...")
        results = coll.query(query_texts=[query_str], n_results=5)
        
        print("\n--- TOP 5 RELEVANT CHUNKS ---")
        if not results['documents'] or not results['documents'][0]:
            print("No documents found.")
            continue
            
        for i, (doc, meta) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            print(f"\n[{i+1}] Page {meta.get('page', '?')} (Type: {meta.get('chunk_type', '?')}) | Source: {meta.get('source', '')}\n" + "-"*40)
            print(doc[:400].replace('\n', ' ') + ("..." if len(doc) > 400 else ""))

if __name__ == "__main__":
    test_rag_retrieval()
