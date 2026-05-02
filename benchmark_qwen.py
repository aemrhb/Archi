import requests
import time
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:9b"

def test_qwen_speed(text_length):
    # Create a long repetitive text to simulate a large contract
    sample_text = "Project Contract for Architectural Services. " * (text_length // 40)
    
    system_prompt = "You are an expert HOAI auditor."
    prompt = f"""Extract the following parameters FROM THE GERMAN TEXT. 
1. "Anrechenbare Kosten" (Chargeable Costs)
2. "Honorar" (Agreed Fee)
3. "Leistungsphasen" (Service Phases)

TEXT TO ANALYZE:
{sample_text} 

OUTPUT ONLY VALID JSON:
{{
  "costs": 0,
  "contract_fee": 0,
  "service_phases": [],
  "reasoning": "..."
}}
"""

    print(f"\n--- Testing {MODEL} with {len(sample_text)} characters ---")
    start_time = time.time()
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "options": {
                    "num_ctx": 16384,  # Increased for larger test
                    "num_predict": 1024,
                    "temperature": 0.1
                },
                "stream": False
            },
            timeout=600
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            content = response.json().get('message', {}).get('content', '')
            print(f"Success! Response received in {duration:.2f} seconds.")
            # print("Response Snippet:", content[:200])
        else:
            print(f"Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"Exception triggered after {time.time() - start_time:.2f} seconds: {str(e)}")

if __name__ == "__main__":
    # Test with 5k (previous limit)
    test_qwen_speed(5000)
    # Test with 20k (moderate context)
    test_qwen_speed(20000)
    # Test with 40k (large context)
    test_qwen_speed(40000)
