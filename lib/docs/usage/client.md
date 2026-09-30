# Python API

While the Blackfish CLI and UI are convenient for interactive, time-limited, or small-scale projects, they can prove quite awkward for workflows that require automation and/or might run for more than a few hours. For this reason, Blackfish provides a Python API for managing services directly from Python scripts, *without* requiring the REST API server to be running. This allows users to, for example, define tasks that make requests to a text generation service as part of a larger orchestration script.

We provide synchronous and asynchronous APIs.

!!! info "Full signatures"

    This guide walks through the client by example. For every method,
    parameter and return type, see the generated
    [API reference](../developer/api/core.md).

## Synchronous API

The synchronous API is the simplest way to use Blackfish in Python scripts:

```python
from blackfish import Blackfish, ManagedService

# Initialize the client
bf = Blackfish(debug=True)

# Create a service
service = bf.launch_service(
    name="tiny-llama-service",
    image="text_generation",
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    job_config={
        "name": "tiny-llama-service",
        "time": "01:00:00",
        "mem": 8,
        "gres": 1,
    }
)

# Wait for service
result = service.wait(timeout=300)
if result:
    print("Yipee!")
else:
    print(f"Shucks! ({result.outcome})")

# List all services
services = bf.list_services()
for svc in services:
    print(f"{svc.id}: {svc.status}")

# Refresh service status
service.refresh()
if service.status == "healthy":
    print("All good!")
else:
    print("Peanuts.")

# Stop and clean up
service.stop()
service.delete()
bf.close()
```

## Asynchronous API

For async applications, use the async methods (prefixed with `async_`):

```python
import asyncio
from blackfish import Blackfish

async def main():
    async with Blackfish() as bf:
        # Create a service
        service = await bf.async_launch_service(
            name="tiny-llama-service",
            image="text_generation",
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            job_config={
                "name": "tiny-llama-service",
                "time": "01:00:00",
                "mem": 8,
                "gres": 1,
            }
        )

        # List services
        services = await bf.async_list_services()

        # Stop and clean up
        await service.async_stop()
        await service.async_delete()

asyncio.run(main())
```

## Progress Output

The Python API is silent by default. Its primary use is a long-running script
that supervises its own service, often under `sbatch`, where a polling loop
would otherwise write thousands of progress lines into the job's output file.

In a notebook or REPL, where watching a service start is useful, opt in:

```python
bf = Blackfish(progress=True)
```

Every service created by that client reports progress for `launch_service`,
`wait`, `refresh`, `stop`, `close_tunnel` and `delete`.

!!! note

    Creating a client does not change your logging configuration. Use
    `set_logging_level()` to control Blackfish's log output, independently of
    the `progress` setting.

## Resource Management

### Services

Blackfish launches services running on external resources. Generally, you will want to tie the lifetime of services to the lifetime of your Python script to ensure that external resources are released. This is the default behavior for services.

In some cases, however, you may want services to outlive your script. To accomplish this, simply set `auto_cleanup=False`:

```python
bf.launch_service(..., auto_cleanup=False)
```

#### Cleanup after a crash

Cleanup distinguishes a clean exit from a crash. If your script exits normally,
every tracked service is stopped and deleted. If it exits because of an
unhandled exception, **healthy** services are left running and their ids are
printed to stderr.

The reasoning is that a script which crashes is likely to be re-run, and a
healthy service is an asset: destroying it means queueing again for something
that was working seconds earlier. Services that are not healthy are cleaned up
either way.

Services left behind this way are yours to manage. The message names each one
with the command to stop it:

```
⚠ Blackfish left 1 healthy service(s) running because the script is exiting on an error.
  - 20054b7c-7600-4c4e-9dde-d893333ca8b1 (still running): blackfish service stop 20054b7c-7600-4c4e-9dde-d893333ca8b1
```

If a service cannot be stopped — an SSH failure during shutdown, for instance —
the remaining services are still cleaned up, and the failures are reported the
same way rather than silently leaving an allocation running.

