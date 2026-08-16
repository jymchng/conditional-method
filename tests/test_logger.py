import os
import subprocess
import sys

# The debug logger is implemented in C (conditional_method._c). Test it through the public
# debug / debug_enabled API and through the env-var-gated behavior.

ENV_KEY = "__conditional_method_debug__"


class TestLogger:
    def test_debug_enabled_false_by_default(self):
        """debug_enabled() is False when the env var is unset or 'false'."""
        original = os.environ.get(ENV_KEY)
        try:
            os.environ.pop(ENV_KEY, None)
            import importlib

            import conditional_method

            importlib.reload(conditional_method)
            assert conditional_method.debug_enabled() is False
        finally:
            if original is not None:
                os.environ[ENV_KEY] = original

    def test_debug_enabled_true_when_env_var_set(self):
        """debug_enabled() is True when the env var is set to a truthy value."""
        original = os.environ.get(ENV_KEY)
        try:
            os.environ[ENV_KEY] = "true"
            import importlib

            import conditional_method

            importlib.reload(conditional_method)
            assert conditional_method.debug_enabled() is True
        finally:
            if original is not None:
                os.environ[ENV_KEY] = original
            else:
                os.environ.pop(ENV_KEY, None)

    def test_debug_callable_does_not_raise_when_disabled(self):
        """conditional_method.debug(...) must not raise when debug is disabled."""
        original = os.environ.get(ENV_KEY)
        try:
            os.environ.pop(ENV_KEY, None)
            import importlib

            import conditional_method

            importlib.reload(conditional_method)
            assert conditional_method.debug("hello") is None
            assert conditional_method.debug("a", "b") is None
        finally:
            if original is not None:
                os.environ[ENV_KEY] = original

    def test_debug_logs_to_stderr_when_enabled(self):
        """When debug is enabled, conditional_method.debug prints to stderr."""
        original = os.environ.get(ENV_KEY)
        try:
            os.environ[ENV_KEY] = "true"
            code = "import conditional_method; conditional_method.debug('marker-xyz'); print('done')"
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"},
            )
            assert "marker-xyz" in proc.stderr
            assert "done" in proc.stdout
        finally:
            if original is not None:
                os.environ[ENV_KEY] = original
            else:
                os.environ.pop(ENV_KEY, None)
