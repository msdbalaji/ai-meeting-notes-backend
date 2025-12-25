import os

DISABLE_ML = os.getenv("DISABLE_ML", "false").lower() == "true"