### Client

Use context managers for automatic cleanup of the Blackfish client:

```python
# Sync context manager
with Blackfish() as bf:
    service = bf.launch_service(...)
    # Connection closes automatically

# Async context manager
async with Blackfish() as bf:
    service = await bf.async_launch_service(...)
    # Connection closes automatically
```

Or manually (with sync API):

```python
bf = Blackfish()
# ... do work ...
bf.close()
```

## Service Objects

The `ManagedService` type wraps a `Service` that should always point to a service that is tracked by the Blackfish database. This means that Blackfish will not lose track of your service even if your Python session crashes[^1]. You can access the internal service's attributes exactly as if you were working with the underlying `Service`:

```python
print(f"Service: {service.id}")
print(f"Status: {service.status}")
print(f"Host: {service.host}")
print(f"Port: {service.port}")
```

### Reaching a Service

To send requests to a service, use `service.url`:

```python
from openai import OpenAI

client = OpenAI(base_url=f"{service.url}/v1", api_key="EMPTY")
```

`url` is always a `localhost` address. For a Slurm service, requests travel
through an SSH tunnel, so `service.host` is the cluster's **login node**, not
where requests go — building a URL from `host` and `port` will not reach the
service.

Services expose several endpoints, so `url` is a base URL to hand to a client
library rather than a complete request path. Text generation runs vLLM's
OpenAI-compatible server, hence the `/v1` suffix above.

A service only has an address once its tunnel is open, which happens while the
job starts. Requesting `url` before then, or after the tunnel has been closed,
raises `ServiceNotReachableError`, so wait for the service to become healthy
first:

```python
if service.wait():
    client = OpenAI(base_url=f"{service.url}/v1", api_key="EMPTY")
```

Note that a recorded port means a tunnel was opened, not that it is still up.
`stop()` closes the tunnel and clears the port, but a job that dies on its own
is only noticed on the next `refresh()`. Until then `url` returns the service's
last known address, which may no longer connect.

!!! note

    The status of a service should be understood as the most recently observed status of that service. The current status of a service is only known to the external system running the service, e.g., Slurm. To update the status of a service, use `service.refresh()`.

After a service is deleted, however, the internal service is no longer valid and is therefore set to `None`. At this point, attempting to access the service's attributes will produce a runtime error:

```python
>>> service.delete()
✔ Service deleted: 20054b7c-7600-4c4e-9dde-d893333ca8b1
True
>>> service.id
RuntimeError: This service has been deleted and can no longer be accessed.
```

## Supervising a Service

A script that runs longer than its scheduler allocation cannot simply start a
service and use it: the allocation expires partway through. Asking for an
allocation long enough to cover the whole script usually means it is never
scheduled at all.

`ensure_healthy()` is the primitive for this. Call it before each unit of work
and it brings the service back if it has gone away:

```python
from openai import OpenAI

service = bf.launch_service(
    name="llm",
    image="text_generation",
    model="meta-llama/Llama-3.3-70B-Instruct",
    job_config={"time": "04:00:00", "mem": 64, "gres": 1},
)

for chunk in workload:
    service.ensure_healthy()
    client = OpenAI(base_url=f"{service.url}/v1", api_key="EMPTY")
    process(chunk, client)
```

The check is cheap when the service is fine: `refresh()` pings the service
first and only asks the scheduler if the ping fails, so the common case costs
one local HTTP request. A failed ping falls through to the scheduler, which is
also what re-opens a tunnel that has dropped.

A service that is merely **queued** is waited on, not restarted. Cancelling and
resubmitting a pending job would only send it to the back of the queue, so
waiting is the correct response and does not consume the restart budget.

`max_restarts` bounds how many relaunches are attempted (default 3) so a model
that never loads cannot burn allocations indefinitely. Exhausting it raises
`RestartLimitExceeded`:

