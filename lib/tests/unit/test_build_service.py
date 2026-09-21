"""`build_service` copies the API key from container_config onto the ORM row.

That copy is the one place a container_config field crosses into the service
row, and it is load bearing: the template gets the key via
`start(container_options=...)`, but the proxy reads it off the row. Without it
a service launches authenticated while every proxied request 401s. The CLI
tests stop at the mocked HTTP boundary, so this is the coverage for it (#534).
"""

from __future__ import annotations

class TestBuildServiceApiKey:
    """`build_service` is the one place a container_config field reaches the row.

    The template gets the key via `start(container_options=...)`, but the proxy
    reads it off the ORM row, so the copy in `build_service` is load bearing:
    without it a service launches authenticated while every proxied request
    401s. Covered here because the CLI tests stop at the mocked HTTP boundary.
    """

    def _build_request(self, image: str, api_key, **container_extra):
        from blackfish.server.asgi import ServiceRequest

        return ServiceRequest(
            name="svc",
            image=image,
            repo_id="openai/gpt-2",
            profile={
                "name": "default",
                "schema": "slurm",
                "host": "h",
                "user": "u",
                "home_dir": "/home/u",
                "cache_dir": "/cache",
            },
            container_config={
                "port": None,
                "model_dir": "/m",
                "revision": "main",
                "api_key": api_key,
                **container_extra,
            },
            job_config={
                "name": "svc",
                "time": "01:00:00",
                "ntasks_per_node": 1,
                "mem": 8,
                "gres": 1,
                "partition": None,
                "constraint": None,
            },
            mount=None,
            grace_period=600,
        )

    def test_api_key_reaches_the_orm_row(self):
        from blackfish.server.asgi import build_service

        service = build_service(self._build_request("text_generation", "sk-secret"))

        assert service._api_key == "sk-secret"
        assert service.auth_headers() == {"Authorization": "Bearer sk-secret"}

    def test_speech_recognition_key_uses_the_bare_token_header(self):
        """The two images disagree on the scheme; the row must dispatch right."""
        from blackfish.server.asgi import build_service

        service = build_service(self._build_request("speech_recognition", "sk-secret"))

        assert service.auth_headers() == {"Token": "sk-secret"}

    def test_no_key_leaves_the_row_unauthenticated(self):
        from blackfish.server.asgi import build_service

        service = build_service(self._build_request("text_generation", None))

        assert service._api_key is None
        assert service.auth_headers() == {}
        assert service.api_key_hint is None

