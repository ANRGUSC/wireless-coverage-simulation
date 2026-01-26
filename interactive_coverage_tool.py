"""
Interactive USC Campus Wireless Coverage Tool

This interactive application allows users to:
- Adjust radio/PHY layer parameters via input fields
- Click on the map to place base stations
- Drag base stations to move them
- Right-click base stations to delete them
- View real-time coverage updates
- Export the map as output.png
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


class CoverageCalculator:
    def __init__(self, building_mask_path):
        img = Image.open(building_mask_path).convert("L")
        self.img_np = np.array(img)
        self.img_height, self.img_width = self.img_np.shape
        self.building_mask = self.img_np < 128
        self.outdoor_mask = ~self.building_mask
        self.outdoor_pixels = np.argwhere(self.outdoor_mask)
        self.map_width_m = 640.0
        self.map_height_m = 430.0

    def meters_to_pixels(self, x_meters, y_meters):
        px = int(x_meters / self.map_width_m * self.img_width)
        py = int(y_meters / self.map_height_m * self.img_height)
        px = max(0, min(self.img_width - 1, px))
        py = max(0, min(self.img_height - 1, py))
        return px, py

    def pixels_to_meters(self, px, py):
        x_meters = px / self.img_width * self.map_width_m
        y_meters = py / self.img_height * self.map_height_m
        return x_meters, y_meters

    def has_line_of_sight(self, x1, y1, x2, y2):
        px1, py1 = self.meters_to_pixels(x1, y1)
        px2, py2 = self.meters_to_pixels(x2, y2)
        dx = abs(px2 - px1)
        dy = abs(py2 - py1)
        sx = 1 if px1 < px2 else -1
        sy = 1 if py1 < py2 else -1
        err = dx - dy
        cx, cy = px1, py1
        while True:
            if self.building_mask[cy, cx]:
                return False
            if cx == px2 and cy == py2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy
        return True

    def free_space_path_loss(self, distance_m, freq_hz):
        c = 3e8
        wavelength = c / freq_hz
        fspl_db = 20 * np.log10(4 * np.pi * distance_m / wavelength)
        return fspl_db

    def calculate_max_range(self, tx_power, noise, snr_threshold, shadow_std, freq_hz):
        c = 3e8
        wavelength = c / freq_hz
        max_path_loss = tx_power - noise - snr_threshold + 3 * shadow_std
        max_range = (wavelength / (4 * np.pi)) * (10 ** (max_path_loss / 20))
        return max_range

    def calculate_coverage(self, base_stations, tx_power, noise, snr_threshold, shadow_std, freq_hz):
        if len(base_stations) == 0:
            output_img = np.ones((self.img_height, self.img_width, 3))
            output_img[self.building_mask] = [0.3, 0.3, 0.3]
            return output_img, 0.0
        num_bs = len(base_stations)
        max_range = self.calculate_max_range(tx_power, noise, snr_threshold, shadow_std, freq_hz)
        np.random.seed(42)
        shadowing_maps = []
        for i in range(num_bs):
            shadow = np.random.normal(0, shadow_std, (self.img_height, self.img_width))
            shadowing_maps.append(shadow)
        coverage_masks = [np.zeros((self.img_height, self.img_width), dtype=bool) for _ in range(num_bs)]
        for bs_idx, (bs_x, bs_y) in enumerate(base_stations):
            for py, px in self.outdoor_pixels:
                pt_x, pt_y = self.pixels_to_meters(px, py)
                distance = np.sqrt((pt_x - bs_x)**2 + (pt_y - bs_y)**2)
                distance = max(distance, 1.0)
                if distance > max_range:
                    continue
                fspl = self.free_space_path_loss(distance, freq_hz)
                shadowing = shadowing_maps[bs_idx][py, px]
                total_path_loss = fspl + shadowing
                received_power_dbm = tx_power - total_path_loss
                snr_db = received_power_dbm - noise
                if snr_db < snr_threshold:
                    continue
                if self.has_line_of_sight(bs_x, bs_y, pt_x, pt_y):
                    coverage_masks[bs_idx][py, px] = True
        if num_bs <= 10:
            colors_rgb = [
                (0.12, 0.47, 0.71), (1.0, 0.50, 0.05), (0.17, 0.63, 0.17),
                (0.84, 0.15, 0.16), (0.58, 0.40, 0.74), (0.55, 0.34, 0.29),
                (0.89, 0.47, 0.76), (0.50, 0.50, 0.50), (0.74, 0.74, 0.13),
                (0.09, 0.75, 0.81)
            ][:num_bs]
        elif num_bs <= 20:
            colors_rgb = []
            for i in range(num_bs):
                hue = i / 20.0
                r, g, b = self.hsv_to_rgb(hue, 0.8, 0.9)
                colors_rgb.append((r, g, b))
        else:
            colors_rgb = []
            for i in range(num_bs):
                hue = i / num_bs
                r, g, b = self.hsv_to_rgb(hue, 0.8, 0.9)
                colors_rgb.append((r, g, b))
        output_img = np.ones((self.img_height, self.img_width, 3))
        output_img[self.building_mask] = [0.3, 0.3, 0.3]
        alpha = 0.35
        for py, px in self.outdoor_pixels:
            covering_bs = [i for i in range(num_bs) if coverage_masks[i][py, px]]
            if len(covering_bs) == 0:
                continue
            blended = np.array([1.0, 1.0, 1.0])
            for bs_idx in covering_bs:
                color = np.array(colors_rgb[bs_idx])
                blended = alpha * color + (1 - alpha) * blended
            output_img[py, px] = np.clip(blended, 0, 1)
        any_coverage = np.zeros((self.img_height, self.img_width), dtype=bool)
        for mask in coverage_masks:
            any_coverage |= mask
        total_covered = np.sum(any_coverage & self.outdoor_mask)
        total_outdoor = len(self.outdoor_pixels)
        coverage_percent = 100 * total_covered / total_outdoor
        return output_img, coverage_percent, colors_rgb

    def hsv_to_rgb(self, h, s, v):
        if s == 0.0:
            return (v, v, v)
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6
        if i == 0:
            return (v, t, p)
        if i == 1:
            return (q, v, p)
        if i == 2:
            return (p, v, t)
        if i == 3:
            return (p, q, v)
        if i == 4:
            return (t, p, v)
        if i == 5:
            return (v, p, q)


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
        self.tx_power_input = QLineEdit("-10.0")
        self.tx_power_input.setToolTip("Transmit power in dBm. Typical: -10 to 30 dBm")
        params_layout.addRow("TX Power (dBm):", self.tx_power_input)
        self.noise_input = QLineEdit("-101.0")
        self.noise_input.setToolTip("Noise floor in dBm. For 20 MHz bandwidth: ~-101 dBm")
        params_layout.addRow("Noise Floor (dBm):", self.noise_input)
        self.snr_input = QLineEdit("10.0")
        self.snr_input.setToolTip("Minimum SNR for connectivity. Typical: 10-20 dB")
        params_layout.addRow("SNR Threshold (dB):", self.snr_input)
        self.shadow_input = QLineEdit("4.0")
        self.shadow_input.setToolTip("Shadowing std dev. Typical: 4-8 dB for urban")
        params_layout.addRow("Shadowing Std (dB):", self.shadow_input)
        self.freq_input = QLineEdit("2.4")
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
        bs_positions = [(item.pos().x() / self.calculator.img_width * self.calculator.map_width_m,
                         item.pos().y() / self.calculator.img_height * self.calculator.map_height_m)
                        for item in self.bs_items]
        result = self.calculator.calculate_coverage(bs_positions, tx_power, noise, snr_threshold, shadow_std, freq_hz)
        if len(result) == 2:
            output_img, coverage_percent = result
            self.colors_rgb = []
        else:
            output_img, coverage_percent, self.colors_rgb = result
        img_uint8 = (output_img * 255).astype(np.uint8)
        height, width, channels = img_uint8.shape
        bytes_per_line = channels * width
        q_image = QImage(img_uint8.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        new_bs_items = []
        for i, (bs_x, bs_y) in enumerate(bs_positions):
            px = bs_x / self.calculator.map_width_m * self.calculator.img_width
            py = bs_y / self.calculator.map_height_m * self.calculator.img_height
            if i < len(self.colors_rgb):
                r, g, b = self.colors_rgb[i]
                color = QColor(int(r * 255), int(g * 255), int(b * 255))
            else:
                color = QColor(255, 0, 0)
            bs_item = BaseStationItem(px, py, i, color, self)
            self.scene.addItem(bs_item)
            new_bs_items.append(bs_item)
        self.bs_items = new_bs_items
        self.bs_count_label.setText(f"Base Stations: {len(self.bs_items)}")
        self.coverage_label.setText(f"Coverage: {coverage_percent:.1f}%")
        max_range = self.calculator.calculate_max_range(tx_power, noise, snr_threshold, shadow_std, freq_hz)
        self.max_range_label.setText(f"Max Range: {max_range:.1f} m")
        self.current_coverage_image = output_img

    def add_base_station_at(self, px, py):
        px = max(0, min(px, self.calculator.img_width - 1))
        py = max(0, min(py, self.calculator.img_height - 1))
        int_px = int(px)
        int_py = int(py)
        if self.calculator.building_mask[int_py, int_px]:
            self.statusBar.showMessage("Cannot place base station inside a building", 3000)
            return
        num_bs = len(self.bs_items)
        if num_bs < 10:
            colors = [
                (0.12, 0.47, 0.71), (1.0, 0.50, 0.05), (0.17, 0.63, 0.17),
                (0.84, 0.15, 0.16), (0.58, 0.40, 0.74), (0.55, 0.34, 0.29),
                (0.89, 0.47, 0.76), (0.50, 0.50, 0.50), (0.74, 0.74, 0.13),
                (0.09, 0.75, 0.81)
            ]
            r, g, b = colors[num_bs]
        else:
            hue = num_bs / 20.0
            r, g, b = self.calculator.hsv_to_rgb(hue, 0.8, 0.9)
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
        output_img = self.current_coverage_image.copy()
        bs_positions = [(item.pos().x() / self.calculator.img_width * self.calculator.map_width_m,
                         item.pos().y() / self.calculator.img_height * self.calculator.map_height_m)
                        for item in self.bs_items]
        for i, (bs_x, bs_y) in enumerate(bs_positions):
            px = int(bs_x / self.calculator.map_width_m * self.calculator.img_width)
            py = int(bs_y / self.calculator.map_height_m * self.calculator.img_height)
            if i < len(self.colors_rgb):
                color = self.colors_rgb[i]
            else:
                color = (1.0, 0.0, 0.0)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    if 0 <= py + dy < self.calculator.img_height and 0 <= px + dx < self.calculator.img_width:
                        output_img[py + dy, px + dx] = color
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
