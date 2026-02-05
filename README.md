# Resilient Distributed Data Persistence System

A production-grade, multi-node data persistence solution engineered for high availability and strong durability guarantees. Built with Python 3.10+ using asynchronous replication, automatic failure recovery, and support for diverse query patterns.

## Core Capabilities

- **Persistent Storage** — Write-ahead logging with atomic snapshots ensures no data loss
- **Multi-Node Replication** — Automatic change propagation to replica nodes
- **Flexible Consistency** — Choose between strict leader-based or multi-writer modes
- **Rich Indexing** — Value, full-text, and vector similarity search built-in
- **Automatic Recovery** — Fast startup with snapshot + journal replay
- **Concurrent Access** — Thread-safe operations with fine-grained locking
- **TCP Networking** — JSON-lines protocol for language-agnostic clients

## Installation & Setup

### Prerequisites
- Python 3.10 or newer
- Standard library only (no external dependencies)

### Install from Source

```bash
git clone <repository>
cd distributed-datastore
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
pip install pytest          # For running tests
```

## Quick Start

### Single-Node Server

Launch a standalone node:

```bash
datastore-node --host 127.0.0.1 --port 9000 --data-dir ./storage
```

### Client Operations

```python
from datastore.connector import DatastoreConnector

# Connect to running node
client = DatastoreConnector("127.0.0.1", 9000)

# Basic key-value operations
client.set("username", "alice")
print(client.get("username"))  # Output: alice

client.delete("username")
print(client.get("username"))  # Output: None

# Batch operations
records = [("user:1", "Alice"), ("user:2", "Bob")]
client.bulk_set(records)

# Search capabilities
client.set("bio", "Software engineer passionate about databases")
matches = client.search_text("databases")  # Inverted index search
print(matches)  # Returns matching keys

# Vector similarity
client.add_vector("doc1_embedding", [1.0, 0.2, 0.3])
client.add_vector("doc2_embedding", [0.9, 0.3, 0.2])
similar = client.vector_search([1.0, 0.2, 0.3], top_k=5)
print(similar)  # Sorted by cosine similarity
```

## Multi-Node Deployment

### Leader-Based Replication (Primary + Replicas)

Ideal for transactional workloads requiring strong consistency.

```bash
# Terminal 1 - Primary
datastore-node \
  --host 127.0.0.1 --port 9000 \
  --node-id 1 --role primary \
  --data-dir ./storage/node1 \
  --peers '[{"node_id":2,"host":"127.0.0.1","port":9001}]'

# Terminal 2 - Replica
datastore-node \
  --host 127.0.0.1 --port 9001 \
  --node-id 2 --role secondary \
  --data-dir ./storage/node2 \
  --peers '[{"node_id":1,"host":"127.0.0.1","port":9000}]'
```

All writes go to primary; replicas accept reads and sync automatically.

### Dynamo-Style Multi-Writer

All nodes accept writes independently; changes propagate asynchronously.

```bash
# All nodes use --mode dynamo
datastore-node \
  --host 127.0.0.1 --port 9000 \
  --node-id 1 --mode dynamo \
  --data-dir ./storage/node1 \
  --peers '[{"node_id":2,"host":"127.0.0.1","port":9001}]'

datastore-node \
  --host 127.0.0.1 --port 9001 \
  --node-id 2 --mode dynamo \
  --data-dir ./storage/node2 \
  --peers '[{"node_id":1,"host":"127.0.0.1","port":9000}]'
```

## Testing

### Run Unit & Integration Tests

```bash
pytest                           # Basic test suite
RUN_INTEGRATION=1 pytest        # Including failover tests
pytest tests/advanced_test.py   # Specific test file
pytest -v                        # Verbose output
```

### Performance Benchmarking

```bash
# Start a node
datastore-node --port 9000 --data-dir ./bench_data &

# Run write benchmark
python utilities/perf_write_test.py --host 127.0.0.1 --port 9000 --count 10000
# Output: Throughput in operations/second
```

### Chaos Testing (Crash Recovery)

```bash
# Automatically restart server every 5 seconds
python utilities/chaos_test.py \
  --command "datastore-node --port 9000 --data-dir ./chaos_data" \
  --interval 5.0 \
  --restart

# In another terminal, stress the system
while true; do
  python utilities/perf_write_test.py --count 1000
  sleep 1
done
```

## Architecture Overview

The system comprises five interconnected layers:

| Layer | Responsibility | Key Files |
|-------|-----------------|-----------|
| **Network** | TCP socket handling, message routing | `network.py` |
| **Persistence** | WAL, snapshots, recovery | `persistence.py` |
| **Query Engine** | In-memory storage, indexing | `core.py` |
| **Replication** | Multi-node sync, leader election | `replication.py` |
| **Client** | Remote operation interface | `connector.py` |

