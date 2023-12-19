from app import db
from flask_bcrypt import check_password_hash,generate_password_hash

class Docente(db.Model):
    uid_firebase = db.Column(db.String(255), primary_key=True)
    id_universidad_fk = db.Column(db.Integer, db.ForeignKey('universidad.id_universidad'))  # Clave foránea correcta
    nombres = db.Column(db.String(255))
    correo = db.Column(db.String(255))
    inscripciones = db.relationship('Inscripcion', backref='docente', lazy=True)
    universidad = db.relationship('Universidad', back_populates='docentes')  # Relación bidireccional
    certificados = db.relationship('Certificados', backref='docentes', lazy=True)

class Capacitacion(db.Model):
    id_capacitacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255))
    horas = db.Column(db.Integer)
    tipo = db.Column(db.String(255))
    fechas = db.Column(db.ARRAY(db.Date))
    nombre_tutor = db.Column(db.String(255))
    allow_inscripcion = db.Column(db.Boolean)
    allow_asistencia_entrada = db.Column(db.Boolean)
    allow_asistencia_salida = db.Column(db.Boolean)
    cupo = db.Column(db.Integer)
    presencial = db.Column(db.Boolean, nullable=True)
    direccion = db.Column(db.String(255), nullable=True)
    talleres = db.relationship('Taller', backref='capacitacion', cascade='all, delete-orphan', lazy=True)
    inscripciones = db.relationship('Inscripcion', backref='capacitacion',cascade='all, delete-orphan', lazy=True)

class Taller(db.Model):
    id_taller = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(255))
    id_capacitacion = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))

class Acreditacion(db.Model):
    id_acreditacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    asistencia = db.Column(db.Boolean)
    aprobado = db.Column(db.Boolean)
    observacion = db.Column(db.String)
    id_inscripcion = db.Column(db.Integer, db.ForeignKey('inscripcion.id_inscripcion'), unique=True)

class Asistencia(db.Model):
    id_asistencia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    asiste_entrada = db.Column(db.Boolean)
    asiste_salida = db.Column(db.Boolean)
    fecha = db.Column(db.Date)
    id_inscripcion = db.Column(db.Integer, db.ForeignKey('inscripcion.id_inscripcion'))

class Inscripcion(db.Model):
    id_inscripcion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_capacitacion = db.Column(db.Integer, db.ForeignKey('capacitacion.id_capacitacion'))
    id_docente = db.Column(db.String(255), db.ForeignKey('docente.uid_firebase'))
    id_taller = db.Column(db.Integer, db.ForeignKey('taller.id_taller'))
    isaccepted = db.Column(db.Boolean)
    asistencias = db.relationship('Asistencia', backref='inscripcion', lazy=True, cascade='all, delete-orphan')
    acreditacion = db.relationship('Acreditacion', backref='inscripcion', uselist=False, lazy=True, cascade='all, delete-orphan')

class TermsCompetenciaPedagogica(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    palabra = db.Column(db.String(255))
    isvalid = db.Column(db.Boolean)
    isapproved = db.Column(db.Boolean)

class TermsCompetenciaComunicativa(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    palabra = db.Column(db.String(255))
    isvalid = db.Column(db.Boolean)
    isapproved = db.Column(db.Boolean)

class TermsCompetenciaTecnologica(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    palabra = db.Column(db.String(255))
    isvalid = db.Column(db.Boolean)
    isapproved = db.Column(db.Boolean)

class TermsCompetenciaInvestigativa(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    palabra = db.Column(db.String(255))
    isvalid = db.Column(db.Boolean)
    isapproved = db.Column(db.Boolean)

class TermsCompetenciaGestion(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    palabra = db.Column(db.String(255))
    isvalid = db.Column(db.Boolean)
    isapproved = db.Column(db.Boolean)

class Universidad(db.Model):
    id_universidad = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    docentes = db.relationship('Docente', back_populates='universidad', lazy=True)  # Relación bidireccional

class Facultad(db.Model):
    id_facultad = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    id_universidad_fk = db.Column(db.Integer, db.ForeignKey('universidad.id_universidad'))
    carreras = db.relationship('Carrera', backref='facultad', lazy=True)

class Carrera(db.Model):
    id_carrera = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    id_facultad_fk = db.Column(db.Integer, db.ForeignKey('facultad.id_facultad'))

class Cursos(db.Model):
    id_curso = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text)
    urlimagen = db.Column(db.Text)
    urllogo = db.Column(db.Text)
    ofertante = db.Column(db.Text)
    descripcion = db.Column(db.Text)
    habilidades = db.Column(db.ARRAY(db.Text))
    competencia = db.Column(db.String(20))
    puntuacion = db.Column(db.Float)
    len_keywords = db.Column(db.Integer)
    resumen_descripcion = db.Column(db.Text)
    fecha_carga = db.Column(db.DateTime, default=db.func.current_timestamp())
    certificados = db.relationship('Certificados', backref='curso', lazy=True)

class Encuesta(db.Model):
    id_encuesta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_resultado_fk = db.Column(db.Integer, db.ForeignKey('resultado.id_resultado'))
    id_periodo_fk = db.Column(db.Integer, db.ForeignKey('periodo.id_periodo'))
    id_carrera_fk = db.Column(db.Integer, db.ForeignKey('carrera.id_carrera'))
    id_facultad_fk = db.Column(db.Integer, db.ForeignKey('facultad.id_facultad'))
    uid_firebase_fk = db.Column(db.String(50), db.ForeignKey('docente.uid_firebase'))
    cedula = db.Column(db.String(15))
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())

class Periodo(db.Model):
    id_periodo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False)

class Pregunta(db.Model):
    id_pregunta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pregunta = db.Column(db.Text, nullable=False)
    competencia = db.Column(db.String(50))
    momento = db.Column(db.String(50))

class Puntuacion(db.Model):
    id_puntuacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    puntaje = db.Column(db.Integer, nullable=False)
    id_pregunta_fk = db.Column(db.Integer, db.ForeignKey('pregunta.id_pregunta'))
    id_encuesta_fk = db.Column(db.Integer, db.ForeignKey('encuesta.id_encuesta'))

class Resultado(db.Model):
    id_resultado = db.Column(db.Integer, primary_key=True, autoincrement=True)
    competencia_investigativa_momento = db.Column(db.String(20))
    competencia_gestion_momento = db.Column(db.String(20))
    competencia_comunicativa_momento = db.Column(db.String(20))
    competencia_pedagogica_momento = db.Column(db.String(20))
    competencia_tecnologica_momento = db.Column(db.String(20))

class Certificados(db.Model):
    id_certificado = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Text, db.ForeignKey('docente.uid_firebase'))
    file_name = db.Column(db.Text)
    path_to_file = db.Column(db.Text)
    id_curso = db.Column(db.Integer, db.ForeignKey('cursos.id_curso'))
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp())
    isapproved = db.Column(db.Boolean, default=False)

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