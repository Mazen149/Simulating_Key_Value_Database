"""Performance profiling tool for sustained write operations."""

from __future__ import annotations

import argparse
import time
from datastore.connector import DatastoreConnector


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Performance Benchmark")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--count", type=int, default=5000)
    args = parser.parse_args()

    client = DatastoreConnector(args.host, args.port)
    start = time.time()

    for i in range(args.count):
        client.set(f"bench_key_{i}", f"value_{i}")
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            print(f"Completed {i + 1}/{args.count} writes @ {rate:.1f} ops/sec")

    total_time = time.time() - start
    print(f"\nBenchmark complete: {args.count} writes in {total_time:.2f}s ({args.count / total_time:.1f} ops/sec)")


if __name__ == "__main__":
    main()
