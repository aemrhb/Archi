import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"

def debug_qwen_simple():
    prompt = "Say hello in German and tell me what model you are."

    print(f"Sending simple generate request to {MODEL}...")
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
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
    debug_qwen_simple()
