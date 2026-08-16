import os
import subprocess
import sys

# The debug logger is implemented in C (cfg._c). These tests exercise the
# env-var-gated behavior through cfg.debug / cfg.debug_enabled.

ENV_KEY = "__conditional_method_debug__"


class TestDebugMode:
    def test_debug_env_var_true_enables_logging(self):
        """Setting the env var to a truthy value enables debug logging."""
        original = os.environ.get(ENV_KEY)
        try:
            os.environ[ENV_KEY] = "true"
            import cfg
            import importlib

            importlib.reload(cfg)
            assert cfg.debug_enabled() is True
            # debug() writes a marker to stderr
            code = "import cfg; cfg.debug('marker-abc-123')"
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
            import cfg
            import importlib

            importlib.reload(cfg)
            assert cfg.debug_enabled() is False
            code = "import cfg; cfg.debug('should-not-appear')"
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
        """Debug logs appear when a conditional method calls cfg.debug."""
        from cfg import cfg

        original = os.environ.get(ENV_KEY)
        try:
            os.environ[ENV_KEY] = "true"
            import cfg as cfgmod
            import importlib

            importlib.reload(cfgmod)

            code = (
                "import cfg\n"
                "class TestClass:\n"
                "    @cfg.cfg(condition=True)\n"
                "    def test_method(self):\n"
                "        cfg.debug('inside-method-xyz')\n"
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
