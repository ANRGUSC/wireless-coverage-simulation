"""
Interactive USC Campus Wireless Coverage Tool

This interactive application allows users to:
- Adjust radio/PHY layer parameters via input fields
- Click on the map to place base stations
- Drag base stations to move them
- Right-click base stations to delete them
- View real-time coverage updates
- Export the map as output.png

Uses the webapp-compatible coverage engine from usc_coverage.py for
results that match the web application exactly.
"""

import sys
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
                             QGroupBox, QFormLayout, QStatusBar, QMessageBox)
from PyQt5.QtGui import QImage, QPixmap, QPen, QBrush, QColor, QPainter
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer

from usc_coverage import (
    CoverageCalculator, MAP_WIDTH_M, MAP_HEIGHT_M, TX_POWER_DBM,
    NOISE_DBM, SNR_THRESHOLD_DB, SHADOW_STD_DB, FREQ_HZ, COMPUTE_SCALE
)


class BaseStationItem(QGraphicsEllipseItem):
    def __init__(self, x, y, index, color, parent_tool):
        size = 14
        super().__init__(-size/2, -size/2, size, size)
        self.setPos(x, y)
        self.index = index
        self.parent_tool = parent_tool
        self.color = color
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)
        self.setZValue(100)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.parent_tool.delete_base_station(self)
            event.accept()
        else:
            self.setCursor(Qt.ClosedHandCursor)
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            self.parent_tool.on_base_station_moved()

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionChange and self.scene():
            new_pos = value
            rect = self.scene().sceneRect()
            if not rect.contains(new_pos):
                new_pos.setX(min(rect.right(), max(new_pos.x(), rect.left())))
                new_pos.setY(min(rect.bottom(), max(new_pos.y(), rect.top())))
                return new_pos
        return super().itemChange(change, value)


class MapGraphicsView(QGraphicsView):
    def __init__(self, scene, parent_tool):
        super().__init__(scene)
        self.parent_tool = parent_tool
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, BaseStationItem):
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.parent_tool.add_base_station_at(scene_pos.x(), scene_pos.y())
        else:
            super().mousePressEvent(event)


class InteractiveCoverageTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USC Campus Wireless Coverage Tool")
        self.calculator = CoverageCalculator("usc_map_buildings_filled.png")
        self.base_stations = []
        self.bs_items = []
        self.colors_rgb = []
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.recalculate_coverage)
        self.init_ui()
        self.update_map_display()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(280)
        params_group = QGroupBox("Radio/PHY Parameters")
        params_layout = QFormLayout()
        self.tx_power_input = QLineEdit(str(TX_POWER_DBM))
        self.tx_power_input.setToolTip("Transmit power in dBm. Typical: -10 to 30 dBm")
        params_layout.addRow("TX Power (dBm):", self.tx_power_input)
        self.noise_input = QLineEdit(str(NOISE_DBM))
        self.noise_input.setToolTip("Noise floor in dBm. For 20 MHz bandwidth: ~-101 dBm")
        params_layout.addRow("Noise Floor (dBm):", self.noise_input)
        self.snr_input = QLineEdit(str(SNR_THRESHOLD_DB))
        self.snr_input.setToolTip("Minimum SNR for connectivity. Typical: 10-20 dB")
        params_layout.addRow("SNR Threshold (dB):", self.snr_input)
        self.shadow_input = QLineEdit(str(SHADOW_STD_DB))
        self.shadow_input.setToolTip("Shadowing std dev. Typical: 4-8 dB for urban")
        params_layout.addRow("Shadowing Std (dB):", self.shadow_input)
        self.freq_input = QLineEdit(str(FREQ_HZ / 1e9))
        self.freq_input.setToolTip("Carrier frequency. Common: 2.4 GHz (WiFi), 3.5 GHz (5G)")
        params_layout.addRow("Frequency (GHz):", self.freq_input)
        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)
        self.apply_button = QPushButton("Apply Parameters")
        self.apply_button.clicked.connect(self.on_apply_parameters)
        left_layout.addWidget(self.apply_button)
        stats_group = QGroupBox("Coverage Statistics")
        stats_layout = QVBoxLayout()
        self.bs_count_label = QLabel("Base Stations: 0")
        self.coverage_label = QLabel("Coverage: 0.0%")
        self.max_range_label = QLabel("Max Range: 0.0 m")
        stats_layout.addWidget(self.bs_count_label)
        stats_layout.addWidget(self.coverage_label)
        stats_layout.addWidget(self.max_range_label)
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group)
        instructions_group = QGroupBox("Instructions")
        instructions_layout = QVBoxLayout()
        instructions_text = QLabel(
            "Left-click: Place base station\n"
            "Drag: Move base station\n"
            "Right-click: Delete base station\n"
            "Apply Parameters: Recalculate"
        )
        instructions_text.setWordWrap(True)
        instructions_layout.addWidget(instructions_text)
        instructions_group.setLayout(instructions_layout)
        left_layout.addWidget(instructions_group)
        self.clear_button = QPushButton("Clear All Base Stations")
        self.clear_button.clicked.connect(self.clear_all_base_stations)
        left_layout.addWidget(self.clear_button)
        self.export_button = QPushButton("Export Map (output.png)")
        self.export_button.clicked.connect(self.export_map)
        left_layout.addWidget(self.export_button)
        left_layout.addStretch()
        main_layout.addWidget(left_panel)
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, self.calculator.img_width, self.calculator.img_height)
        self.view = MapGraphicsView(self.scene, self)
        self.view.setMinimumSize(800, 600)
        main_layout.addWidget(self.view, 1)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Click on the map to place base stations")

    def get_parameters(self):
        try:
            tx_power = float(self.tx_power_input.text())
            noise = float(self.noise_input.text())
            snr_threshold = float(self.snr_input.text())
            shadow_std = float(self.shadow_input.text())
            freq_hz = float(self.freq_input.text()) * 1e9
            return tx_power, noise, snr_threshold, shadow_std, freq_hz
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for all parameters.")
            return None

    def update_map_display(self):
        params = self.get_parameters()
        if params is None:
            return
        tx_power, noise, snr_threshold, shadow_std, freq_hz = params

        # Convert pixel positions to meter positions
        bs_positions = []
        for item in self.bs_items:
            x_m = item.pos().x() / self.calculator.img_width * MAP_WIDTH_M
            y_m = item.pos().y() / self.calculator.img_height * MAP_HEIGHT_M
            bs_positions.append((x_m, y_m))

        # Calculate coverage using the new engine
        result = self.calculator.calculate_coverage_detailed(
            bs_positions, tx_power, noise, snr_threshold, shadow_std, freq_hz
        )

        coverage_percent = result['coverage_percent']
        image_data = result['image_data']  # (small_h, small_w, 4) RGBA
        max_range = result['max_range']
        self.colors_rgb = [(c[0]/255.0, c[1]/255.0, c[2]/255.0) for c in result['bs_colors']]

        # Upscale image to full resolution for display
        small_h, small_w = image_data.shape[:2]
        full_img = np.zeros((self.calculator.img_height, self.calculator.img_width, 3), dtype=np.uint8)

        for y in range(self.calculator.img_height):
            sy = min(y // COMPUTE_SCALE, small_h - 1)
            for x in range(self.calculator.img_width):
                sx = min(x // COMPUTE_SCALE, small_w - 1)
                full_img[y, x] = image_data[sy, sx, :3]

        # Create QImage and display
        height, width = full_img.shape[:2]
        bytes_per_line = 3 * width
        q_image = QImage(full_img.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.scene.clear()
        self.scene.addPixmap(pixmap)

        # Re-add base station items
        new_bs_items = []
        for i, (bs_x, bs_y) in enumerate(bs_positions):
            px = bs_x / MAP_WIDTH_M * self.calculator.img_width
            py = bs_y / MAP_HEIGHT_M * self.calculator.img_height
            if i < len(self.colors_rgb):
                r, g, b = self.colors_rgb[i]
                color = QColor(int(r * 255), int(g * 255), int(b * 255))
            else:
                color = QColor(255, 0, 0)
            bs_item = BaseStationItem(px, py, i, color, self)
            self.scene.addItem(bs_item)
            new_bs_items.append(bs_item)
        self.bs_items = new_bs_items

        # Update statistics
        self.bs_count_label.setText(f"Base Stations: {len(self.bs_items)}")
        self.coverage_label.setText(f"Coverage: {coverage_percent:.1f}%")
        self.max_range_label.setText(f"Max Range: {max_range:.1f} m")
        self.current_coverage_image = full_img

    def add_base_station_at(self, px, py):
        px = max(0, min(px, self.calculator.img_width - 1))
        py = max(0, min(py, self.calculator.img_height - 1))
        int_px = int(px)
        int_py = int(py)

        # Check if location is outdoor using meter coordinates
        x_m = px / self.calculator.img_width * MAP_WIDTH_M
        y_m = py / self.calculator.img_height * MAP_HEIGHT_M

        if not self.calculator.is_outdoor(x_m, y_m):
            self.statusBar.showMessage("Cannot place base station inside a building", 3000)
            return

        num_bs = len(self.bs_items)
        from usc_coverage import get_bs_colors
        colors = get_bs_colors(num_bs + 1)
        r, g, b = colors[num_bs]
        color = QColor(int(r * 255), int(g * 255), int(b * 255))

        bs_item = BaseStationItem(px, py, num_bs, color, self)
        self.scene.addItem(bs_item)
        self.bs_items.append(bs_item)
        self.statusBar.showMessage(f"Added base station {num_bs + 1}", 2000)
        self.schedule_update()

    def delete_base_station(self, bs_item):
        if bs_item in self.bs_items:
            self.bs_items.remove(bs_item)
            self.scene.removeItem(bs_item)
            self.statusBar.showMessage(f"Deleted base station", 2000)
            self.schedule_update()

    def on_base_station_moved(self):
        self.schedule_update()

    def schedule_update(self):
        self.update_timer.start(100)

    def recalculate_coverage(self):
        self.statusBar.showMessage("Recalculating coverage...")
        QApplication.processEvents()
        self.update_map_display()
        self.statusBar.showMessage("Coverage calculation complete", 2000)

    def on_apply_parameters(self):
        self.recalculate_coverage()

    def clear_all_base_stations(self):
        for item in self.bs_items:
            self.scene.removeItem(item)
        self.bs_items = []
        self.update_map_display()
        self.statusBar.showMessage("Cleared all base stations", 2000)

    def export_map(self):
        if not hasattr(self, 'current_coverage_image'):
            QMessageBox.warning(self, "Export Error", "No map to export. Please calculate coverage first.")
            return

        output_img = self.current_coverage_image.copy().astype(np.float32) / 255.0

        # Draw base station markers
        bs_positions = []
        for item in self.bs_items:
            x_m = item.pos().x() / self.calculator.img_width * MAP_WIDTH_M
            y_m = item.pos().y() / self.calculator.img_height * MAP_HEIGHT_M
            bs_positions.append((x_m, y_m))

        for i, (bs_x, bs_y) in enumerate(bs_positions):
            px = int(bs_x / MAP_WIDTH_M * self.calculator.img_width)
            py = int(bs_y / MAP_HEIGHT_M * self.calculator.img_height)
            if i < len(self.colors_rgb):
                color = self.colors_rgb[i]
            else:
                color = (1.0, 0.0, 0.0)

            # Draw colored square
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    if 0 <= py + dy < self.calculator.img_height and 0 <= px + dx < self.calculator.img_width:
                        output_img[py + dy, px + dx] = color

            # Draw black border
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    if abs(dy) == 4 or abs(dx) == 4:
                        if 0 <= py + dy < self.calculator.img_height and 0 <= px + dx < self.calculator.img_width:
                            output_img[py + dy, px + dx] = [0, 0, 0]

        img_uint8 = (output_img * 255).astype(np.uint8)
        pil_image = Image.fromarray(img_uint8)
        pil_image.save("output.png")
        self.statusBar.showMessage("Map exported to output.png", 3000)
        QMessageBox.information(self, "Export Complete", "Map saved as output.png")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = InteractiveCoverageTool()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
