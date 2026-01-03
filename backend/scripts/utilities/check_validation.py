"""Check validation results from a run."""
import sys
import json
from planproof.storage import StorageClient

if len(sys.argv) < 2:
    print("Usage: python scripts/check_validation.py <run_id>")
    sys.exit(1)

run_id = sys.argv[1]
sc = StorageClient()

try:
    data = sc.download_blob('artefacts', f'runs/{run_id}/validation_{run_id}.json')
    result = json.loads(data.decode('utf-8'))
    
    print("Validation Summary:")
    print(json.dumps(result['summary'], indent=2))
    print("\nFindings:")
    for f in result['findings']:
        print(f"  {f['rule_id']}: {f['status']} ({f['severity']})")
        print(f"    Message: {f['message']}")
        if f.get('missing_fields'):
            print(f"    Missing: {f['missing_fields']}")
except Exception as e:
    print(f"Error: {e}")

