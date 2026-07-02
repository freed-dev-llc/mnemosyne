# Examples

Minimal scripts showing Mnemosyne's library API end-to-end. All assume Ollama is running
locally with the default models pulled (`ollama pull bge-m3 qwen2.5:1.5b`) and are
run from the repo root.

| Script | What it shows |
| --- | --- |
| [`ask_ubiquiti.py`](ask_ubiquiti.py) | Build the Ubiquiti index, then ask it a question — the API behind `mnemosyne ingest` + `mnemosyne ask`. |

```bash
python examples/ask_ubiquiti.py
```
