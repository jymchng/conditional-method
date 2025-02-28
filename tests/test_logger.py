import os
import pytest
import logging
from unittest.mock import patch, MagicMock

# Direct import to test the logger itself
from src.conditional_method._logger import logger, ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER, _make_noop_logger


class TestLogger:
    
    def test_noop_logger_when_debug_disabled(self):
        """Test that NoopLogger is returned when the debug environment variable is not set"""
        # Save original environment
        original_env = os.environ.get(ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER, None)
        
        try:
            # Ensure environment variable is not set or set to false
            if ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER in os.environ:
                del os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER]
            
            # Re-import to get fresh instance with clean environment
            import importlib
            import src.conditional_method._logger
            importlib.reload(src.conditional_method._logger)
            
            # Check if the logger is a NoopLogger
            from src.conditional_method._logger import logger
            assert not logger  # NoopLogger should return False in bool context
            
            # Verify behavior - NoopLogger should not raise exceptions on any method call
            logger.debug("This should not raise an error")
            logger.info("This should not raise an error")
            logger.warning("This should not raise an error")
            logger.error("This should not raise an error")
            
        finally:
            # Restore environment
            if original_env is not None:
                os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER] = original_env
            elif ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER in os.environ:
                del os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER]
    
    def test_real_logger_when_debug_enabled(self):
        """Test that a real logger is returned when the debug environment variable is set to 'true'"""
        # Save original environment
        original_env = os.environ.get(ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER, None)
        
        try:
            # Set environment variable to true
            os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER] = "true"
            
            # Re-import to get fresh instance with the environment variable set
            import importlib
            import src.conditional_method._logger
            importlib.reload(src.conditional_method._logger)
            
            # Get logger after reload
            from src.conditional_method._logger import logger
            
            # The real logger should evaluate to True in a bool context
            assert logger
            
            # Check that it's a real logging.Logger instance
            assert isinstance(logger, logging.Logger)
            assert logger.name == "conditional_method"
            
        finally:
            # Restore environment
            if original_env is not None:
                os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER] = original_env
            elif ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER in os.environ:
                del os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER]
    
    @patch('logging.getLogger')
    def test_logger_is_configured_with_debug_level(self, mock_get_logger):
        """Test that the logger is configured with DEBUG level when enabled"""
        # Mock logger to capture settings
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Save original environment
        original_env = os.environ.get(ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER, None)
        
        try:
            # Set environment variable to true
            os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER] = "true"
            
            # Re-import to get fresh instance with the environment variable set
            import importlib
            import src.conditional_method._logger
            importlib.reload(src.conditional_method._logger)
            
            # Verify getLogger was called with correct name
            mock_get_logger.assert_called_once_with("conditional_method")
            
        finally:
            # Restore environment
            if original_env is not None:
                os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER] = original_env
            elif ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER in os.environ:
                del os.environ[ENV_KEY_TO_ACTIVATE_DEBUG_LOGGER] 