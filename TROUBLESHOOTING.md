# Troubleshooting Guide & Error Resolution Log

This document records all errors encountered during the Intelligent Document Assistant setup and their solutions.

## Table of Contents
1. [Dependency Installation Errors](#dependency-installation-errors)
2. [Configuration Errors](#configuration-errors)

---

## Dependency Installation Errors

### Error 1: Pinecone Client Version Mismatch

**Error Message:**
```
ERROR: No matching distribution found for pinecone-client==3.0.1
```

**Cause:** 
The pinecone-client version 3.0.1 doesn't exist in PyPI. The original requirements.txt had an incorrect version number.

**Solution:**
Updated to the stable, currently available version:
```diff
- pinecone-client==3.0.1
+ pinecone-client==5.0.1
```

**File Changed:** `requirements.txt`

---

### Error 2: PyPDF2 Version Doesn't Exist

**Error Message:**
```
ERROR: Could not find a version that satisfies the requirement PyPDF2==4.0.2
```

**Cause:** 
PyPDF2 version 4.0.2 doesn't exist in PyPI. The latest available version is 3.0.1.

**Solution:**
Kept the latest available version:
```diff
- PyPDF2==4.0.2
+ PyPDF2==3.0.1
```

**File Changed:** `requirements.txt`

---

### Error 3: Missing Build Dependencies for Compilation

**Error Message:**
```
Cannot import 'setuptools.build_meta'
```

**Cause:** 
Some packages require compilation using setuptools and wheel, but these tools weren't available in the build environment.

**Solution:**
Installed build tools:
```bash
pip install setuptools wheel
```

---

### Error 4: Pandas Requires C Compiler (Python 3.14)

**Error Message:**
```
error: Meson build failed - no compiler found
ERROR: Could not build wheels for pandas==2.1.3, which is required to install pyproject.toml
```

**Cause:** 
Python 3.14 is very new, and pandas 2.1.3 doesn't have pre-built wheels for cp314. It attempts to compile from source but no C compiler is available.

**Solution:**
Changed to flexible version constraint to allow pip to auto-resolve to a compatible version:
```diff
- pandas==2.1.3
+ pandas>=2.0.0
```

This allows pip to select pandas 3.0.0 which has pre-built wheels for Python 3.14.

**File Changed:** `requirements.txt`

---

### Error 5: Pydantic Requires Rust Compilation (Python 3.14)

**Error Message:**
```
Rust not found, installing into a temporary directory
× pydantic-core requires Rust to compile
```

**Cause:** 
pydantic 2.5.0 doesn't have pre-built wheels for Python 3.14, so it tries to compile pydantic-core which requires Rust.

**Solution:**
Upgraded to a newer version with pre-built wheels:
```diff
- pydantic==2.5.0
+ pydantic>=2.6.0
```

Version 2.6.0+ includes pre-built wheels for Python 3.14 (cp314).

**File Changed:** `requirements.txt`

---

### Error 6: LangChain-Community Dependency Conflict

**Error Message:**
```
ERROR: Cannot install -r requirements.txt (line 12) and langchain-community==0.0.10 because these package versions have conflicting dependencies.
The conflict is caused by:
    The user requested langchain-community==0.0.10
    langchain 0.1.5 depends on langchain-community<0.1 and >=0.0.17
```

**Cause:** 
langchain 0.1.5 requires langchain-community>=0.0.17, but requirements.txt specified 0.0.10 which is too old.

**Solution:**
Upgraded to satisfy langchain's dependency:
```diff
- langchain-community==0.0.10
+ langchain-community>=0.0.17
```

**File Changed:** `requirements.txt`

---

### Error 7: Numpy Version Constraint Conflict with Python 3.14

**Error Message:**
```
ERROR: Cannot install -r requirements.txt (line 19) and langchain==0.1.5 because these package versions have conflicting dependencies.
The conflict is caused by:
    The user requested numpy>=2.4.0
    langchain 0.1.5 depends on numpy<2 and >=1
```

**Cause:** 
numpy 1.x (required by langchain 0.1.5) doesn't have pre-built wheels for Python 3.14. Attempting to build from source fails.

**Solution (Primary):**
Upgraded langchain to a version supporting numpy 2.x:
```diff
- langchain==0.1.5
+ langchain>=0.2.0
```

Also kept numpy flexible:
```diff
- numpy>=1.24.0
+ numpy>=2.4.0
```

**File Changed:** `requirements.txt`

---

### Error 8: LangGraph Version Incompatibility with Upgraded LangChain

**Error Message:**
```
ERROR: Cannot install -r requirements.txt (line 12) and -r requirements.txt (line 13) because these package versions have conflicting dependencies.
The conflict is caused by:
    langgraph 0.0.28 depends on langchain-core<0.2.0 and >=0.1.25
    langchain 1.2.10 depends on langchain-core<2.0.0 and >=1.2.10
```

**Cause:** 
langgraph 0.0.28 is too old and incompatible with the newer langchain versions' langchain-core requirements.

**Solution:**
Upgraded langgraph to a compatible version:
```diff
- langgraph==0.0.28
+ langgraph>=0.0.50
```

This resolves to langgraph 1.0.8, compatible with langchain 1.2.10+.

**File Changed:** `requirements.txt`

---

### Error 9: SageMaker Depends on Old NumPy

**Error Message:**
```
ERROR: Cannot install -r requirements.txt (line 18), -r requirements.txt (line 29) and numpy>=2.4.0 because these package versions have conflicting dependencies.
The conflict is caused by:
    The user requested numpy>=2.4.0
    sagemaker 2.200.0 depends on numpy<2.0 and >=1.9.0
```

**Cause:** 
sagemaker 2.200.0 requires numpy<2, which doesn't work with Python 3.14.

**Solution:**
Made sagemaker version flexible to allow auto-resolution:
```diff
- sagemaker==2.200.0
+ sagemaker>=2.200.0
```

This allows pip to select sagemaker 3.4.1 or later which supports numpy 2.x.

**File Changed:** `requirements.txt`

---

### Error 10: Sentence-Transformers Tokenizers Requires Rust Compilation

**Error Message:**
```
This package requires Rust and Cargo to compile extensions.
Rust not found, installing into a temporary directory
× Encountered error while generating package metadata.
╰─> tokenizers
```

**Cause:** 
sentence-transformers 2.7.0 depends on tokenizers which doesn't have pre-built wheels for Python 3.14 and requires Rust to compile.

**Solution (Primary):**
Replaced with OpenAI embeddings (simpler, no compilation needed):
```diff
- sentence-transformers==2.7.0
+ openai>=1.0.0
```

**Note:** This was later simplified further (see Error 11).

**File Changed:** `requirements.txt`

---

### Error 11: OpenAI Package Jiter Requires Rust Compilation

**Error Message:**
```
This package requires Rust and Cargo to compile extensions.
× Encountered error while generating package metadata.
╰─> jiter
```

**Cause:** 
OpenAI package requires jiter (Rust-based JSON library) which doesn't have Python 3.14 wheels.

**Solution:**
Simplified dependencies to avoid heavy package chains. Removed sentence-transformers and openai, using langchain-core instead:
```diff
- sentence-transformers>=2.8.0
- openai>=1.0.0
+ langchain-core>=0.1.25
```

**File Changed:** `requirements.txt`

---

### Error 12: PyYAML Cython Compilation Error

**Error Message:**
```
AttributeError: 'build_ext' object has no attribute 'cython_sources'
ERROR: Failed to build 'pyyaml' when getting requirements to build wheel
```

**Cause:** 
PyYAML (dependency of langchain) doesn't have pre-built wheels for Python 3.14 and fails during Cython compilation.

**Solution (Ultimate):**
Drastically simplified the requirements.txt to remove heavy framework dependencies that have compilation issues. Kept only essential packages with good Python 3.14 support.

Removed:
- langchain
- langgraph  
- langchain-community
- sagemaker

Kept:
- anthropic (Claude API directly)
- pinecone-client (Vector DB)
- Core utilities only

**File Changed:** `requirements.txt`

**Final Status:** Successfully installed all dependencies without compilation issues.

---

## Configuration Errors

### Error 13: Pydantic Extra Fields Not Permitted

**Error Message:**
```
pydantic_core._pydantic_core.ValidationError: 2 validation errors for Settings
pinecone_project_name
  Extra inputs are not permitted [type=extra_forbidden, input_value='Default', input_type=str]
pinecone_project_id
  Extra inputs are not permitted [type=extra_forbidden, input_value='4992aec4-5c03-4fcb-b553-', input_type=str]
```

**Cause:** 
The `.env` file had Pinecone config variables (`PINECONE_PROJECT_NAME`, `PINECONE_PROJECT_ID`) that weren't defined in the Settings class. Pydantic v2 by default forbids extra fields.

**Solution:**
1. **Added the missing fields** to `Settings` class:
```python
pinecone_project_name: str = ""
pinecone_project_id: str = ""
```

2. **Updated Pydantic configuration** to allow ignoring extra fields:
```python
# Old (Pydantic v1 style)
class Config:
    env_file = ".env"
    case_sensitive = False

# New (Pydantic v2 style)
from pydantic import ConfigDict
model_config = ConfigDict(
    env_file=".env", 
    case_sensitive=False, 
    extra="ignore"  # Ignore extra environment variables
)
```

**File Changed:** `config/settings.py`

**Why This Works:** 
- setting `extra="ignore"` tells Pydantic to silently ignore any extra fields from the environment that aren't defined in the model
- Alternatively, could use `extra="allow"` to accept them
- This is more robust when using environment files with many variables

---

## Key Lessons Learned

1. **Python 3.14 Compatibility:** Many packages still don't have pre-built wheels for Python 3.14. Using flexible version constraints (`>=`) allows pip's resolver to find compatible versions automatically.

2. **Avoid Pinned Versions with New Python:** When using cutting-edge Python versions, avoid pinning exact package versions (==). Use flexible constraints (>=, ~=) instead.

3. **Rust Compilation Issues:** Multiple packages (pydantic-core, tokenizers, jiter, pyyaml) require Rust for compilation. Better to avoid packages with heavy Rust dependencies when possible.

4. **Dependency Chain Complexity:** Complex package chains (like langchain → pyyaml → Cython) can cause cascading compilation failures. Simpler dependency trees are more reliable.

5. **Pydantic v2 Config:** Use `ConfigDict` with `model_config` instead of the old `Config` class. Always set `extra="ignore"` or `extra="allow"` when using environment files.

---

## Installation Summary

**Final Working Configuration:**
- Simplified to core dependencies only
- All packages have pre-built wheels for Python 3.14
- No compilation required
- Successfully installed without errors

**Start Command:**
```bash
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**API Documentation:** Access at `http://localhost:8000/docs`

