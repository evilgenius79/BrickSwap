from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .comfy_client import ComfyClient
from .config import Settings, bundled_refs
from . import pipeline


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    log = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            def progress(_a, _b, msg):
                self.log.emit(msg)
            self.finished.emit(self.fn(progress))
        except Exception:
            self.failed.emit(traceback.format_exc())


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BrickSwap")
        self.resize(1100, 720)
        self.settings = Settings.load()
        self._thread = None
        self._worker = None

        root = QSplitter(Qt.Horizontal)
        self.setCentralWidget(root)

        left = QWidget()
        form = QVBoxLayout(left)

        clip_row = QHBoxLayout()
        self.clip = QLineEdit(self.settings.last_clip)
        browse = QPushButton("Open clip")
        browse.clicked.connect(self.pick_clip)
        clip_row.addWidget(self.clip)
        clip_row.addWidget(browse)
        form.addLayout(clip_row)

        refs = QGroupBox("Reference stills")
        rf = QFormLayout(refs)
        self.living = QLineEdit(self.settings.living_ref)
        self.zombie = QLineEdit(self.settings.zombie_ref)
        self.dog = QLineEdit(self.settings.dog_ref)
        rf.addRow("Living", self._ref_row(self.living))
        rf.addRow("Zombie", self._ref_row(self.zombie))
        rf.addRow("Dog", self._ref_row(self.dog))
        form.addWidget(refs)

        gen = QGroupBox("Generation")
        gf = QFormLayout(gen)
        self.comfy = QLineEdit(self.settings.comfy_url)
        self.classes = QLineEdit(self.settings.detect_classes)
        self.pad = QDoubleSpinBox(); self.pad.setRange(0, 0.3); self.pad.setSingleStep(0.01); self.pad.setValue(self.settings.mask_pad)
        self.protect = QDoubleSpinBox(); self.protect.setRange(0, 0.4); self.protect.setSingleStep(0.01); self.protect.setValue(self.settings.protect_bottom)
        self.seconds = QDoubleSpinBox(); self.seconds.setRange(1, 30); self.seconds.setValue(self.settings.preview_seconds)
        self.long_side = QSpinBox(); self.long_side.setRange(320, 1280); self.long_side.setSingleStep(16); self.long_side.setValue(self.settings.max_long_side)
        self.steps = QSpinBox(); self.steps.setRange(1, 30); self.steps.setValue(self.settings.steps)
        self.lora = QCheckBox("Speed LoRA (4-step)"); self.lora.setChecked(self.settings.use_speed_lora)
        self.prompt = QPlainTextEdit(self.settings.prompt); self.prompt.setMaximumHeight(80)
        gf.addRow("ComfyUI", self.comfy)
        gf.addRow("Detect", self.classes)
        gf.addRow("Mask pad", self.pad)
        gf.addRow("Protect bottom", self.protect)
        gf.addRow("Preview seconds", self.seconds)
        gf.addRow("Long side", self.long_side)
        gf.addRow("Steps", self.steps)
        gf.addRow("", self.lora)
        gf.addRow("Prompt", self.prompt)
        form.addWidget(gen)

        btns = QHBoxLayout()
        self.btn_masks = QPushButton("Preview masks")
        self.btn_five = QPushButton("Preview 5 seconds")
        self.btn_check = QPushButton("Check setup")
        self.btn_masks.clicked.connect(self.do_masks)
        self.btn_five.clicked.connect(self.do_five)
        self.btn_check.clicked.connect(self.do_check)
        btns.addWidget(self.btn_masks)
        btns.addWidget(self.btn_five)
        btns.addWidget(self.btn_check)
        form.addLayout(btns)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        form.addWidget(self.log, 1)
        root.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        self.preview = QLabel("Mask sheet / preview appears here")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumWidth(420)
        rv.addWidget(self.preview, 1)
        root.addWidget(right)
        root.setStretchFactor(0, 3)
        root.setStretchFactor(1, 2)
        self._seed_default_refs()

    def _ref_row(self, line: QLineEdit) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("...")
        btn.setFixedWidth(32)
        btn.clicked.connect(lambda: self.pick_ref(line))
        row.addWidget(line)
        row.addWidget(btn)
        return w

    def _seed_default_refs(self):
        refs = bundled_refs()
        mapping = [
            (self.living, "living_woman.jpg"),
            (self.zombie, "zombie.jpg"),
            (self.dog, "dog.jpg"),
        ]
        for widget, name in mapping:
            if not widget.text():
                hit = refs / name
                if hit.exists():
                    widget.setText(str(hit))

    def pick_clip(self):
        path, _ = QFileDialog.getOpenFileName(self, "Clip", "", "Video (*.mp4 *.mov *.mkv *.avi)")
        if path:
            self.clip.setText(path)

    def pick_ref(self, line: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Reference still", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            line.setText(path)

    def gather(self) -> Settings:
        s = self.settings
        s.last_clip = self.clip.text().strip()
        s.living_ref = self.living.text().strip()
        s.zombie_ref = self.zombie.text().strip()
        s.dog_ref = self.dog.text().strip()
        s.comfy_url = self.comfy.text().strip() or s.comfy_url
        s.detect_classes = self.classes.text().strip() or s.detect_classes
        s.mask_pad = float(self.pad.value())
        s.protect_bottom = float(self.protect.value())
        s.preview_seconds = float(self.seconds.value())
        s.max_long_side = int(self.long_side.value())
        s.steps = int(self.steps.value())
        s.use_speed_lora = self.lora.isChecked()
        s.prompt = self.prompt.toPlainText().strip() or s.prompt
        s.save()
        self.settings = s
        return s

    def append(self, msg: str):
        self.log.appendPlainText(msg)

    def set_busy(self, busy: bool):
        self.btn_masks.setEnabled(not busy)
        self.btn_five.setEnabled(not busy)

    def run_job(self, fn):
        self.set_busy(True)
        self._thread = QThread()
        self._worker = Worker(fn)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.log.connect(self.append)
        self._worker.finished.connect(self._on_done)
        self._worker.failed.connect(self._on_fail)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, result):
        self.set_busy(False)
        if isinstance(result, tuple) and result:
            first = result[0]
            self.append(str(result[-1]))
            if first and Path(first).exists() and str(first).lower().endswith((".png", ".jpg", ".jpeg")):
                pix = QPixmap(str(first))
                self.preview.setPixmap(pix.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.append(str(result))

    def _on_fail(self, err: str):
        self.set_busy(False)
        self.append(err)
        QMessageBox.critical(self, "BrickSwap", err[-1500:])

    def do_check(self):
        s = self.gather()
        client = ComfyClient(s.comfy_url)
        if not client.ok():
            self.append("ComfyUI not reachable at " + s.comfy_url)
            return
        missing = client.has_nodes(["WanAnimateToVideo", "VHS_LoadVideo", "UNETLoader", "CLIPVisionLoader"])
        if missing:
            self.append("Missing nodes: " + ", ".join(missing))
        else:
            self.append("ComfyUI looks ready.")

    def do_masks(self):
        s = self.gather()
        clip = Path(s.last_clip)
        if not clip.exists():
            QMessageBox.warning(self, "BrickSwap", "Open a clip first.")
            return
        self.append("Preview masks...")
        self.run_job(lambda progress: pipeline.preview_masks(clip, s, progress))

    def do_five(self):
        s = self.gather()
        clip = Path(s.last_clip)
        if not clip.exists():
            QMessageBox.warning(self, "BrickSwap", "Open a clip first.")
            return
        self.append("Preview 5 seconds...")
        self.run_job(lambda progress: pipeline.preview_five(clip, s, progress))


def main():
    app = QApplication([])
    win = Main()
    win.show()
    app.exec()
