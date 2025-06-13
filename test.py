from PyQt6.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsItem
)
from PyQt6.QtCore import Qt, QRectF
import sys

class DragHandle(QGraphicsRectItem):
    def __init__(self):
        super().__init__(QRectF(0, 0, 26, 50))
        self.setBrush(Qt.GlobalColor.yellow)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    # No need for mouse events: QGraphicsItem drag just works!

app = QApplication(sys.argv)
scene = QGraphicsScene()
handle = DragHandle()
scene.addItem(handle)
view = QGraphicsView(scene)
view.show()
sys.exit(app.exec())
