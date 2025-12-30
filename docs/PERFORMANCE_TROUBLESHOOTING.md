# Performance Troubleshooting Guide

## Identifying Performance Bottlenecks

### Quick Diagnosis

If document processing is taking more than 1-2 minutes per document, use the profiling script:

```bash
python scripts/utilities/profile_processing.py "path/to/document.pdf"
```

This will show you exactly where time is being spent in the pipeline.

### Expected Processing Times

**Typical performance:**
- Small documents (1-5 pages): 5-15 seconds
- Medium documents (6-20 pages): 15-45 seconds
- Large documents (21+ pages): 45-120 seconds

**If processing takes >5 minutes per document, there's likely an issue.**

## Common Bottlenecks

### 1. Document Intelligence API (Most Common)

**Symptom**: Processing takes 2-5+ minutes per document

**Cause**: The Document Intelligence API call is synchronous and can be slow:
- Large/complex documents take longer to analyze
- Network latency to Azure
- Azure service throttling/rate limits
- Azure service queue/load

**Solutions**:
1. **Check network connectivity**:
   ```bash
   # Test Azure connectivity
   ping <your-docintel-endpoint>
   ```

2. **Check document size**:
   - Large PDFs (>10MB) take longer
   - Multi-page documents (>20 pages) take longer
   - Scanned documents (images) take longer than text PDFs

3. **Check Azure service status**:
   - Visit Azure Portal → Document Intelligence service
   - Check service health and quotas
   - Look for throttling/rate limit errors in logs

4. **Enable caching** (already implemented):
   - Documents are cached after first extraction
   - Same document hash = reuse cached extraction
   - Check if documents are being re-processed unnecessarily

5. **Consider parallel processing** (for batch operations):
   - Currently documents are processed sequentially
   - Could process multiple documents in parallel
   - Trade-off: Higher Azure API usage/rate limits

### 2. Database Operations

**Symptom**: Processing seems fast but total time is slow

**Cause**: Multiple database writes per document (pages, evidence, fields, etc.)

**Solutions**:
1. **Batch database operations** (future optimization)
2. **Disable relational table writes** for testing:
   - Set `write_to_tables=False` in `extract_from_pdf_bytes()`
   - Only JSON artefacts are written
   - Significantly faster but loses relational query capability

### 3. Blob Storage Operations

**Symptom**: Upload/download delays

**Cause**: Network latency to Azure Blob Storage

**Solutions**:
1. **Check network connectivity** to Azure
2. **Use Azure region closest to you**
3. **Check blob storage performance tier** (Standard vs Premium)

### 4. LLM Calls

**Symptom**: Processing stalls at validation/LLM stage

**Cause**: Azure OpenAI API calls can be slow (2-10 seconds per call)

**Solutions**:
1. **Check if LLM is being triggered unnecessarily**:
   ```bash
   # Check LLM call count
   python scripts/utilities/check_run.py <run_id>
   ```

2. **Review LLM gating logic** - should only trigger when needed
3. **Check Azure OpenAI service status**

## Diagnostic Steps

### Step 1: Profile a Single Document

```bash
python scripts/utilities/profile_processing.py "path/to/test.pdf"
```

This shows:
- Time per stage (ingestion, extraction, validation)
- Document Intelligence API time (main bottleneck)
- Percentage of time in each stage

### Step 2: Check for Caching Issues

If the same document is being processed multiple times:

```bash
# Check if document hash exists
python scripts/utilities/check_document.py <document_id>
```

Documents with the same content hash should be reused (deduplication).

### Step 3: Check Network Connectivity

```bash
# Test Azure connectivity
python scripts/smoke_test.py
```

This tests:
- Blob Storage connectivity
- Document Intelligence connectivity
- Database connectivity
- Azure OpenAI connectivity

### Step 4: Check Azure Service Health

1. Visit Azure Portal
2. Check Document Intelligence service:
   - Quotas and limits
   - Service health
   - Recent errors/alerts
3. Check if you're hitting rate limits or throttling

### Step 5: Review Logs

Check for errors or warnings in:
- Processing output/console
- Azure service logs (if enabled)
- Database logs

## Performance Optimization Tips

### Immediate Fixes

1. **Enable document caching** (already implemented):
   - Same document = reuse extraction
   - Saves 5-30 seconds per duplicate document

2. **Process smaller batches**:
   - Instead of 10 documents at once, process 3-5
   - Reduces Azure API queue/load

3. **Check document complexity**:
   - Simplify documents if possible
   - Remove unnecessary pages/sections

### Future Optimizations

1. **Parallel processing**:
   - Process multiple documents concurrently
   - Trade-off: Higher Azure API usage

2. **Async API calls**:
   - Use async Document Intelligence SDK
   - Allows processing other documents while waiting

3. **Batch database operations**:
   - Group multiple DB writes into transactions
   - Reduces database round-trips

4. **Optimize field mapping**:
   - Cache regex compilation
   - Optimize text processing loops

## Monitoring Performance

### Track Processing Times

Add timing to your processing logs:

```python
import time
start = time.time()
# ... process document ...
elapsed = time.time() - start
print(f"Document processed in {elapsed:.2f}s")
```

### Set Performance Baselines

- Note typical processing times for your document types
- Alert if processing time exceeds baseline by 2-3x
- Track trends over time

### Monitor Azure Metrics

In Azure Portal, monitor:
- Document Intelligence API latency
- API call success rate
- Throttling/rate limit events
- Blob storage throughput

## Getting Help

If performance is still poor after troubleshooting:

1. **Collect diagnostic information**:
   - Profile output from `profile_processing.py`
   - Document sizes and page counts
   - Network latency test results
   - Azure service status

2. **Check known issues**:
   - Review GitHub issues
   - Check Azure service status page
   - Review recent code changes

3. **Consider alternatives**:
   - Different Document Intelligence model
   - Different Azure region
   - Local processing (if applicable)

