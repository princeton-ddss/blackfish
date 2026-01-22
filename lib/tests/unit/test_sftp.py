"""Unit tests for remote file operations."""

import pytest
from unittest import mock

from litestar.exceptions import NotFoundException, ValidationException

from blackfish.server.sftp import get_remote_profile
from blackfish.server.models.profile import SlurmProfile, LocalProfile


class TestGetRemoteProfile:
    def test_get_remote_profile_success(self):
        remote_profile = SlurmProfile(
            name="remote",
            host="remote.example.com",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        with mock.patch(
            "blackfish.server.sftp.deserialize_profile",
            return_value=remote_profile,
        ):
            result = get_remote_profile("remote")
            assert result == remote_profile

    def test_get_remote_profile_not_found(self):
        with mock.patch(
            "blackfish.server.sftp.deserialize_profile",
            return_value=None,
        ):
            with pytest.raises(NotFoundException):
                get_remote_profile("nonexistent")

    def test_get_remote_profile_file_not_found(self):
        with mock.patch(
            "blackfish.server.sftp.deserialize_profile",
            side_effect=FileNotFoundError(),
        ):
            with pytest.raises(NotFoundException):
                get_remote_profile("nonexistent")

    def test_get_remote_profile_local_profile(self):
        local_profile = LocalProfile(
            name="local",
            home_dir="/home/local",
            cache_dir="/home/local/.cache",
        )

        with mock.patch(
            "blackfish.server.sftp.deserialize_profile",
            return_value=local_profile,
        ):
            with pytest.raises(ValidationException):
                get_remote_profile("local")

    def test_get_remote_profile_localhost_slurm(self):
        localhost_profile = SlurmProfile(
            name="localhost",
            host="localhost",
            user="testuser",
            home_dir="/home/testuser",
            cache_dir="/home/testuser/.cache",
        )

        with mock.patch(
            "blackfish.server.sftp.deserialize_profile",
            return_value=localhost_profile,
        ):
            with pytest.raises(ValidationException):
                get_remote_profile("localhost")
