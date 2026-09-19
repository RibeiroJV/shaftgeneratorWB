# -*- coding: utf-8 -*-
"""GUI commands for the Axis Generator workbench."""

import os

import FreeCAD as App
import FreeCADGui as Gui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets

        QtGui = QtWidgets
    except ImportError:
        from PySide6 import QtCore, QtWidgets

        QtGui = QtWidgets

import AxisFeature

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

# ISO Metric Coarse Presets: { Designation: (Nominal Diameter, Pitch, Exit Groove Width, Exit Groove Depth) }
METRIC_PRESETS = {
    "Personalizado (Custom)": None,
    "M3 (P=0.5mm)": (3.0, 0.50, 1.0, 0.40),
    "M4 (P=0.7mm)": (4.0, 0.70, 1.4, 0.50),
    "M5 (P=0.8mm)": (5.0, 0.80, 1.6, 0.60),
    "M6 (P=1.0mm)": (6.0, 1.00, 2.0, 0.70),
    "M8 (P=1.25mm)": (8.0, 1.25, 2.5, 0.90),
    "M10 (P=1.5mm)": (10.0, 1.50, 3.0, 1.00),
    "M12 (P=1.75mm)": (12.0, 1.75, 3.5, 1.20),
    "M16 (P=2.0mm)": (16.0, 2.00, 4.0, 1.40),
    "M20 (P=2.5mm)": (20.0, 2.50, 5.0, 1.70),
    "M24 (P=3.0mm)": (24.0, 3.00, 6.0, 2.10),
}


def _active_doc():
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument()
    return doc


def _find_a4_landscape_template():
    """Locate a usable A4 landscape TechDraw template on this install.

    The exact template filename shipped by FreeCAD has changed across
    versions (e.g. "A4_Landscape_TD.svg" in older releases vs.
    "A4_Landscape_blank.svg"/other names in newer ones), which is why a
    hardcoded name broke with "Could not read the new template file" on
    FreeCAD 1.1. Scanning the real Templates folder instead works on any
    version.
    """
    templates_dir = os.path.join(
        App.getResourceDir(), "Mod", "TechDraw", "Templates"
    )
    if not os.path.isdir(templates_dir):
        return None

    try:
        svgs = [
            f for f in os.listdir(templates_dir) if f.lower().endswith(".svg")
        ]
    except OSError:
        return None

    def _score(name):
        low = name.lower()
        score = 0
        if "a4" in low:
            score += 2
        if "landscape" in low:
            score += 2
        if "blank" in low or "plain" in low:
            score += 1
        return score

    if not svgs:
        return None
    svgs.sort(key=_score, reverse=True)
    return os.path.join(templates_dir, svgs[0])


def _is_axis(obj):
    return hasattr(obj, "Proxy") and isinstance(
        getattr(obj, "Proxy", None), AxisFeature.Axis
    )


def _is_segment(obj):
    return hasattr(obj, "Proxy") and isinstance(
        getattr(obj, "Proxy", None), AxisFeature.Segment
    )


def _parent_axis(obj):
    for parent in obj.InList:
        if _is_axis(parent):
            return parent
    return None


def _find_target_axis():
    for obj in Gui.Selection.getSelection():
        if _is_axis(obj):
            return obj
        if _is_segment(obj):
            parent = _parent_axis(obj)
            if parent:
                return parent
    return None


def _all_axes(doc):
    return [obj for obj in doc.Objects if _is_axis(obj)]


def _resolve_target_axis(doc):
    """Find which Axis a new segment should be added to, without ever
    creating one implicitly - that's what the 'Create Axis' button is for.

    - Selection (an Axis or one of its segments) always wins.
    - With nothing selected: if there's exactly one Axis in the document,
      use it (the common case, no need to force a selection every time).
    - With nothing selected and zero or multiple Axes, it's ambiguous -
      ask the user to select (or create) one instead of guessing.
    """
    axis = _find_target_axis()
    if axis is not None:
        return axis

    axes = _all_axes(doc)
    if len(axes) == 1:
        return axes[0]

    if not axes:
        QtWidgets.QMessageBox.information(
            None,
            "Nenhum Eixo Encontrado",
            "Não há nenhum Eixo neste documento ainda.\n\n"
            "Clique em 'Create Axis' para criar um antes de adicionar"
            " segmentos.",
        )
    else:
        QtWidgets.QMessageBox.information(
            None,
            "Selecione um Eixo",
            "Há mais de um Eixo neste documento.\n\n"
            "Selecione o Eixo (ou um segmento dele) ao qual deseja"
            " adicionar o novo segmento e tente novamente.",
        )
    return None


