# coding: utf-8
from app import db
from flask_bcrypt import check_password_hash, generate_password_hash

from datetime import datetime, date, time
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Date,
    Time,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
    text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Curso(Base):
    __tablename__ = "cursos"

    id_curso = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('cursos_id_curso_seq'::regclass)"),
    )
    titulo = Column(Text)
    url = Column(Text)
    urlimagen = Column(Text)
    urllogo = Column(Text)
    ofertante = Column(Text)
    descripcion = Column(Text)
    habilidades = Column(ARRAY(Text()))
    competencia = Column(String(20))
    puntuacion = Column(Float(53))
    len_keywords = Column(Integer)
    resumen_descripcion = Column(Text)
    similitud_title_sm = Column(Float(53))
    resumen_similitud_desc_xl = Column(Float(53))
    similitud_title_sm_percent = Column(Float(53))
    resumen_similitud_desc_xl_percent = Column(Float(53))
    similitud_title_desc = Column(Float(53))
    keywords = Column(ARRAY(Text()))
    momento = Column(Text)
    fecha_carga = Column(DateTime(True), server_default=text("now()"))


class Evento(Base):
    __tablename__ = "eventos"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('eventos_id_seq'::regclass)"),
    )
    nombre = Column(String)
    tipo = Column(Integer)
    horas = Column(Integer)
    cupos = Column(Integer)
    inscripcion = Column(Boolean)

    charla = relationship("Charla", back_populates="evento", uselist=False)
    talleres = relationship(
        "Talleres", back_populates="evento", cascade="all, delete-orphan"
    )
    microtaller = relationship("Microtalleres", back_populates="evento", uselist=False)
    horariosdisponibles = relationship("HorarioDisponible", back_populates="evento")
    fechasevento = relationship("FechasEvento", back_populates="evento")


class Periodo(Base):
    __tablename__ = "periodo"

    id_periodo = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('periodo_id_periodo_seq'::regclass)"),
    )
    nombre = Column(String(50))


class Pregunta(Base):
    __tablename__ = "pregunta"

    id_pregunta = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('pregunta_id_pregunta_seq'::regclass)"),
    )
    pregunta = Column(Text)
    competencia = Column(String(50))
    momento = Column(String(50))


class Resultado(Base):
    __tablename__ = "resultado"

    id_resultado = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('resultado_id_resultado_seq'::regclass)"),
    )
    competencia_investigativa_momento = Column(String(20))
    competencia_gestion_momento = Column(String(20))
    competencia_comunicativa_momento = Column(String(20))
    competencia_pedagogica_momento = Column(String(20))
    competencia_tecnologica_momento = Column(String(20))


class TermsCompetenciaComunicativa(Base):
    __tablename__ = "terms_competencia_comunicativa"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text(
            "nextval('terms_competencia_comunicativa_id_seq'::regclass)"
        ),
    )
    palabra = Column(String(250))
    isvalid = Column(Boolean)
    isapproved = Column(Boolean, server_default=text("true"))


class TermsCompetenciaGestion(Base):
    __tablename__ = "terms_competencia_gestion"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('terms_competencia_gestion_id_seq'::regclass)"),
    )
    palabra = Column(String(250))
    isvalid = Column(Boolean)
    isapproved = Column(Boolean, server_default=text("true"))


class TermsCompetenciaInvestigativa(Base):
    __tablename__ = "terms_competencia_investigativa"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text(
            "nextval('terms_competencia_investigativa_id_seq'::regclass)"
        ),
    )
    palabra = Column(String(250))
    isvalid = Column(Boolean)
    isapproved = Column(Boolean, server_default=text("true"))


class TermsCompetenciaPedagogica(Base):
    __tablename__ = "terms_competencia_pedagogica"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('terms_competencia_pedagogica_id_seq'::regclass)"),
    )
    palabra = Column(String(250))
    isvalid = Column(Boolean)
    isapproved = Column(Boolean, server_default=text("true"))


class TermsCompetenciaTecnologica(Base):
    __tablename__ = "terms_competencia_tecnologica"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text(
            "nextval('terms_competencia_tecnologica_id_seq'::regclass)"
        ),
    )
    palabra = Column(String(250))
    isvalid = Column(Boolean)
    isapproved = Column(Boolean, server_default=text("true"))


class Universidad(Base):
    __tablename__ = "universidad"

    id_universidad = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('universidad_id_universidad_seq'::regclass)"),
    )
    nombre = Column(String(255))


