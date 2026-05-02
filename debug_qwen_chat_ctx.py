import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5:9b"

def debug_qwen_chat_lower_ctx():
    system_prompt = "You are an expert HOAI auditor."
    prompt = "Extract these: Costs 1M, Fee 100k, LPH 1-3. Output JSON."

    print(f"Sending chat request to {MODEL} with num_ctx=16384...")
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
                    "num_ctx": 16384,
                    "num_predict": 2048,
                    "temperature": 0.2
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
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    debug_qwen_chat_lower_ctx()
