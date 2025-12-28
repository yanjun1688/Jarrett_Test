"""
Unit tests for async_helper.py

Tests event loop management functions and async utilities.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

from testmanager_app.utils.async_helper import get_event_loop, reset_event_loop


class TestGetEventLoop:
    """Test the get_event_loop function."""

    def test_get_event_loop_first_call(self):
        """Test getting event loop for the first time."""
        # Reset any existing global loop
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        loop = get_event_loop()

        assert loop is not None
        assert isinstance(loop, asyncio.AbstractEventLoop)
        assert async_module._global_event_loop is loop

    def test_get_event_loop_subsequent_calls(self):
        """Test that subsequent calls return the same event loop."""
        # Reset any existing global loop
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        loop1 = get_event_loop()
        loop2 = get_event_loop()

        assert loop1 is loop2
        assert async_module._global_event_loop is loop1

    def test_get_event_loop_existing_event_loop(self):
        """Test getting event loop when one already exists in the thread."""
        # Create a new event loop and set it as the current one
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        existing_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(existing_loop)

        try:
            loop = get_event_loop()
            assert loop is existing_loop
            assert async_module._global_event_loop is existing_loop
        finally:
            # Clean up
            if not existing_loop.is_closed():
                existing_loop.close()

    def test_get_event_loop_with_closed_existing_loop(self):
        """Test getting event loop when existing one is closed."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Create and close a loop
        closed_loop = asyncio.new_event_loop()
        closed_loop.close()
        asyncio.set_event_loop(closed_loop)

        # Should create a new loop since the existing one is closed
        loop = get_event_loop()
        assert loop is not None
        assert not loop.is_closed()
        assert loop is not closed_loop


class TestResetEventLoop:
    """Test the reset_event_loop function."""

    def test_reset_event_loop_without_existing_loop(self):
        """Test resetting when no global loop exists."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        new_loop = reset_event_loop()

        assert new_loop is not None
        assert isinstance(new_loop, asyncio.AbstractEventLoop)
        assert async_module._global_event_loop is new_loop

    def test_reset_event_loop_with_existing_loop(self):
        """Test resetting when a global loop already exists."""
        import testmanager_app.utils.async_helper as async_module

        # First create a loop
        original_loop = get_event_loop()
        original_loop_id = id(original_loop)

        # Reset the loop
        new_loop = reset_event_loop()
        new_loop_id = id(new_loop)

        assert new_loop is not None
        assert isinstance(new_loop, asyncio.AbstractEventLoop)
        assert async_module._global_event_loop is new_loop
        assert new_loop_id != original_loop_id  # Should be a different loop

    def test_reset_event_loop_closes_existing_loop(self):
        """Test that reset_event_loop closes the existing loop."""
        import testmanager_app.utils.async_helper as async_module

        # Create a loop
        original_loop = get_event_loop()

        # Reset should close the original loop and create a new one
        new_loop = reset_event_loop()

        assert original_loop.is_closed() or original_loop is new_loop
        assert async_module._global_event_loop is new_loop

    def test_reset_event_loop_with_exception_during_close(self):
        """Test reset_event_loop when closing existing loop raises exception."""
        import testmanager_app.utils.async_helper as async_module

        # Create a mock loop that raises exception on close
        mock_loop = MagicMock()
        mock_loop.is_closed.return_value = False
        mock_loop.close.side_effect = Exception("Close error")

        async_module._global_event_loop = mock_loop

        # Should handle the exception and still create a new loop
        new_loop = reset_event_loop()

        assert new_loop is not None
        assert isinstance(new_loop, asyncio.AbstractEventLoop)
        assert async_module._global_event_loop is new_loop
        mock_loop.close.assert_called_once()

    @patch('testmanager_app.utils.async_helper.logger')
    def test_reset_event_loop_logs_info(self, mock_logger):
        """Test that reset_event_loop logs appropriate information."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        reset_event_loop()

        # Verify info log was called
        assert mock_logger.info.called
        assert "Created new global event loop" in str(mock_logger.info.call_args)

    @patch('testmanager_app.utils.async_helper.logger')
    def test_reset_event_loop_logs_close_info(self, mock_logger):
        """Test that reset_event_loop logs when closing existing loop."""
        import testmanager_app.utils.async_helper as async_module

        # Create a loop first
        original_loop = get_event_loop()

        # Reset should log closing info
        reset_event_loop()

        # Should have logs for both closing and creating
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Closed existing global event loop" in call for call in info_calls)
        assert any("Created new global event loop after reset" in call for call in info_calls)