def _create_segment_for_profile(profile):
    doc = _active_doc()
    axis = _resolve_target_axis(doc)
    if axis is None:
        return

    if profile == AxisFeature.PROFILE_SQUARE:
        size_label = "Side Width / Lado (mm):"
        title = "New Square Segment"
    elif profile == AxisFeature.PROFILE_HEX:
        size_label = "Across Flats / Distância entre faces (mm):"
        title = "New Hexagonal Segment"
    else:
        size_label = "Diameter / Diâmetro (mm):"
        title = "New Circular Segment"

    size, ok = QtWidgets.QInputDialog.getDouble(
        None, title, size_label, 10.0, 0.01, 1000000.0, 2
    )
    if not ok:
        return

    length, ok = QtWidgets.QInputDialog.getDouble(
        None, title, "Length / Comprimento (mm):", 20.0, 0.01, 1000000.0, 2
    )
    if not ok:
        return

    doc.openTransaction(f"Add {profile} Segment")
    try:
        seg = doc.addObject("Part::FeaturePython", "Segment")
        AxisFeature.Segment(seg)
        if Gui.ActiveDocument:
            AxisFeature.ViewProviderSegment(seg.ViewObject)

        seg.ProfileType = profile
        if profile == AxisFeature.PROFILE_SQUARE:
            seg.Width = size
        elif profile == AxisFeature.PROFILE_HEX:
            seg.AcrossFlats = size
        else:
            seg.Diameter = size
        seg.Length = length

        group = list(axis.Group)
        group.append(seg)
        axis.Group = group

        doc.recompute()
    finally:
        doc.commitTransaction()

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(seg)


