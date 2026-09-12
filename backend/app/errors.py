"""The single error envelope used by every route.

Contract (MVP_TEAM_WORK_PLAN.md section 4):
    {"error": {"code": "INSUFFICIENT_STOCK", "message": "...", "details": {}}}

Status codes: 401 unauthenticated, 403 forbidden, 404 missing, 409 conflict,
422 invalid input, 503 unavailable dependency. Validation errors use the same
envelope, so the frontend only ever parses one error shape.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Raise this anywhere in the app to produce a contract-shaped error."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}

    def to_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=self.status_code,
            content={
                "error": {
                    "code": self.code,
                    "message": self.message,
                    "details": self.details,
                }
            },
        )


def unauthenticated(message: str = "Authentication required.", **details: Any) -> ApiError:
    return ApiError(401, "UNAUTHENTICATED", message, details)


def forbidden(message: str = "You do not have access to this resource.", **details: Any) -> ApiError:
    return ApiError(403, "FORBIDDEN", message, details)


def not_found(message: str = "Resource not found.", **details: Any) -> ApiError:
    return ApiError(404, "NOT_FOUND", message, details)


def conflict(code: str, message: str, **details: Any) -> ApiError:
    return ApiError(409, code, message, details)


def invalid(message: str, code: str = "INVALID_INPUT", **details: Any) -> ApiError:
    return ApiError(422, code, message, details)


def unavailable(code: str, message: str, **details: Any) -> ApiError:
    return ApiError(503, code, message, details)


# Status codes that carry a meaningful default error code when raised as a
# plain HTTPException (mostly from FastAPI internals).
_HTTP_CODES = {
    400: "INVALID_INPUT",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "INVALID_INPUT",
    503: "DEPENDENCY_UNAVAILABLE",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())[1:]),
                "message": error.get("msg", "invalid value"),
            }
            for error in exc.errors()
        ]
        return ApiError(
            422,
            "INVALID_INPUT",
            "Request body failed validation.",
            {"fields": fields},
        ).to_response()

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "ERROR")
        return ApiError(exc.status_code, code, str(exc.detail)).to_response()
