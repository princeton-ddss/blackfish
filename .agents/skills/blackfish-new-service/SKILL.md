---
name: blackfish-new-service
description: Add a Blackfish service across backend, CLI, frontend, and tests when implementing a new service type.
---

Paths and commands below are relative to the repository root unless a working directory is specified.

Help me create a new service for the Blackfish platform.

Use the service name supplied in the request. Clarify it before creating files if it is missing.

Guide me through creating:
1. Service class in `lib/src/blackfish/server/services/` following the existing `Service` subclasses
2. API routes in `lib/src/blackfish/server/asgi.py`
3. CLI commands in `lib/src/blackfish/cli/services/`
4. Frontend route in `web/src/routes/{service-name}/` (registered in `web/src/router.jsx`)
5. Tests for the new service

First, examine the existing services (text_generation, speech_recognition) to understand the patterns, then create the new service following those patterns.
