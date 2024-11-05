import os
from dotenv import load_dotenv

load_dotenv()  

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('POSTGRES_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('EMAIL_USER')
    MAIL_PASSWORD = os.getenv('EMAIL_PASS')