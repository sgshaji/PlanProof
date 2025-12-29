# Troubleshooting Guide

## Common Issues

### "Rule catalog not found"

**Solution**: Run `python scripts/build_rule_catalog.py` to generate the catalog from `validation_requirements.md`.

### "Cannot access local variable 'json'"

**Solution**: This was a scoping issue that's been fixed. If you see this, ensure you're using the latest code with `jsonlib` imports.

### "ModuleNotFoundError: No module named 'planproof'"

**Solution**: Set `PYTHONPATH`:
```bash
export PYTHONPATH="$PWD"  # Linux/Mac
$env:PYTHONPATH="$PWD"    # Windows PowerShell
```

### Duplicate documents being processed

**Solution**: Ensure content hash column exists:
```bash
python scripts/add_content_hash_column.py
```

### LLM triggering too often

**Check**:
1. Field ownership rules in `llm_gate.py`
2. Document type classification
3. Severity of rules (only errors trigger LLM)

### Fields not being extracted

**Check**:
1. Document type classification
2. Field mapper heuristics match your document format
3. Evidence index in extraction result

### Database connection errors

**Check**:
1. `DATABASE_URL` format: `postgresql+psycopg://user:pass@host:5432/dbname`
2. Database is accessible from your network
3. PostGIS extension enabled: `python scripts/enable_postgis.py`

### Blob storage errors

**Check**:
1. `AZURE_STORAGE_CONNECTION_STRING` is correct
2. Containers `inbox` and `artefacts` exist
3. Storage account is accessible

## Debugging Tips

### Check extraction results

```bash
python scripts/show_extraction.py <document_id>
```

### Check validation results

```bash
python scripts/check_validation.py <run_id>
```

### Check database state

```bash
python scripts/check_db.py
python scripts/list_runs.py
```

### Check blob storage

```bash
python scripts/check_blobs.py
```

## Performance Issues

### Slow batch processing

- Documents are processed sequentially; consider parallelization
- Check Document Intelligence API rate limits
- Verify network connectivity to Azure

### High LLM costs

- Review field ownership rules
- Check if field cache is working
- Verify severity levels (warnings shouldn't trigger LLM)

## Getting Help

1. Check logs in run metadata
2. Review validation findings for clues
3. Check evidence_index for extraction issues
4. Verify rule catalog is up to date

