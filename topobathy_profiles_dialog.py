# -*- coding: utf-8 -*-
import os
import numpy as np
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QColorDialog
)
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsProject, QgsMapLayerProxyModel

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .topobathy_profiles_functions import estrai_punti_per_sezione_plugin

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'topobathy_profiles_dialog_base.ui')
)

class TopoBathyProfilesDialog(QDialog, FORM_CLASS):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle("TopoBathy Profiles")
        self.iface = iface

        # Axis limits
        for spin in (self.spinXMin, self.spinYMin):
            spin.setMinimum(-1e12)
        for spin in (self.spinXMax, self.spinYMax):
            spin.setMaximum(1e12)

        # Section layer combo
        self.sectionLayerCombo = QgsMapLayerComboBox(self)
        self.sectionLayerCombo.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.groupInput.layout().replaceWidget(
            self.comboSectionLayer, self.sectionLayerCombo
        )
        self.comboSectionLayer.deleteLater()
        self.comboSectionLayer = self.sectionLayerCombo

        self.punti_layers = []
        self.risultati = []

        # Matplotlib canvas
        self.fig = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.fig)
        self.layoutPreview.layout().addWidget(self.canvas)

        # Signals
        self.btnAddLayer.clicked.connect(self.aggiungiLayer)
        self.btnRemoveLayer.clicked.connect(self.rimuoviLayer)
        self.btnRun.clicked.connect(self.eseguiAnalisi)
        self.btnPreview.clicked.connect(self.aggiornaPreview)
        self.btnSaveGraph.clicked.connect(self.salvaGrafico)
        self.btnSaveCSV.clicked.connect(self.salvaCSV)
        self.tableLayerAnno.cellDoubleClicked.connect(self.scegliColore)
        self.sectionLayerCombo.currentIndexChanged.connect(self.aggiornaFeatureCombo)

        self._reset_completo()

    def showEvent(self, event):
        super().showEvent(event)
        self._reset_completo()
        self.aggiornaComboPunti()
        self.aggiornaFeatureCombo()

    def _reset_completo(self):
        """Reset completo dei dati e della UI"""
        self.punti_layers = []
        self.risultati = []

        # Table
        self.tableLayerAnno.setRowCount(0)
        self.tableLayerAnno.setColumnCount(3)
        self.tableLayerAnno.setHorizontalHeaderLabels(
            ["Point layer", "Label", "Color"]
        )

        # Combos
        self.comboPreview.clear()
        self.comboFeatureSelezionata.clear()

        # Axis spinboxes
        for spin in (self.spinXMin, self.spinXMax, self.spinYMin, self.spinYMax,
                     self.spinSplitDistance, self.spinDistanzaMinPlot):
            spin.blockSignals(True)
            if spin == self.spinDistanzaMinPlot:
                spin.setValue(5)
            else:
                spin.setValue(0)
            spin.blockSignals(False)

        # Checkboxes
        self.chkSplitLine.setChecked(False)
        self.chkFiltraPunti.setChecked(False)

        # Clear plot
        self.fig.clear()
        self.canvas.draw()

    def aggiornaComboPunti(self):
        self.comboPunti.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.geometryType() == 0:  # Point layer
                self.comboPunti.addItem(lyr.name(), lyr)

    def aggiungiLayer(self):
        lyr = self.comboPunti.currentData()
        if not lyr or lyr in self.punti_layers:
            return
        self.punti_layers.append(lyr)
        row = self.tableLayerAnno.rowCount()
        self.tableLayerAnno.insertRow(row)
        self.tableLayerAnno.setItem(row, 0, QTableWidgetItem(lyr.name()))
        self.tableLayerAnno.setItem(row, 1, QTableWidgetItem(""))

        color_item = QTableWidgetItem()
        color = QColor(np.random.randint(0,256),
                       np.random.randint(0,256),
                       np.random.randint(0,256))
        color_item.setBackground(color)
        self.tableLayerAnno.setItem(row, 2, color_item)

    def rimuoviLayer(self):
        row = self.tableLayerAnno.currentRow()
        if row >= 0:
            self.punti_layers.pop(row)
            self.tableLayerAnno.removeRow(row)

    def scegliColore(self, row, col):
        if col != 2:
            return
        c = self.tableLayerAnno.item(row, col).background().color()
        new = QColorDialog.getColor(c, self)
        if new.isValid():
            self.tableLayerAnno.item(row, col).setBackground(new)

    def aggiornaFeatureCombo(self):
        self.comboFeatureSelezionata.clear()
        layer = self.sectionLayerCombo.currentLayer()
        if not layer:
            return
        for f in layer.getFeatures():
            self.comboFeatureSelezionata.addItem(f"ID {f.id()}", f.id())

    def eseguiAnalisi(self):
        sez_layer = self.sectionLayerCombo.currentLayer()
        if not sez_layer or not self.punti_layers:
            QMessageBox.warning(self,"Error","Invalid layers")
            return

        feat_id = self.comboFeatureSelezionata.currentData()
        if feat_id is None:
            QMessageBox.warning(self,"Error","Select a feature")
            return

        for r in range(self.tableLayerAnno.rowCount()):
            if not self.tableLayerAnno.item(r,1).text().strip():
                QMessageBox.warning(self,"Error","Fill all labels")
                return

        self.risultati = estrai_punti_per_sezione_plugin(
            sez_layer,
            self.punti_layers,
            feature_id=feat_id
        )

        self.comboPreview.clear()
        self.comboPreview.addItem(f"ID {feat_id}",0)
        self.comboPreview.setCurrentIndex(0)
        self.aggiornaPreview(automatic=True)

    def aggiornaPreview(self, automatic=False):
        if not self.risultati:
            return

        dati = self.risultati[0]

        self.fig.clear()
        ax = self.fig.add_subplot(111)

        split_enabled = self.chkSplitLine.isChecked()
        split_dist = self.spinSplitDistance.value()

        filtra_enabled = self.chkFiltraPunti.isChecked()
        filtro_dist = self.spinDistanzaMinPlot.value()

        for riga, nome in enumerate(dati):
            d = dati[nome]

            x = np.array(d["x_plot"], dtype=float)
            y = np.array(d["y_plot"], dtype=float)

            # Filter nearby points
            if filtra_enabled and filtro_dist>0:
                xf, yf = [], []
                last_x = None
                for xi, yi in zip(x, y):
                    if np.isnan(xi):
                        xf.append(np.nan)
                        yf.append(np.nan)
                        last_x = None
                        continue
                    if last_x is None or xi - last_x >= filtro_dist:
                        xf.append(xi)
                        yf.append(yi)
                        last_x = xi
                x = np.array(xf)
                y = np.array(yf)

            # Split line
            if split_enabled:
                start=0
                for i in range(1,len(x)):
                    if np.isnan(x[i]) or x[i]-x[i-1]>split_dist:
                        ax.plot(x[start:i], y[start:i],
                                color=self.tableLayerAnno.item(riga,2).background().color().name(),
                                label=self.tableLayerAnno.item(riga,1).text() if start==0 else None)
                        start=i+1
                ax.plot(x[start:],y[start:],color=self.tableLayerAnno.item(riga,2).background().color().name())
            else:
                ax.plot(x,y,label=self.tableLayerAnno.item(riga,1).text(),
                        color=self.tableLayerAnno.item(riga,2).background().color().name())

        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Height (m)")
        ax.legend()
        ax.grid(True)

        if automatic:
            self.canvas.draw()
            xmin,xmax = ax.get_xlim()
            ymin,ymax = ax.get_ylim()
            for s,v in ((self.spinXMin,xmin),(self.spinXMax,xmax),(self.spinYMin,ymin),(self.spinYMax,ymax)):
                s.setValue(v)
            return

        ax.set_xlim(self.spinXMin.value(), self.spinXMax.value())
        ax.set_ylim(self.spinYMin.value(), self.spinYMax.value())
        self.canvas.draw()

    def salvaGrafico(self):
        path,_ = QFileDialog.getSaveFileName(self,"Save image","","PNG (*.png)")
        if path:
            self.fig.savefig(path,dpi=300)

    def salvaCSV(self):
        path,_ = QFileDialog.getSaveFileName(self,"Save CSV","","CSV (*.csv)")
        if not path:
            return

        import csv
        dati = self.risultati[0]

        with open(path,'w',newline='') as f:
            w = csv.writer(f)
            header=[]
            for r,n in enumerate(dati):
                label = self.tableLayerAnno.item(r,1).text()
                header += [f"H_{label}", f"D_{label}"]
            w.writerow(header)

            maxlen=max(len(v["x_plot"]) for v in dati.values())
            for i in range(maxlen):
                row=[]
                for n in dati:
                    xp=dati[n]["x_plot"]
                    yp=dati[n]["y_plot"]
                    row+=[f"{yp[i]:.3f}" if i<len(yp) and yp[i] is not None else "",
                          f"{xp[i]:.3f}" if i<len(xp) and xp[i] is not None else ""]
                w.writerow(row)
