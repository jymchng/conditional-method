import os
import sys
import pytest
import logging
from io import StringIO


# Always set up basic logging configuration for these tests
@pytest.fixture(autouse=True)
def configure_logging():
    """Set up logging to capture output"""
    # Configure logging before tests
    root = logging.getLogger()

    # Store original level
    original_level = root.level

    # Set to DEBUG
    root.setLevel(logging.DEBUG)

    # Capture log output
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Store original handlers
    original_handlers = root.handlers.copy()

    # Clear existing handlers
    root.handlers = []

    # Add capture handler
    root.addHandler(handler)

    yield log_capture

    # Restore original logging setup
    root.handlers = original_handlers
    root.setLevel(original_level)


class TestDebugMode:
    """Tests specifically focused on the debug environment variable functionality"""

    def test_debug_env_var_true_enables_logging(self, configure_logging):
        """Test that setting environment variable to true enables logging"""
        # Store original value
        original_value = os.environ.get("__conditional_method_debug__", None)

        try:
            # Set environment variable to true
            os.environ["__conditional_method_debug__"] = "true"

            # Import to trigger logger initialization
            import importlib

            # Clear any existing imports
            if "conditional_method" in sys.modules:
                del sys.modules["conditional_method"]
            if "conditional_method._logger" in sys.modules:
                del sys.modules["conditional_method._logger"]

            # Force reload with new environment
            import conditional_method._logger

            importlib.reload(conditional_method._logger)

            # Trigger log message
            from conditional_method._logger import logger

            logger.debug("This is a test debug message")

            # Check captured output
            log_output = configure_logging.getvalue()
            assert "This is a test debug message" in log_output
            assert "conditional_method - DEBUG" in log_output

        finally:
            # Restore original value
            if original_value is None:
                if "__conditional_method_debug__" in os.environ:
                    del os.environ["__conditional_method_debug__"]
            else:
                os.environ["__conditional_method_debug__"] = original_value

    def test_debug_env_var_false_disables_logging(self, configure_logging):
        """Test that setting environment variable to false disables logging"""
        # Store original value
        original_value = os.environ.get("__conditional_method_debug__", None)

        try:
            # Set environment variable to false
            os.environ["__conditional_method_debug__"] = "false"

            # Import to trigger logger initialization
            import importlib

            # Clear any existing imports
            if "conditional_method" in sys.modules:
                del sys.modules["conditional_method"]
            if "conditional_method._logger" in sys.modules:
                del sys.modules["conditional_method._logger"]

            # Force reload with new environment
            import conditional_method._logger

            importlib.reload(conditional_method._logger)

            # Trigger log message
            from conditional_method._logger import logger

            # Clear capture buffer
            configure_logging.truncate(0)
            configure_logging.seek(0)

            # Log a message with the noop logger
            logger.debug("This message should not appear")

            # Check captured output
            log_output = configure_logging.getvalue()
            assert "This message should not appear" not in log_output
            assert log_output == ""  # Should be empty

        finally:
            # Restore original value
            if original_value is None:
                if "__conditional_method_debug__" in os.environ:
                    del os.environ["__conditional_method_debug__"]
            else:
                os.environ["__conditional_method_debug__"] = original_value

    def test_debug_mode_in_conditional_methods(self, configure_logging):
        """Test that debug logs appear when using conditional methods"""
        from conditional_method import conditional_method

        # Store original value
        original_value = os.environ.get("__conditional_method_debug__", None)

        try:
            # Set environment variable to true
            os.environ["__conditional_method_debug__"] = "true"

            # Import to trigger logger initialization
            import importlib

            # Clear any existing imports related to logger
            if "conditional_method._logger" in sys.modules:
                del sys.modules["conditional_method._logger"]

            # Force reload with new environment
            import conditional_method._logger as logger

            importlib.reload(logger)

            # Define a test class using conditional methods
            class TestClass:
                @conditional_method(condition=True)
                def test_method(self):
                    logger.logger.debug("This is a test debug message")
                    return "TestClass::test_method"

            # Clear capture buffer
            configure_logging.truncate(0)
            configure_logging.seek(0)

            # Instantiate and use the class to trigger logging
            test_instance = TestClass()
            result = test_instance.test_method()
            assert result == "TestClass::test_method"

            # Check captured output
            log_output = configure_logging.getvalue()

            # Verify log output contains Dispatcher debug information
            assert "This is a test debug message" in log_output

        finally:
            # Restore original value
            if original_value is None:
                if "__conditional_method_debug__" in os.environ:
                    del os.environ["__conditional_method_debug__"]
            else:
                os.environ["__conditional_method_debug__"] = original_value
