from app import db
from flask_bcrypt import check_password_hash,generate_password_hash

class Docente(db.Model):
    uid_firebase = db.Column(db.String(255), primary_key=True)
    universidad = db.Column(db.String(255))
    nombre = db.Column(db.String(255))
    correo = db.Column(db.String(255))
    inscripciones = db.relationship('Inscripcion', backref='docente', lazy=True)
    acreditaciones = db.relationship('Acreditacion', backref='docente', lazy=True)

class Capacitacion(db.Model):
    id_capacitacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255))
    horas = db.Column(db.Integer)
    tipo = db.Column(db.String(255))
    fechas = db.Column(db.ARRAY(db.Date))
    nombre_tutor = db.Column(db.String(255))
    allow_inscripcion = db.Column(db.Boolean)
    allow_asistencia = db.Column(db.Boolean)
    talleres = db.relationship('Taller', backref='capacitacion', cascade='all, delete-orphan', lazy=True)
    inscripciones = db.relationship('Inscripcion', backref='capacitacion',cascade='all, delete-orphan', lazy=True)

class Taller(db.Model):
    id_taller = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255))
    id_capacitacion = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))

class Inscripcion(db.Model):
    id_inscripcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_capacitacion = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))
    id_docente = db.Column(db.String(255), db.ForeignKey('docente.uid_firebase'))
    id_taller = db.Column(db.Integer, db.ForeignKey('taller.id_taller'))
    asiste_entrada = db.Column(db.Boolean)
    asiste_salida = db.Column(db.Boolean)

class Acreditacion(db.Model):
    id_acreditacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_capacitacion = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))
    id_docente = db.Column(db.String(255), db.ForeignKey('docente.uid_firebase'))

class Usuario(db.Model):
    id_usuario = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contrasena = db.Column(db.String(100), nullable=False)    
    nombre = db.Column(db.String(100), nullable=False)

    def __init__(self, nombre, correo, contrasena):
        self.nombre = nombre
        self.correo = correo
        self.contrasena = generate_password_hash(contrasena).decode('utf-8')
        

    def check_password(self, password):
        print(self.contrasena)
        print(password)
        print(check_password_hash(self.contrasena, password))
        return check_password_hash(self.contrasena, password)