class ThreadConfigDialog(QtWidgets.QDialog):
    """Configuration Pop-up Dialog with ISO Metric Presets and Auto-Diameter Update."""

    def __init__(self, segment, parent=None):
        super(ThreadConfigDialog, self).__init__(parent)
        self.seg = segment
        self.target_diameter = None
        self.setWindowTitle("Configurar Rosca Métrica - " + segment.Label)
        self.resize(380, 360)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        # Enable Thread
        self.chk_has_thread = QtWidgets.QCheckBox("Ativar Rosca")
        self.chk_has_thread.setChecked(getattr(segment, "HasThread", False))
        form.addRow(self.chk_has_thread)

        # 3D visual indicator toggle (cheap helix curve, no material cut)
        self.chk_show_indicator = QtWidgets.QCheckBox(
            "Mostrar indicação da rosca na vista 3D (hélice cosmética)"
        )
        self.chk_show_indicator.setChecked(
            getattr(segment, "ShowThreadIndicator", True)
        )
        form.addRow(self.chk_show_indicator)

        # Metric Preset Selection
        self.cmb_preset = QtWidgets.QComboBox()
        self.cmb_preset.addItems(list(METRIC_PRESETS.keys()))
        form.addRow("Preset Métrico ISO:", self.cmb_preset)

        # Pitch
        self.spn_pitch = QtWidgets.QDoubleSpinBox()
        self.spn_pitch.setRange(0.1, 100.0)
        self.spn_pitch.setValue(
            getattr(segment, "ThreadPitch", 1.5).Value
            if hasattr(segment.ThreadPitch, "Value")
            else 1.5
        )
        self.spn_pitch.setSuffix(" mm")
        form.addRow("Passo da Rosca:", self.spn_pitch)

        # Extent
        self.cmb_extent = QtWidgets.QComboBox()
        self.cmb_extent.addItems(AxisFeature.THREAD_EXTENTS)
        ext_val = getattr(segment, "ThreadExtent", AxisFeature.THREAD_TOTAL)
        idx = self.cmb_extent.findText(ext_val)
        if idx >= 0:
            self.cmb_extent.setCurrentIndex(idx)
        form.addRow("Extensão:", self.cmb_extent)

        # Length
        self.spn_length = QtWidgets.QDoubleSpinBox()
        self.spn_length.setRange(0.1, 10000.0)
        self.spn_length.setValue(
            getattr(segment, "ThreadLength", 10.0).Value
            if hasattr(segment.ThreadLength, "Value")
            else 10.0
        )
        self.spn_length.setSuffix(" mm")
        form.addRow("Comprimento da Rosca:", self.spn_length)

        # Side
        self.cmb_side = QtWidgets.QComboBox()
        self.cmb_side.addItems(AxisFeature.THREAD_SIDES)
        side_val = getattr(segment, "ThreadSide", AxisFeature.THREAD_LEFT)
        idx = self.cmb_side.findText(side_val)
        if idx >= 0:
            self.cmb_side.setCurrentIndex(idx)
        form.addRow("Lado Inicial:", self.cmb_side)

        # Exit Groove Toggle
        self.chk_exit_groove = QtWidgets.QCheckBox(
            "Ativar Canal de Saída (DIN 76)"
        )
        self.chk_exit_groove.setChecked(
            getattr(segment, "HasThreadExitGroove", False)
        )
        form.addRow(self.chk_exit_groove)

        # Exit Groove Width
        self.spn_exit_w = QtWidgets.QDoubleSpinBox()
        self.spn_exit_w.setRange(0.1, 100.0)
        self.spn_exit_w.setValue(
            getattr(segment, "ThreadExitGrooveWidth", 2.0).Value
            if hasattr(segment.ThreadExitGrooveWidth, "Value")
            else 2.0
        )
        self.spn_exit_w.setSuffix(" mm")
        form.addRow("Largura Canal de Saída:", self.spn_exit_w)

        # Exit Groove Depth
        self.spn_exit_d = QtWidgets.QDoubleSpinBox()
        self.spn_exit_d.setRange(0.1, 100.0)
        self.spn_exit_d.setValue(
            getattr(segment, "ThreadExitGrooveDepth", 1.0).Value
            if hasattr(segment.ThreadExitGrooveDepth, "Value")
            else 1.0
        )
        self.spn_exit_d.setSuffix(" mm")
        form.addRow("Profundidade Canal de Saída:", self.spn_exit_d)

        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Signals
        self.chk_has_thread.toggled.connect(self._update_states)
        self.cmb_extent.currentIndexChanged.connect(self._update_states)
        self.chk_exit_groove.toggled.connect(self._update_states)
        self.cmb_preset.currentIndexChanged.connect(self._on_preset_changed)

        self._auto_select_preset_from_diameter()
        self._update_states()

    def _auto_select_preset_from_diameter(self):
        """Initial dropdown selection matching current segment diameter."""
        if hasattr(self.seg, "Diameter"):
            dia = int(round(self.seg.Diameter.Value))
            target_key = f"M{dia} "
            for idx, key in enumerate(METRIC_PRESETS.keys()):
                if key.startswith(target_key):
                    self.cmb_preset.setCurrentIndex(idx)
                    break

    def _on_preset_changed(self, index):
        key = self.cmb_preset.currentText()
        preset = METRIC_PRESETS.get(key)
        if preset:
            nom_dia, pitch, g_w, g_d = preset
            self.target_diameter = nom_dia
            self.spn_pitch.setValue(pitch)
            self.spn_exit_w.setValue(g_w)
            self.spn_exit_d.setValue(g_d)
        else:
            self.target_diameter = None

    def _update_states(self):
        has_th = self.chk_has_thread.isChecked()
        is_partial = (
            self.cmb_extent.currentText() == AxisFeature.THREAD_PARTIAL
        )
        has_exit = self.chk_exit_groove.isChecked()

        self.cmb_preset.setEnabled(has_th)
        self.spn_pitch.setEnabled(has_th)
        self.cmb_extent.setEnabled(has_th)
        self.spn_length.setEnabled(has_th and is_partial)
        self.cmb_side.setEnabled(has_th and is_partial)
        self.chk_show_indicator.setEnabled(has_th)
        self.chk_exit_groove.setEnabled(has_th)
        self.spn_exit_w.setEnabled(has_th and has_exit)
        self.spn_exit_d.setEnabled(has_th and has_exit)

    def apply_to_segment(self):
        doc = _active_doc()
        doc.openTransaction("Configure Thread")
        try:
            if self.target_diameter is not None and hasattr(
                self.seg, "Diameter"
            ):
                self.seg.Diameter = self.target_diameter

            self.seg.HasThread = self.chk_has_thread.isChecked()
            self.seg.ShowThreadIndicator = self.chk_show_indicator.isChecked()
            self.seg.ThreadPitch = self.spn_pitch.value()
            self.seg.ThreadExtent = self.cmb_extent.currentText()
            self.seg.ThreadLength = self.spn_length.value()
            self.seg.ThreadSide = self.cmb_side.currentText()
            self.seg.HasThreadExitGroove = self.chk_exit_groove.isChecked()
            self.seg.ThreadExitGrooveWidth = self.spn_exit_w.value()
            self.seg.ThreadExitGrooveDepth = self.spn_exit_d.value()
            doc.recompute()
        finally:
            doc.commitTransaction()


