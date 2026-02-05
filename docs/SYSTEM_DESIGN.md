# System Architecture Overview

## High-Level Design

The Distributed Data Store is architected as a resilient, multi-node system designed for fault tolerance and scalability. The system separates concerns across several key layers:

### Core Components

1. **Network Layer** (`network.py`)
   - Handles all TCP socket communication
   - Processes JSON-line protocol messages
   - Manages concurrent client connections via threading

2. **Storage Layer** (`persistence.py`)
   - Implements write-ahead logging (WAL) for durability
   - Maintains snapshot files for fast recovery
   - Ensures atomic state transitions

3. **Query Layer** (`core.py`)
   - In-memory data structure with thread-safe operations
   - Multiple index types for diverse query patterns
   - Supports value, text, and vector searching

4. **Replication Layer** (`replication.py`)
   - Asynchronous changelog distribution
   - Leader election with quorum awareness
   - Peer discovery and health monitoring

5. **Client Interface** (`connector.py`)
   - Synchronous request-response protocol
   - Connection pooling via socket context managers
   - Timeout handling and error propagation

## Data Flow

### Write Operation
```
Client Request → Network Handler → Durability Log → In-Memory Index → Snapshot → Peer Replication
```

### Read Operation
```
Client Request → Network Handler → In-Memory Data Retrieval → Response
```

### Consistency Model

- **Strong Consistency**: Single-node and leader-based modes guarantee ordered writes
- **Eventual Consistency**: Dynamo-style mode allows concurrent writes with convergence

## Durability Guarantees

1. Journal Entry appended (fsync)
2. In-memory state updated
3. Index structures maintained
4. Snapshot file created (fsync + atomic rename)
5. WAL rotation on snapshot

Recovery follows snapshot → replay journal ordering.

