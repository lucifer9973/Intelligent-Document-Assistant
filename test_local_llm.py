#!/usr/bin/env python3
"""Test script to verify local LLM is working"""
import os
import sys

# Set the model path
os.environ["LOCAL_LLM_MODEL_PATH"] = "/home/lucifer/models/Llama-3.2-1B-Instruct-Q4_0.gguf"
__test__ = False  # Utility script, not part of automated pytest collection.

from src.llm.local_model import LocalLLM

def main():
    model_path = os.getenv('LOCAL_LLM_MODEL_PATH')
    print(f"Model path: {model_path}")
    print(f"File exists: {os.path.exists(model_path)}")
    
    try:
        llm = LocalLLM(model_path=model_path)
        print("LocalLLM initialized successfully!")
        
        response = llm.generate("Say hello in one sentence.", max_tokens=50)
        print(f"Response: {response}")
        print("\n✓ Local LLM is working without API keys!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