class CreateAxisCommand:

    def GetResources(self):
        return {
            "MenuText": "New Axis",
            "ToolTip": "Create a new empty horizontal Axis container",
            "Pixmap": AxisIcons.icon("axis_new.svg"),
        }

    def Activated(self):
        doc = _active_doc()
        doc.openTransaction("Create Axis")
        try:
            obj = doc.addObject("App::DocumentObjectGroupPython", "Axis")
            AxisFeature.Axis(obj)
            if Gui.ActiveDocument:
                AxisFeature.ViewProviderAxis(obj.ViewObject)
            doc.recompute()
        finally:
            doc.commitTransaction()

        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(obj)

    def IsActive(self):
        return True


class AddCircularSegmentCommand:

    def GetResources(self):
        return {
            "MenuText": "Add Circular Segment",
            "ToolTip": "Add a new cylindrical step along X",
            "Pixmap": AxisIcons.icon("segment_circular.svg"),
        }

    def Activated(self):
        _create_segment_for_profile(AxisFeature.PROFILE_CIRCULAR)

    def IsActive(self):
        return App.ActiveDocument is not None


class AddSquareSegmentCommand:

    def GetResources(self):
        return {
            "MenuText": "Add Square Segment",
            "ToolTip": "Add a new square step along X",
            "Pixmap": AxisIcons.icon("segment_square.svg"),
        }

    def Activated(self):
        _create_segment_for_profile(AxisFeature.PROFILE_SQUARE)

    def IsActive(self):
        return App.ActiveDocument is not None


class AddHexSegmentCommand:

    def GetResources(self):
        return {
            "MenuText": "Add Hexagonal Segment",
            "ToolTip": "Add a new hexagonal step along X",
            "Pixmap": AxisIcons.icon("segment_hex.svg"),
        }

    def Activated(self):
        _create_segment_for_profile(AxisFeature.PROFILE_HEX)

    def IsActive(self):
        return App.ActiveDocument is not None


class ToggleThreadCommand:

    def GetResources(self):
        return {
            "MenuText": "Configure Thread",
            "ToolTip": (
                "Add/Configure aesthetic thread & exit groove on the selected"
                " segment"
            ),
            "Pixmap": AxisIcons.icon("thread_config.svg"),
        }

    def Activated(self):
        sel = Gui.Selection.getSelection()

        if not sel or not _is_segment(sel[0]):
            QtWidgets.QMessageBox.warning(
                None,
                "Nenhum Segmento Selecionado",
                "Por favor, selecione um segmento do eixo na árvore de modelo"
                " antes de adicionar/editar a rosca.",
            )
            return

        seg = sel[0]
        if getattr(seg, "ProfileType", "") != AxisFeature.PROFILE_CIRCULAR:
            QtWidgets.QMessageBox.warning(
                None,
                "Perfil Incompatível",
                "A rosca só pode ser aplicada em segmentos com perfil"
                " Circular.",
            )
            return

        dlg = ThreadConfigDialog(seg)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            dlg.apply_to_segment()

    def IsActive(self):
        return True


