"""Import-smoke tests that verify every plugin module loads under PyQt6.

This catches short-form Qt enum regressions (for example ``Qt.AlignCenter``
instead of ``Qt.AlignmentFlag.AlignCenter``) which raise ``AttributeError`` in
PyQt6 during class-body evaluation.

The plugin package is auto-discovered: the first sibling directory of
``tests/`` that contains a ``metadata.txt`` is treated as the plugin root,
so this file does not need to be edited per-plugin.
"""

import importlib
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# This plugin's package lives at the repo root (metadata.txt sits next to
# samgeo_plugin.py). When QGIS installs the plugin, the directory is named
# ``samgeo_plugin`` (see install_plugin.sh); the conftest mirrors that name
# in sys.modules so we use it as the dotted-import prefix here.
PLUGIN_ROOT = REPO_ROOT
PACKAGE_NAME = "samgeo_plugin"
SKIP_DIRS = {"tests", ".git", "__pycache__", ".venv", "venv"}
SKIP_MODULES = {
    # test_plugin.py is the existing in-QGIS smoke script; it imports the
    # real qgis.utils.iface and is not designed to run under the PyQt6 stub.
    f"{PACKAGE_NAME}.test_plugin",
    # install_plugin.py is a one-shot installer script invoked outside QGIS.
    f"{PACKAGE_NAME}.install_plugin",
}


def _module_names():
    """Yield dotted module names for every .py file under the plugin package."""
    for path in sorted(PLUGIN_ROOT.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        rel = path.relative_to(PLUGIN_ROOT).with_suffix("")
        parts = (PACKAGE_NAME,) + rel.parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        name = ".".join(parts)
        if name in SKIP_MODULES:
            continue
        yield name


@pytest.mark.parametrize("module_name", list(_module_names()))
def test_module_imports_under_pyqt6(module_name):
    """Each plugin module must import cleanly when qgis.PyQt maps to PyQt6."""
    importlib.import_module(module_name)
