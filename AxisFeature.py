# -*- coding: utf-8 -*-
"""Core document object classes for the Axis Generator workbench (Horizontal X-Axis)."""

import math
import FreeCAD as App

try:
    import Part
except ImportError:
    Part = None

try:
    import AxisIcons
except ImportError:
    import os

    class AxisIcons:  # minimal inline fallback
        _DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "Resources", "icons"
        )

        @staticmethod
        def icon(name):
            return os.path.join(AxisIcons._DIR, name)

PROFILE_CIRCULAR = "Circular"
PROFILE_SQUARE = "Quadrado"
PROFILE_HEX = "Hexagonal"
PROFILE_TYPES = [PROFILE_CIRCULAR, PROFILE_SQUARE, PROFILE_HEX]

THREAD_TOTAL = "Total"
THREAD_PARTIAL = "Parcial"
THREAD_EXTENTS = [THREAD_TOTAL, THREAD_PARTIAL]

THREAD_LEFT = "Left (Esquerda)"
THREAD_RIGHT = "Right (Direita)"
THREAD_SIDES = [THREAD_LEFT, THREAD_RIGHT]

KEYWAY_FORM_A = "Forma A - Arredondada nas duas pontas"
KEYWAY_FORM_B = "Forma B - Reta nas duas pontas"
KEYWAY_FORM_C = "Forma C - Uma ponta arredondada, outra reta"
KEYWAY_END_FORMS = [KEYWAY_FORM_A, KEYWAY_FORM_B, KEYWAY_FORM_C]


def _base_shape(obj):
    """Build the plain shape oriented along the local X-axis."""
    length = obj.Length.Value
    if length <= 0:
        return None

    profile = getattr(obj, "ProfileType", PROFILE_CIRCULAR)

    if profile == PROFILE_SQUARE:
        w = obj.Width.Value
        if w <= 0:
            return None
        base = Part.makeBox(length, w, w, App.Vector(0, -w / 2.0, -w / 2.0))
        half = w / 2.0

    elif profile == PROFILE_HEX:
        af = obj.AcrossFlats.Value
        if af <= 0:
            return None
        r = af / math.sqrt(3.0)
        pts = []
        for i in range(6):
            ang = math.radians(60 * i + 30)
            pts.append(App.Vector(0, r * math.cos(ang), r * math.sin(ang)))
        pts.append(pts[0])
        wire = Part.makePolygon(pts)
        face = Part.Face(wire)
        base = face.extrude(App.Vector(length, 0, 0))
        half = af / 2.0

    else:
        d = obj.Diameter.Value
        if d <= 0:
            return None
        base = Part.makeCylinder(
            d / 2.0, length, App.Vector(0, 0, 0), App.Vector(1, 0, 0)
        )
        # Part.makeCylinder always closes its periodic surface with a seam
        # edge; for an axis extruded along +X, OCC places it at local
        # Y=+radius by default, which shows up as a straight line running
        # the full length of the shaft on the "front" side in the default
        # view. The seam can't be deleted (it's required to describe a
        # periodic surface), but rotating the finished solid about its own
        # axis of symmetry doesn't change the shape at all - only where the
        # seam sits - so we move it to the underside (-Z) where it's out of
        # the way in the default 3D/TechDraw views.
        base.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90.0)
        half = d / 2.0

    return base, half


def keyway_effective_extent(obj):
    """Return the (position, length) the keyway actually occupies along
    the segment's local X-axis, after applying Forma C's tip-pinning.

    Shared between the 3D shape generation (_apply_keyway) and the
    TechDraw annotation code, so the section cut/leader always land where
    the slot really is instead of drifting out of sync with it.
    """
    ln = obj.KeywayLength.Value
    seg_len = obj.Length.Value
    end_form = getattr(obj, "KeywayEndForm", KEYWAY_FORM_A)
    invert = getattr(obj, "KeywayInvertEnds", False)

    if end_form == KEYWAY_FORM_C:
        ln = min(ln, seg_len)
        pos = 0.0 if invert else max(0.0, seg_len - ln)
    else:
        pos = max(0.0, min(obj.KeywayPosition.Value, seg_len))
        ln = min(ln, seg_len - pos)

    return pos, ln


