import secrets
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api import (
    amenities,
    auth,
    bank,
    billing,
    committee,
    complaints,
    health,
    notices,
    notifications,
    operations,
    payments,
    visitors,
)
from backend.app.core.config import settings
from backend.app.core.database import Base, engine

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Township One - Gated Township Resident & Operations Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID and Timing Middleware
@app.middleware("http")
async def add_process_time_and_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response


# CSRF Protection Middleware for State-Changing Requests (POST, PUT, PATCH, DELETE)
@app.middleware("http")
async def csrf_protect_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        path = request.url.path.rstrip("/")
        exempt_paths = {
            f"{settings.API_PREFIX}/auth/otp/request",
            "/auth/otp/request",
            f"{settings.API_PREFIX}/auth/otp/verify",
            "/auth/otp/verify",
            f"{settings.API_PREFIX}/auth/login",
            "/auth/login",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        if path not in exempt_paths:
            session_cookie = request.cookies.get("township_session")
            if session_cookie:
                csrf_cookie = request.cookies.get("township_csrf")
                csrf_header = request.headers.get("X-CSRF-Token")

                # Sessions are strictly cookie-based. CSRF token validation is mandatory for all mutating requests.
                if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": {
                                "code": "CSRF_ERROR",
                                "message": "CSRF token missing or invalid",
                                "request_id": getattr(request.state, "request_id", None),
                            }
                        },
                    )

    response = await call_next(request)
    return response


# Standardized Error Handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


# Include Routers
app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(billing.router, prefix=settings.API_PREFIX)
app.include_router(payments.router, prefix=settings.API_PREFIX)
app.include_router(bank.router, prefix=settings.API_PREFIX)
app.include_router(complaints.router, prefix=settings.API_PREFIX)
app.include_router(notifications.router, prefix=settings.API_PREFIX)
app.include_router(visitors.router, prefix=settings.API_PREFIX)
app.include_router(amenities.router, prefix=settings.API_PREFIX)
app.include_router(notices.router, prefix=settings.API_PREFIX)
app.include_router(committee.router, prefix=settings.API_PREFIX)
app.include_router(operations.router, prefix=settings.API_PREFIX)


FRONTEND_DIST = (Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()


@app.get("/")
def root():
    """Serve the compiled resident application when present; retain an API fallback for local tests."""
    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "message": "Welcome to Township One API",
        "documentation": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }


@app.get("/{requested_path:path}", include_in_schema=False)
def serve_frontend_route(requested_path: str):
    """Serve static assets and React Router paths from the same origin as the API."""
    reserved_prefixes = ("api/", "docs", "redoc", "openapi.json", "health")
    if requested_path.startswith(reserved_prefixes):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")

    candidate = (FRONTEND_DIST / requested_path).resolve()
    try:
        candidate.relative_to(FRONTEND_DIST)
    except ValueError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Not found")

    if candidate.is_file():
        return FileResponse(candidate)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Frontend build is unavailable")
