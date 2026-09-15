# -*- coding: utf-8 -*-
"""Resolves bundled icon files for the Axis Generator workbench.

Previously the code pointed at FreeCAD's built-in Qt resource paths
(":/icons/Part_Cylinder.svg", ":/icons/TechDraw_PageDefault.svg", ...).
Those aliases are not guaranteed to exist under every FreeCAD version/
icon theme, which is why the toolbar/menu icons showed up blank for you.

Shipping our own small SVGs next to the code and resolving them with an
absolute filesystem path (built from __file__) works the same on every
FreeCAD install, regardless of theme or version.
"""

import os

_ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources", "icons")


def icon(name):
    """Return the absolute path to a bundled icon file by name.

    Falls back gracefully (returns the path anyway) if the file happens
    to be missing; FreeCAD will just show its own default icon instead
    of raising an error.
    """
    return os.path.join(_ICON_DIR, name)
