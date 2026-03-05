# -*- coding: utf-8 -*-
import os
import numpy as np

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QMessageBox,
    QTableWidgetItem, QComboBox, QColorDialog,
    QProgressBar
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt

from qgis.gui import QgsMapLayerComboBox
from qgis.core import (
    QgsProject,
    QgsMapLayerProxyModel,
    QgsVectorLayer,
    QgsWkbTypes
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .topobathy_profiles_functions import extract_points_along_section


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__),
                 'topobathy_profiles_dialog_base.ui')
)


class TopoBathyProfilesDialog(QDialog, FORM_CLASS):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.iface = iface

        # ---------------- SECTION LAYER FILTER ----------------
        self.sectionLayerCombo = QgsMapLayerComboBox(self)
        self.sectionLayerCombo.setFilters(QgsMapLayerProxyModel.LineLayer)

        self.groupInput.layout().replaceWidget(
            self.comboSectionLayer,
            self.sectionLayerCombo
        )

        self.comboSectionLayer.deleteLater()
        self.comboSectionLayer = self.sectionLayerCombo

        # ---------------- INTERNAL STATE ----------------
        self.point_layers = []
        self.results = []
        self.buffer_distance = 4.0

        # ---------------- MATPLOTLIB ----------------
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self.layoutPreview.addWidget(self.canvas)

        # ---------------- PROGRESS BAR ----------------
        self.progressBar = QProgressBar()
        self.progressBar.setVisible(False)
        self.layout().addWidget(self.progressBar)

        # ---------------- REMOVE LIMITS X/Y ----------------
        for spin in [
            self.spinXMin,
            self.spinXMax,
            self.spinYMin,
            self.spinYMax
        ]:
            spin.setMinimum(-1e15)
            spin.setMaximum(1e15)

        # ---------------- ENABLE MAX DISTANCE SPIN ----------------
        self.spinMaxSegmentLength.setEnabled(
            self.chkSplitProfile.isChecked()
        )

        self.chkSplitProfile.stateChanged.connect(
            lambda state: self.spinMaxSegmentLength.setEnabled(state == Qt.Checked)
        )

        # ---------------- SIGNALS ----------------
        self.btnAddLayer.clicked.connect(self.addPointLayer)
        self.btnRemoveLayer.clicked.connect(self.removePointLayer)
        self.btnRun.clicked.connect(self.runAnalysis)
        self.btnPreview.clicked.connect(self.updatePreview)
        self.btnSaveGraph.clicked.connect(self.exportPNG)
        self.btnSaveCSV.clicked.connect(self.exportCSV)
        self.btnSetBuffer.clicked.connect(self.setBufferDistance)

        self.comboSectionLayer.layerChanged.connect(self.populateSectionFields)
        self.comboSectionIdField.currentIndexChanged.connect(self.populateSectionFeatures)
        self.comboSectionFeature.currentIndexChanged.connect(self.highlightSelectedFeature)

        self.tableLayerAnno.cellDoubleClicked.connect(self.handleColorChange)

        self.chkFilterPoints.stateChanged.connect(
            lambda state: self.spinFilterDistance.setEnabled(state == Qt.Checked)
        )

        self.populatePointLayerCombo()

    # ----------------------------------------------------------
    # POPULATE POINT LAYERS
    # ----------------------------------------------------------
    def populatePointLayerCombo(self):
        self.comboPunti.clear()
        from qgis.core import QgsWkbTypes
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                geom_type = QgsWkbTypes.geometryType(layer.wkbType())
                if geom_type == QgsWkbTypes.PointGeometry:
                    self.comboPunti.addItem(layer.name(), layer)

    # ----------------------------------------------------------
    # SECTION FIELD
    # ----------------------------------------------------------
    def populateSectionFields(self):
        self.comboSectionIdField.clear()
        layer = self.comboSectionLayer.currentLayer()
        if not layer:
            return

        for f in layer.fields():
            if f.typeName() in ("String", "Integer"):
                self.comboSectionIdField.addItem(f.name())

    # ----------------------------------------------------------
    # SECTION FEATURES
    # ----------------------------------------------------------
    def populateSectionFeatures(self):
        self.comboSectionFeature.clear()
        layer = self.comboSectionLayer.currentLayer()
        field_name = self.comboSectionIdField.currentText()

        if not layer or not field_name:
            return

        for feat in layer.getFeatures():
            self.comboSectionFeature.addItem(
                str(feat[field_name]),
                feat.id()
            )

    def highlightSelectedFeature(self):
        layer = self.comboSectionLayer.currentLayer()
        if not layer:
            return

        fid = self.comboSectionFeature.currentData()
        if fid is not None:
            layer.selectByIds([fid])
            self.iface.mapCanvas().zoomToSelected(layer)
            self.iface.mapCanvas().refresh()

    # ----------------------------------------------------------
    # ADD / REMOVE POINT LAYER
    # ----------------------------------------------------------
    def addPointLayer(self):
        layer = self.comboPunti.currentData()
        if not layer or layer in self.point_layers:
            return

        self.point_layers.append(layer)

        row = self.tableLayerAnno.rowCount()
        self.tableLayerAnno.insertRow(row)

        # Layer name
        self.tableLayerAnno.setItem(row, 0, QTableWidgetItem(layer.name()))

        # Label (editable)
        self.tableLayerAnno.setItem(row, 1, QTableWidgetItem(layer.name()))

        # Random color
        color = QColor(
            np.random.randint(0, 255),
            np.random.randint(0, 255),
            np.random.randint(0, 255)
        )
        color_item = QTableWidgetItem()
        color_item.setBackground(color)
        self.tableLayerAnno.setItem(row, 2, color_item)

        # Elevation field dropdown
        combo = QComboBox()

        combo.addItem("Z geometry", "__Z__")

        from qgis.PyQt.QtCore import QVariant

        for field in layer.fields():
            if field.type() in (
                QVariant.Int,
                QVariant.Double,
                QVariant.LongLong
            ):
                combo.addItem(field.name(), field.name())

        self.tableLayerAnno.setCellWidget(row, 3, combo)

    def removePointLayer(self):
        row = self.tableLayerAnno.currentRow()
        if row >= 0:
            self.point_layers.pop(row)
            self.tableLayerAnno.removeRow(row)

    # ----------------------------------------------------------
    # COLOR CHANGE
    # ----------------------------------------------------------
    def handleColorChange(self, row, column):
        if column == 2:
            item = self.tableLayerAnno.item(row, column)
            current_color = item.background().color()
            color = QColorDialog.getColor(current_color, self)
            if color.isValid():
                item.setBackground(color)

    # ----------------------------------------------------------
    # BUFFER
    # ----------------------------------------------------------
    def setBufferDistance(self):
        from qgis.PyQt.QtWidgets import QInputDialog
        value, ok = QInputDialog.getDouble(
            self,
            "Buffer Distance",
            "Buffer distance (m):",
            self.buffer_distance,
            0,
            10000,
            2
        )
        if ok:
            self.buffer_distance = value

    # ----------------------------------------------------------
    # RUN ANALYSIS
    # ----------------------------------------------------------
    def runAnalysis(self):

        section_layer = self.comboSectionLayer.currentLayer()
        if not section_layer:
            QMessageBox.warning(self, "Error", "Select a section layer.")
            return

        if not self.point_layers:
            QMessageBox.warning(self, "Error", "Add at least one point layer.")
            return

        field_name = self.comboSectionIdField.currentText()
        feature_id = self.comboSectionFeature.currentData()

        if feature_id is None:
            QMessageBox.warning(self, "Error", "Select a section feature.")
            return

        elevation_fields = []
        use_z_flags = []

        for row in range(self.tableLayerAnno.rowCount()):
            combo = self.tableLayerAnno.cellWidget(row, 3)
            value = combo.currentData()

            if value == "__Z__":
                elevation_fields.append(None)
                use_z_flags.append(True)
            else:
                elevation_fields.append(value)
                use_z_flags.append(False)

        self.progressBar.setVisible(True)
        self.progressBar.setMaximum(len(self.point_layers))
        self.progressBar.setValue(0)

        def update_progress():
            self.progressBar.setValue(self.progressBar.value() + 1)

        self.results = extract_points_along_section(
            section_layer=section_layer,
            point_layers=self.point_layers,
            elevation_fields=elevation_fields,
            use_z_geometry_flags=use_z_flags,
            buffer_distance=self.buffer_distance,
            min_plot_spacing=self.spinFilterDistance.value()
            if self.chkFilterPoints.isChecked() else 1.0,
            section_id_field=field_name,
            selected_feature_ids=[feature_id],
            progress_callback=update_progress,
            split_profile_on_max_distance=self.chkSplitProfile.isChecked(),
            max_segment_length=self.spinMaxSegmentLength.value()
        )

        self.progressBar.setVisible(False)

        if not self.results:
            QMessageBox.warning(self, "Warning", "No data extracted.")
            return

        self.comboPreview.clear()
        for r in self.results:
            self.comboPreview.addItem(str(r["id"]))

        self.updatePreview(automatic=True)

    # ----------------------------------------------------------
    # PREVIEW
    # ----------------------------------------------------------
    def updatePreview(self, automatic=False):

        if not self.results:
            return

        idx = self.comboPreview.currentIndex()
        if idx < 0:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        data = self.results[idx]["data"]

        for row, layer_name in enumerate(data):

            x_plot = data[layer_name]["x_plot"]
            y_plot = data[layer_name]["y_plot"]

            if not x_plot:
                continue

            color_item = self.tableLayerAnno.item(row, 2)
            color = color_item.background().color().name()

            label_item = self.tableLayerAnno.item(row, 1)
            label = label_item.text()

            ax.plot(x_plot, y_plot, label=label, color=color)

        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Elevation (m)")



        #ax.set_title("Topo-bathymetric profile", fontsize=12, pad=20)

        # Buffer info sotto il titolo
        #ax.text(
        #    0.5, 1.08,
        #    f"Buffer distance: {self.buffer_distance} m",
        #    transform=ax.transAxes,
        #    ha='center',
        #    fontsize=9,
        #    alpha=0.7
        #)

        # ---- titolo e buffer fissi ----
        self.figure.subplots_adjust(top=0.85)  # spazio sufficiente per titolo e buffer

        # titolo al 95% della figura in alto
        self.figure.text(
            0.5, 0.95,
            "Topo-bathymetric profile",
            ha='center', va='top', fontsize=12, weight='bold'
        )

        # buffer sotto il titolo, 5% più in basso
        self.figure.text(
            0.5, 0.90,
            f"Buffer distance: {self.buffer_distance} m",
            ha='center', va='top', fontsize=9, alpha=0.7
        )





        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend()

        if automatic:
            self.spinXMin.setValue(ax.get_xlim()[0])
            self.spinXMax.setValue(ax.get_xlim()[1])
            self.spinYMin.setValue(ax.get_ylim()[0])
            self.spinYMax.setValue(ax.get_ylim()[1])
        else:
            ax.set_xlim(self.spinXMin.value(), self.spinXMax.value())
            ax.set_ylim(self.spinYMin.value(), self.spinYMax.value())

        self.canvas.draw()

    # ----------------------------------------------------------
    # EXPORT
    # ----------------------------------------------------------
    def exportPNG(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "", "PNG (*.png)")
        if path:
            self.figure.savefig(path, dpi=300)

    def exportCSV(self):

        if not self.results:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV (*.csv)")
        if not path:
            return

        import csv

        data = self.results[self.comboPreview.currentIndex()]["data"]

        export_only_visible = self.chkExportShownOnly.isChecked()

        x_min = float(self.spinXMin.value())
        x_max = float(self.spinXMax.value())
        y_min = float(self.spinYMin.value())
        y_max = float(self.spinYMax.value())

        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)

            header = []
            for row, name in enumerate(data):
                label = self.tableLayerAnno.item(row, 1).text()
                header += [f"Elevation_{label}", f"Distance_{label}"]

            writer.writerow(header)

            maxlen = max(len(v["x_plot"]) for v in data.values())

            for i in range(maxlen):
                row_data = []

                for name in data:
                    xp = data[name]["x_plot"]
                    yp = data[name]["y_plot"]

                    if i < len(xp):
                        x_val = xp[i]
                        y_val = yp[i]

                        if export_only_visible:
                            if not (x_min <= x_val <= x_max and y_min <= y_val <= y_max):
                                row_data += ["", ""]
                                continue

                        row_data += [y_val, x_val]
                    else:
                        row_data += ["", ""]

                writer.writerow(row_data)