Detailed architecture documentation: [ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Advanced Usage

### Value-Based Searching

Find all keys matching a specific value:

```python
client.set("status:alice", "active")
client.set("status:bob", "active")
client.set("status:charlie", "inactive")

active_users = client.search_by_value("active")
# Returns: ["status:alice", "status:bob"]
```

### Full-Text Search

Token-based search across string values:

```python
client.set("post:1", "learning database internals")
client.set("post:2", {"text": "database optimization techniques"})

results = client.search_text("database")
# Returns both posts
```

### Vector Embeddings (Semantic Search)

Store and query high-dimensional embeddings:

```python
# Store pre-computed embeddings
embeddings = {
    "query_1": [0.1, 0.2, 0.3],
    "doc_1": [0.11, 0.21, 0.31],
    "doc_2": [0.9, 0.8, 0.7],
}

for key, vec in embeddings.items():
    client.add_vector(key, vec)

# Find semantically similar items
results = client.vector_search([0.1, 0.2, 0.3], top_k=2)
# Returns doc_1 (highest cosine similarity)
```

## Configuration Reference

### Startup Parameters

```bash
datastore-node [OPTIONS]

Options:
  --host HOST                 Network interface to bind (default: 127.0.0.1)
  --port PORT                 TCP port number (default: 9000)
  --node-id ID               Unique node identifier (default: 1)
  --data-dir PATH            Directory for snapshots and logs (default: ./data)
  --role {primary,secondary} Node role (default: primary)
  --mode {leader,dynamo}     Replication mode (default: leader)
  --peers JSON               JSON list of peer nodes
  --drop-rate RATE           Chaos testing - fsync failure probability (default: 0.0)
```

### Peers JSON Format

```json
[
  {"node_id": 2, "host": "192.168.1.2", "port": 9001},
  {"node_id": 3, "host": "192.168.1.3", "port": 9002}
]
```

## Durability Guarantees

1. **Atomic Writes** — Entire operation succeeds or fails; no partial state
2. **Persistent Snapshots** — JSON snapshots with fsync guarantees
3. **Write-Ahead Logging** — All mutations logged before in-memory update
4. **Fast Recovery** — Snapshot + replay typically completes in <100ms
5. **Replication Safety** — Primary waits for acknowledgment from replicas (in leader mode)

See [DURABILITY.md](docs/DURABILITY.md) for failure recovery details.

## Clustering & Failover

### Leader Election

When primary becomes unavailable:
1. Remaining nodes detect absence (election_interval timeout)
2. Candidates propose themselves based on node ID
3. Lowest available ID becomes new primary
4. Others promote via `promote` RPC

### Replication Modes

**Leader Mode**: Single writer (primary), multiple readers
- Strong consistency
- Ordered writes
- Leader election automatic

**Dynamo Mode**: Multiple writers, asynchronous convergence
- High availability during partitions
- Eventual consistency
- No single point of failure

Full clustering guide: [CLUSTERING.md](docs/CLUSTERING.md)

## Search & Indexing

### Supported Query Types

| Query Type | Time | Index Type | Use Case |
|-----------|------|-----------|----------|
| get(key) | O(1) | None | Exact lookup |
| search_by_value(v) | O(1) | Secondary | Find keys with value |
| search_text(term) | O(1) | Inverted | Full-text search |
| vector_search(vec) | O(K) | Vector | Similarity ranking |

Indexes are maintained automatically on all mutations.

Indexing deep dive: [INDEXING.md](docs/INDEXING.md)

## Project Structure

```
.
├── src/
│   └── datastore/              # Core implementation
│       ├── connector.py         # Client SDK
│       ├── network.py          # Server & networking
│       ├── core.py             # Query engine
│       ├── persistence.py      # Durability layer
│       ├── replication.py      # Clustering
│       ├── indexing.py         # Search indexes
│       ├── messaging.py        # Protocol
│       ├── settings.py         # Configuration
│       └── launcher.py         # CLI entry point
├── utilities/                  # Operational tools
│       ├── perf_write_test.py  # Throughput benchmark
│       └── chaos_test.py       # Failure testing
├── tests/                      # Test suite
│       ├── test_core.py
│       ├── test_persistence.py
│       └── test_failover_integration.py
├── docs/                       # Documentation
│       ├── ARCHITECTURE.md
│       ├── CLUSTERING.md
│       ├── INDEXING.md
│       └── DURABILITY.md
└── pyproject.toml             # Project metadata
```

## Performance Characteristics

Typical performance on modern hardware:

- **Writes**: 5,000-10,000 ops/sec (including fsync)
- **Reads**: 100,000+ ops/sec (in-memory)
- **Replication Latency**: <10ms for adjacent nodes
- **Recovery Time**: ~100ms per 10K items
- **Memory Overhead**: ~1.5x for indexes

## Limitations & Future Work

Current version:
- Single-machine recovery (WAL + snapshot only)
- No automatic sharding
- Vector index uses exact similarity (no LSH/approximation)
- No compression

Planned enhancements:
- Distributed transactions
- Range queries and sorting
- Approximate nearest-neighbor search
- RocksDB backend option
- ACID guarantees across clusters

## Contributing

Test coverage should remain >80%. Run:

```bash
pytest --cov=datastore tests/
```

All code must pass:
```bash
python -m pytest
python -m mypy src/
```

## License

See LICENSE file for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: Report bugs and feature requests
- **Questions**: Check test files for usage examples
