import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"

def debug_qwen_no_options():
    prompt = """Extract the following parameters FROM THE GERMAN TEXT. 
1. "Anrechenbare Kosten" (Chargeable Costs): 1.250.000,00 EUR
2. "Honorar": 120.000,00 EUR
3. "Leistungsphasen": 1-5

OUTPUT ONLY VALID JSON:
{
  "costs": 1250000.0,
  "contract_fee": 120000.0,
  "service_phases": [1,2,3,4,5],
  "reasoning": "Test"
}
"""

    print(f"Sending request to {MODEL} without options...")
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        if response.status_code == 200:
            result = response.json().get('response', '')
            print("--- RAW OUTPUT ---")
            print(result)
            print("--- END RAW OUTPUT ---")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    debug_qwen_no_options()
