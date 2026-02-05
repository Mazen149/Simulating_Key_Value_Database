# Durability and Failure Recovery

## Write-Ahead Logging (WAL)

Every mutation operation follows this sequence:

```
1. Allocate JournalEntry{op, data}
2. Acquire lock
3. Append to journal.log (with fsync)
4. Update in-memory state
5. Update all indexes
6. Create snapshot (fsync + atomic rename)
7. Release lock
```

This guarantees:
- **Atomicity**: Entire operation succeeds or fails
- **Durability**: Data persists even on crash
- **Consistency**: All indexes stay synchronized

## Recovery Process

On startup, the system:

1. Loads `snapshot.json` if present
2. Replays all entries in `journal.log`
3. Rebuilds all secondary indexes
4. Clears journal file after snapshot

Example recovery:
```
Loaded snapshot: {data: 100 items}
Replayed journal: 5 new mutations
Final state: 105 items
```

## Failure Scenarios

### Node Crash During Write
- Before snapshot: Data lost, recovered from last snapshot + partial journal
- After snapshot: Changes durable and persistent

### Network Partition
- Primary: Continues accepting writes if quorum reachable
- Secondary: Will not accept writes (unless in Dynamo mode)
- Resolution: Automatic re-sync when partition heals

### Concurrent Writes (Leader Mode)
- Only primary accepts writes
- All secondaries reject writes with `not_primary` error
- Strongly consistent ordering guaranteed

### Replica Desynchronization
- Change log captures all mutations in order
- Followers replay in same order
- Temporary lag acceptable; eventual consistency achieved

## Fault Tolerance Parameters

```python
# In DatastoreSettings:
replication_timeout = 2.0  # ms to wait for replica ACK
election_interval = 0.5    # frequency of leader checks
heartbeat_interval = 1.0   # how often leader checks are made
drop_rate = 0.0            # chaos: fail writes with probability P
```

## Testing Durability

Simulate failures with:

```bash
# Crash during writes (random fsync failures)
datastore-node --drop-rate 0.01 --port 9000

# Then use client with error handling:
try:
    client.set("key", "value")
except Exception as e:
    # Handle transient failure
    pass
```

Check recovery with:
```python
client1 = DatastoreConnector("localhost", 9000)
before = client1.get("key")

# Restart server (kill and restart process)

client2 = DatastoreConnector("localhost", 9000)
after = client2.get("key")
assert before == after  # Data persists!
```

