from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import realtime_routes  # websocket routes (package)
from app.unified_media import router as media_router
from app.api import auth as auth_api
import os
try:
    from fastapi_limiter import FastAPILimiter
    import redis.asyncio as redis
except Exception:  # pragma: no cover - optional dependency
    FastAPILimiter = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):  # FastAPI 0.110+ lifespan style
    if FastAPILimiter:  # initialize rate limiter once at startup
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        try:
            r = redis.from_url(redis_url, encoding='utf-8', decode_responses=True)
            await FastAPILimiter.init(r)
        except Exception:
            pass
    # Keep-alive task (does nothing but prevents some envs from treating app as idle)
    import asyncio
    _alive = True
    async def _tick():
        while _alive:
            await asyncio.sleep(30)
    task = asyncio.create_task(_tick())
    yield
    # (Optional) add shutdown cleanup here
    _alive = False  # type: ignore
    try:
        task.cancel()
    except Exception:
        pass


app = FastAPI(title="Video-Audio Insight Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unified routers
app.include_router(auth_api.router)
app.include_router(media_router)
app.include_router(realtime_routes.router, prefix="/realtime", tags=["Realtime"])  # existing ws


@app.get("/")
def root():
    return {"message": "Video-Audio Insight Platform API Running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/_debug/routes")
def list_routes():
    routes = []
    for r in app.router.routes:
        try:
            methods = list(r.methods) if hasattr(r, 'methods') else []
            path = getattr(r, 'path', None)
            name = getattr(r, 'name', None)
            if path:
                routes.append({"path": path, "methods": methods, "name": name})
        except Exception:
            pass
    return {"routes": routes}


@app.middleware("http")
async def _log_requests(request, call_next):  # minimal logging
    from time import time
    start = time()
    try:
        response = await call_next(request)
        return response
    finally:
        dur_ms = int((time() - start)*1000)
        # Avoid noisy body logging, just method/path/status/duration
        try:
            print(f"[REQ] {request.method} {request.url.path} -> {getattr(response,'status_code', 'NA')} {dur_ms}ms")  # noqa: T201
        except Exception:
            pass


