import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QSlider,
    QFileDialog, QPushButton, QGroupBox, QGridLayout, QMessageBox, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


def cv_to_pixmap(cv_img):
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qt_image).scaled(300, 300, Qt.KeepAspectRatio)


class ColorSegmentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Segmentation Viewer")
        self.setStyleSheet("background-color: #1e1e2f; color: white; font-family: 'Microsoft YaHei';")
        self.image = None
        self.hsv = None
        self.result_images = [None] * 4
        self.original_image = None  # 新增，保存原始图片
        self.contrast = 1.0        # 新增，对比度参数
        self.brightness = 0        # 新增，亮度参数

        self.green_range = [30, 95, 20, 255, 20, 255]
        self.orange_range = [5, 30, 30, 255, 30, 255]

        self.title_labels = []  # 保存标题标签引用
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.img_labels = []
        self.img_titles = ["Original", "Green Regions", "Orange Regions", "Binary Image"]
        grid = QGridLayout()

        for i in range(4):
            vbox = QVBoxLayout()
            title_label = QLabel(f"<b>{self.img_titles[i]}</b>")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-size: 16px; color: #00ccff; font-family: 'Microsoft YaHei';")
            self.title_labels.append(title_label)
            vbox.addWidget(title_label)

            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("")
            self.img_labels.append(label)
            vbox.addWidget(label)

            grid.addLayout(vbox, i // 2, i % 2)

        layout.addLayout(grid, stretch=1)  # 图片显示区自适应拉伸

        # 按钮区域
        btn_layout = QHBoxLayout()

        btn_open = QPushButton("Open Image")
        btn_open.setStyleSheet("background-color: #0055aa; color: white; font-weight: bold; font-family: 'Microsoft YaHei';")
        btn_open.clicked.connect(self.load_image)
        btn_layout.addWidget(btn_open)

        btn_save = QPushButton("Save Images")
        btn_save.setStyleSheet("background-color: #007733; color: white; font-weight: bold; font-family: 'Microsoft YaHei';")
        btn_save.clicked.connect(self.save_images)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

        sliders = self.create_sliders()
        layout.addWidget(sliders)

        # 新增：对比度/亮度滑块，两行显示
        self.contrast_box = QGroupBox("Original Image Contrast/Brightness")
        self.contrast_box.setStyleSheet("QGroupBox { margin-top: 8px; margin-bottom: 2px; padding: 0 0 0 0; font-size: 12px; font-family: 'Microsoft YaHei'; } QLabel { font-size: 12px; font-family: 'Microsoft YaHei'; } QSlider { min-height: 12px; max-height: 16px; font-family: 'Microsoft YaHei'; }")
        contrast_vlayout = QVBoxLayout()
        # 对比度行
        contrast_hlayout = QHBoxLayout()
        self.contrast_label = QLabel("Contrast: 1.0")
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(50)
        self.contrast_slider.setMaximum(200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.update_contrast_brightness)
        contrast_hlayout.addWidget(self.contrast_label)
        contrast_hlayout.addWidget(self.contrast_slider)
        contrast_vlayout.addLayout(contrast_hlayout)
        # 亮度行
        brightness_hlayout = QHBoxLayout()
        self.brightness_label = QLabel("Brightness: 0.0")
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setMinimum(-100)
        self.brightness_slider.setMaximum(100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self.update_contrast_brightness)
        brightness_hlayout.addWidget(self.brightness_label)
        brightness_hlayout.addWidget(self.brightness_slider)
        contrast_vlayout.addLayout(brightness_hlayout)
        self.contrast_box.setLayout(contrast_vlayout)
        layout.addWidget(self.contrast_box)

        self.setLayout(layout)

    def create_sliders(self):
        box = QGroupBox("Adjust HSV Range")
        box.setStyleSheet("QGroupBox { color: white; font-weight: bold; font-family: 'Microsoft YaHei'; }")
        layout = QGridLayout()

        self.sliders = []
        labels = [
            "Green H Low", "Green H High", "Orange H Low", "Orange H High",
            "S Low", "S High", "V Low", "V High"
        ]
        ranges = [(0, 180)] * 4 + [(0, 255)] * 4
        defaults = [30, 95, 5, 30, 20, 255, 20, 255]

        for i, (name, (mn, mx), val) in enumerate(zip(labels, ranges, defaults)):
            label = QLabel(f"{name}: {val}")
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(mn)
            slider.setMaximum(mx)
            slider.setValue(val)
            slider.valueChanged.connect(self.update_sliders)
            layout.addWidget(label, i, 0)
            layout.addWidget(slider, i, 1)
            self.sliders.append((label, slider))

        box.setLayout(layout)
        return box

    def update_sliders(self):
        values = [s.value() for (_, s) in self.sliders]
        self.green_range = [values[0], values[1], values[4], values[5], values[6], values[7]]
        self.orange_range = [values[2], values[3], values[4], values[5], values[6], values[7]]
        for i, (label, slider) in enumerate(self.sliders):
            label.setText(f"{label.text().split(':')[0]}: {slider.value()}")
        if self.image is not None:
            self.process_image()

    def update_contrast_brightness(self):
        self.contrast = self.contrast_slider.value() / 100.0
        self.brightness = self.brightness_slider.value()
        self.contrast_label.setText(f"Contrast: {self.contrast:.2f}")
        self.brightness_label.setText(f"Brightness: {self.brightness:.2f}")
        if self.original_image is not None:
            self.process_image()

    def is_binary_image(self, img):
        # 判断是否为二值化图像（单通道或三通道，只有0和255）
        if len(img.shape) == 2:
            unique = np.unique(img)
            return set(unique).issubset({0, 255})
        elif len(img.shape) == 3 and img.shape[2] == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            unique = np.unique(gray)
            return set(unique).issubset({0, 255})
        return False

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.bmp)")
        if path:
            self.original_image = cv2.imread(path)
            self.image = self.original_image.copy()
            self.process_image()

    def count_regions(self, mask):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return len(contours)

    def apply_contrast(self, img, alpha, beta):
        # alpha为对比度系数，1.0为原始，beta为亮度偏移
        img = img.astype(np.float32) * alpha + beta
        img = np.clip(img, 0, 255)
        return img.astype(np.uint8)

    def process_image(self):
        if self.original_image is None:
            return
        # 对比度和亮度调整
        img_adj = self.apply_contrast(self.original_image, self.contrast, self.brightness)
        self.image = img_adj
        # 检查是否为二值化图
        if self.is_binary_image(self.image):
            if len(self.image.shape) == 3 and self.image.shape[2] == 3:
                binary_img = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            else:
                binary_img = self.image
            img_binary = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
            img_ori = img_binary.copy()
            img_green = np.zeros_like(img_ori)
            img_orange = np.zeros_like(img_ori)
            self.result_images = [img_ori, img_green, img_orange, img_binary]
            cnt = self.count_regions(binary_img)
            self.title_labels[1].setText(f"<b>Green Regions (0)</b>")
            self.title_labels[2].setText(f"<b>Orange Regions (0)</b>")
            self.title_labels[0].setText(f"<b>Original ({cnt})</b>")
            self.title_labels[3].setText("<b>Binary Image</b>")
            for i in range(4):
                self.img_labels[i].setPixmap(cv_to_pixmap(self.result_images[i]))
            return
        # 原有流程
        self.hsv = cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV)
        gl, gh, sl, sh, vl, vh = self.green_range
        ol, oh, _, _, _, _ = self.orange_range
        lower_green = np.array([gl, sl, vl])
        upper_green = np.array([gh, sh, vh])
        lower_orange = np.array([ol, sl, vl])
        upper_orange = np.array([oh, sh, vh])

        mask_green_raw = cv2.inRange(self.hsv, lower_green, upper_green)
        mask_orange_raw = cv2.inRange(self.hsv, lower_orange, upper_orange)

        conflict = cv2.bitwise_and(mask_green_raw, mask_orange_raw)
        mask_green = cv2.bitwise_and(mask_green_raw, cv2.bitwise_not(conflict))
        mask_orange = cv2.bitwise_and(mask_orange_raw, cv2.bitwise_not(conflict))
        mask_all = cv2.bitwise_or(mask_green, mask_orange)

        img_ori = self.image
        img_green = cv2.bitwise_and(img_ori, img_ori, mask=mask_green)
        img_orange = cv2.bitwise_and(img_ori, img_ori, mask=mask_orange)
        img_binary = cv2.cvtColor(mask_all, cv2.COLOR_GRAY2BGR)

        self.result_images = [img_ori, img_green, img_orange, img_binary]

        for i in range(4):
            self.img_labels[i].setPixmap(cv_to_pixmap(self.result_images[i]))

        # 统计数量并更新标题
        green_cnt = self.count_regions(mask_green)
        orange_cnt = self.count_regions(mask_orange)
        self.title_labels[1].setText(f"<b>Green Regions ({green_cnt})</b>")
        self.title_labels[2].setText(f"<b>Orange Regions ({orange_cnt})</b>")
        self.title_labels[0].setText(f"<b>Original ({green_cnt+orange_cnt})</b>")
        self.title_labels[3].setText("<b>Binary Image</b>")

    def save_images(self):
        if self.result_images[0] is None:
            QMessageBox.warning(self, "Not Processed", "Please open and process an image first!")
            return
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if folder:
            names = ["original.png", "green.png", "orange.png", "binary.png"]
            for img, name in zip(self.result_images, names):
                cv2.imwrite(os.path.join(folder, name), img)
            QMessageBox.information(self, "Save Successful", f"Images saved to:\n{folder}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    viewer = ColorSegmentApp()
    viewer.resize(900, 750)
    viewer.show()
    sys.exit(app.exec_())
