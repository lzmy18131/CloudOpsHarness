"""Legacy import compatibility shim for the pre-rename package name.

The real package lives in ``cloudops_harness``. This module maps every
``aegisops.*`` import onto the new package so old scripts/tests keep working
during migration. New code must import ``cloudops_harness``.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys

import cloudops_harness

for _info in pkgutil.walk_packages(cloudops_harness.__path__, prefix="cloudops_harness."):
    _module = importlib.import_module(_info.name)
    sys.modules["aegisops." + _info.name[len("cloudops_harness.") :]] = _module

__version__ = cloudops_harness.__version__