class Usuario(db.Model):
    __tablename__ = "usuario"
    id_usuario = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contrasena = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    def __init__(self, nombre, correo, contrasena):
        self.nombre = nombre
        self.correo = correo
        self.contrasena = generate_password_hash(contrasena).decode("utf-8")

    def check_password(self, password):
        print(self.contrasena)
        print(password)
        print(check_password_hash(self.contrasena, password))
        return check_password_hash(self.contrasena, password)


class Charla(Base):
    __tablename__ = "charlas"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('charlas_id_seq'::regclass)"),
    )
    evento_id = Column(ForeignKey("eventos.id"))
    hora_inicio = Column(Time)
    duracion = Column(Integer)
    modalidad = Column(String)
    ubicacion = Column(String)

    evento = relationship("Evento", back_populates="charla")
    charlas_ponentes = relationship("CharlasPonente", back_populates="charla")


class Docente(Base):
    __tablename__ = "docente"

    uid_firebase = Column(String(50), primary_key=True)
    nombres = Column(String(100))
    correo = Column(String(100))
    id_universidad_fk = Column(ForeignKey("universidad.id_universidad"))

    universidad = relationship("Universidad")


class Facultad(Base):
    __tablename__ = "facultad"

    id_facultad = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('facultad_id_facultad_seq'::regclass)"),
    )
    nombre = Column(String(100))
    id_universidad_fk = Column(ForeignKey("universidad.id_universidad"))

    universidad = relationship("Universidad")


class FechasEvento(Base):
    __tablename__ = "fechas_evento"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('fechasevento_id_seq'::regclass)"),
    )
    evento_id = Column(ForeignKey("eventos.id"))
    fecha = Column(Date)

    evento = relationship("Evento")


class HorarioDisponible(Base):
    __tablename__ = "horario_disponible"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('horariodisponible_id_seq'::regclass)"),
    )
    evento_id = Column(ForeignKey("eventos.id"))
    dia_semana = Column(String(10))
    hora_inicio = Column(Time)
    hora_fin = Column(Time)

    evento = relationship("Evento", back_populates="horariosdisponibles")


class Microtalleres(Base):
    __tablename__ = "microtalleres"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('microtalleres_id_seq'::regclass)"),
    )
    evento_id = Column(ForeignKey("eventos.id"))
    hora_inicio = Column(Time)
    duracion = Column(Integer)
    modalidad = Column(String)
    ubicacion = Column(String)

    evento = relationship("Evento", back_populates="microtaller")
    microtalleres_ponentes = relationship(
        "MicrotalleresPonente", back_populates="microtalleres"
    )


class MicrotalleresPonente(Base):
    __tablename__ = "microtalleres_ponentes"

    id = Column(Integer, primary_key=True)
    microtaller_id = Column(Integer, ForeignKey("microtalleres.id", ondelete="CASCADE"))
    nombre = Column(String)

    microtalleres = relationship(
        "Microtalleres", back_populates="microtalleres_ponentes"
    )


class Talleres(Base):
    __tablename__ = "talleres"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('talleres_id_seq'::regclass)"),
    )
    evento_id = Column(ForeignKey("eventos.id"))
    nombre = Column(String)
    modalidad = Column(Integer)
    ubicacion = Column(String)
    hora_inicio = Column(Time)
    duracion = Column(Integer)

    evento = relationship("Evento", back_populates="talleres")
    talleres_ponentes = relationship(
        "TalleresPonente",
        back_populates="talleres",
    )


class TalleresPonente(Base):
    __tablename__ = "talleres_ponentes"

    id = Column(Integer, primary_key=True)
    taller_id = Column(Integer, ForeignKey("talleres.id", ondelete="CASCADE"))
    nombre = Column(String)

    talleres = relationship("Talleres", back_populates="talleres_ponentes")


class Carrera(Base):
    __tablename__ = "carrera"

    id_carrera = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('carrera_id_carrera_seq'::regclass)"),
    )
    nombre = Column(String(200))
    id_facultad_fk = Column(ForeignKey("facultad.id_facultad"))

    facultad = relationship("Facultad")


