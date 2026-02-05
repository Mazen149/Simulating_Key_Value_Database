# Search and Indexing Capabilities

## Query Types Supported

### 1. Exact Match Retrieval
Fastest operation - direct dictionary lookup.

```python
value = client.get("mykey")
```

### 2. Value-Based Search
Find all keys with a specific value (secondary index).

```python
# Returns list of keys where value == "blue"
matching_keys = client.search_by_value("blue")
```

Efficient when:
- Values are hashable (strings, numbers, tuples)
- Searching for exact matches
- Value selectivity is low

### 3. Full-Text Search
Token-based inverted index for string content.

```python
# Returns keys containing word "hello"
results = client.search_text("hello")
```

Index automatically created for:
- String values directly
- Dict values with "text" field

Example:
```python
client.set("doc1", "hello world example")
client.set("doc2", {"text": "hello there", "meta": {...}})
client.search_text("hello")  # Returns ["doc1", "doc2"]
```

### 4. Vector Similarity Search
Cosine similarity matching for embeddings.

```python
# Store a vector
client.add_vector("embedding1", [1.0, 0.0, 0.0])
client.add_vector("embedding2", [0.9, 0.1, 0.0])

# Search for top-5 nearest neighbors
results = client.vector_search([1.0, 0.0, 0.0], top_k=5)
# Returns: [{"key": "embedding1", "score": 1.0}, {"key": "embedding2", "score": 0.99}, ...]
```

## Index Internals

### ValueIndex (Secondary Index)
- Structure: `Dict[value] -> List[keys]`
- Space: O(V × N) where V = unique values, N = keys
- Query: O(1) lookup, returns list directly
- Updates: O(1) add/remove operations

### FullTextIndex (Inverted Index)
- Structure: `Dict[token] -> List[keys]`
- Space: O(T × N) where T = unique tokens
- Query: O(1) lookup, case-insensitive
- Updates: O(words) per document

### EmbeddingIndex (Vector Index)
- Structure: `Dict[key] -> vector`
- Space: O(K × D) where K = vectors, D = dimensions
- Query: O(K) similarity computation (no approximation)
- Updates: O(1) add/remove operations

## Performance Characteristics

| Operation | Time | Space | Notes |
|-----------|------|-------|-------|
| get(key) | O(1) | - | Constant time lookup |
| set(key, value) | O(1) | O(1) | Indexed automatically |
| delete(key) | O(1) | O(1) | Unindexed automatically |
| search_by_value(v) | O(1) | O(matches) | Returns matching key list |
| search_text(term) | O(1) | O(matches) | Token-based lookup |
| vector_search(vec) | O(K) | O(top_k) | Linear scan + sort |
| bulk_set(items) | O(N) | O(N) | Atomic operation |

## Index Maintenance

All indexes are maintained **automatically** on every write:

```python
# Updating "author" key
client.set("author", "John Doe")
# Automatically:
# - Indexes "John Doe" in text index
# - Adds to value index for "John Doe"
# - Logs to WAL
# - Creates snapshot
# - Replicates to peers
```

Deleting similarly triggers automatic unindexing.

