#!/usr/bin/env python3
"""
Script to clear Pinecone index and reset document storage
"""
import os
import sys

# You'll need to set your Pinecone credentials
# Either export them as environment variables or set them here:
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT", "gcp-starter")
INDEX_NAME = "llama-text-embed-v2-index"  # or your configured index name

def clear_pinecone():
    """Clear all vectors from Pinecone index"""
    if not PINECONE_API_KEY:
        print("ERROR: PINECONE_API_KEY not set!")
        print("Please run: export PINECONE_API_KEY='your-api-key'")
        return False
    
    try:
        from pinecone import Pinecone
        
        # Initialize Pinecone
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Connect to index
        index = pc.Index(INDEX_NAME)
        
        # Delete all vectors (delete all in namespace '')
        print(f"Deleting all vectors from index '{INDEX_NAME}'...")
        index.delete(delete_all=True, namespace='')
        
        print("✅ Pinecone index cleared successfully!")
        return True
        
    except ImportError:
        print("ERROR: pinecone-client not installed")
        print("Run: pip install pinecone")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Pinecone Index Cleaner")
    print("=" * 50)
    
    if input("This will delete ALL documents from Pinecone. Continue? (y/n): ").lower() == 'y':
        success = clear_pinecone()
        sys.exit(0 if success else 1)
    else:
        print("Cancelled.")
        sys.exit(0)
