# Vanna Fork Integration

## Overview

We've successfully forked Vanna and added metadata support to enable proper multi-database and multi-tenant isolation.

## Fork Details

- **Repository**: https://github.com/zadleyindia/vanna
- **Branch**: `add-metadata-support`
- **Pull Request URL**: https://github.com/zadleyindia/vanna/pull/new/add-metadata-support

## Changes Made

### 1. Modified `train()` method in `base.py`
- Added `metadata` parameter
- Updated all internal method calls to pass metadata
- Maintains backward compatibility (metadata is optional)

### 2. Enhanced PGVector implementation
- Updated `add_question_sql()` to store custom metadata
- Updated `add_ddl()` to store custom metadata
- Updated `add_documentation()` to store custom metadata
- Metadata is merged with existing document metadata

## Installation

The project now uses the forked version:

```bash
pip install git+https://github.com/zadleyindia/vanna.git@add-metadata-support
```

## Benefits

1. **Direct Metadata Support**: Can now pass metadata directly to `vn.train()`
2. **Cleaner API**: No need for workarounds when using base Vanna methods
3. **Future Compatibility**: When Vanna adds official metadata support, migration will be easier
4. **Maintains Our Custom Solution**: Our FilteredPGVectorStore still works and provides additional filtering capabilities

## Usage Example

```python
# Using the forked Vanna with metadata
vn = VannaMCP()
vn.train(
    question="Show all customers",
    sql="SELECT * FROM customers",
    metadata={
        "database_type": "bigquery",
        "tenant_id": "acme_corp"
    }
)
```

## Next Steps

1. **Test the Integration**: Install the forked version and test with your existing code
2. **Consider Contributing Back**: Once tested, consider submitting a PR to the main Vanna repository
3. **Monitor Updates**: Keep your fork updated with upstream changes

## Maintenance

To update your fork with latest Vanna changes:

```bash
cd vanna-fork
git remote add upstream https://github.com/vanna-ai/vanna
git fetch upstream
git checkout main
git merge upstream/main
git checkout add-metadata-support
git rebase main
```

## Alternative Approach

If you prefer not to maintain a fork, you can:
1. Continue using the current FilteredPGVectorStore solution
2. Wait for official metadata support in Vanna
3. Use the existing workaround with custom vector store implementation

The fork provides a cleaner solution but requires maintenance. Choose based on your needs.