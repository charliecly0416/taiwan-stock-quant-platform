import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=os.getenv("TW_CLEAN_HOST", "0.0.0.0"), port=int(os.getenv("TW_CLEAN_PORT", "5000")))