class CreateTechDrawViewCommand:
    """Generates a TechDraw Page and View with ISO 6410 Cosmetic Lines."""

    def GetResources(self):
        return {
            "MenuText": "Gerar Desenho 2D (TechDraw)",
            "ToolTip": (
                "Criar página TechDraw com linhas de indicação de rosca"
                " (ISO 6410)"
            ),
            "Pixmap": AxisIcons.icon("techdraw_view.svg"),
        }

    @staticmethod
    def _add_cosmetic_line(view, p1, p2):
        """Add a cosmetic line from 3D model-space points.

        `DrawViewPart.makeCosmeticLine(p1, p2)` expects points already in
        the *view's* 2D page coordinate system, not raw model coordinates
        - passing model coordinates there (as the previous version of this
        command did) silently produced garbage/off-page geometry, which is
        why no thread indication ever showed up. `makeCosmeticLine3d`
        exists specifically to take 3D model-space points and project them
        through the view's own Direction/XDirection/Scale, which is what
        we want here.
        """
        try:
            return view.makeCosmeticLine3d(p1, p2)
        except AttributeError:
            # Very old FreeCAD without makeCosmeticLine3d: fall back to a
            # flat drop-Z projection, valid only because this workbench
            # always uses a straight-on Direction=(0,0,1) view.
            App.Console.PrintWarning(
                "AxisGenerator: makeCosmeticLine3d unavailable, using"
                " approximate 2D fallback for thread lines.\n"
            )
            return view.makeCosmeticLine(
                App.Vector(p1.x, p1.y, 0), App.Vector(p2.x, p2.y, 0)
            )

    def Activated(self):
        axis = _find_target_axis()
        if not axis:
            QtWidgets.QMessageBox.warning(
                None,
                "Eixo Não Selecionado",
                "Selecione um Eixo ou Segmento na árvore do modelo para gerar o"
                " desenho.",
            )
            return

        doc = _active_doc()
        doc.openTransaction("Gerar TechDraw com Roscas")
        try:
            # 1. Create TechDraw Page
            page = doc.addObject("TechDraw::DrawPage", "DesenhoEixo")
            template = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
            template_path = _find_a4_landscape_template()
            if not template_path:
                QtWidgets.QMessageBox.warning(
                    None,
                    "Modelo TechDraw Não Encontrado",
                    "Não foi possível localizar um modelo (template) A4"
                    " Paisagem na instalação do FreeCAD. Crie a página"
                    " manualmente pelo menu TechDraw e escolha um modelo.",
                )
                doc.removeObject(template.Name)
                doc.removeObject(page.Name)
                return
            template.Template = template_path
            page.Template = template

            # 2. Add Part View for Axis
            view = doc.addObject("TechDraw::DrawViewPart", "VistaEixo")
            view.Source = axis.Group
            view.Direction = App.Vector(0, 0, 1)  # Front projection view
            page.addView(view)
            doc.recompute()

            # 3. Automatic ISO 6410 thread indication overlay
            designations = []
            for child in axis.Group:
                if not (
                    hasattr(child, "Proxy")
                    and isinstance(
                        getattr(child, "Proxy", None), AxisFeature.Segment
                    )
                    and getattr(child, "HasThread", False)
                    and getattr(child, "ProfileType", "")
                    == AxisFeature.PROFILE_CIRCULAR
                ):
                    continue

                span = AxisFeature._thread_span(child)
                if not span:
                    continue
                span_start_local, span_len = span

                seg_len = child.Length.Value
                start_x = child.StartOffset.Value + span_start_local
                end_x = start_x + span_len

                major_r = child.Diameter.Value / 2.0
                pitch = child.ThreadPitch.Value
                minor_r = max(0.1, major_r - (0.6134 * pitch))

                # Minor-diameter (root) lines: thin lines running the
                # threaded length, offset in from the real (major
                # diameter) outline - the standard ISO 6410 side-view
                # thread symbol.
                self._add_cosmetic_line(
                    view,
                    App.Vector(start_x, minor_r, 0),
                    App.Vector(end_x, minor_r, 0),
                )
                self._add_cosmetic_line(
                    view,
                    App.Vector(start_x, -minor_r, 0),
                    App.Vector(end_x, -minor_r, 0),
                )

                # Thread limit line: a full line across the major diameter
                # at the boundary where the thread stops, but only where
                # that boundary sits *inside* the segment (i.e. a partial
                # thread) - if the boundary coincides with the segment's
                # own end face, that face is already drawn as a real edge
                # and a duplicate cosmetic line would be redundant.
                local_start = span_start_local
                local_end = span_start_local + span_len
                if local_start > 1e-6:
                    self._add_cosmetic_line(
                        view,
                        App.Vector(start_x, major_r, 0),
                        App.Vector(start_x, -major_r, 0),
                    )
                if local_end < seg_len - 1e-6:
                    self._add_cosmetic_line(
                        view,
                        App.Vector(end_x, major_r, 0),
                        App.Vector(end_x, -major_r, 0),
                    )

                designation = AxisFeature.thread_designation(child)
                if designation:
                    designations.append(
                        "{}: {}".format(child.Label, designation)
                    )

            doc.recompute()

            # 4. ISO 6410 designation callouts as a text legend on the page.
            # Precisely positioning a leader/text next to each thread in
            # page coordinates is fragile (depends on page scale/rotation
            # in ways that shift between FreeCAD versions), so instead we
            # place one readable legend the user can drag anywhere.
            if designations:
                legend = doc.addObject(
                    "TechDraw::DrawViewAnnotation", "RoscasISO6410"
                )
                legend.Text = ["Roscas (ISO 6410):"] + designations
                legend.X = 15
                legend.Y = 15
                page.addView(legend)
                doc.recompute()

        finally:
            doc.commitTransaction()

    def IsActive(self):
        return App.ActiveDocument is not None