def _apply_keyway(shape, obj, half):
    if not getattr(obj, "HasKeyway", False):
        return shape

    w = obj.KeywayWidth.Value
    d = obj.KeywayDepth.Value
    ln = obj.KeywayLength.Value
    seg_len = obj.Length.Value
    if w <= 0 or d <= 0 or ln <= 0 or d >= half:
        return shape

    # A real keyway is milled with a round end-mill, so each end is
    # naturally capped by a semicircle whose diameter equals the slot
    # width (the mill's own diameter) - DIN 6885 "Forma A". Some keyways
    # instead need a flat/square end (Forma B), or a flat end only where
    # the slot runs off the tip of the shaft (Forma C). KeywayEndForm picks
    # which of the two ends gets the round cap; for Forma C, KeywayInvertEnds
    # flips which end (segment start vs. segment end) is the flat one.
    end_form = getattr(obj, "KeywayEndForm", KEYWAY_FORM_A)
    invert = getattr(obj, "KeywayInvertEnds", False)
    round_start = end_form != KEYWAY_FORM_B
    round_end = end_form == KEYWAY_FORM_A
    if end_form == KEYWAY_FORM_C and invert:
        round_start, round_end = round_end, round_start

    # An "open" (Forma C) keyway is pinned flush with a tip of the segment;
    # KeywayPosition is ignored/hidden in that mode. See
    # keyway_effective_extent() for the shared position/length logic.
    pos, ln = keyway_effective_extent(obj)

    if ln <= 0:
        return shape

    r = w / 2.0
    min_len = (r if round_start else 0.0) + (r if round_end else 0.0)
    if ln < min_len:
        # Not enough length for the requested rounded end(s) to fit
        # without overlapping; grow to the minimum valid length.
        ln = min_len
        pos = max(0.0, min(pos, seg_len - ln))

    x_start = pos + (r if round_start else 0.0)
    x_end = pos + ln - (r if round_end else 0.0)
    straight = x_end - x_start

    if round_start and round_end and straight <= 1e-6:
        # Both ends round and no room for a straight middle section: the
        # slot collapses to a single round-ended (fully circular) pocket.
        center = App.Vector((x_start + x_end) / 2.0, 0, 0)
        footprint = Part.Face(
            Part.Wire(Part.makeCircle(r, center, App.Vector(0, 0, 1)))
        )
    else:
        p_start_bottom = App.Vector(x_start, -r, 0)
        p_end_bottom = App.Vector(x_end, -r, 0)
        p_end_top = App.Vector(x_end, r, 0)
        p_start_top = App.Vector(x_start, r, 0)

        line_bottom = Part.LineSegment(p_start_bottom, p_end_bottom).toShape()

        if round_end:
            end_cap = Part.Arc(
                p_end_bottom, App.Vector(x_end + r, 0, 0), p_end_top
            ).toShape()
        else:
            end_cap = Part.LineSegment(p_end_bottom, p_end_top).toShape()

        line_top = Part.LineSegment(p_end_top, p_start_top).toShape()

        if round_start:
            start_cap = Part.Arc(
                p_start_top, App.Vector(x_start - r, 0, 0), p_start_bottom
            ).toShape()
        else:
            start_cap = Part.LineSegment(p_start_top, p_start_bottom).toShape()

        wire = Part.Wire([line_bottom, end_cap, line_top, start_cap])
        footprint = Part.Face(wire)

    overshoot = half + d + 5.0
    tool = footprint.extrude(App.Vector(0, 0, overshoot))
    tool.translate(App.Vector(0, 0, half - d))

    angle = obj.KeywayAngle.Value
    if angle:
        tool.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), angle)

    try:
        return shape.cut(tool)
    except Exception:
        return shape


def _apply_groove(shape, obj, half, profile):
    if not getattr(obj, "HasGroove", False):
        return shape
    if profile != PROFILE_CIRCULAR:
        App.Console.PrintWarning(
            "AxisGenerator: '{}' - Canal (groove) is only supported on"
            " Circular segments; skipped for profile '{}'.\n".format(
                obj.Label, profile
            )
        )
        return shape

    w = obj.GrooveWidth.Value
    d = obj.GrooveDepth.Value
    seg_len = obj.Length.Value
    if w <= 0 or d <= 0 or d >= half:
        return shape

    pos = max(0.0, min(obj.GroovePosition.Value, seg_len))
    w = min(w, seg_len - pos)
    if w <= 0:
        return shape

    outer = Part.makeCylinder(
        half + 1.0, w, App.Vector(pos, 0, 0), App.Vector(1, 0, 0)
    )
    inner = Part.makeCylinder(
        half - d, w + 2.0, App.Vector(pos - 1.0, 0, 0), App.Vector(1, 0, 0)
    )
    tool = outer.cut(inner)

    try:
        return shape.cut(tool)
    except Exception:
        return shape


