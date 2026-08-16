"""Smoke-test an installed python-cfg wheel (used by CI wheels.yml).

Run from a clean venv after ``pip install`` of a wheel::

    python scripts/smoke_wheel.py
"""

import cfg
from cfg import cfg as cfg_deco, cfg_attr, cm, if_, conditional_method


@cfg_deco(condition=True)
def _pick():
    return "prod"


@cfg_deco(condition=False)
def _pick():
    return "dev"


assert _pick() == "prod"


@cfg_attr(condition=True, decorators=[lambda fn: fn])
def _attr():
    return 1


assert _attr() == 1
assert cm is conditional_method and cm is if_ and cm is cfg_deco
assert cfg.__version__

print(f"wheel smoke OK (python-cfg {cfg.__version__})")
