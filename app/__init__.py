from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from datetime import timedelta
from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(Config)
app.config['JWT_SECRET_KEY'] = 'innovacion2024'  
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1) 
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
# Cualquier origen (dominio) puede acceder a los recursos de la aplicación.
CORS(app,resources={r"/*/*":{"origins":"*"},})

from app import routes, models