def _thread_span(obj):
    seg_len = obj.Length.Value
    extent = getattr(obj, "ThreadExtent", THREAD_TOTAL)
    if extent == THREAD_TOTAL:
        return 0.0, seg_len

    length = min(obj.ThreadLength.Value, seg_len)
    if length <= 0:
        return None
    side = getattr(obj, "ThreadSide", THREAD_LEFT)
    if side == THREAD_RIGHT:
        return seg_len - length, length
    return 0.0, length


def _apply_thread(shape, obj, half, profile):
    """Lightweight thread *indication*, not a machined thread.

    Cutting real V-groove teeth (or a true helical sweep) is a boolean
    operation per tooth/turn - on a shaft with several threaded segments
    that becomes far too slow to recompute live, which is the whole
    point of this being a fast concept-modeling tool. So the 3D shape
    here stays the plain cylinder (cheap, always succeeds); the only
    thing added is a cosmetic helix curve on the surface - a single
    parametric edge, not a cut, so its cost doesn't scale with pitch
    count or segment length.
    """
    if not getattr(obj, "HasThread", False):
        return shape
    if profile != PROFILE_CIRCULAR:
        App.Console.PrintWarning(
            "AxisGenerator: '{}' - Rosca (thread) is only supported on"
            " Circular segments; skipped for profile '{}'.\n".format(
                obj.Label, profile
            )
        )
        return shape

    pitch = obj.ThreadPitch.Value
    if pitch <= 0:
        return shape

    span = _thread_span(obj)
    if span is None:
        return shape
    span_start, span_len = span
    if span_len <= 0:
        return shape

    seg_len = obj.Length.Value
    major_r = half
    thread_depth = min(0.6134 * pitch, major_r * 0.25)
    minor_r = max(0.05, major_r - thread_depth)

    # Track the helix span separately to shorten it if there is a groove
    helix_start = span_start
    helix_len = span_len

    # 1. Optional Thread Exit Groove (DIN 76)
    if getattr(obj, "HasThreadExitGroove", False):
        g_w = obj.ThreadExitGrooveWidth.Value
        g_d = obj.ThreadExitGrooveDepth.Value
        if g_w > 0 and g_d > 0 and g_d < major_r:
            if getattr(obj, "ThreadSide", THREAD_LEFT) == THREAD_RIGHT and getattr(
                obj, "ThreadExtent", THREAD_TOTAL
            ) == THREAD_PARTIAL:
                g_pos = span_start
                helix_start += g_w  # Move helix start past the groove
            else:
                g_pos = span_start + span_len - g_w
            
            helix_len -= g_w  # Shorten the helix by the groove width

            if -0.01 <= g_pos <= seg_len - g_w + 0.01:
                try:
                    p1 = App.Vector(g_pos, major_r - g_d, 0)
                    p2 = App.Vector(g_pos + g_w, major_r - g_d, 0)
                    p3 = App.Vector(g_pos + g_w, major_r + 2.0, 0)
                    p4 = App.Vector(g_pos, major_r + 2.0, 0)
                    
                    poly = Part.makePolygon([p1, p2, p3, p4, p1])
                    face = Part.Face(poly)
                    tool = face.revolve(App.Vector(0,0,0), App.Vector(1,0,0), 360)
                    
                    shape = shape.cut(tool)
                except Exception as e:
                    App.Console.PrintError(f"AxisGenerator: Failed to cut exit groove: {e}\n")

    # 2. Cosmetic helix indicator (edges only - no boolean cut at all).
    if getattr(obj, "ShowThreadIndicator", True) and helix_len > 0:
        try:
            edges = []
            for radius, phase in ((major_r, 0.0), (minor_r, pitch / 2.0)):
                helix = Part.makeHelix(pitch, helix_len, radius)
                helix.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90)
                helix.translate(App.Vector(helix_start, 0, 0))
                if phase:
                    helix.rotate(
                        App.Vector(helix_start, 0, 0), App.Vector(1, 0, 0),
                        360.0 * phase / pitch,
                    )
                edges.extend(helix.Edges)
            if edges:
                shape = Part.makeCompound([shape] + edges)
        except Exception:
            pass 

    return shape


