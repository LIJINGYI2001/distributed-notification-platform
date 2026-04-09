from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from workers.base_worker import run_worker

if __name__ == "__main__":
    run_worker(
        service_name="push-worker-2",
        queue_name="push_normal_queue",
    )