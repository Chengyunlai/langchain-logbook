from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import tempfile
import time
from typing import Annotated, TypedDict
import unittest

from fastapi import Request
import httpx
from langchain_core.messages import AnyMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from mini_deerflow.runtime import (
    RuntimeConflictError,
    RuntimeNotFoundError,
    LocalRunManager,
    RunStatus,
    SSEEncoder,
    SqliteRuntimeRepository,
)
from mini_deerflow.app import build_application, build_default_dependencies
from mini_deerflow.api import (
    CreateThreadRequest,
    MiniDeerFlowGateway,
    RunCreateRequest,
    create_fastapi_app,
)
from mini_deerflow.config import ApplicationSettings
from mini_deerflow.persistence import open_sqlite_checkpointer, open_sqlite_store
from mini_deerflow.store import UserPreferenceRepository


class SqliteRuntimeRepositoryTests(unittest.TestCase):
    def test_local_worker_restart_marks_orphaned_active_runs_error_and_replayable(self) -> None:
        class EmptyGraph:
            def stream(self, graph_input, **kwargs):
                del graph_input, kwargs
                return iter(())

            def get_state(self, config):
                del config
                return SimpleNamespace(values={}, next=(), tasks=())

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "runtime.sqlite"
            first = SqliteRuntimeRepository(database)
            first.create_thread(user_id="learner", thread_id="thread-orphan")
            orphan = first.create_run(
                user_id="learner",
                thread_id="thread-orphan",
                input_kind="message",
                input_data={"message": "尚未执行"},
                stream_modes=("updates",),
                on_disconnect="continue",
                run_id="run-orphan",
            )

            restarted = SqliteRuntimeRepository(database)
            manager = LocalRunManager(restarted, EmptyGraph())
            recovered = restarted.get_run(orphan.run_id, user_id="learner")
            events = restarted.list_events(orphan.run_id, user_id="learner")
            replacement = manager.start_message(
                user_id="learner",
                thread_id="thread-orphan",
                message="重新执行",
            )
            manager.wait(replacement.run_id, user_id="learner", timeout=3)
            manager.close()

            self.assertEqual(recovered.status, RunStatus.error)
            self.assertEqual(recovered.error_code, "worker_restarted")
            self.assertEqual([event.event for event in events], ["error", "end"])

    def test_threads_runs_and_events_survive_restart_and_enforce_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "runtime.sqlite"
            first = SqliteRuntimeRepository(database)
            thread = first.create_thread(
                user_id="learner-a",
                thread_id="thread-runtime-1",
                metadata={"title": "SSE 学习"},
            )
            run = first.create_run(
                user_id="learner-a",
                thread_id=thread.thread_id,
                input_kind="message",
                input_data={"message": "解释 Runtime"},
                stream_modes=("updates", "values"),
                on_disconnect="continue",
                run_id="run-runtime-1",
            )
            first.transition_run(
                run.run_id,
                user_id="learner-a",
                to_status=RunStatus.running,
            )
            first_event = first.append_event(
                run.run_id,
                user_id="learner-a",
                event="updates",
                data={"model": {"messages": ["chunk-1"]}},
            )
            second_event = first.append_event(
                run.run_id,
                user_id="learner-a",
                event="values",
                data={"messages": ["snapshot"]},
            )
            first.finish_run(
                run.run_id,
                user_id="learner-a",
                to_status=RunStatus.success,
            )

            restarted = SqliteRuntimeRepository(database)

            self.assertEqual(
                restarted.get_thread(thread.thread_id, user_id="learner-a"),
                thread,
            )
            self.assertEqual(
                restarted.get_run(run.run_id, user_id="learner-a").status,
                RunStatus.success,
            )
            self.assertEqual(
                [event.sequence for event in restarted.list_events(
                    run.run_id,
                    user_id="learner-a",
                )],
                [1, 2, 3],
            )
            self.assertEqual(first_event.event_id, "run-runtime-1:1")
            self.assertEqual(second_event.event_id, "run-runtime-1:2")
            self.assertEqual(
                [item.run_id for item in restarted.list_runs(
                    thread.thread_id,
                    user_id="learner-a",
                )],
                [run.run_id],
            )
            with self.assertRaises(RuntimeNotFoundError):
                restarted.get_thread(thread.thread_id, user_id="learner-b")
            with self.assertRaises(RuntimeNotFoundError):
                restarted.get_run(run.run_id, user_id="learner-b")
            with self.assertRaises(RuntimeConflictError):
                restarted.transition_run(
                    run.run_id,
                    user_id="learner-a",
                    to_status=RunStatus.running,
                )

    def test_sse_frames_are_replayable_after_last_event_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            repository.create_thread(
                user_id="learner",
                thread_id="thread-sse-1",
            )
            run = repository.create_run(
                user_id="learner",
                thread_id="thread-sse-1",
                input_kind="message",
                input_data={"message": "流式解释"},
                stream_modes=("updates",),
                on_disconnect="continue",
                run_id="run-sse-1",
            )
            first = repository.append_event(
                run.run_id,
                user_id="learner",
                event="updates",
                data={"model": {"text": "第一行\n第二行"}},
            )
            second = repository.append_event(
                run.run_id,
                user_id="learner",
                event="end",
                data={"status": "success"},
            )
            encoder = SSEEncoder()

            self.assertEqual(
                encoder.encode(first),
                'id: run-sse-1:1\nevent: updates\ndata: {"model":{"text":"第一行\\n第二行"}}\n\n',
            )
            self.assertEqual(encoder.heartbeat(), ": heartbeat\n\n")
            after_sequence = encoder.sequence_after(
                first.event_id,
                run_id=run.run_id,
            )
            replayed = repository.list_events(
                run.run_id,
                user_id="learner",
                after_sequence=after_sequence,
            )

            self.assertEqual(replayed, (second,))
            self.assertEqual(encoder.sequence_after(None, run_id=run.run_id), 0)
            self.assertEqual(encoder.sequence_after("-", run_id=run.run_id), 0)
            with self.assertRaises(ValueError):
                encoder.sequence_after("another-run:1", run_id=run.run_id)