class _ReorderCommand:
    direction = 0

    def Activated(self):
        sel = Gui.Selection.getSelection()
        if len(sel) != 1 or not _is_segment(sel[0]):
            return
        seg = sel[0]
        axis = _parent_axis(seg)
        if axis is None:
            return

        group = list(axis.Group)
        idx = group.index(seg)
        new_idx = idx + self.direction
        if new_idx < 0 or new_idx >= len(group):
            return

        doc = _active_doc()
        doc.openTransaction("Reorder Axis Segment")
        try:
            group[idx], group[new_idx] = group[new_idx], group[idx]
            axis.Group = group
            doc.recompute()
        finally:
            doc.commitTransaction()

        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(seg)

    def IsActive(self):
        sel = Gui.Selection.getSelection()
        return len(sel) == 1 and _is_segment(sel[0])


class MoveSegmentUpCommand(_ReorderCommand):
    direction = -1

    def GetResources(self):
        return {
            "MenuText": "Move Segment Left / Up",
            "ToolTip": "Move selected segment earlier along the horizontal axis",
            "Pixmap": AxisIcons.icon("arrow_left.svg"),
        }


class MoveSegmentDownCommand(_ReorderCommand):
    direction = 1

    def GetResources(self):
        return {
            "MenuText": "Move Segment Right / Down",
            "ToolTip": "Move selected segment later along the horizontal axis",
            "Pixmap": AxisIcons.icon("arrow_right.svg"),
        }
