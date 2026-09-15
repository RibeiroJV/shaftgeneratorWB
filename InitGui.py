# -*- coding: utf-8 -*-
"""Registers the Axis Generator workbench with FreeCAD's GUI."""

import FreeCADGui as Gui


class AxisGeneratorWorkbench(Gui.Workbench):
    MenuText = "Axis Generator"
    ToolTip = "Build horizontal stepped axles/shafts from profile segments"
    # NOTE: FreeCAD evaluates MenuText/ToolTip/Icon at class-body level in a
    # context where imports, `os`, and `__file__` are NOT available (this is
    # what raised the "name 'AxisIcons'/'__file__' is not defined" errors
    # from earlier attempts) - it must stay a plain, dependency-free
    # literal. Raw inline SVG text also isn't reliably recognized by
    # FreeCAD's icon loader (unlike XPM), so we keep this pointed at a
    # standard built-in resource that ships with every FreeCAD install.
    # The command/segment icons you actually click are the ones that
    # matter day-to-day, and those (in AxisGeneratorCmds.py / AxisFeature.py)
    # are resolved through real methods at full module load, where our
    # bundled custom SVGs work reliably - see AxisIcons.py.
    Icon = "Std_Part"

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


Gui.addWorkbench(AxisGeneratorWorkbench())