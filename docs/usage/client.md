# Python API

While the Blackfish CLI and UI are convenient for interactive, time-limited, or small-scale projects, they can prove quite awkward for workflows that require automation and/or might run for more than a few hours.

For this reason, Blackfish provides a Python API for managing services directly from Python scripts, *without* requiring the REST API server to be running. This allows users to, for example, define tasks that make requests to a text generation service as part of a larger orchestration script.

We provide synchronous and asynchronous APIs.

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
service.wait(timeout=300)
if service.status == "healthy":
    print("Yipee!")
else:
    print("Shucks!")

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

For async applications, use the async methods (prefixed with `async`):

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

## Resource Management

### Services

Blackfish launches services running on external resources. Generally, you will want to tie the lifetime of services to the lifetime of your Python script to ensure that external resources are released. This is the default behavior for services.

In some cases, however, you may want services to outlive your script. To accomplish this, simply set `auto_cleanup=False`:

```python
bf.launch_service(..., auto_cleanup=False)
```

### Client

Use context managers for automatic cleanup of the Blackfish client:

```python
# Sync context manager
with Blackfish() as bf:
    service = bf.create_service(...)
    # Connection closes automatically

# Async context manager
async with Blackfish() as bf:
    service = await bf.acreate_service(...)
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

!!! note

    The status of a service should be understood as the most recently observed status of that service. The current status of a service only known to the external system running the service, e.g., Slurm. To update the status of a service, use `service.refresh()`.

After a service is deleted, however, the internal service is no longer valid and is therefore set to `None`. At this point, attempting to access the service's attributes will produce a runtime error:

```python
>>> service.delete()
✔ Service deleted: 20054b7c-7600-4c4e-9dde-d893333ca8b1
True
>>> service.id
---------------------------------------------------------------------------
RuntimeError                              Traceback (most recent call last)
Cell In[9], line 1
----> 1 s.status

File ~/GitHub/blackfish/src/blackfish/__init__.py:83, in ManagedService.__getattr__(self, name)
     81 """Delegate attribute access to the underlying service."""
     82 if self._service is None:
---> 83     raise RuntimeError("This service has been deleted and can no longer be accessed.")
     84 return getattr(self._service, name)

RuntimeError: This service has been deleted and can no longer be accessed.
```

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
            bf.async_create_service(
                name=f"service-1",
                image="text_generation",
                model="meta-llama/Llama-3.3-70B-Instruct",
                profile_name="default"
            ),
            bf.async_create_service(
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

[^1]: If `auto_clean=False`. Otherwise, Blackfish automatically deletes services on shutdown.
