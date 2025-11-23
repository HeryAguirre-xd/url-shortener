from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
import redis.asyncio as redis
import asyncpg
import os

app = FastAPI(title="Redirect Service")

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres/url_shortener")

@app.on_event("startup")
async def startup_event():
    app.state.redis = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.redis.close()
    await app.state.db_pool.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "read-redirector"}

@app.get("/{short_code}")
async def redirect_url(short_code: str):
    # 1. Try Redis cache first
    cached_url = await app.state.redis.get(f"url:{short_code}")
    if cached_url:
        return RedirectResponse(url=cached_url, status_code=307)
    
    # 2. Cache miss - query database
    async with app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT long_url FROM urls WHERE short_code = $1", short_code
        )
    
    if not row:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    long_url = row['long_url']
    
    # 3. Cache it in Redis (TTL: 1 hour)
    await app.state.redis.setex(f"url:{short_code}", 3600, long_url)
    
    # 4. Redirect user
    return RedirectResponse(url=long_url, status_code=307)
