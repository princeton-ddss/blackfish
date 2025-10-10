from unittest.mock import patch, MagicMock
from click.testing import CliRunner


from app.cli.__main__ import stop


class TestStopCLI:
    """Test cases for the blackfish stop CLI command."""

    def test_stop_with_full_uuid(self):
        """Test stopping a service with a full UUID."""
        runner = CliRunner()
        full_uuid = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        # Mock the PUT request to the stop endpoint
        with patch("app.cli.__main__.requests.put") as mock_put:
            mock_put.return_value.ok = True
            mock_put.return_value.status_code = 200

            result = runner.invoke(stop, [full_uuid])

            assert result.exit_code == 0
            mock_put.assert_called_once_with(
                f"http://localhost:8000/api/services/{full_uuid}/stop", json={}
            )

    def test_stop_with_abbreviated_id_single_match(self):
        """Test stopping a service with an abbreviated ID that matches exactly one service."""
        runner = CliRunner()
        abbreviated_id = "4c2216ea"
        full_uuid = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        # Mock the GET request to fetch services
        mock_get_response = MagicMock()
        mock_get_response.ok = True
        mock_get_response.json.return_value = [
            {"id": full_uuid, "name": "test-service"}
        ]

        # Mock the PUT request to stop the service
        mock_put_response = MagicMock()
        mock_put_response.ok = True
        mock_put_response.status_code = 200

        with (
            patch(
                "app.cli.__main__.requests.get", return_value=mock_get_response
            ) as mock_get,
            patch(
                "app.cli.__main__.requests.put", return_value=mock_put_response
            ) as mock_put,
        ):
            result = runner.invoke(stop, [abbreviated_id])

            assert result.exit_code == 0
            mock_get.assert_called_once_with("http://localhost:8000/api/services")
            mock_put.assert_called_once_with(
                f"http://localhost:8000/api/services/{full_uuid}/stop", json={}
            )

    def test_stop_with_abbreviated_id_multiple_matches(self):
        """Test stopping a service with an abbreviated ID that matches multiple services."""
        runner = CliRunner()
        abbreviated_id = "4c"

        # Mock the GET request to return multiple matching services
        mock_get_response = MagicMock()
        mock_get_response.ok = True
        mock_get_response.json.return_value = [
            {"id": "4c2216ea-df22-4bf6-bcea-56964df12af5", "name": "test-service-1"},
            {"id": "4c3456ea-df22-4bf6-bcea-56964df12af5", "name": "test-service-2"},
        ]

        with patch(
            "app.cli.__main__.requests.get", return_value=mock_get_response
        ) as mock_get:
            result = runner.invoke(stop, [abbreviated_id])

            assert result.exit_code == 0
            mock_get.assert_called_once_with("http://localhost:8000/api/services")
            # Should show an error message about multiple matches
            assert "Multiple services match" in result.output

    def test_stop_with_abbreviated_id_no_matches(self):
        """Test stopping a service with an abbreviated ID that matches no services."""
        runner = CliRunner()
        abbreviated_id = "xyz123"

        # Mock the GET request to return no matching services
        mock_get_response = MagicMock()
        mock_get_response.ok = True
        mock_get_response.json.return_value = []

        with patch(
            "app.cli.__main__.requests.get", return_value=mock_get_response
        ) as mock_get:
            result = runner.invoke(stop, [abbreviated_id])

            assert result.exit_code == 0
            mock_get.assert_called_once_with("http://localhost:8000/api/services")
            # Should show an error message about no matches
            assert "No service found matching" in result.output

    def test_stop_service_fetch_error(self):
        """Test handling of errors when fetching services list."""
        runner = CliRunner()
        abbreviated_id = "4c2216ea"

        # Mock the GET request to fail
        mock_get_response = MagicMock()
        mock_get_response.ok = False
        mock_get_response.status_code = 500

        with patch(
            "app.cli.__main__.requests.get", return_value=mock_get_response
        ) as mock_get:
            result = runner.invoke(stop, [abbreviated_id])

            assert result.exit_code == 0
            mock_get.assert_called_once_with("http://localhost:8000/api/services")
            # Should show an error message about fetching services
            assert "Failed to fetch services" in result.output

    def test_stop_service_api_error(self):
        """Test handling of errors when stopping a service."""
        runner = CliRunner()
        full_uuid = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        # Mock the PUT request to fail
        mock_put_response = MagicMock()
        mock_put_response.ok = False
        mock_put_response.status_code = 404

        with patch(
            "app.cli.__main__.requests.put", return_value=mock_put_response
        ) as mock_put:
            result = runner.invoke(stop, [full_uuid])

            assert result.exit_code == 0
            mock_put.assert_called_once_with(
                f"http://localhost:8000/api/services/{full_uuid}/stop", json={}
            )
            # Should show an error message about stopping the service
            assert "Failed to stop service" in result.output

    def test_stop_with_short_abbreviated_id(self):
        """Test stopping a service with a very short abbreviated ID."""
        runner = CliRunner()
        abbreviated_id = "4c22"
        full_uuid = "4c2216ea-df22-4bf6-bcea-56964df12af5"

        # Mock the GET request to fetch services
        mock_get_response = MagicMock()
        mock_get_response.ok = True
        mock_get_response.json.return_value = [
            {"id": full_uuid, "name": "test-service"},
            {"id": "5d2216ea-df22-4bf6-bcea-56964df12af5", "name": "other-service"},
        ]

        # Mock the PUT request to stop the service
        mock_put_response = MagicMock()
        mock_put_response.ok = True
        mock_put_response.status_code = 200

        with (
            patch(
                "app.cli.__main__.requests.get", return_value=mock_get_response
            ) as mock_get,
            patch(
                "app.cli.__main__.requests.put", return_value=mock_put_response
            ) as mock_put,
        ):
            result = runner.invoke(stop, [abbreviated_id])

            assert result.exit_code == 0
            mock_get.assert_called_once_with("http://localhost:8000/api/services")
            mock_put.assert_called_once_with(
                f"http://localhost:8000/api/services/{full_uuid}/stop", json={}
            )
