"""Shared pytest fixtures.

Stubs the ``qgis`` package so the plugin's modules can be imported without a
running QGIS instance. The stub reproduces the real ``qgis.PyQt`` shim
behavior on Qt6: it re-exports ``QAction``, ``QActionGroup`` and ``QShortcut``
from ``PyQt6.QtGui`` under ``qgis.PyQt.QtWidgets`` (they moved out of
``QtWidgets`` in Qt6).
"""

import importlib.util
import pathlib
import sys
import types
from unittest.mock import MagicMock

import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtNetwork
import PyQt6.QtWidgets


def _install_qgis_stub() -> None:
    qgis = types.ModuleType("qgis")
    qgis.__path__ = []
    sys.modules["qgis"] = qgis

    qgis_pyqt = types.ModuleType("qgis.PyQt")
    qgis_pyqt.__path__ = []
    sys.modules["qgis.PyQt"] = qgis_pyqt
    qgis.PyQt = qgis_pyqt

    pyqt_submodules = {
        "QtCore": PyQt6.QtCore,
        "QtGui": PyQt6.QtGui,
        "QtNetwork": PyQt6.QtNetwork,
        "QtWidgets": PyQt6.QtWidgets,
    }
    for name, real in pyqt_submodules.items():
        alias = types.ModuleType(f"qgis.PyQt.{name}")
        for attr in dir(real):
            if not attr.startswith("_"):
                setattr(alias, attr, getattr(real, attr))
        sys.modules[f"qgis.PyQt.{name}"] = alias
        setattr(qgis_pyqt, name, alias)

    # Qt6: QAction, QActionGroup, and QShortcut live in QtGui. The real
    # qgis.PyQt.QtWidgets shim re-exports them, so mirror that here.
    qtwidgets_alias = sys.modules["qgis.PyQt.QtWidgets"]
    for attr in ("QAction", "QActionGroup", "QShortcut"):
        setattr(qtwidgets_alias, attr, getattr(PyQt6.QtGui, attr))

    for submodule in ("QtSvg", "QtWebEngineWidgets"):
        alias = MagicMock()
        sys.modules[f"qgis.PyQt.{submodule}"] = alias
        setattr(qgis_pyqt, submodule, alias)

    for name in ("core", "gui", "utils"):
        stub = MagicMock()
        stub.__spec__ = None
        sys.modules[f"qgis.{name}"] = stub
        setattr(qgis, name, stub)


def _install_plugin_alias() -> None:
    """Load the repo's ``__init__.py`` as the ``samgeo_plugin`` package.

    QGIS installs this plugin under the directory name ``samgeo_plugin`` (see
    ``install_plugin.sh``); the repo directory itself uses hyphens, which is
    not a valid Python module name. We use ``importlib.util`` to execute the
    real ``__init__.py`` rather than registering a blank ``ModuleType`` alias,
    so the smoke test also validates the package init under PyQt6.
    """
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "samgeo_plugin",
        repo_root / "__init__.py",
        submodule_search_locations=[str(repo_root)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["samgeo_plugin"] = module
    spec.loader.exec_module(module)


_install_qgis_stub()
_install_plugin_alias()
