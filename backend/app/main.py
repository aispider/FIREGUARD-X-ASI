"""FastAPI application: middlewares (body size, rate limit, security headers, CORS) and the router."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes
from app.api.deps import limiter
from app.config import get_settings
from app.db import init_engine

log = logging.getLogger("fireguard")


def create_app() -> FastAPI:
    settings = get_settings()
    settings.assert_production_safe()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_engine()
        yield

    app = FastAPI(title="FIREGUARD-X API", version="1.0.0", lifespan=lifespan,
                  description="Adaptive Scientific Intelligence for spacecraft fire safety. Prototype; all actions simulated.",
                  docs_url="/api/docs" if settings.demo_mode else None, redoc_url=None,
                  openapi_url="/api/openapi.json" if settings.demo_mode else None)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type"], max_age=600)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > settings.max_body_bytes:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        if request.url.path.startswith("/api/") and request.url.path != "/api/health":
            ip = request.client.host if request.client else "unknown"
            d = limiter().hit(f"ip:{ip}", settings.rate_limit_per_min)
            if not d.allowed:
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": str(d.retry_after)})
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    app.include_router(routes.router)
    return app


app = create_app()
