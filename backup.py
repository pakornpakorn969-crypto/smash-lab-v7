import os
import shutil
from datetime import datetime

# กำหนด Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "smashlab.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def run_backup():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"smashlab_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"Backup created successfully: {backup_path}")
    except Exception as e:
        print(f"Failed to create backup: {str(e)}")

if __name__ == "__main__":
    run_backup()