class LocalRunManagerTests(unittest.TestCase):
    def test_graph_failure_is_redacted_and_persisted_with_end(self) -> None:
        class FailingGraph:
            def stream(self, graph_input, **kwargs):
                del graph_input, kwargs
                raise RuntimeError("api_key=super-secret /private/workspace")

            def get_state(self, config):
                del config
                raise AssertionError("失败后不应读取 state")

        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            manager = LocalRunManager(repository, FailingGraph())
            manager.create_thread(user_id="learner", thread_id="thread-error")
            run = manager.start_message(
                user_id="learner",
                thread_id="thread-error",
                message="触发失败",
            )
            failed = manager.wait(run.run_id, user_id="learner", timeout=3)
            events = manager.list_events(run.run_id, user_id="learner")
            manager.close()

            serialized = repr([event.model_dump() for event in events])
            self.assertEqual(failed.status, RunStatus.error)
            self.assertEqual(
                [event.event for event in events],
                ["metadata", "error", "end"],
            )
            self.assertNotIn("super-secret", failed.error_message or "")
            self.assertNotIn("super-secret", serialized)
            self.assertNotIn("/private/workspace", serialized)

    def test_background_run_persists_graph_modes_terminal_event_and_state(self) -> None:
        class FakeGraph:
            def __init__(self) -> None:
                self.values: dict[str, object] = {}

            def stream(
                self,
                graph_input,
                *,
                config,
                context,
                stream_mode,
                version,
            ):
                self.values = {
                    "received": graph_input["messages"][0][1],
                    "runtime_user": context["user_id"],
                }
                self.config = config
                self.modes = tuple(stream_mode)
                self.version = version
                for mode in stream_mode:
                    yield {
                        "type": mode,
                        "ns": (),
                        "data": (
                            {"model": {"answer": "完成"}}
                            if mode == "updates"
                            else dict(self.values)
                        ),
                    }

            def get_state(self, config):
                return SimpleNamespace(values=self.values, next=(), tasks=())

        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            graph = FakeGraph()
            manager = LocalRunManager(
                repository,
                graph,
                context_factory=lambda record: {"user_id": record.user_id},
            )
            thread = manager.create_thread(
                user_id="learner",
                thread_id="thread-manager-1",
            )
            run = manager.start_message(
                user_id="learner",
                thread_id=thread.thread_id,
                message="解释 RunManager",
                stream_modes=("updates", "values"),
                on_disconnect="continue",
                run_id="run-manager-1",
            )

            completed = manager.wait(
                run.run_id,
                user_id="learner",
                timeout=3,
            )
            events = manager.list_events(run.run_id, user_id="learner")
            state = manager.get_thread_state(thread.thread_id, user_id="learner")
            manager.close()

            self.assertEqual(completed.status, RunStatus.success)
            self.assertEqual(
                [event.event for event in events],
                ["metadata", "updates", "values", "end"],
            )
            self.assertEqual(events[-1].data, {"status": "success"})
            self.assertEqual(state.values["received"], "解释 RunManager")
            self.assertEqual(state.values["runtime_user"], "learner")
            self.assertEqual(state.next, ())
            self.assertEqual(state.interrupts, ())
            self.assertEqual(graph.modes, ("updates", "values"))
            self.assertEqual(graph.version, "v2")
            self.assertEqual(
                graph.config["configurable"]["thread_id"],
                thread.thread_id,
            )

    def test_interrupt_is_persisted_and_a_new_run_resumes_the_same_thread(self) -> None:
        class ApprovalState(TypedDict, total=False):
            messages: Annotated[list[AnyMessage], add_messages]
            approved: bool

        def review(_state: ApprovalState) -> ApprovalState:
            decision = interrupt({"question": "是否批准报告？"})
            return {"approved": bool(decision["approved"])}

        builder = StateGraph(ApprovalState)
        builder.add_node("review", review)
        builder.add_edge(START, "review")
        builder.add_edge("review", END)
        graph = builder.compile(checkpointer=InMemorySaver())

        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            manager = LocalRunManager(repository, graph)
            thread = manager.create_thread(
                user_id="learner",
                thread_id="thread-interrupt-1",
            )
            first = manager.start_message(
                user_id="learner",
                thread_id=thread.thread_id,
                message="发布报告",
                stream_modes=("updates",),
                run_id="run-interrupt-1",
            )
            interrupted = manager.wait(first.run_id, user_id="learner", timeout=3)
            paused_state = manager.get_thread_state(
                thread.thread_id,
                user_id="learner",
            )
            resumed_run = manager.start_resume(
                user_id="learner",
                thread_id=thread.thread_id,
                resume={"approved": True},
                stream_modes=("updates", "values"),
                run_id="run-resume-1",
            )
            resumed = manager.wait(
                resumed_run.run_id,
                user_id="learner",
                timeout=3,
            )
            final_state = manager.get_thread_state(
                thread.thread_id,
                user_id="learner",
            )
            manager.close()

            self.assertEqual(interrupted.status, RunStatus.interrupted)
            self.assertEqual(
                paused_state.interrupts,
                ({"question": "是否批准报告？"},),
            )
            self.assertEqual(resumed.status, RunStatus.success)
            self.assertTrue(final_state.values["approved"])
            self.assertEqual(final_state.interrupts, ())
            self.assertIn(
                "interrupt",
                [event.event for event in repository.list_events(
                    first.run_id,
                    user_id="learner",
                )],
            )

    def test_cancel_request_is_cooperative_and_prevents_later_events(self) -> None:
        first_chunk_ready = Event()
        allow_next_chunk = Event()

        class SlowGraph:
            def stream(self, graph_input, **kwargs):
                del graph_input, kwargs
                first_chunk_ready.set()
                yield {
                    "type": "updates",
                    "ns": (),
                    "data": {"step": {"value": 1}},
                }
                allow_next_chunk.wait(timeout=3)
                yield {
                    "type": "updates",
                    "ns": (),
                    "data": {"step": {"value": 2}},
                }

            def get_state(self, config):
                del config
                return SimpleNamespace(values={"value": 1}, next=(), tasks=())

        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            manager = LocalRunManager(repository, SlowGraph())
            thread = manager.create_thread(
                user_id="learner",
                thread_id="thread-cancel-1",
            )
            run = manager.start_message(
                user_id="learner",
                thread_id=thread.thread_id,
                message="执行长任务",
                run_id="run-cancel-1",
            )
            self.assertTrue(first_chunk_ready.wait(timeout=3))
            deadline = time.monotonic() + 3
            while len(repository.list_events(run.run_id, user_id="learner")) < 2:
                if time.monotonic() > deadline:
                    self.fail("首个 graph event 未持久化")
                time.sleep(0.01)
            manager.request_cancel(run.run_id, user_id="learner")
            allow_next_chunk.set()
            cancelled = manager.wait(run.run_id, user_id="learner", timeout=3)
            events = manager.list_events(run.run_id, user_id="learner")
            manager.close()

            self.assertEqual(cancelled.status, RunStatus.cancelled)
            self.assertEqual(
                [event.event for event in events],
                ["metadata", "updates", "end"],
            )
            self.assertEqual(events[-1].data, {"status": "cancelled"})

    def test_application_state_store_and_runtime_records_survive_service_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = ApplicationSettings.offline(workspace_root=root)
            runtime_database = root / "runtime.sqlite"
            checkpoint_database = root / "checkpoints.sqlite"
            store_database = root / "store.sqlite"

            with (
                open_sqlite_checkpointer(checkpoint_database) as checkpointer,
                open_sqlite_store(store_database) as store,
            ):
                dependencies = replace(
                    build_default_dependencies(settings),
                    checkpointer=checkpointer,
                    store=store,
                )
                application = build_application(settings, dependencies=dependencies)
                repository = SqliteRuntimeRepository(runtime_database)
                first_manager = LocalRunManager(
                    repository,
                    application.graph,
                    context_factory=lambda record: application.context_for(
                        request_id=record.run_id,
                        user_id=record.user_id,
                    ),
                )
                thread = first_manager.create_thread(
                    user_id="learner",
                    thread_id="thread-restart-1",
                )
                first_run = first_manager.start_message(
                    user_id="learner",
                    thread_id=thread.thread_id,
                    message="第一轮解释 Checkpointer",
                    run_id="run-restart-1",
                )
                first_manager.wait(first_run.run_id, user_id="learner", timeout=3)
                UserPreferenceRepository(store).save(
                    "learner",
                    {"answer_detail": "high"},
                )
                first_manager.close()

            with (
                open_sqlite_checkpointer(checkpoint_database) as checkpointer,
                open_sqlite_store(store_database) as store,
            ):
                dependencies = replace(
                    build_default_dependencies(settings),
                    checkpointer=checkpointer,
                    store=store,
                )
                restarted_application = build_application(
                    settings,
                    dependencies=dependencies,
                )
                restarted_repository = SqliteRuntimeRepository(runtime_database)
                restarted_manager = LocalRunManager(
                    restarted_repository,
                    restarted_application.graph,
                    context_factory=lambda record: restarted_application.context_for(
                        request_id=record.run_id,
                        user_id=record.user_id,
                    ),
                )
                restored_before_second_run = restarted_manager.get_thread_state(
                    thread.thread_id,
                    user_id="learner",
                )
                second_run = restarted_manager.start_message(
                    user_id="learner",
                    thread_id=thread.thread_id,
                    message="第二轮继续解释 Store",
                    run_id="run-restart-2",
                )
                restarted_manager.wait(
                    second_run.run_id,
                    user_id="learner",
                    timeout=3,
                )
                restored_after_second_run = restarted_manager.get_thread_state(
                    thread.thread_id,
                    user_id="learner",
                )
                preferences = UserPreferenceRepository(store).load("learner")
                runs = restarted_repository.list_runs(
                    thread.thread_id,
                    user_id="learner",
                )
                restarted_manager.close()

            self.assertTrue(restored_before_second_run.values["messages"])
            human_messages = [
                message
                for message in restored_after_second_run.values["messages"]
                if message.get("type") == "human"
            ]
            self.assertEqual(
                [message["content"] for message in human_messages],
                ["第一轮解释 Checkpointer", "第二轮继续解释 Store"],
            )
            self.assertEqual(preferences, {"answer_detail": "high"})
            self.assertEqual(
                [(run.run_id, run.status) for run in runs],
                [
                    ("run-restart-1", RunStatus.success),
                    ("run-restart-2", RunStatus.success),
                ],
            )


