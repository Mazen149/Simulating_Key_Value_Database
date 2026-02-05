# Multi-Node Deployment Guide

## Cluster Configuration

The system supports two operational modes:

### Leader-Follower Mode (Leader-based)

**Best for**: Strict consistency requirements, write ordering guarantees

```bash
# Node 1 - Primary (Leader)
datastore-node \
  --host 127.0.0.1 --port 9000 \
  --node-id 1 --role primary \
  --data-dir ./data1 \
  --peers '[{"node_id":2,"host":"127.0.0.1","port":9001},{"node_id":3,"host":"127.0.0.1","port":9002}]'

# Node 2 - Secondary (Follower)
datastore-node \
  --host 127.0.0.1 --port 9001 \
  --node-id 2 --role secondary \
  --data-dir ./data2 \
  --peers '[{"node_id":1,"host":"127.0.0.1","port":9000},{"node_id":3,"host":"127.0.0.1","port":9002}]'

# Node 3 - Secondary (Follower)
datastore-node \
  --host 127.0.0.1 --port 9002 \
  --node-id 3 --role secondary \
  --data-dir ./data3 \
  --peers '[{"node_id":1,"host":"127.0.0.1","port":9000},{"node_id":2,"host":"127.0.0.1","port":9001}]'
```

### Dynamo Mode (Multi-Writer)

**Best for**: High availability, partition tolerance, writes during leader unavailability

```bash
# All nodes are equal peers
datastore-node \
  --host 127.0.0.1 --port 9000 \
  --node-id 1 --mode dynamo \
  --data-dir ./data1 \
  --peers '[{"node_id":2,"host":"127.0.0.1","port":9001}]'

datastore-node \
  --host 127.0.0.1 --port 9001 \
  --node-id 2 --mode dynamo \
  --data-dir ./data2 \
  --peers '[{"node_id":1,"host":"127.0.0.1","port":9000}]'
```

## Failover Behavior

- **Leader Mode**: Automatic election of new primary from lowest available node ID
- **Dynamo Mode**: All replicas continue accepting writes independently
- **Election Window**: Configurable via `--election-interval` (default: 0.5s)
- **Replication Timeout**: Set via cluster settings (default: 2.0s)

## Network Topology

Each node maintains connections to all configured peers:
- Unidirectional change replication (primary → secondaries)
- Bidirectional role queries for leader election
- Heartbeat mechanisms built into existing queries

