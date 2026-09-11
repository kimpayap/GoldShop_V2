import os
from pathlib import Path

os.environ["GOLDSHOP_DB_PATH"]=str(Path(__file__).resolve().parent/"database"/"gold_shop_demo.db")

from ui.login import LoginWindow

if __name__=="__main__":
    app=LoginWindow();app.mainloop()
