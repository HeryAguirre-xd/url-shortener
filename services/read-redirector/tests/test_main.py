import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from main import app

# Helper to create a future for async return
def future_return(result=None):
    f = asyncio.Future()
    f.set_result(result)
    return f

def side_effect_future(result=None):
    def _func(*args, **kwargs):
        return future_return(result)
    return _func

# Helper class to mock asyncpg Pool
class MockPool:
    def __init__(self, conn_return_value=None):
        self.conn = AsyncMock()
        if conn_return_value:
            self.conn.fetchrow.return_value = conn_return_value
        else:
            self.conn.fetchrow.return_value = None

    def acquire(self):
        return self.ContextManager(self.conn)

    async def close(self):
        pass

    class ContextManager:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            return self.conn
        async def __aexit__(self, exc_type, exc, tb):
            pass

# Mock Redis globally
@pytest.fixture(autouse=True)
def mock_redis(mocker):
    mocker.patch("redis.asyncio.from_url", return_value=AsyncMock())

def test_health_check(mocker):
    # Mock DB pool for health check
    mocker.patch("asyncpg.create_pool", side_effect=side_effect_future(AsyncMock()))
    
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "read-redirector"}

@pytest.mark.asyncio
async def test_redirect_cache_hit(mocker):
    # Mock Redis client
    mock_redis_client = AsyncMock()
    mock_redis_client.get.return_value = "https://cached.com"
    mocker.patch("redis.asyncio.from_url", return_value=mock_redis_client)
    
    # Mock DB pool
    mocker.patch("asyncpg.create_pool", side_effect=side_effect_future(AsyncMock()))

    with TestClient(app) as client:
        response = client.get("/cached_code", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "https://cached.com"

@pytest.mark.asyncio
async def test_redirect_cache_miss_db_hit(mocker):
    # Mock Redis miss
    mock_redis_client = AsyncMock()
    mock_redis_client.get.return_value = None
    mocker.patch("redis.asyncio.from_url", return_value=mock_redis_client)
    
    # Mock DB hit using MockPool
    mock_pool = MockPool(conn_return_value={"long_url": "https://db-found.com"})
    
    mocker.patch("asyncpg.create_pool", side_effect=side_effect_future(mock_pool))

    with TestClient(app) as client:
        response = client.get("/db_code", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "https://db-found.com"
        # Verify it set the cache
        mock_redis_client.setex.assert_called_with("url:db_code", 3600, "https://db-found.com")

@pytest.mark.asyncio
async def test_redirect_not_found(mocker):
    # Mock Redis miss
    mock_redis_client = AsyncMock()
    mock_redis_client.get.return_value = None
    mocker.patch("redis.asyncio.from_url", return_value=mock_redis_client)
    
    # Mock DB miss using MockPool
    mock_pool = MockPool(conn_return_value=None)
    
    mocker.patch("asyncpg.create_pool", side_effect=side_effect_future(mock_pool))

    with TestClient(app) as client:
        response = client.get("/unknown_code", follow_redirects=False)
        assert response.status_code == 404
