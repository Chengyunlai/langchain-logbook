"""FastAPI adapter：认证、HTTP 状态码和 SSE wire protocol。"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from mini_deerflow.api.contracts import (
    CreateThreadRequest,
    ErrorResponse,
    RunCreateRequest,
    RunResponse,
    RunResumeRequest,
    ThreadResponse,
    ThreadStateResponse,
)
from mini_deerflow.api.gateway import MiniDeerFlowGateway
from mini_deerflow.runtime.manager import RunWaitTimeoutError
from mini_deerflow.runtime.repository import RuntimeConflictError, RuntimeNotFoundError


IdentityResolver = Callable[[Request], str]


def create_fastapi_app(
    gateway: MiniDeerFlowGateway,
    *,
    identity_resolver: IdentityResolver,
) -> FastAPI:
    """创建 HTTP adapter；manager/checkpointer/store 的生命周期由组合根持有。"""

    app = FastAPI(title="Mini DeerFlow Runtime Gateway", version="0.1.0")

    def authenticated_user(request: Request) -> str:
        try:
            user_id = identity_resolver(request)
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=401, detail="缺少或无效的认证身份") from error
        if not user_id or not user_id.strip():
            raise HTTPException(status_code=401, detail="缺少或无效的认证身份")
        return user_id

    @app.exception_handler(RuntimeNotFoundError)
    async def not_found_handler(_request: Request, error: RuntimeNotFoundError) -> JSONResponse:
        payload = ErrorResponse(code="not_found", message=str(error))
        return JSONResponse(status_code=404, content=payload.model_dump(mode="json"))

    @app.exception_handler(RuntimeConflictError)
    async def conflict_handler(_request: Request, error: RuntimeConflictError) -> JSONResponse:
        payload = ErrorResponse(code="conflict", message=str(error))
        return JSONResponse(status_code=409, content=payload.model_dump(mode="json"))

    @app.exception_handler(RunWaitTimeoutError)
    async def timeout_handler(_request: Request, error: RunWaitTimeoutError) -> JSONResponse:
        payload = ErrorResponse(code="wait_timeout", message=str(error))
        return JSONResponse(status_code=408, content=payload.model_dump(mode="json"))

    @app.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
    def create_thread(
        body: CreateThreadRequest,
        user_id: str = Depends(authenticated_user),
    ) -> ThreadResponse:
        return gateway.create_thread(body, user_id=user_id)

    @app.get("/threads/{thread_id}/state", response_model=ThreadStateResponse)
    def get_state(
        thread_id: str,
        user_id: str = Depends(authenticated_user),
    ) -> ThreadStateResponse:
        return gateway.get_state(thread_id, user_id=user_id)

    @app.post(
        "/threads/{thread_id}/runs",
        response_model=RunResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def start_run(
        thread_id: str,
        body: RunCreateRequest,
        user_id: str = Depends(authenticated_user),
    ) -> RunResponse:
        return gateway.start_run(thread_id, body, user_id=user_id)

    @app.post(
        "/threads/{thread_id}/runs/resume",
        response_model=RunResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def resume_thread(
        thread_id: str,
        body: RunResumeRequest,
        user_id: str = Depends(authenticated_user),
    ) -> RunResponse:
        return gateway.resume_thread(thread_id, body, user_id=user_id)

    @app.get("/threads/{thread_id}/runs/{run_id}", response_model=RunResponse)
    def get_run(
        thread_id: str,
        run_id: str,
        user_id: str = Depends(authenticated_user),
    ) -> RunResponse:
        return gateway.get_run(thread_id, run_id, user_id=user_id)

    @app.post("/threads/{thread_id}/runs/{run_id}/wait", response_model=RunResponse)
    def wait_run(
        thread_id: str,
        run_id: str,
        timeout: float | None = Query(default=None, gt=0, le=300),
        user_id: str = Depends(authenticated_user),
    ) -> RunResponse:
        return gateway.wait_run(
            thread_id,
            run_id,
            user_id=user_id,
            timeout=timeout,
        )

    @app.post("/threads/{thread_id}/runs/{run_id}/cancel", response_model=RunResponse)
    def cancel_run(
        thread_id: str,
        run_id: str,
        user_id: str = Depends(authenticated_user),
    ) -> RunResponse:
        return gateway.cancel_run(thread_id, run_id, user_id=user_id)

    @app.get("/threads/{thread_id}/runs/{run_id}/events")
    def stream_events(
        thread_id: str,
        run_id: str,
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        user_id: str = Depends(authenticated_user),
    ) -> StreamingResponse:
        # 在返回 200 之前完成 ownership 与 Last-Event-ID 校验。
        iterator = gateway.iter_run_events(
            thread_id,
            run_id,
            user_id=user_id,
            last_event_id=last_event_id,
        )
        try:
            first = next(iterator)
        except StopIteration:
            first = None
        except ValueError as error:
            iterator.close()
            raise HTTPException(status_code=400, detail=str(error)) from error

        def stream():
            try:
                if first is not None:
                    yield first
                yield from iterator
            finally:
                iterator.close()

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app


__all__ = ["IdentityResolver", "create_fastapi_app"]
