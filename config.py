import os

class Config(object):
    TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN","write it here")
    API_ID = int(os.environ.get("API_ID","write it here"))
    API_HASH = os.environ.get("API_HASH","write it here")
    ADMIN = int(os.environ.get("ADMIN","write it here"))
