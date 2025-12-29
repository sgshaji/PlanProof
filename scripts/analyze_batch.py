"""Analyze batch processing results."""
import sys
import json

if len(sys.argv) < 2:
    print("Usage: python scripts/analyze_batch.py <batch_json_file>")
    sys.exit(1)

with open(sys.argv[1]) as f:
    data = json.load(f)

print("=" * 60)
print("BATCH PROCESSING SUMMARY")
print("=" * 60)
print(f"Run ID: {data.get('run_id')}")
print(f"Application Ref: {data.get('application_ref')}")
print(f"Total Documents: {data.get('total_documents')}")
print(f"Successes: {data.get('successes')}")
print(f"Failures: {data.get('failures')}")
print(f"LLM Calls: {data.get('llm_calls', 0)}")
print()

results = data.get('results', [])
unique_docs = {}
for r in results:
    doc_id = r.get('document_id')
    if doc_id not in unique_docs:
        unique_docs[doc_id] = r

print(f"Unique Documents Processed: {len(unique_docs)}")
print()

llm_triggered = sum(1 for r in unique_docs.values() if r.get('llm_triggered', False))
needs_llm = sum(1 for r in unique_docs.values() if r.get('validation_summary', {}).get('needs_llm', False))

print("Validation Statistics:")
print(f"  Documents with needs_llm=true: {needs_llm}")
print(f"  Documents with LLM actually triggered: {llm_triggered}")
print()

pass_counts = {}
for r in unique_docs.values():
    summary = r.get('validation_summary', {})
    passes = summary.get('pass', 0)
    needs_review = summary.get('needs_review', 0)
    fails = summary.get('fail', 0)
    key = f"P:{passes} R:{needs_review} F:{fails}"
    pass_counts[key] = pass_counts.get(key, 0) + 1

print("Validation Breakdown:")
for key, count in sorted(pass_counts.items()):
    print(f"  {key}: {count} document(s)")

print()
print("Documents with LLM Triggered:")
for doc_id, r in unique_docs.items():
    if r.get('llm_triggered', False):
        print(f"  Doc {doc_id}: {r.get('filename')}")