class SequentialSegmentDialog(QtWidgets.QDialog):
    """Dialog for rapidly adding multiple shaft segments sequentially."""

    def __init__(self, axis_obj, parent=None):
        super(SequentialSegmentDialog, self).__init__(parent)
        self.axis = axis_obj
        self.count = 0
        self.setWindowTitle("Adicionar Múltiplos Segmentos")
        self.resize(340, 240)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        # Profile Type Selection
        self.cmb_profile = QtWidgets.QComboBox()
        self.cmb_profile.addItems([
            AxisFeature.PROFILE_CIRCULAR,
            AxisFeature.PROFILE_SQUARE,
            AxisFeature.PROFILE_HEX,
        ])
        form.addRow("Tipo de Perfil:", self.cmb_profile)

        # Size Input (Diameter / Width / Across Flats)
        self.lbl_size = QtWidgets.QLabel("Diâmetro (mm):")
        self.spn_size = QtWidgets.QDoubleSpinBox()
        self.spn_size.setRange(0.01, 1000000.0)
        self.spn_size.setValue(10.0)
        self.spn_size.setDecimals(2)
        self.spn_size.setSuffix(" mm")
        form.addRow(self.lbl_size, self.spn_size)

        # Length Input
        self.spn_length = QtWidgets.QDoubleSpinBox()
        self.spn_length.setRange(0.01, 1000000.0)
        self.spn_length.setValue(20.0)
        self.spn_length.setDecimals(2)
        self.spn_length.setSuffix(" mm")
        form.addRow("Comprimento (mm):", self.spn_length)

        layout.addLayout(form)

        # Status Tracker
        self.lbl_status = QtWidgets.QLabel("Segmentos adicionados nesta sessão: 0")
        self.lbl_status.setStyleSheet("font-weight: bold; color: #337ab7;")
        layout.addWidget(self.lbl_status)

        # Action Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Adicionar Próximo (Enter)")
        self.btn_add.setDefault(True)  # Pressing Enter inside spinboxes triggers this

        self.btn_finish = QtWidgets.QPushButton("Concluir")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_finish)
        layout.addLayout(btn_layout)

        # Signals
        self.cmb_profile.currentIndexChanged.connect(self._on_profile_changed)
        self.btn_add.clicked.connect(self._add_segment)
        self.btn_finish.clicked.connect(self.accept)

    def _on_profile_changed(self, index):
        profile = self.cmb_profile.currentText()
        if profile == AxisFeature.PROFILE_SQUARE:
            self.lbl_size.setText("Lado / Largura (mm):")
        elif profile == AxisFeature.PROFILE_HEX:
            self.lbl_size.setText("Distância entre faces (mm):")
        else:
            self.lbl_size.setText("Diâmetro (mm):")

    def _add_segment(self):
        doc = self.axis.Document
        profile = self.cmb_profile.currentText()
        size = self.spn_size.value()
        length = self.spn_length.value()

        seg = doc.addObject("Part::FeaturePython", "Segment")
        AxisFeature.Segment(seg)
        if Gui.ActiveDocument:
            AxisFeature.ViewProviderSegment(seg.ViewObject)

        seg.ProfileType = profile
        if profile == AxisFeature.PROFILE_SQUARE:
            seg.Width = size
        elif profile == AxisFeature.PROFILE_HEX:
            seg.AcrossFlats = size
        else:
            seg.Diameter = size
        seg.Length = length

        group = list(self.axis.Group)
        group.append(seg)
        self.axis.Group = group

        doc.recompute()
        self.count += 1
        self.lbl_status.setText(f"Segmentos adicionados nesta sessão: {self.count}")

        # Re-select size value for fast typing of the next segment
        self.spn_size.setFocus()
        self.spn_size.selectAll()


class AddSequentialSegmentsCommand:

    def GetResources(self):
        return {
            "MenuText": "Add Multiple Segments (Sequence)",
            "ToolTip": "Sequentially add multiple segments until finished",
            "Pixmap": AxisIcons.icon("sequential_segments.svg"),
        }

    def Activated(self):
        doc = _active_doc()
        axis = _resolve_target_axis(doc)
        if axis is None:
            return

        doc.openTransaction("Add Sequential Segments")
        try:
            dlg = SequentialSegmentDialog(axis)
            dlg.exec_()

            # When finished, set 3D view to Isometric and Fit to Screen
            if dlg.count > 0 and Gui.ActiveDocument and Gui.ActiveDocument.ActiveView:
                Gui.ActiveDocument.ActiveView.viewIsometric()
                Gui.ActiveDocument.ActiveView.fitAll()
        finally:
            doc.commitTransaction()

    def IsActive(self):
        return App.ActiveDocument is not None


Gui.addCommand("AxisGen_CreateAxis", CreateAxisCommand())
Gui.addCommand("AxisGen_AddSequentialSegments", AddSequentialSegmentsCommand())
Gui.addCommand("AxisGen_AddCircularSegment", AddCircularSegmentCommand())
Gui.addCommand("AxisGen_AddSquareSegment", AddSquareSegmentCommand())
Gui.addCommand("AxisGen_AddHexSegment", AddHexSegmentCommand())
Gui.addCommand("AxisGen_ToggleThread", ToggleThreadCommand())
Gui.addCommand("AxisGen_CreateTechDrawView", CreateTechDrawViewCommand())
Gui.addCommand("AxisGen_MoveSegmentUp", MoveSegmentUpCommand())
Gui.addCommand("AxisGen_MoveSegmentDown", MoveSegmentDownCommand())