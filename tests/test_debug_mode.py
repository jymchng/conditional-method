import os
import subprocess
import sys

# The debug logger is implemented in C (conditional_method._c). These tests exercise the
# env-var-gated behavior through conditional_method.debug / conditional_method.debug_enabled.

ENV_KEY = "__conditional_method_debug__"


class TestDebugMode:
    def test_debug_env_var_true_enables_logging(self):
        """Setting the env var to a truthy value enables debug logging."""
        original = os.environ.get(ENV_KEY)
        try:
            os.environ[ENV_KEY] = "true"
            import importlib

            import conditional_method

            importlib.reload(conditional_method)
            assert conditional_method.debug_enabled() is True
            # debug() writes a marker to stderr
            code = "import conditional_method; conditional_method.debug('marker-abc-123')"
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"},
            )
            assert "marker-abc-123" in proc.stderr
            assert "DEBUG" in proc.stderr
        finally:
            if original is not None:
                os.environ[ENV_KEY] = original
            else:
                os.environ.pop(ENV_KEY, None)

    def test_debug_env_var_false_disables_logging(self):
        """Setting the env var to 'false' disables debug logging."""
        original = os.environ.get(ENV_KEY)
        try:
            os.environ[ENV_KEY] = "false"
            import importlib

            import conditional_method

            importlib.reload(conditional_method)
            assert conditional_method.debug_enabled() is False
            code = "import conditional_method; conditional_method.debug('should-not-appear')"
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"},
            )
            assert "should-not-appear" not in proc.stderr
        finally:
            if original is not None:
                os.environ[ENV_KEY] = original
            else:
                os.environ.pop(ENV_KEY, None)

    def test_debug_mode_in_conditional_methods(self):
        """Debug logs appear when a conditional method calls conditional_method.debug."""

        original = os.environ.get(ENV_KEY)
        try:
            os.environ[ENV_KEY] = "true"
            import importlib

            import conditional_method as cfgmod

            importlib.reload(cfgmod)

            code = (
                "import conditional_method\n"
                "class TestClass:\n"
                "    @conditional_method.cfg(condition=True)\n"
                "    def test_method(self):\n"
                "        conditional_method.debug('inside-method-xyz')\n"
                "        return 'TestClass::test_method'\n"
                "assert TestClass().test_method() == 'TestClass::test_method'\n"
            )
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"},
            )
            assert "inside-method-xyz" in proc.stderr
            assert proc.stdout.strip() == ""
        finally:
            if original is not None:
                os.environ[ENV_KEY] = original
            else:
                os.environ.pop(ENV_KEY, None)
