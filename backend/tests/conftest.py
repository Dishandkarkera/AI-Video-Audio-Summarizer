import asyncio, os, pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

os.environ.setdefault('DATABASE_URL','sqlite+aiosqlite:///./test.db')
os.environ.setdefault('APP_ENV','test')

from app.main import app  # after env setup

@pytest.fixture(scope='session')
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope='session')
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        yield ac
