import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.gui.app import SchedulerApp

if __name__ == "__main__":
    app = SchedulerApp()
    app.mainloop()