import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"

def debug_qwen_generate_8k():
    prompt = """Extract these: Costs 1M, Fee 100k, LPH 1-3. Output JSON."""

    print(f"Sending generate request to {MODEL} with num_ctx=8192...")
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "options": {
                    "num_ctx": 8192,
                    "num_predict": 1024,
                    "temperature": 0.2
                },
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
    debug_qwen_generate_8k()
