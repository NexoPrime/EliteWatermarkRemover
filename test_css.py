import sys
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

def main():
    app = QApplication(sys.argv)
    w = QWidget()
    layout = QVBoxLayout(w)
    btn = QPushButton("Test Button")
    layout.addWidget(btn)
    w.setStyleSheet("""
        QPushButton {
            padding: 0.5em 1em;
            background-color: blue;
            color: white;
            font-size: 14pt;
        }
    """)
    w.show()
    # just print if it runs without CSS parsing errors
    print("No crash!")

if __name__ == "__main__":
    main()
