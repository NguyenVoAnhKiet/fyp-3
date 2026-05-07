import sys
import os

# Ensure src is in PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "src"))

from PyQt5.QtWidgets import QApplication
from attendance_system.ui.login_widget import LoginWidget

def main():
    app = QApplication(sys.argv)
    
    widget = LoginWidget()
    widget.setWindowTitle("Test Login Widget")
    widget.resize(450, 550)
    
    widget.login_requested.connect(lambda u, p: print(f"Login Requested: {u} / {p}"))
    widget.cancel_requested.connect(lambda: (print("Cancel Requested"), app.quit()))
    
    widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
