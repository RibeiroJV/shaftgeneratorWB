# -*- coding: utf-8 -*-
"""Registers the Axis Generator workbench with FreeCAD's GUI."""

import os
import FreeCAD
import FreeCADGui as Gui

class AxisGeneratorWorkbench(Gui.Workbench):
    MenuText = "Axis Generator"
    ToolTip = "Build horizontal stepped axles/shafts from profile segments"
    # Safe built-in fallback so the workbench never fails to load
    Icon = "Workbench_Part" 

    def Initialize(self):
        import AxisGeneratorCmds  # noqa: F401

        self.stack_commands = [
            "AxisGen_CreateAxis",
            "AxisGen_AddCircularSegment",
            "AxisGen_AddSquareSegment",
            "AxisGen_AddHexSegment",
            "AxisGen_ToggleThread",
            "AxisGen_CreateTechDrawView",
        ]
        self.reorder_commands = [
            "AxisGen_MoveSegmentUp",
            "AxisGen_MoveSegmentDown",
        ]

        self.appendToolbar(
            "Axis Generator", self.stack_commands + self.reorder_commands
        )
        self.appendMenu("Axis Generator", self.stack_commands)
        self.appendMenu(["Axis Generator", "Reorder"], self.reorder_commands)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


# -----------------------------------------------------------------------------
# Workaround for FreeCAD 1.1 scoping: Apply the icon path OUTSIDE the class
# -----------------------------------------------------------------------------
try:
    _custom_icon = os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "AxisGenerator", "Resources", "icons", "workbench.svg")
    
    if os.path.exists(_custom_icon):
        # Overwrite the class attribute directly now that we are safely outside the class block
        AxisGeneratorWorkbench.Icon = _custom_icon
except Exception:
    pass

# Register the workbench
Gui.addWorkbench(AxisGeneratorWorkbench())