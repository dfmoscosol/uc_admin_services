from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from datetime import timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/*/*": {"origins": "*"},
    },
)
app.config.from_object(Config)
app.config["JWT_SECRET_KEY"] = "innovacion2024"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Asegúrate de que `UPLOAD_FOLDER` esté configurado correctamente
app.config['UPLOAD_FOLDER'] = r'C:\Users\diego\Documents\Github\uc_admin_services\pdfs'

from app import routes, models
