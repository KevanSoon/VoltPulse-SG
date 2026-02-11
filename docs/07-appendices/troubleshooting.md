# Troubleshooting Guide

Common issues and solutions for VoltPulse-SG.

---

## Database Connection Issues

### Error: "Connection refused" or "Timeout"

**Symptoms:**
```
psycopg.OperationalError: connection failed: timeout expired
```

**Solutions:**

1. **Check environment variables:**
```bash
echo $SUPABASE_DB_HOST
echo $SUPABASE_DB_PASSWORD
```

2. **Test connection manually:**
```bash
psql -h db.yourproject.supabase.co -U postgres.yourproject -d postgres
```

3. **Verify SSL mode:**
```env
SUPABASE_DB_SSLMODE=require
```

4. **Check firewall/network:**
- Ensure port 6543 is not blocked
- Verify VPN/proxy settings

---

### Error: "SSL connection required"

**Solution:**
```env
SUPABASE_DB_SSLMODE=require  # Not "disable"
```

---

### Error: "Too many connections"

**Symptoms:**
```
psycopg.OperationalError: FATAL: remaining connection slots are reserved
```

**Solutions:**

1. **Use connection pooling (pgBouncer):**
```env
SUPABASE_DB_PORT=6543  # pgBouncer port, not 5432
```

2. **Reduce pool size:**
```python
# In graph/builder.py
pool = AsyncConnectionPool(
    conninfo=create_connection_string(),
    max_size=10,  # Reduce from 20 to 10
)
```

3. **Close unused connections:**
```python
await pool.close()
```

---

## LLM & API Issues

### Error: "Ollama API key invalid"

**Symptoms:**
```
HTTPException: 401 Unauthorized
```

**Solutions:**

1. **Verify API key:**
```bash
curl -H "Authorization: Bearer $OLLAMA_API_KEY" https://ollama.com/api/v1/health
```

2. **Check environment variable:**
```python
import os
print(os.getenv('OLLAMA_API_KEY'))
```

3. **Fallback to local Ollama:**
```bash
# Remove OLLAMA_API_KEY from .env
# System will use local Ollama at localhost:11434
```

---

### Error: "SEALION endpoint unreachable"

**Symptoms:**
```
httpx.ConnectError: Connection refused
```

**Solutions:**

1. **Test endpoint manually:**
```bash
curl -X POST https://your-sealion-endpoint.com/api/encode \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'
```

2. **Check firewall/CORS:**
- Ensure endpoint is publicly accessible
- Verify authentication if required

3. **Use alternative endpoint:**
```env
SEALION_ENDPOINT=https://backup-endpoint.com/api/encode
```

---

### Error: "OpenAI rate limit exceeded"

**Symptoms:**
```
openai.RateLimitError: Rate limit exceeded
```

**Solutions:**

1. **Implement retry with backoff:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def call_openai_api():
    # API call here
```

2. **Reduce concurrent requests:**
- Limit parallel OCR processing
- Add delays between requests

3. **Upgrade OpenAI plan:**
- Increase rate limits on OpenAI dashboard

---

## Vector Search Issues

### Error: "IVFFlat index not found"

**Symptoms:**
- Slow vector search queries (>5 seconds)
- Sequential scans in query plan

**Solution:**

Create IVFFlat index:
```sql
CREATE INDEX my_embeddings_embedding_idx
    ON my_embeddings
    USING ivfflat (embedding vector_l2_ops)
    WITH (lists = 100);
```

---

### Issue: Poor search results

**Solutions:**

1. **Check embedding quality:**
```python
# Verify embedding dimension
embedding = await encoder.encode("test query")
assert len(embedding) == 1024
```

2. **Adjust distance metric:**
```sql
-- Try different distance metrics
embedding <-> query_embedding  -- L2 distance (current)
embedding <=> query_embedding  -- Cosine distance
```

3. **Increase search limit:**
```python
results = await vector_store.find_similar(
    query_embedding=embedding,
    limit=800  # Increase from 10 to 800
)
```

---

## Performance Issues

### Issue: Slow API responses (>5 seconds)

**Diagnosis:**

1. **Enable logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Profile query time:**
```python
import time

start = time.time()
result = await expensive_operation()
print(f"Took {time.time() - start:.2f}s")
```

**Solutions:**

1. **Enable RRF quick mode:**
```env
RRF_QUICK_MODE_THRESHOLD=20  # Lower threshold
```

2. **Reduce vector search limit:**
```python
results = await vector_store.find_similar(
    query_embedding=embedding,
    limit=100  # Instead of 800
)
```

3. **Add caching:**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(param):
    # ...
```

---

### Issue: High memory usage

**Solutions:**

1. **Limit concurrent connections:**
```python
max_size=10  # Instead of 20 in connection pool
```

2. **Close connections after use:**
```python
finally:
    await pool.close()
```

3. **Reduce batch sizes:**
```python
# Process in smaller batches
for batch in chunks(data, size=10):  # Instead of 100
    process_batch(batch)
```

---

## Frontend Issues

### Error: "Network request failed"

**Solutions:**

1. **Check API URL:**
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7860';
```

2. **Enable CORS:**
```python
# backend/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Check network console:**
- Open browser DevTools → Network tab
- Verify request/response details

---

### Issue: Leaflet map not loading

**Solutions:**

1. **Check CSS import:**
```typescript
import 'leaflet/dist/leaflet.css';
```

2. **Fix icon paths:**
```typescript
import L from 'leaflet';
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: '/leaflet/marker-icon-2x.png',
  iconUrl: '/leaflet/marker-icon.png',
  shadowUrl: '/leaflet/marker-shadow.png',
});
```

3. **Verify GeoJSON data:**
```typescript
console.log(geojsonData);  // Should have valid coordinates
```

---

## Deployment Issues

### Error: "Module not found"

**Solution:**

Install dependencies:
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

---

### Error: "Port already in use"

**Solution:**

Change port or kill existing process:
```bash
# Find process on port 7860
lsof -i :7860

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app:app --port 7861
```

---

### Issue: Production environment variables not loading

**Solution:**

1. **Check .env file location:**
```bash
ls -la backend/.env  # Should exist
```

2. **Load explicitly:**
```python
from dotenv import load_dotenv
load_dotenv()  # Add this at top of app.py
```

3. **Use system environment variables:**
```bash
export SUPABASE_DB_PASSWORD="your_password"
```

---

## Getting Help

**Check Logs:**
```bash
# Backend logs
tail -f backend/logs/app.log

# Frontend logs
npm run dev  # Check console output
```

**Enable Debug Mode:**
```env
LOG_LEVEL=DEBUG
```

**Community Support:**
- GitHub Issues: https://github.com/anthropics/voltpulse/issues
- Documentation: https://docs.voltpulse.sg

---

## Related Documentation

- [Deployment Guide](../01-architecture/deployment.md)
- [Environment Variables](./environment-variables.md)
- [Database Schema](./database-schema.md)

---

**Generated:** 2024-06-15
**Last Updated:** 2024-06-15