def thread_designation(child):
    """ISO-style callout for a threaded Circular segment, e.g. 'M8x1.25'.

    Returns None if the segment has no active thread. Shared between the
    tree label and the TechDraw ISO 6410 annotation so both stay in sync.
    """
    if not getattr(child, "HasThread", False):
        return None
    if getattr(child, "ProfileType", PROFILE_CIRCULAR) != PROFILE_CIRCULAR:
        return None
    dia = child.Diameter.Value
    pitch = child.ThreadPitch.Value
    designation = "M{:g}x{:g}".format(dia, pitch)
    if getattr(child, "ThreadExtent", THREAD_TOTAL) == THREAD_PARTIAL:
        designation += " (Parcial {:g}mm)".format(child.ThreadLength.Value)
    return designation


def _segment_label(child):
    profile = getattr(child, "ProfileType", PROFILE_CIRCULAR)
    if profile == PROFILE_SQUARE:
        size = "{:g}x{:g}".format(child.Width.Value, child.Width.Value)
    elif profile == PROFILE_HEX:
        size = "H{:g}".format(child.AcrossFlats.Value)
    else:
        size = "\u2300{:g}".format(child.Diameter.Value)
    label = "{} x {:g}".format(size, child.Length.Value)
    designation = thread_designation(child)
    if designation:
        label += " - {}".format(designation)
    return label


def _ensure_keyway_end_form(obj):
    """Add the KeywayEndForm/KeywayInvertEnds properties to segments that
    predate them.

    Existing documents (or segments already placed in the tree before these
    properties were introduced) keep whatever properties they had when the
    Python object was first created; a code update alone doesn't retrofit
    them. Calling this on execute()/onDocumentRestored() self-heals those
    older segments instead of requiring the user to delete and recreate
    them.
    """
    kw_mode = 0 if getattr(obj, "HasKeyway", False) else 2

    if not hasattr(obj, "KeywayEndForm"):
        obj.addProperty(
            "App::PropertyEnumeration",
            "KeywayEndForm",
            "Chaveta",
            "End shape, per DIN 6885: Forma A = round both ends, Forma B ="
            " flat/square both ends, Forma C = round on one end, flat on"
            " the other (open end, e.g. keyway that runs to the shaft tip)",
        )
        obj.KeywayEndForm = KEYWAY_END_FORMS
        obj.KeywayEndForm = KEYWAY_FORM_A
        obj.setEditorMode("KeywayEndForm", kw_mode)

    if not hasattr(obj, "KeywayInvertEnds"):
        obj.addProperty(
            "App::PropertyBool",
            "KeywayInvertEnds",
            "Chaveta",
            "Forma C only: swap which end is round and which is flat."
            " Off = round end towards the segment start (KeywayPosition"
            " side), flat end towards the segment end. On = the reverse.",
        ).KeywayInvertEnds = False
        obj.setEditorMode("KeywayInvertEnds", kw_mode)


