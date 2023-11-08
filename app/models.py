from app import db

class Docente(db.Model):
    uid = db.Column(db.String(255), primary_key=True)
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
    taller = db.relationship('Taller', backref='capacitacion', lazy=True)
    inscripciones = db.relationship('Inscripcion', backref='capacitacion', lazy=True)


class Taller(db.Model):
    id_taller = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255))
    capacitacion_id = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))

class Inscripcion(db.Model):
    id_inscripcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_capacitacion = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))
    id_docente = db.Column(db.String(255), db.ForeignKey('docente.uid_firebase'))
    id_taller = db.Column(db.Integer, db.ForeignKey('taller.id_taller'))
    asistio = db.Column(db.Boolean)

class Acreditacion(db.Model):
    id_acreditacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_capacitacion = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))
    id_docente = db.Column(db.String(255), db.ForeignKey('docente.uid_firebase'))