class Certificado(Base):
    __tablename__ = "certificados"

    id_certificado = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('certificados_id_certificado_seq'::regclass)"),
    )
    user_id = Column(ForeignKey("docente.uid_firebase"))
    file_name = Column(Text)
    path_to_file = Column(Text)
    id_curso = Column(ForeignKey("cursos.id_curso"))
    fecha_creacion = Column(DateTime(True), server_default=text("now()"))
    isapproved = Column(Boolean)
    horas = Column(Integer)
    observacion = Column(String(255))

    curso = relationship("Curso")
    user = relationship("Docente")


class CharlasPonente(Base):
    __tablename__ = "charlas_ponentes"

    id = Column(Integer, primary_key=True)
    charla_id = Column(Integer, ForeignKey("charlas.id", ondelete="CASCADE"))
    titulo_charla = Column(String)
    nombre = Column(String)

    charla = relationship("Charla", back_populates="charlas_ponentes")


class Inscripcion(Base):
    __tablename__ = "inscripcion"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('inscripcion_id_seq'::regclass)"),
    )
    evento_id = Column(ForeignKey("eventos.id"))
    docente_uid_firebase = Column(ForeignKey("docente.uid_firebase"))
    taller_id = Column(ForeignKey("talleres.id"))
    aceptada = Column(Boolean)

    docente = relationship("Docente")
    evento = relationship("Evento")
    taller = relationship("Talleres")


class EncuestaObservacion(Inscripcion):
    __tablename__ = "encuesta_observacion"

    inscripcion_id = Column(ForeignKey("inscripcion.id"), primary_key=True)
    anios_ejercicio = Column(Integer)
    numero_celular = Column(String(15))
    facultad_id = Column(ForeignKey("facultad.id_facultad"))
    carrera_id = Column(ForeignKey("carrera.id_carrera"))
    asignatura = Column(String(100))
    ciclo_carrera = Column(Integer)
    numero_estudiantes = Column(Integer)
    inclusion = Column(Boolean)
    campus = Column(String(100))
    duracion_clase = Column(Integer)
    comentarios = Column(Text)

    carrera = relationship("Carrera")
    facultad = relationship("Facultad")
    horarios = relationship("HorarioDisponible", secondary="encuesta_horario")


class Acreditacion(Base):
    __tablename__ = "acreditacion"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('acreditacion_id_seq'::regclass)"),
    )
    inscripcion_id = Column(ForeignKey("inscripcion.id"), unique=True)
    asistio = Column(Boolean)
    aprobo = Column(Boolean)
    comentario = Column(Text)

    inscripcion = relationship("Inscripcion", uselist=False)


class Encuesta(Base):
    __tablename__ = "encuesta"

    id_encuesta = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('encuesta_id_encuesta_seq'::regclass)"),
    )
    id_resultado_fk = Column(ForeignKey("resultado.id_resultado"))
    id_periodo_fk = Column(ForeignKey("periodo.id_periodo"))
    id_facultad_fk = Column(ForeignKey("facultad.id_facultad"))
    id_carrera_fk = Column(ForeignKey("carrera.id_carrera"))
    uid_firebase_fk = Column(ForeignKey("docente.uid_firebase"))
    cedula = Column(String(15))
    fecha_creacion = Column(DateTime(True), server_default=text("now()"))

    carrera = relationship("Carrera")
    facultad = relationship("Facultad")
    periodo = relationship("Periodo")
    resultado = relationship("Resultado")
    docente = relationship("Docente")


class InformeObservacionAulica(Base):
    __tablename__ = "informe_observacion_aulica"

    id = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('informeobservacionaulica_id_seq'::regclass)"),
    )
    inscripcion_id = Column(ForeignKey("inscripcion.id"), unique=True)
    nombre_archivo = Column(String(255))
    ubicacion_archivo = Column(String(255))
    fecha_carga = Column(DateTime)

    inscripcion = relationship("Inscripcion", uselist=False)


t_encuesta_horario = Table(
    "encuesta_horario",
    metadata,
    Column(
        "encuesta_id",
        ForeignKey("encuesta_observacion.inscripcion_id"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "horario_id",
        ForeignKey("horario_disponible.id"),
        primary_key=True,
        nullable=False,
    ),
)


class Puntuacion(Base):
    __tablename__ = "puntuacion"

    id_puntuacion = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('puntuacion_id_puntuacion_seq'::regclass)"),
    )
    puntaje = Column(Integer)
    id_pregunta_fk = Column(ForeignKey("pregunta.id_pregunta"))
    id_encuesta_fk = Column(ForeignKey("encuesta.id_encuesta"))

    encuesta = relationship("Encuesta")
    pregunta = relationship("Pregunta")