class Segment:

    def __init__(self, obj):
        obj.Proxy = self

        obj.addProperty(
            "App::PropertyEnumeration",
            "ProfileType",
            "Segment",
            "Cross-section shape",
        )
        obj.ProfileType = PROFILE_TYPES
        obj.ProfileType = PROFILE_CIRCULAR

        obj.addProperty(
            "App::PropertyLength", "Diameter", "Segment", "Outer diameter"
        ).Diameter = 10.0
        obj.addProperty(
            "App::PropertyLength", "Width", "Segment", "Side length"
        ).Width = 10.0
        obj.addProperty(
            "App::PropertyLength",
            "AcrossFlats",
            "Segment",
            "Distance across flats",
        ).AcrossFlats = 10.0
        obj.addProperty(
            "App::PropertyLength", "Length", "Segment", "Length along X-axis"
        ).Length = 20.0

        obj.addProperty(
            "App::PropertyLength",
            "StartOffset",
            "Segment",
            "Distance from axis origin",
        )
        obj.setEditorMode("StartOffset", 1)

        obj.addProperty(
            "App::PropertyString",
            "AutoLabel",
            "Segment",
            "Internal: last auto-generated tree label, used to detect a"
            " manual rename so it doesn't get overwritten",
        )
        obj.setEditorMode("AutoLabel", 2)  # hidden

        # Keyway
        obj.addProperty(
            "App::PropertyBool", "HasKeyway", "Chaveta", "Add keyway slot"
        ).HasKeyway = False
        obj.addProperty(
            "App::PropertyLength", "KeywayWidth", "Chaveta", "Width"
        ).KeywayWidth = 4.0
        obj.addProperty(
            "App::PropertyLength", "KeywayDepth", "Chaveta", "Depth"
        ).KeywayDepth = 2.5
        obj.addProperty(
            "App::PropertyLength", "KeywayLength", "Chaveta", "Length"
        ).KeywayLength = 15.0
        obj.addProperty(
            "App::PropertyLength",
            "KeywayPosition",
            "Chaveta",
            "Start position",
        ).KeywayPosition = 0.0
        obj.addProperty(
            "App::PropertyAngle", "KeywayAngle", "Chaveta", "Angular position"
        ).KeywayAngle = 0.0
        _ensure_keyway_end_form(obj)

        # Groove
        obj.addProperty(
            "App::PropertyBool", "HasGroove", "Canal", "Add groove"
        ).HasGroove = False
        obj.addProperty(
            "App::PropertyLength", "GrooveWidth", "Canal", "Width"
        ).GrooveWidth = 3.0
        obj.addProperty(
            "App::PropertyLength", "GrooveDepth", "Canal", "Depth"
        ).GrooveDepth = 1.0
        obj.addProperty(
            "App::PropertyLength", "GroovePosition", "Canal", "Position"
        ).GroovePosition = 0.0

        # Cosmetic Thread & Exit Groove
        obj.addProperty(
            "App::PropertyBool",
            "HasThread",
            "Rosca (Estética)",
            "Enable cosmetic thread",
        ).HasThread = False
        obj.addProperty(
            "App::PropertyBool",
            "ShowThreadIndicator",
            "Rosca (Estética)",
            "Show a lightweight helix curve indicating the thread in the"
            " 3D view. This is a cosmetic edge only - no material is cut"
            " - so it stays cheap regardless of pitch or length; the 2D"
            " ISO 6410 indication on a TechDraw drawing does not depend"
            " on this and works either way.",
        ).ShowThreadIndicator = False
        obj.addProperty(
            "App::PropertyLength",
            "ThreadPitch",
            "Rosca (Estética)",
            "Thread pitch",
        ).ThreadPitch = 1.5
        obj.addProperty(
            "App::PropertyEnumeration",
            "ThreadExtent",
            "Rosca (Estética)",
            "Total or Partial extent",
        )
        obj.ThreadExtent = THREAD_EXTENTS
        obj.ThreadExtent = THREAD_TOTAL
        obj.addProperty(
            "App::PropertyLength",
            "ThreadLength",
            "Rosca (Estética)",
            "Length if partial",
        ).ThreadLength = 10.0
        obj.addProperty(
            "App::PropertyEnumeration",
            "ThreadSide",
            "Rosca (Estética)",
            "Start side for partial thread",
        )
        obj.ThreadSide = THREAD_SIDES
        obj.ThreadSide = THREAD_LEFT

        obj.addProperty(
            "App::PropertyBool",
            "HasThreadExitGroove",
            "Rosca (Estética)",
            "Add thread exit groove",
        ).HasThreadExitGroove = False
        obj.addProperty(
            "App::PropertyLength",
            "ThreadExitGrooveWidth",
            "Rosca (Estética)",
            "Exit groove width",
        ).ThreadExitGrooveWidth = 2.0
        obj.addProperty(
            "App::PropertyLength",
            "ThreadExitGrooveDepth",
            "Rosca (Estética)",
            "Exit groove depth",
        ).ThreadExitGrooveDepth = 1.0

        self._update_visibilities(obj)

    def _update_visibilities(self, obj):
        profile = obj.ProfileType
        obj.setEditorMode("Diameter", 0 if profile == PROFILE_CIRCULAR else 2)
        obj.setEditorMode("Width", 0 if profile == PROFILE_SQUARE else 2)
        obj.setEditorMode("AcrossFlats", 0 if profile == PROFILE_HEX else 2)

        kw_mode = 0 if obj.HasKeyway else 2
        for prop in (
            "KeywayWidth",
            "KeywayDepth",
            "KeywayLength",
            "KeywayAngle",
            "KeywayEndForm",
            "KeywayInvertEnds",
        ):
            obj.setEditorMode(prop, kw_mode)

        # Forma C pins the flat end flush with a tip of the segment
        # (start or end, per KeywayInvertEnds) and derives its position
        # from that automatically, so KeywayPosition doesn't apply.
        is_form_c = getattr(obj, "KeywayEndForm", KEYWAY_FORM_A) == KEYWAY_FORM_C
        pos_mode = 2 if (obj.HasKeyway and is_form_c) else kw_mode
        obj.setEditorMode("KeywayPosition", pos_mode)

        gr_mode = 0 if obj.HasGroove else 2
        for prop in ("GrooveWidth", "GrooveDepth", "GroovePosition"):
            obj.setEditorMode(prop, gr_mode)

        th_mode = 0 if obj.HasThread else 2
        obj.setEditorMode("ThreadPitch", th_mode)
        obj.setEditorMode("ThreadExtent", th_mode)
        obj.setEditorMode("ShowThreadIndicator", th_mode)
        obj.setEditorMode("HasThreadExitGroove", th_mode)

        ext_mode = (
            0 if obj.HasThread and obj.ThreadExtent == THREAD_PARTIAL else 2
        )
        obj.setEditorMode("ThreadLength", ext_mode)
        obj.setEditorMode("ThreadSide", ext_mode)

        exit_mode = (
            0
            if obj.HasThread and getattr(obj, "HasThreadExitGroove", False)
            else 2
        )
        obj.setEditorMode("ThreadExitGrooveWidth", exit_mode)
        obj.setEditorMode("ThreadExitGrooveDepth", exit_mode)

    def execute(self, obj):
        if Part is None:
            return
        _ensure_keyway_end_form(obj)
        result = _base_shape(obj)
        if result is None:
            return
        shape, half = result
        profile = getattr(obj, "ProfileType", PROFILE_CIRCULAR)

        shape = _apply_keyway(shape, obj, half)
        shape = _apply_groove(shape, obj, half, profile)
        shape = _apply_thread(shape, obj, half, profile)

        obj.Shape = shape

    def onDocumentRestored(self, obj):
        # Segments saved before KeywayEndForm existed won't have the
        # property restored from the file; add it back in so old shafts
        # keep working (defaulting to the old Forma A / round-round look).
        _ensure_keyway_end_form(obj)

    def onChanged(self, obj, prop):
        if prop == "Length":
            for parent in getattr(obj, "InList", []):
                if hasattr(parent, "Proxy") and isinstance(parent.Proxy, Axis):
                    parent.touch()

        if hasattr(obj, "HasKeyway"):
            self._update_visibilities(obj)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class ViewProviderSegment:

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        obj = getattr(self, "Object", None)
        profile = getattr(obj, "ProfileType", PROFILE_CIRCULAR) if obj else PROFILE_CIRCULAR
        if profile == PROFILE_SQUARE:
            return AxisIcons.icon("segment_square.svg")
        if profile == PROFILE_HEX:
            return AxisIcons.icon("segment_hex.svg")
        return AxisIcons.icon("segment_circular.svg")

    def attach(self, vobj):
        self.Object = vobj.Object

    def updateData(self, obj, prop):
        if prop in ("Shape", "HasThread"):
            vobj = obj.ViewObject
            if vobj:
                if getattr(obj, "HasThread", False):
                    vobj.ShapeColor = (0.65, 0.7, 0.75)
                else:
                    vobj.ShapeColor = (0.8, 0.8, 0.8)

    def onChanged(self, vobj, prop):
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class Axis:
    """Container stacking segments horizontally along the X-axis."""

    def __init__(self, obj):
        obj.Proxy = self
        obj.addProperty(
            "App::PropertyLength", "TotalLength", "Axis", "Total shaft length"
        ).setEditorMode("TotalLength", 1)
        if not hasattr(obj, "Group"):
            obj.Group = []
        self._recomputing = False

    def execute(self, obj):
        offset = 0.0
        for child in obj.Group:
            if hasattr(child, "Proxy") and isinstance(
                getattr(child, "Proxy", None), Segment
            ):
                child.Placement = App.Placement(
                    App.Vector(offset, 0, 0), App.Rotation()
                )
                child.StartOffset = offset
                label = _segment_label(child)
                # Only refresh the tree label while it still matches the
                # last auto-generated value; once someone renames a
                # segment by hand, leave it alone from then on.
                if getattr(child, "AutoLabel", "") in ("", child.Label):
                    if child.Label != label:
                        child.Label = label
                    child.AutoLabel = label
                offset += child.Length.Value
        obj.TotalLength = offset

    def onChanged(self, obj, prop):
        if prop == "Group" and not self._recomputing:
            self._recomputing = True
            try:
                obj.touch()
                if obj.Document:
                    obj.Document.recompute()
            finally:
                self._recomputing = False

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class ViewProviderAxis:

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return AxisIcons.icon("workbench.svg")

    def attach(self, vobj):
        self.Object = vobj.Object

    def updateData(self, obj, prop):
        pass

    def onChanged(self, vobj, prop):
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None