```python
from blackfish import RestartLimitExceeded

try:
    service.ensure_healthy(max_restarts=5)
except RestartLimitExceeded as e:
    print(f"Giving up after {e.max_restarts} attempts; check the job logs.")
```

Restarts replay the arguments the service was launched with, so you do not have
to keep them in sync yourself. `restart()` is also available directly.

!!! note

    Only services created by `launch_service` can restart themselves. One
    retrieved with `get_service()` or `list_services()` has no launch spec, so
    `restart()` and `ensure_healthy()` raise on it.

## Waiting for a Service

`wait()` blocks until a service becomes healthy and returns a `WaitResult`
describing what happened. The result is falsy unless the service became
healthy, so it can be tested directly:

```python
result = service.wait(timeout=300)
if result:
    print(f"Ready on port {service.port}")
```

Four outcomes are possible, available as `result.outcome`:

| Outcome | Meaning |
| --- | --- |
| `HEALTHY` | The service came up. |
| `FAILED` | The service reached a terminal state (`FAILED`, `TIMEOUT` or `STOPPED`). |
| `TIMEOUT_PENDING` | Gave up while the job was still queued; the scheduler had not run it. |
| `TIMEOUT_STARTING` | Gave up after the job started but before the service answered. |

The two `TIMEOUT_*` outcomes mean *you* ran out of patience, not that anything
is wrong. They are only reachable when `wait()` is given a maximum waiting
time; passing `timeout=None` waits indefinitely, so only `HEALTHY` and
`FAILED` can occur.

The distinction matters because the outcomes warrant different responses. A
`TIMEOUT_PENDING` service is queued and will run, so waiting longer is usually
right — cancelling and resubmitting only returns it to the back of the queue:

```python
from blackfish import WaitOutcome

result = service.wait(timeout=600)
while result.outcome is WaitOutcome.TIMEOUT_PENDING:
    print(f"Still queued after {result.elapsed:.0f}s; waiting longer")
    result = service.wait(timeout=600)
```

!!! note

    `timeout` is how long `wait()` keeps polling, not a limit on the service.
    When it expires the service keeps running. To limit the service itself,
    set the job's time limit with `job_config={"time": "01:00:00"}`.

## Examples

### Monitoring Services

```python
from blackfish import Blackfish, ServiceStatus

def monitor_services(bf: Blackfish):
    """Print status of all active services."""
    services = bf.list_services()

    active = [s for s in services if s.status == ServiceStatus.HEALTHY]

    print(f"Active services: {len(active)}")
    for service in active:
        print(f"  > {service.id}: {service.host}:{service.port}")

with Blackfish() as bf:
    monitor_services(bf)
```

### Concurrent Service Creation (Async)

```python
import asyncio
from blackfish import Blackfish

async def create_multiple_services():
    async with Blackfish() as bf:
        tasks = [
            bf.async_launch_service(
                name=f"service-1",
                image="text_generation",
                model="meta-llama/Llama-3.3-70B-Instruct",
                profile_name="default"
            ),
            bf.async_launch_service(
                name=f"service-2",
                image="text_generation",
                model="meta-llama/Llama-3.3-70B-Instruct",
                profile_name="default"
            ),
        ]

        services = await asyncio.gather(*tasks)
        print(f"Created {len(services)} services")

        for service in services:
            print(f"  {service.name}: {service.id}")

asyncio.run(create_multiple_services())
```

## Troubleshooting

### Service won't start

Enable debug logging and check the service status:

```python
from blackfish import set_logging_level

set_logging_level("debug")

service = bf.get_service(service_id)
print(f"Status: {service.status}")

job = service._service.get_job(verbose=True)
if job:
    print(f"Job state: {job.state}")
```

### Database connection issues

Ensure Blackfish is initialized:

```bash
blackfish init
```

And verify that the home directory `~/.blackfish` exists.

[^1]: If `auto_cleanup=False`. Otherwise, Blackfish automatically deletes services on shutdown.
