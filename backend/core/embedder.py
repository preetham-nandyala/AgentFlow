"""
Shared Embedder Module.
Loads the SentenceTransformer model LAZILY (only when first needed) to save RAM.
Falls back gracefully if the model can't load (e.g., low memory machines).
"""

import sys
import os

# Fix Windows console encoding for emoji/unicode characters
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

_embedder = None
_embedder_loaded = False

def get_embedder():
    """Lazy-loads the SentenceTransformer model on first use. Returns None if it can't load."""
    global _embedder, _embedder_loaded
    
    if _embedder_loaded:
        return _embedder
    
    _embedder_loaded = True
    
    try:
        from sentence_transformers import SentenceTransformer
        print("[EMBEDDER] Loading Embedding Model (all-MiniLM-L6-v2)...")
        _embedder = SentenceTransformer('all-MiniLM-L6-v2')
        print("[EMBEDDER] Embedding Model loaded successfully.")
    except Exception as e:
        print(f"[EMBEDDER] WARNING: Could not load embedding model: {e}")
        print("[EMBEDDER] Falling back to keyword-based search.")
        _embedder = None
    
    return _embedder

# For backwards compatibility — modules can still do `from core.embedder import embedder`
# but it will be None until get_embedder() is called
embedder = None
