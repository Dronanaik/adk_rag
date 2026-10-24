"""FastAPI application factory, lifespan hooks, CORS, and standardized error handlers."""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import api_v1_router
from app.config import get_settings
from app.dependencies import APIException
from app.schemas.common import ErrorDetail, ErrorEnvelope
from app.utils.logging import configure_logging, get_current_request_id, request_id_ctx_var


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure structured logging and application lifecycle resources."""
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    logger = structlog.get_logger("app.lifespan")
    logger.info("application_starting", version=__version__, env=settings.APP_ENV)
    yield
    logger.info("application_stopping", version=__version__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    application = FastAPI(
        title="Agentic RAG System with Centralized Memory and Knowledge Graph",
        version=__version__,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Accept",
            "X-App-Role",
            "X-Admin-Api-Key",
            "X-Request-Id",
        ],
        expose_headers=["X-Request-Id"],
    )

    @application.middleware("http")
    async def attach_request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Bind X-Request-Id to contextvars and response headers on every HTTP request."""
        incoming_id = request.headers.get("X-Request-Id", "").strip()
        req_id = incoming_id or f"req_{uuid.uuid4().hex[:16]}"
        request.state.request_id = req_id
        token = request_id_ctx_var.set(req_id)
        structlog.contextvars.bind_contextvars(request_id=req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = req_id
            return response
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
            request_id_ctx_var.reset(token)

    @application.exception_handler(APIException)
    async def handle_api_exception(_request: Request, exc: APIException) -> JSONResponse:
        """Format domain APIException into the canonical ErrorEnvelope."""
        req_id = get_current_request_id()
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=req_id,
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope.model_dump(),
            headers={"X-Request-Id": req_id},
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Format FastAPI RequestValidationError into the canonical ErrorEnvelope."""
        req_id = get_current_request_id()
        first_error = exc.errors()[0] if exc.errors() else {}
        loc_parts = [str(part) for part in first_error.get("loc", [])]
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request payload or query parameter validation failed.",
                details={
                    "field": ".".join(loc_parts),
                    "reason": str(first_error.get("msg", "Invalid input")),
                },
                request_id=req_id,
            )
        )
        return JSONResponse(
            status_code=400,
            content=envelope.model_dump(),
            headers={"X-Request-Id": req_id},
        )

    application.include_router(api_v1_router)
    return application


app = create_app()