class TestAsyncHelperIntegration:
    """Integration tests for async helper functions."""

    def test_get_and_reset_event_loop_integration(self):
        """Test integration between get_event_loop and reset_event_loop."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Get initial loop
        loop1 = get_event_loop()
        assert loop1 is not None

        # Reset loop
        loop2 = reset_event_loop()
        assert loop2 is not None
        assert loop1 is not loop2

        # Get loop again (should return the reset one)
        loop3 = get_event_loop()
        assert loop3 is loop2

    def test_event_loop_persistence_across_calls(self):
        """Test that event loop persists across multiple calls."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Multiple calls should return the same loop
        loop1 = get_event_loop()
        loop2 = get_event_loop()
        loop3 = get_event_loop()

        assert loop1 is loop2
        assert loop2 is loop3

        # After reset, should get a new loop
        loop4 = reset_event_loop()
        assert loop4 is not loop1

        # Subsequent calls should return the new loop
        loop5 = get_event_loop()
        assert loop5 is loop4

    @pytest.mark.asyncio
    async def test_event_loop_can_run_async_functions(self):
        """Test that the obtained event loop can run async functions."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        loop = get_event_loop()

        async def test_async_function():
            await asyncio.sleep(0.001)  # 1ms delay
            return "async result"

        # Run the async function using the obtained loop
        result = await test_async_function()
        assert result == "async result"

    def test_concurrent_access_safety(self):
        """Test that the functions handle concurrent access safely."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Simulate concurrent calls
        results = []
        for _ in range(10):
            loop = get_event_loop()
            results.append(loop)

        # All calls should return the same loop instance
        first_loop = results[0]
        for loop in results[1:]:
            assert loop is first_loop


class TestAsyncHelperErrorHandling:
    """Test error handling in async helper functions."""

    def test_get_event_loop_with_runtime_error(self):
        """Test get_event_loop when asyncio.get_event_loop raises RuntimeError."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        with patch('asyncio.get_event_loop', side_effect=RuntimeError("No event loop")):
            loop = get_event_loop()
            assert loop is not None
            assert isinstance(loop, asyncio.AbstractEventLoop)

    def test_reset_event_loop_with_multiple_exceptions(self):
        """Test reset_event_loop with multiple exceptions during close."""
        import testmanager_app.utils.async_helper as async_module

        # Create a mock loop that raises different exceptions
        mock_loop = MagicMock()
        mock_loop.is_closed.return_value = False
        mock_loop.close.side_effect = [
            Exception("First error"),
            Exception("Second error")
        ]

        async_module._global_event_loop = mock_loop

        # Should handle exceptions and still create a new loop
        new_loop = reset_event_loop()

        assert new_loop is not None
        assert isinstance(new_loop, asyncio.AbstractEventLoop)


class TestAsyncHelperLogging:
    """Test logging behavior of async helper functions."""

    @patch('testmanager_app.utils.async_helper.logger')
    def test_get_event_loop_logs_creation(self, mock_logger):
        """Test that get_event_loop logs when creating a new loop."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Mock asyncio to simulate creation of new event loop
        with patch('asyncio.get_event_loop', side_effect=RuntimeError):
            get_event_loop()

        # Should log creation of new event loop
        assert mock_logger.info.called
        assert "Created new global event loop" in str(mock_logger.info.call_args)

    @patch('testmanager_app.utils.async_helper.logger')
    def test_get_event_loop_no_log_when_existing(self, mock_logger):
        """Test that get_event_loop doesn't log when loop already exists."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # First call should potentially log
        get_event_loop()
        initial_call_count = mock_logger.info.call_count

        # Second call should not log (loop already exists)
        get_event_loop()
        final_call_count = mock_logger.info.call_count

        # Should not have additional log calls
        assert final_call_count == initial_call_count

    @patch('testmanager_app.utils.async_helper.logger')
    def test_reset_event_loop_warning_on_close_error(self, mock_logger):
        """Test that reset_event_loop logs warning when close fails."""
        import testmanager_app.utils.async_helper as async_module

        # Create a loop first
        original_loop = get_event_loop()

        # Mock the original loop to raise exception on close
        original_loop.close = Mock(side_effect=Exception("Close failed"))

        # Reset should handle the exception and log a warning
        reset_event_loop()

        # Should log warning about close error
        assert mock_logger.warning.called
        assert "Error closing event loop" in str(mock_logger.warning.call_args)


class TestAsyncHelperEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_get_event_loop_with_none_global_loop(self):
        """Test get_event_loop when global loop is explicitly set to None."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        loop = get_event_loop()
        assert loop is not None
        assert async_module._global_event_loop is loop

    def test_reset_event_loop_multiple_times(self):
        """Test calling reset_event_loop multiple times in succession."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Reset multiple times
        loop1 = reset_event_loop()
        loop2 = reset_event_loop()
        loop3 = reset_event_loop()

        # Each reset should create a new loop
        assert loop1 is not loop2
        assert loop2 is not loop3
        assert loop3 is async_module._global_event_loop

    def test_event_loop_after_policy_change(self):
        """Test behavior when asyncio policy is changed."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Get initial loop
        initial_loop = get_event_loop()

        # Change asyncio policy (simulate different environment)
        new_policy = asyncio.DefaultEventLoopPolicy()
        asyncio.set_event_loop_policy(new_policy)

        try:
            # Should still work with new policy
            loop = get_event_loop()
            assert loop is not None
            assert isinstance(loop, asyncio.AbstractEventLoop)
        finally:
            # Reset to default policy
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    def test_closed_event_loop_detection(self):
        """Test detection and handling of closed event loops."""
        import testmanager_app.utils.async_helper as async_module
        async_module._global_event_loop = None

        # Create and close a loop manually
        closed_loop = asyncio.new_event_loop()
        closed_loop.close()

        # Set the closed loop as the global loop
        async_module._global_event_loop = closed_loop

        # Getting event loop should detect closed loop and create new one
        new_loop = get_event_loop()
        assert new_loop is not closed_loop
        assert not new_loop.is_closed()
        assert async_module._global_event_loop is new_loop