import os
import tempfile
import time
from pathlib import Path

OUTPUT = Path(
    "/home/ubuntu/monitoring-exporter-metrics/"
    "matchwise_render_collector.prom"
)

content = (
    "# HELP matchwise_render_collector_last_success_timestamp_seconds "
    "Unix timestamp of the last successful Render log collection\n"
    "# TYPE matchwise_render_collector_last_success_timestamp_seconds gauge\n"
    "matchwise_render_collector_last_success_timestamp_seconds "
    f"{int(time.time())}\n"
)

fd, temporary = tempfile.mkstemp(
    prefix=".matchwise-render-",
    suffix=".tmp",
    dir=OUTPUT.parent,
)

try:
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())

    os.chmod(temporary, 0o644)
    os.replace(temporary, OUTPUT)

finally:
    if os.path.exists(temporary):
        os.unlink(temporary)

print("Collector success metric updated.")
