import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    print("Geometry:", screen.geometry())
    print("Available Geometry:", screen.availableGeometry())
    print("Logical DPI:", screen.logicalDotsPerInch())
    print("Physical DPI:", screen.physicalDotsPerInch())
    print("Device Pixel Ratio:", screen.devicePixelRatio())

if __name__ == "__main__":
    main()
