import secrets
import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


@app.get("/")
def root():
    return {"message": "Welcome to Township One API", "documentation": "/docs", "health": "/health", "version": "1.0.0"}
