import chromadb
from chromadb.utils import embedding_functions
import json

chroma_client = chromadb.PersistentClient(path="./hoai_db")
default_ef = embedding_functions.DefaultEmbeddingFunction()
hoai_collection = chroma_client.get_collection(name="hoai_reference", embedding_function=default_ef)

query = "Fee table for costs 2500000 and complexity related to Honorarzone III"
results = hoai_collection.query(query_texts=[query], n_results=6)

print(f"Query: {query}\n")
print(f"Retrieved {len(results['documents'][0])} chunks:")
for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
    chunk_type = meta.get("chunk_type", "UNKNOWN")
    section = meta.get("section", "N/A")
    print(f"\n--- Result {i+1} (Dist: {dist:.4f}) | Type: {chunk_type} | Section: {section} ---")
    print(doc[:300] + "..." if len(doc) > 300 else doc)
