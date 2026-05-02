import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:9b"

def debug_qwen():
    system_prompt = "You are an expert HOAI auditor."
    prompt = """Extract the following parameters FROM THE GERMAN TEXT. 
BEWARE: Financial numbers often use '.' as thousands separator and ',' as decimal separator in German.

1. "Anrechenbare Kosten" (Chargeable Costs): The main construction budget.
2. "Honorar" / "Pauschalhonorar" (Agreed Fee): The specific fee agreed for the architect. 
3. "Leistungsphasen" (Service Phases): List which ones (1-9) are mentioned.
4. Difficulty: Any mention of "Honorarzone", "Denkmalschutz", "Hanglage", or "Schwierig".

TEXT TO ANALYZE:
Das Projekt umfasst den Neubau eines Wohnhauses. Die anrechenbaren Kosten betragen 1.250.000,00 EUR. 
Als Honorar wird ein Pauschalbetrag von 120.000,00 EUR vereinbart.
Beauftragt werden die Leistungsphasen 1 bis 5.
Das Gebäude befindet sich in Honorarzone III.

OUTPUT ONLY VALID JSON:
{
  "costs": float,
  "contract_fee": float or null,
  "service_phases": [int],
  "complexity_clues": [string],
  "reasoning": "Explain exactly where you found the costs and the contract_fee"
}
"""

    print(f"Sending debug request to {MODEL}...")
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
                    "num_ctx": 8192,
                    "num_predict": 2048,
                    "temperature": 0
                },
                "stream": False
            },
            timeout=120
        )
        if response.status_code == 200:
            result = response.json().get('message', {}).get('content', '')
            print("--- RAW OUTPUT ---")
            print(result)
            print("--- END RAW OUTPUT ---")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    debug_qwen()
