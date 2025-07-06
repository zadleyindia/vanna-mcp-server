# Vanna Forking Guide

## Where to Clone

Recommended locations for your Vanna fork:

1. **Separate development directory** (RECOMMENDED):
   ```bash
   cd ~/claude
   git clone https://github.com/YOUR_USERNAME/vanna.git vanna-fork
   ```

2. **Within the MCP server project**:
   ```bash
   cd ~/claude/vanna-mcp-server
   git clone https://github.com/YOUR_USERNAME/vanna.git vanna-fork
   ```

## After Cloning

1. **Install in development mode**:
   ```bash
   cd vanna-fork
   pip install -e .
   ```

2. **Make your changes**:
   - Add metadata parameter to `train()` method in `vanna/base/base.py`
   - Update vector store integration to accept metadata
   - Modify the embeddings storage to include metadata

3. **Test locally**:
   ```bash
   # In your vanna-mcp-server directory
   pip uninstall vanna
   pip install -e ../vanna-fork
   ```

4. **Update requirements.txt**:
   ```txt
   # Instead of: vanna>=0.5.0
   git+https://github.com/YOUR_USERNAME/vanna.git@main
   ```

## Key Files to Modify in Vanna

1. `vanna/base/base.py` - Add metadata parameter to train methods
2. `vanna/chromadb/chromadb_vector.py` - Update ChromaDB integration
3. `vanna/pgvector/pgvector.py` - Update pgvector integration

## Example Modification

In `vanna/base/base.py`:

```python
def train(self, 
          question: str = None,
          sql: str = None,
          ddl: str = None,
          documentation: str = None,
          # ADD THIS:
          metadata: dict = None) -> str:
    """Train Vanna with various types of data"""
    # ... existing code ...
```

Then propagate metadata through to the vector store methods.