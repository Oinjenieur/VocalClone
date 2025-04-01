MAIN_STYLE = """
/* Style général de la fenêtre */
QMainWindow {
    background-color: #1e1e1e;
    color: #ffffff;
}

/* Boîtes de dialogue */
QMessageBox {
    background-color: #f0f0f0;
}

QMessageBox QLabel {
    color: #000000;
    font-size: 12px;
    padding: 10px;
}

QMessageBox QPushButton {
    background-color: #007acc;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 8px 15px;
    min-width: 80px;
}

QMessageBox QPushButton:hover {
    background-color: #0098ff;
}

QMessageBox QPushButton:pressed {
    background-color: #005999;
}

QMessageBox QPushButton[text="OK"] {
    background-color: #2ea043;
}

QMessageBox QPushButton[text="OK"]:hover {
    background-color: #3cb371;
}

QMessageBox QPushButton[text="OK"]:pressed {
    background-color: #1a7f37;
}

QMessageBox QPushButton[text="Annuler"] {
    background-color: #6c757d;
}

QMessageBox QPushButton[text="Annuler"]:hover {
    background-color: #5a6268;
}

QMessageBox QPushButton[text="Annuler"]:pressed {
    background-color: #545b62;
}

/* Groupes */
QGroupBox {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    margin-top: 1em;
    padding: 10px;
}

QGroupBox::title {
    color: #00a6ff;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
}

/* Zone de texte */
QTextEdit {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    padding: 5px;
    selection-background-color: #264f78;
}

/* Listes déroulantes */
QComboBox {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    padding: 5px;
    min-width: 6em;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(resources/icons/down_arrow.png);
    width: 12px;
    height: 12px;
}

/* Boutons */
QPushButton {
    background-color: #007acc;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 8px 15px;
    min-width: 100px;
}

QPushButton:hover {
    background-color: #0098ff;
}

QPushButton:pressed {
    background-color: #005999;
}

QPushButton:disabled {
    background-color: #3d3d3d;
    color: #808080;
}

/* Boutons spéciaux */
QPushButton#recordButton {
    background-color: #ff4444;
}

QPushButton#recordButton:hover {
    background-color: #ff6666;
}

QPushButton#recordButton:checked {
    background-color: #cc0000;
}

QPushButton#cloneButton {
    background-color: #2ea043;
}

QPushButton#cloneButton:hover {
    background-color: #3cb371;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #3d3d3d;
    height: 8px;
    background: #2d2d2d;
    margin: 2px 0;
}

QSlider::handle:horizontal {
    background: #007acc;
    border: none;
    width: 18px;
    margin: -2px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #0098ff;
}

/* Cases à cocher */
QCheckBox {
    color: #ffffff;
    spacing: 5px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QCheckBox::indicator:unchecked {
    border: 1px solid #3d3d3d;
    background: #2d2d2d;
}

QCheckBox::indicator:checked {
    background: #0078d4;
    border: 1px solid #0078d4;
}

/* Labels */
QLabel {
    color: #ffffff;
}

/* Barres de progression */
QProgressBar {
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    text-align: center;
    background-color: #2d2d2d;
}

QProgressBar::chunk {
    background-color: #007acc;
    border-radius: 4px;
}

/* Volume Meter */
VolumeMeter {
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    min-height: 20px;
}

VolumeMeter::chunk {
    background-color: #00ff00;
    border-radius: 2px;
}

QStatusBar {
    background-color: #2d2d2d;
    color: #ffffff;
}

QMenuBar {
    background-color: #2d2d2d;
    color: #ffffff;
}

QMenuBar::item {
    padding: 5px 10px;
}

QMenuBar::item:selected {
    background-color: #3d3d3d;
}

QMenu {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3d3d3d;
}

QMenu::item:selected {
    background-color: #3d3d3d;
}
""" 