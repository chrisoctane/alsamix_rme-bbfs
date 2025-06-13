# main.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar, QFileDialog
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from patchbay import PatchbayView
from outputs import OutputTabs

CARD_INDEX = 1  # Update as needed for your interface

class MainWindow(QMainWindow):
    def __init__(self, card_index=1):
        super().__init__()
        self.card = card_index

        # Central widget: tabs for Patchbay and Output Mixer
        self.tabs = QTabWidget()
        self.patch = PatchbayView(self.card)
        self.outtabs = OutputTabs(self.card)
        self.tabs.addTab(self.patch, "Patchbay")
        self.tabs.addTab(self.outtabs, "Output Mixer")

        self.setCentralWidget(self.tabs)
        self.build_toolbar()
        self.setWindowTitle("alsabay_rme-bbfs — Patchbay + Mixer")
        self.resize(1700, 900)

    def build_toolbar(self):
        tb = QToolBar("File")
        self.addToolBar(tb)
        act_save = QAction("Save Patchbay", self); act_save.triggered.connect(self.save)
        act_load = QAction("Load Patchbay", self); act_load.triggered.connect(self.load)
        act_reset = QAction("Reset Patchbay", self); act_reset.triggered.connect(self.patch.populate_items)
        tb.addAction(act_save)
        tb.addAction(act_load)
        tb.addAction(act_reset)
        tb.addSeparator()
        # (You can add more actions here!)

    def save(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Save Patchbay Layout", "patchbay.json", "JSON (*.json)")
        if fn: self.patch.save_layout(fn)
    def load(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Load Patchbay Layout", "", "JSON (*.json)")
        if fn: self.patch.load_layout(fn)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow(CARD_INDEX)
    win.show()
    sys.exit(app.exec())
