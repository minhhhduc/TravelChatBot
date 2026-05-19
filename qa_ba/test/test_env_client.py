import os
from pathlib import Path
from dotenv import load_dotenv
import google.genai as genai

def test_api():
    repo_root = Path(__file__).resolve().parents[2]
    env_paths = [
        repo_root / "ai_module" / "models" / ".env",
        repo_root / "backend" / "ai_module" / "models" / ".env",
    ]
    for local_env in env_paths:
        print("Env path:", local_env)
        if local_env.exists():
            load_dotenv(dotenv_path=local_env)
            break
    
    api_key = os.getenv("API_KEY")
    model_name = os.getenv("MODELS", "gemini-2.5-flash")
    print("Loaded API key:", api_key[:8] + "..." if api_key else "None")
    print("Loaded Model:", model_name)
    
    if not api_key:
        print("Error: API_KEY not found in env.")
        return
        
    client = genai.Client(api_key=api_key)
    
    # Try listing models
    try:
        print("\nListing models:")
        models = client.models.list()
        for m in models:
            print(f"- {m.name} ({m.display_name})")
    except Exception as e:
        print("Listing models failed:", e)

if __name__ == "__main__":
    test_api()
