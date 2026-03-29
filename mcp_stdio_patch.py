def patch():
    import mcp.server.stdio as _stdio_mod
    from contextlib import asynccontextmanager
    from io import TextIOWrapper
    import sys
    import anyio
    import anyio.lowlevel
    from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
    import mcp.types as types
    from mcp.shared.message import SessionMessage

    @asynccontextmanager
    async def _patched_stdio_server(stdin=None, stdout=None):
        if not stdin:
            stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8"))
        if not stdout:
            stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))

        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

        async def stdin_reader():
            try:
                async with read_stream_writer:
                    async for line in stdin:
                        if not line.strip():
                            continue
                        try:
                            message = types.JSONRPCMessage.model_validate_json(line)
                        except Exception as exc:
                            await read_stream_writer.send(exc)
                            continue
                        session_message = SessionMessage(message)
                        await read_stream_writer.send(session_message)
            except anyio.ClosedResourceError:
                await anyio.lowlevel.checkpoint()

        async def stdout_writer():
            try:
                async with write_stream_reader:
                    async for session_message in write_stream_reader:
                        json_str = session_message.message.model_dump_json(
                            by_alias=True, exclude_none=True
                        )
                        await stdout.write(json_str + "\n")
                        await stdout.flush()
            except anyio.ClosedResourceError:
                await anyio.lowlevel.checkpoint()

        async with anyio.create_task_group() as tg:
            tg.start_soon(stdin_reader)
            tg.start_soon(stdout_writer)
            yield read_stream, write_stream

    _stdio_mod.stdio_server = _patched_stdio_server

    import mcp.server.fastmcp.server as _fastmcp_mod

    setattr(_fastmcp_mod, "stdio_server", _patched_stdio_server)
