"""Run synthetic fixtures and package only the explicit portable worker files."""

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

from phd_searcher.ddw import worker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "ddw"))
from test_worker import task  # noqa: E402

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
job = task()
directory, receipt = worker.run(job, output / "results")
assert receipt["state"] == "complete"
assert worker.run(job, output / "results")[1] == receipt
worker.verify(directory, receipt["work_key"])

files = ["src/phd_searcher/__init__.py", "src/phd_searcher/pipeline/__init__.py",
         "src/phd_searcher/pipeline/schema_quality.py", "tools/ddw/requirements.txt",
         "tools/ddw/README.md", *[str(p.relative_to(ROOT)) for p in (ROOT / "src/phd_searcher/ddw").glob("*.py")]]
with zipfile.ZipFile(output / "worker.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(files):
        archive.write(ROOT / name, name)
metadata = {"version": 1, "source_commit": os.environ.get("DDW_SOURCE_COMMIT", "local-uncommitted"),
            "build_id": worker.build_id(), "python": sys.version.split()[0], "work_key": receipt["work_key"],
            "state": receipt["state"], "input": "synthetic-fixture-only"}
worker.write_json(output / "experiment.json", metadata)
checksums = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob("*")) if p.is_file() and p.name != "checksums.json"}
worker.write_json(output / "checksums.json", checksums)
print(json.dumps(metadata))
