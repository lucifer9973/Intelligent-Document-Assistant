## Local Model Setup (CPU / GPU)

This project can optionally run a local open-source LLM via `llama-cpp-python` (ggml-style models) or GPT4All-compatible binaries.

Summary:
- `llama-cpp-python` provides Python bindings to `llama.cpp`/GGML models and works on CPU/GPU (with proper builds).
- Models are multi-GB (several hundred MBs to many GBs). Downloading and storing them requires sufficient disk space.

Quick steps (recommended):

1. Choose model
   - CPU (fastest compatibility): choose a GGML CPU model (e.g., `ggml-alpaca-7b-q4.bin`, `ggml-vicuna-7b-q4.bin`) or GPT4All CPU builds.
   - GPU (if you have CUDA-capable GPU): choose a model built with GPU support and ensure `llama-cpp-python` was installed with CUDA support.

2. Install `llama-cpp-python` (example, CPU-only):

```bash
python -m pip install --upgrade pip
python -m pip install "llama-cpp-python"
```

If you need CUDA builds, follow `llama-cpp-python` docs to install the right wheel or build from source.

3. Download a model and place it somewhere on disk (example):

 - Create a folder: `C:\models\llama` or `/home/user/models/llama`
 - Download a GGML model file (e.g., `ggml-model.bin`) into that folder.

Recommended local-first models (no HF token required):

 - GPT4All releases (direct download from project releases) — good CPU-quantized 3B models and easy to use.

Helper script (recommended): a small PowerShell script is provided at `scripts/download_model.ps1` which prompts for a direct model download URL and saves it to `C:\models\llama` by default.

Example (interactive):

```powershell
# runs the script and prompts for a direct download URL
.\scripts\download_model.ps1
```

Example (non-interactive):

```powershell
.\scripts\download_model.ps1 -Url "https://example.com/your-ggml-model.bin" -Dest "C:\models\llama"
```

Notes:
 - Ensure the URL is a direct binary file link (ends with `.bin` or similar). If the host requires cookies or an account, download manually.
 - After download, set the environment variable (PowerShell session):

```powershell
$Env:LOCAL_LLM_MODEL_PATH = 'C:\models\llama\ggml-model-q4.bin'
```

4. Point the project to the model

 - Set environment variable `LOCAL_LLM_MODEL_PATH` to the absolute model file path.
   Example (PowerShell):

```powershell
$env:LOCAL_LLM_MODEL_PATH = 'C:\models\llama\ggml-model-q4.bin'
```

Or export it in your shell for development:

```bash
export LOCAL_LLM_MODEL_PATH=/home/user/models/llama/ggml-model-q4.bin
```

5. Test from Python REPL

```python
from src.llm.local_model import LocalLLM
llm = LocalLLM()  # reads LOCAL_LLM_MODEL_PATH
print(llm.generate('Say hello in one sentence.'))
```

Notes and troubleshooting:
- If import fails, install `llama-cpp-python` and ensure wheel supports your platform.
- On Windows, consider using WSL2 for better compatibility with GPU builds.
- Model performance varies by CPU/GPU and model quantization.

Security & disk:
- Models can be large — check disk space before downloading.
- Only run models from trusted sources. Verify checksums if provided.