class FastAPIGatewayTests(unittest.TestCase):
    def test_http_api_creates_runs_reads_state_and_replays_sse_with_ownership(self) -> None:
        class HTTPGraph:
            def __init__(self) -> None:
                self.states: dict[str, dict[str, object]] = {}

            def stream(self, graph_input, *, config, stream_mode, **kwargs):
                del kwargs
                thread_id = config["configurable"]["thread_id"]
                message = graph_input["messages"][0][1]
                self.states[thread_id] = {"answer": f"已处理：{message}"}
                for mode in stream_mode:
                    yield {
                        "type": mode,
                        "ns": (),
                        "data": (
                            {"model": {"answer": "已处理"}}
                            if mode == "updates"
                            else dict(self.states[thread_id])
                        ),
                    }

            def get_state(self, config):
                thread_id = config["configurable"]["thread_id"]
                return SimpleNamespace(
                    values=self.states.get(thread_id, {}),
                    next=(),
                    tasks=(),
                )

        def test_identity(request: Request) -> str:
            return request.headers["x-test-user"]

        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            manager = LocalRunManager(repository, HTTPGraph())
            gateway = MiniDeerFlowGateway(manager)
            app = create_fastapi_app(gateway, identity_resolver=test_identity)
            headers = {"x-test-user": "learner-a"}

            async def exercise_http_api():
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                ) as client:
                    created = await client.post(
                        "/threads",
                        headers=headers,
                        json={
                            "thread_id": "thread-http-1",
                            "metadata": {"title": "HTTP/SSE"},
                        },
                    )
                    started = await client.post(
                        "/threads/thread-http-1/runs",
                        headers=headers,
                        json={
                            "message": "解释 SSE replay",
                            "stream_modes": [
                                "messages",
                                "updates",
                                "values",
                                "custom",
                            ],
                            "on_disconnect": "continue",
                        },
                    )
                    run_id = started.json()["run_id"]
                    waited = await client.post(
                        f"/threads/thread-http-1/runs/{run_id}/wait?timeout=3",
                        headers=headers,
                    )
                    state = await client.get(
                        "/threads/thread-http-1/state",
                        headers=headers,
                    )
                    stream = await client.get(
                        f"/threads/thread-http-1/runs/{run_id}/events",
                        headers=headers,
                    )
                    first_event_id = repository.list_events(
                        run_id,
                        user_id="learner-a",
                    )[0].event_id
                    replay = await client.get(
                        f"/threads/thread-http-1/runs/{run_id}/events",
                        headers={**headers, "Last-Event-ID": first_event_id},
                    )
                    invalid_replay = await client.get(
                        f"/threads/thread-http-1/runs/{run_id}/events",
                        headers={**headers, "Last-Event-ID": "another-run:1"},
                    )
                    hidden = await client.get(
                        "/threads/thread-http-1/state",
                        headers={"x-test-user": "learner-b"},
                    )
                    return (
                        created,
                        started,
                        waited,
                        state,
                        stream,
                        replay,
                        invalid_replay,
                        hidden,
                    )

            (
                created,
                started,
                waited,
                state,
                stream,
                replay,
                invalid_replay,
                hidden,
            ) = asyncio.run(exercise_http_api())
            manager.close()

            self.assertEqual(created.status_code, 201)
            self.assertEqual(started.status_code, 202)
            self.assertEqual(waited.json()["status"], "success")
            self.assertEqual(state.json()["values"]["answer"], "已处理：解释 SSE replay")
            self.assertTrue(stream.headers["content-type"].startswith("text/event-stream"))
            self.assertIn("event: metadata", stream.text)
            self.assertIn("event: updates", stream.text)
            self.assertIn("event: values", stream.text)
            self.assertIn("event: messages", stream.text)
            self.assertIn("event: custom", stream.text)
            self.assertIn("event: end", stream.text)
            self.assertNotIn("event: metadata", replay.text)
            self.assertIn("event: end", replay.text)
            self.assertEqual(invalid_replay.status_code, 400)
            self.assertEqual(hidden.status_code, 404)

    def test_http_api_resumes_an_interrupted_thread_with_a_new_run(self) -> None:
        class ApprovalState(TypedDict, total=False):
            messages: Annotated[list[AnyMessage], add_messages]
            approved: bool

        def review(_state: ApprovalState) -> ApprovalState:
            decision = interrupt({"question": "是否批准？"})
            return {"approved": bool(decision["approved"])}

        builder = StateGraph(ApprovalState)
        builder.add_node("review", review)
        builder.add_edge(START, "review")
        builder.add_edge("review", END)
        graph = builder.compile(checkpointer=InMemorySaver())

        def identity(_request: Request) -> str:
            return "learner"

        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            manager = LocalRunManager(repository, graph)
            app = create_fastapi_app(
                MiniDeerFlowGateway(manager),
                identity_resolver=identity,
            )

            async def exercise_resume():
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                ) as client:
                    await client.post(
                        "/threads",
                        json={"thread_id": "thread-http-resume"},
                    )
                    started = await client.post(
                        "/threads/thread-http-resume/runs",
                        json={"message": "发布"},
                    )
                    started_body = started.json()
                    paused = await client.post(
                        f"/threads/thread-http-resume/runs/{started_body['run_id']}/wait",
                        params={"timeout": 3},
                    )
                    paused_state = await client.get(
                        "/threads/thread-http-resume/state"
                    )
                    resumed = await client.post(
                        "/threads/thread-http-resume/runs/resume",
                        json={
                            "resume": {"approved": True},
                            "stream_modes": ["updates", "values"],
                        },
                    )
                    completed = await client.post(
                        f"/threads/thread-http-resume/runs/{resumed.json()['run_id']}/wait",
                        params={"timeout": 3},
                    )
                    final_state = await client.get(
                        "/threads/thread-http-resume/state"
                    )
                    return (
                        started_body,
                        paused,
                        paused_state,
                        resumed,
                        completed,
                        final_state,
                    )

            (
                started,
                paused,
                paused_state,
                resumed,
                completed,
                final_state,
            ) = asyncio.run(exercise_resume())
            manager.close()

            self.assertEqual(paused.json()["status"], "interrupted")
            self.assertEqual(
                paused_state.json()["interrupts"],
                [{"question": "是否批准？"}],
            )
            self.assertEqual(resumed.status_code, 202)
            self.assertNotEqual(started["run_id"], resumed.json()["run_id"])
            self.assertEqual(completed.json()["status"], "success")
            self.assertTrue(final_state.json()["values"]["approved"])

    def test_http_stream_close_propagates_cancel_through_prefetched_first_frame(self) -> None:
        first_chunk_ready = Event()
        release_graph = Event()

        class DisconnectGraph:
            def stream(self, graph_input, **kwargs):
                del graph_input, kwargs
                first_chunk_ready.set()
                yield {"type": "updates", "ns": (), "data": {"step": 1}}
                release_graph.wait(timeout=3)
                yield {"type": "updates", "ns": (), "data": {"step": 2}}

            def get_state(self, config):
                del config
                return SimpleNamespace(values={"step": 1}, next=(), tasks=())

        with tempfile.TemporaryDirectory() as directory:
            repository = SqliteRuntimeRepository(Path(directory) / "runtime.sqlite")
            manager = LocalRunManager(repository, DisconnectGraph())
            gateway = MiniDeerFlowGateway(
                manager,
                poll_interval=0.01,
                heartbeat_interval=0.05,
            )
            gateway.create_thread(
                # API DTO keeps ownership out of the caller-controlled body.
                CreateThreadRequest(thread_id="thread-disconnect"),
                user_id="learner",
            )
            run = gateway.start_run(
                "thread-disconnect",
                RunCreateRequest(
                    message="执行长任务",
                    on_disconnect="cancel",
                ),
                user_id="learner",
            )
            self.assertTrue(first_chunk_ready.wait(timeout=3))
            app = create_fastapi_app(
                gateway,
                identity_resolver=lambda _request: "learner",
            )
            stream_endpoint = next(
                route.endpoint
                for route in app.routes
                if getattr(route, "path", None)
                == "/threads/{thread_id}/runs/{run_id}/events"
            )
            response = stream_endpoint(
                thread_id="thread-disconnect",
                run_id=run.run_id,
                last_event_id=None,
                user_id="learner",
            )

            async def receive_first_frame_then_disconnect() -> str:
                first_frame = await anext(response.body_iterator)
                await response.body_iterator.aclose()
                return first_frame

            first_frame = asyncio.run(receive_first_frame_then_disconnect())
            deadline = time.monotonic() + 3
            while not manager.get_run(
                run.run_id,
                user_id="learner",
            ).cancel_requested:
                if time.monotonic() > deadline:
                    self.fail("HTTP stream close 未传播到 Run cancel policy")
                time.sleep(0.01)
            release_graph.set()
            cancelled = manager.wait(run.run_id, user_id="learner", timeout=3)
            manager.close()

            self.assertIn("event: metadata", first_frame)
            self.assertEqual(cancelled.status, RunStatus.cancelled)


if __name__ == "__main__":
    unittest.main()
