from app import app, db, jwt
import os
from app.models import (
    Evento,
    Usuario,
    Talleres,
    TermsCompetenciaPedagogica,
    TermsCompetenciaComunicativa,
    TermsCompetenciaTecnologica,
    TermsCompetenciaInvestigativa,
    TermsCompetenciaGestion,
    SesionesTalleres,
    FechasEvento,
    Charla,
    Docente,
    CharlasPonente,
    TalleresPonente,
    Inscripcion,
    Microtalleres,
    HorarioDisponible,
    MicrotalleresPonente,
    Certificado,
    Curso
)
from flask import jsonify, request, abort, send_file, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask import send_file
from sqlalchemy.orm import joinedload
from datetime import datetime, time
from io import BytesIO
import pandas as pd

modalidades = {
    1: "Presencial",
    2: "Virtual",
    3: "Híbrida"
}

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"estado": False, "respuesta": "", "error": "Token inválido"}), 401


@app.route("/", methods=["GET"])
def hello():
    return {
        "estado": True,
        "respuesta": "Bienvenido al servidor del sistema administrativo de la direccion de innovacion educativa",
        "error": "",
    }, 201


@app.route("/registro", methods=["POST"])
def register():
    nombre = request.json.get("nombre")
    correo = request.json.get("correo")
    contrasena = request.json.get("contrasena")

    # Verificar si el correo ya está en uso
    existing_user = Usuario.query.filter_by(correo=correo).first()

    if existing_user:
        return {
            "estado": False,
            "respuesta": "",
            "error": "El correo ya está en uso",
        }, 400

    new_user = Usuario(nombre=nombre, correo=correo, contrasena=contrasena)

    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id_usuario)

    return {
        "estado": True,
        "respuesta": {"access_token": access_token},
        "error": "",
    }, 201


@app.route("/login", methods=["POST"])
def login():
    correo = request.json.get("correo")
    contrasena = request.json.get("contrasena")

    user = Usuario.query.filter_by(correo=correo).first()

    if user and user.check_password(contrasena):
        access_token = create_access_token(identity=user.id_usuario)
        return {
            "estado": True,
            "respuesta": {"access_token": access_token},
            "error": "",
        }, 200
    else:
        return {
            "estado": False,
            "respuesta": "",
            "error": "Credenciales inválidas",
        }, 401

##JORNADAS DE INNOVACION

@app.route("/eventos/jornadas", methods=["POST"])
# @jwt_required()
def crear_jornada():
    try:
        # Obtener datos del JSON de la solicitud
        datos_jornada = request.json
        nombre = datos_jornada.get("nombre")
        horas = datos_jornada.get("horas")
        fechas = datos_jornada.get("fechas", [])
        inscripcion = datos_jornada.get("inscripcion")
        cupos = datos_jornada.get("cupos")
        talleres = datos_jornada.get("talleres", [])

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
        if not horas:
            campos_faltantes.append("horas")
        if inscripcion is None:
            campos_faltantes.append("inscripcion")
        if not fechas:
            campos_faltantes.append("fechas")
        if not cupos:
            campos_faltantes.append("cupo")
        if not talleres:
            campos_faltantes.append("talleres")

        if campos_faltantes:
            mensaje_error = f"Faltan los siguientes campos obligatorios: {', '.join(campos_faltantes)}"
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": mensaje_error,
                    }
                ),
                400,
            )

        # Crear registro en la tabla Eventos
        nueva_jornada = Evento(
            nombre=nombre,
            horas=horas,
            tipo=1,
            inscripcion=inscripcion,
            cupos=cupos,
        )

        db.session.add(nueva_jornada)
        db.session.flush()  # Esto es importante para obtener el id de la nueva jornada antes de commit.
        
        # Diccionario para mapear los identificadores de fecha con los IDs de las fechas
        fecha_id_map = {}

        # Crear registros en la tabla FechasEvento
        for fecha in fechas:
            nueva_fecha_evento = FechasEvento(evento_id=nueva_jornada.id, fecha=fecha)
            db.session.add(nueva_fecha_evento)
            db.session.flush()  # Hacer flush para obtener el id
            fecha_id_map[fecha] = nueva_fecha_evento.id

        # Si es de tipo jornada, verificar y crear registros en la tabla Taller
        for taller_data in talleres:
            taller_ponentes = taller_data.get("ponentes", [])
            
            # Crear sesiones para cada fecha con los detalles proporcionados
            sesiones_info = taller_data.get("sesiones", [])
            if not sesiones_info:
                return jsonify({"estado": False, "error": "Cada taller debe incluir al menos una sesión con detalles completos"}), 400
            
            if len(sesiones_info) != len(fechas):
                return jsonify({"estado": False, "error": "Cada taller debe tener una sesión para cada fecha del evento"}), 400
            
            nuevo_taller = Talleres(nombre=taller_data["nombre"], evento_id=nueva_jornada.id)
            db.session.add(nuevo_taller)
            db.session.flush()

            for sesion in sesiones_info:
                # Validar los campos requeridos en cada sesión
                if not all(key in sesion for key in ["fecha_id", "hora_inicio", "duracion", "modalidad", "ubicacion"]):
                    return jsonify({"estado": False, "error": "Cada sesión debe tener fecha_id, hora_inicio, duración, modalidad, y ubicación especificados"}), 400

                fecha_evento_id = fecha_id_map[sesion["fecha_id"]]
                nueva_sesion = SesionesTalleres(
                    taller_id=nuevo_taller.id,
                    fecha_evento_id=fecha_evento_id,
                    hora_inicio=sesion["hora_inicio"],
                    duracion=sesion["duracion"],
                    modalidad=sesion["modalidad"],
                    ubicacion=sesion["ubicacion"]
                )
                db.session.add(nueva_sesion)
                        
            for ponente in taller_ponentes:
                ponente_nombre = ponente.get("nombre")                
                if (
                    not ponente_nombre
                ):
                    return (
                        jsonify(
                            {
                                "estado": False,
                                "respuesta": "",
                                "error": "Todos los ponentes para los talleres deben tener el atributo 'nombre'.",
                            }
                        ),
                        400,
                    )

                nuevo_ponente = TalleresPonente(
                    nombre=ponente_nombre,
                    taller_id=nuevo_taller.id
                )
                db.session.add(nuevo_ponente)                
                
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Jornada de Innovación creada exitosamente",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al crear evento: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al crear evento: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eventos/jornadas/<int:evento_id>", methods=["PATCH"])
def actualizar_jornada_parcial(evento_id):
    try:
        datos_jornada = request.json
        jornada = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        if not jornada:
            return jsonify({"estado": False, "respuesta": "", "error": "Evento no encontrado"}), 404

        for campo in ['nombre', 'horas', 'inscripcion', 'cupos']:
            if campo in datos_jornada:
                setattr(jornada, campo, datos_jornada[campo])

        if "fechas" in datos_jornada:
            # Obtener las fechas existentes para el evento
            fechas_existentes = db.session.query(FechasEvento).filter_by(evento_id=jornada.id).all()
            fechas_existentes_set = {fecha.fecha for fecha in fechas_existentes}  # Convertir a un conjunto para búsqueda rápida

            # Convertir las fechas nuevas recibidas a un conjunto de objetos datetime.date
            nuevas_fechas_set = {datetime.strptime(fecha, "%d-%m-%Y").date() for fecha in datos_jornada['fechas']}

            # Eliminar las fechas que ya no están en las nuevas fechas recibidas
            for fecha in fechas_existentes:
                if fecha.fecha not in nuevas_fechas_set:
                    db.session.query(SesionesTalleres).filter_by(fecha_evento_id=fecha.id).delete()
                    db.session.delete(fecha)

            # Agregar las nuevas fechas que no están en las existentes
            for nueva_fecha in nuevas_fechas_set:
                if nueva_fecha not in fechas_existentes_set:
                    nueva_fecha_evento = FechasEvento(evento_id=jornada.id, fecha=nueva_fecha)
                    db.session.add(nueva_fecha_evento)
                    db.session.flush()  # Hacer flush para obtener el id de la nueva fecha

                    # Obtener todos los talleres existentes para el evento
                    talleres = db.session.query(Talleres).filter_by(evento_id=jornada.id).all()

                    # Crear una nueva sesión en blanco para cada taller para la nueva fecha
                    for taller in talleres:
                        nueva_sesion = SesionesTalleres(
                            taller_id=taller.id,
                            fecha_evento_id=nueva_fecha_evento.id,
                            hora_inicio=time(0, 0),  # Valor predeterminado: medianoche
                            duracion=1,              # Valor predeterminado: 1 hora
                            modalidad=1,             # Valor predeterminado: Presencial
                            ubicacion='Por definir'  # Valor predeterminado: 'Por definir'
                        )
                        db.session.add(nueva_sesion)

        """ if "talleres" in datos_jornada:
            
            talleres_ids = db.session.query(Talleres.id).filter_by(evento_id=jornada.id).all()
            talleres_ids = [t.id for t in talleres_ids]  # Extraemos los ids de talleres
            if talleres_ids:
                db.session.query(TalleresPonente).filter(TalleresPonente.taller_id.in_(talleres_ids)).delete(synchronize_session='fetch')

             # Ahora eliminamos los talleres
            db.session.query(Talleres).filter_by(evento_id=jornada.id).delete(synchronize_session='fetch')
            
            for taller_data in datos_jornada['talleres']:
                if not all(key in taller_data for key in ['nombre', 'modalidad', 'ubicacion', 'hora_inicio', 'duracion', 'ponentes']):
                    return jsonify({"estado": False, "respuesta": "", "error": "Cada taller en 'talleres' debe tener todos los atributos"}), 400

                nuevo_taller = Talleres(
                    nombre=taller_data['nombre'],
                    evento_id=jornada.id,
                    modalidad=taller_data['modalidad'],
                    ubicacion=taller_data['ubicacion'],
                    hora_inicio=taller_data['hora_inicio'],
                    duracion=taller_data['duracion']
                )
                db.session.add(nuevo_taller)
                db.session.flush()

                for ponente_data in taller_data['ponentes']:
                    nuevo_ponente = TalleresPonente(
                    nombre=ponente_data['nombre'],
                    taller_id=nuevo_taller.id
                )
                db.session.add(nuevo_ponente) """
                
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Jornada actualizada parcialmente con éxito", "error": ""}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "respuesta": "", "error": str(e)}), 400

@app.route("/eventos/<int:evento_id>/talleres", methods=["POST"])
# @jwt_required()
def crear_taller(evento_id):
    try:
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        if evento is None or evento.tipo != 1:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No existe la Jornada de Innovación requerida",
                    }
                ),
                400,
            )
        
        # Obtener datos del JSON de la solicitud
        datos_taller = request.json
        nombre = datos_taller.get("nombre")
        ponentes = datos_taller.get("ponentes", [])
        sesiones = datos_taller.get("sesiones", [])

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
        if not ponentes:
            campos_faltantes.append("ponentes")
        if not sesiones:
            campos_faltantes.append("sesiones")

        if campos_faltantes:
            mensaje_error = f"Faltan los siguientes campos obligatorios: {', '.join(campos_faltantes)}"
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": mensaje_error,
                    }
                ),
                400,
            )

        # Crear registro en la tabla Talleres
        nuevo_taller = Talleres(
            evento_id=evento_id,
            nombre=nombre,
        )

        db.session.add(nuevo_taller)
        db.session.flush()  # Esto es importante para obtener el id del nuevo taller antes de commit.

        # Diccionario para mapear los identificadores de fecha con los IDs de las fechas
        fecha_id_map = {fecha.id: fecha.id for fecha in evento.fechasevento}

        # Crear sesiones para el taller
        for sesion in sesiones:
            # Validar los campos requeridos en cada sesión
            if not all(key in sesion for key in ["fecha_id", "hora_inicio", "duracion", "modalidad", "ubicacion"]):
                return jsonify({"estado": False, "error": "Cada sesión debe tener fecha_id, hora_inicio, duración, modalidad, y ubicación especificados"}), 400

            fecha_evento_id = sesion["fecha_id"]
            if fecha_evento_id not in fecha_id_map:
                return jsonify({"estado": False, "error": f"El identificador de fecha {fecha_evento_id} no es válido"}), 400

            nueva_sesion = SesionesTalleres(
                taller_id=nuevo_taller.id,
                fecha_evento_id=fecha_evento_id,
                hora_inicio=sesion["hora_inicio"],
                duracion=sesion["duracion"],
                modalidad=sesion["modalidad"],
                ubicacion=sesion["ubicacion"]
            )
            db.session.add(nueva_sesion)

        # Crear registros de ponentes
        for ponente in ponentes:
            ponente_nombre = ponente.get("nombre")            
            if not ponente_nombre:
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "Todos los ponentes para los talleres deben tener el atributo 'nombre'.",
                        }
                    ),
                    400,
                )

            nuevo_ponente = TalleresPonente(
                nombre=ponente_nombre,
                taller_id=nuevo_taller.id,
            )
            db.session.add(nuevo_ponente)

        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Taller creado exitosamente",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al crear taller: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al crear taller: {str(e)}",
                }
            ),
            500,
        )
     
@app.route("/eventos/<int:evento_id>/talleres/<int:taller_id>", methods=["PATCH"])
# @jwt_required()
def actualizar_taller_parcial(evento_id, taller_id):
    try:
        # Verificar si el evento existe y es del tipo correcto
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        if evento is None or evento.tipo != 1:
            return jsonify({
                "estado": False,
                "error": "No existe la Jornada de Innovación requerida"
            }), 400

        # Obtener el taller existente
        taller = db.session.query(Talleres).filter_by(id=taller_id).one_or_none()
        if taller is None:
            return jsonify({
                "estado": False,
                "error": "El taller especificado no existe"
            }), 404

        # Obtener datos del JSON de la solicitud para actualización
        datos_taller = request.json

        # Actualizar campos si están presentes en el JSON
        if 'nombre' in datos_taller:
            taller.nombre = datos_taller['nombre']

        #Actualizar sesiones
        if 'sesiones' in datos_taller and datos_taller['sesiones']:
            for sesion in datos_taller['sesiones']:
                sesionExistente = db.session.query(SesionesTalleres).filter_by(id=sesion['id']).one_or_none()
                if sesionExistente is None:
                    return jsonify({
                        "estado": False,
                        "error": "La sesion especificada no existe"
                    }), 404
                if 'duracion' in sesion:
                    sesionExistente.duracion = sesion['duracion']
                if 'hora_inicio' in sesion:
                    sesionExistente.hora_inicio = sesion['hora_inicio']
                if 'modalidad' in sesion:
                    sesionExistente.modalidad = sesion['modalidad']
                if 'ubicacion' in sesion:
                    sesionExistente.ubicacion = sesion['ubicacion']
                    
        # Actualizar ponentes si están presentes
        if 'ponentes' in datos_taller and datos_taller['ponentes']:
            # Eliminar y reemplazar todos los ponentes actuales
            db.session.query(TalleresPonente).filter_by(taller_id=taller_id).delete(synchronize_session='fetch')
            for ponente in datos_taller['ponentes']:
                ponente_nombre = ponente.get("nombre")
                if not ponente_nombre:
                    return jsonify({
                        "estado": False,
                        "error": "Todos los ponentes deben tener un nombre."
                    }), 400
                nuevo_ponente = TalleresPonente(
                    nombre=ponente_nombre,
                    taller_id=taller_id
                )
                db.session.add(nuevo_ponente)

        db.session.commit()

        return jsonify({
            "estado": True,
            "respuesta": "Taller actualizado exitosamente"
        }), 200

    except Exception as e:
        app.logger.error(f"Error al actualizar taller: {str(e)}")
        return jsonify({
            "estado": False,
            "error": f"Error al actualizar taller: {str(e)}"
        }), 500

@app.route("/eventos/jornadas/talleres/<int:taller_id>", methods=["DELETE"])
# @jwt_required()
def eliminar_taller(taller_id):
    try:
        # Obtener el taller a eliminar
        taller = db.session.query(Talleres).filter_by(id=taller_id).one_or_none()

        # Verificar si el taller existe
        if not taller:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se encontró el taller especificado",
                    }
                ),
                404,
            )
        #Eliminar los ponentes del taller
        db.session.query(TalleresPonente).filter_by(taller_id=taller.id).delete()
        # Eliminar el taller de la base de datos
        db.session.delete(taller)
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Taller eliminado exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al eliminar taller: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al eliminar taller {str(e)}",
                }
            ),
            500,
        )

##CHARLAS

@app.route("/eventos/charlas", methods=["POST"])
# @jwt_required()
def crear_charla():
    try:
        # Obtener datos del JSON de la solicitud
        datos_charla = request.json
        nombre = datos_charla.get("nombre")
        horas = datos_charla.get("horas")
        fechas = datos_charla.get("fechas", [])
        inscripcion = datos_charla.get("inscripcion")
        cupos = datos_charla.get("cupos")
        ponentes = datos_charla.get("ponentes", [])
        modalidad = datos_charla.get("modalidad")
        ubicacion = datos_charla.get("ubicacion")
        hora_inicio = datos_charla.get("hora_inicio")
        duracion = datos_charla.get("duracion")

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
        if not horas:
            campos_faltantes.append("horas")
        if inscripcion is None:
            campos_faltantes.append("inscripcion")
        if not fechas:
            campos_faltantes.append("fechas")
        if not cupos:
            campos_faltantes.append("cupo")
        if not ponentes:
            campos_faltantes.append("ponentes")
        if not modalidad:
            campos_faltantes.append("modalidad")
        if not ubicacion:
            campos_faltantes.append("ubicacion")
        if not hora_inicio:
            campos_faltantes.append("hora_inicio")
        if not duracion:
            campos_faltantes.append("duracion")

        if campos_faltantes:
            mensaje_error = f"Faltan los siguientes campos obligatorios: {', '.join(campos_faltantes)}"
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": mensaje_error,
                    }
                ),
                400,
            )

        # Crear registro en la tabla Eventos
        nuevo_evento = Evento(
            nombre=nombre,
            horas=horas,
            tipo=2,
            inscripcion=inscripcion,
            cupos=cupos,
        )

        db.session.add(nuevo_evento)
        db.session.flush()  # Esto es importante para obtener el id de la nueva jornada antes de commit.

        nueva_charla = Charla(
            evento_id=nuevo_evento.id,
            hora_inicio=hora_inicio,
            duracion=duracion,
            modalidad=modalidad,
            ubicacion=ubicacion
        )
        
        db.session.add(nueva_charla)
        db.session.flush()

        # Crear registros en la tabla FechasEvento
        for fecha in fechas:
            nueva_fecha_evento = FechasEvento(
                evento_id=nuevo_evento.id,
                fecha=fecha
            )
            db.session.add(nueva_fecha_evento)

        for ponente in ponentes:
            ponente_nombre = ponente.get("nombre")
            titulo_charla = ponente.get("titulo_charla")
            
            if (
                not ponente_nombre
                or not titulo_charla
            ):
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "Todos los ponentes para las charlas deben tener el atributo 'nombre' y 'titulo_charla' ",
                        }
                    ),
                    400,
                )

            nuevo_ponente = CharlasPonente(
                nombre=ponente_nombre,
                titulo_charla=titulo_charla,
                charla_id=nueva_charla.id,
            )
            db.session.add(nuevo_ponente)
            
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Charla creada exitosamente",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al crear evento: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al crear evento: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eventos/charlas/<int:evento_id>", methods=["PATCH"])
# @jwt_required()
def actualizar_charla_parcial(evento_id):
    try:
        datos_charla = request.json
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        if not evento:
            return jsonify({"estado": False, "respuesta": "", "error": "Evento no encontrado"}), 404

        for campo in ['nombre', 'horas', 'inscripcion', 'cupos']:
            if campo in datos_charla:
                setattr(evento, campo, datos_charla[campo])

        charla = db.session.query(Charla).filter_by(evento_id=evento_id).one_or_none()
        if charla:
            for key in ['modalidad', 'ubicacion', 'hora_inicio', 'duracion']:
                if key in datos_charla:
                    setattr(charla, key, datos_charla[key])

        if "fechas" in datos_charla:
            db.session.query(FechasEvento).filter_by(evento_id=evento_id).delete()
            for fecha in datos_charla['fechas']:
                db.session.add(FechasEvento(evento_id=evento_id, fecha=fecha))

        # Update or add ponentes without removing unmentioned ponentes
        if "ponentes" in datos_charla:
            db.session.query(CharlasPonente).filter_by(charla_id=charla.id).delete(synchronize_session='fetch')
            for ponente_data in datos_charla['ponentes']:
                nombre = ponente_data['nombre']
                titulo_charla = ponente_data['titulo_charla']
                new_charlas_ponente = CharlasPonente(
                    charla_id=charla.id,
                    nombre=nombre,
                    titulo_charla=titulo_charla
                )
                db.session.add(new_charlas_ponente)
                    
        db.session.commit()
        return jsonify({"estado": True, "respuesta": "Charla actualizada exitosamente", "error": ""}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "respuesta": "", "error": str(e)}), 400

##MICROTALLERES

@app.route("/eventos/microtalleres", methods=["POST"])
# @jwt_required()
def crear_microtaller():
    try:
        # Obtener datos del JSON de la solicitud
        datos_microtaller = request.json
        nombre = datos_microtaller.get("nombre")
        horas = datos_microtaller.get("horas")
        fechas = datos_microtaller.get("fechas", [])
        inscripcion = datos_microtaller.get("inscripcion")
        cupos = datos_microtaller.get("cupos")
        ponentes = datos_microtaller.get("ponentes", [])
        modalidad = datos_microtaller.get("modalidad")
        ubicacion = datos_microtaller.get("ubicacion")
        hora_inicio = datos_microtaller.get("hora_inicio")
        duracion = datos_microtaller.get("duracion")

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
        if not horas:
            campos_faltantes.append("horas")
        if inscripcion is None:
            campos_faltantes.append("inscripcion")
        if not fechas:
            campos_faltantes.append("fechas")
        if not cupos:
            campos_faltantes.append("cupo")
        if not ponentes:
            campos_faltantes.append("ponentes")
        if not modalidad:
            campos_faltantes.append("modalidad")
        if not ubicacion:
            campos_faltantes.append("ubicacion")
        if not hora_inicio:
            campos_faltantes.append("hora_inicio")
        if not duracion:
            campos_faltantes.append("duracion")

        if campos_faltantes:
            mensaje_error = f"Faltan los siguientes campos obligatorios: {', '.join(campos_faltantes)}"
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": mensaje_error,
                    }
                ),
                400,
            )

        # Crear registro en la tabla Eventos
        nuevo_evento = Evento(
            nombre=nombre,
            horas=horas,
            tipo=3,
            inscripcion=inscripcion,
            cupos=cupos,
        )

        db.session.add(nuevo_evento)
        db.session.flush()  

        nuevo_microtaller = Microtalleres(
            evento_id=nuevo_evento.id,
            hora_inicio=hora_inicio,
            duracion=duracion,
            modalidad=modalidad,
            ubicacion=ubicacion
        )
        
        db.session.add(nuevo_microtaller)
        db.session.flush()

        # Crear registros en la tabla FechasEvento
        for fecha in fechas:
            nueva_fecha_evento = FechasEvento(
                evento_id=nuevo_evento.id,
                fecha=fecha
            )
            db.session.add(nueva_fecha_evento)

        # Si es de tipo jornada, verificar y crear registros en la tabla Taller
        for ponente in ponentes:
            ponente_nombre = ponente.get("nombre")                
            if (
                not ponente_nombre
            ):
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "Todos los ponentes para los microtalleres deben tener el atributo 'nombre'.",
                        }
                    ),
                    400,
                )

            nuevo_ponente = MicrotalleresPonente(
                microtaller_id=nuevo_microtaller.id,
                nombre=ponente_nombre,
            )
            db.session.add(nuevo_ponente)
            
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Microtaller creado exitosamente",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al crear evento: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al crear evento: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eventos/microtalleres/<int:evento_id>", methods=["PATCH"])
# @jwt_required()
def actualizar_microtaller_parcial(evento_id):
    try:
        datos_microtaller = request.json
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        if not evento:
            return jsonify({"estado": False, "respuesta": "", "error": "Evento no encontrado"}), 404

        for campo in ['nombre', 'horas', 'inscripcion', 'cupos']:
            if campo in datos_microtaller:
                setattr(evento, campo, datos_microtaller[campo])

        microtaller = db.session.query(Microtalleres).filter_by(evento_id=evento_id).one_or_none()
        if microtaller:
            for key in ['modalidad', 'ubicacion', 'hora_inicio', 'duracion']:
                if key in datos_microtaller:
                    setattr(microtaller, key, datos_microtaller[key])

        if "fechas" in datos_microtaller:
            db.session.query(FechasEvento).filter_by(evento_id=evento_id).delete()
            for fecha in datos_microtaller['fechas']:
                db.session.add(FechasEvento(evento_id=evento_id, fecha=fecha))

        # Update or add ponentes without removing unmentioned ponentes
        if "ponentes" in datos_microtaller:
            db.session.query(MicrotalleresPonente).filter_by(microtaller_id=microtaller.id).delete(synchronize_session='fetch')
            for ponente_data in datos_microtaller['ponentes']:
                nombre = ponente_data['nombre']
                new_microtalleres_ponente = MicrotalleresPonente(
                    microtaller_id=microtaller.id,
                    nombre=nombre
                )
                db.session.add(new_microtalleres_ponente)
                    
        db.session.commit()
        return jsonify({"estado": True, "respuesta": "Charla actualizada exitosamente", "error": ""}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "respuesta": "", "error": str(e)}), 400

##OBSERVACIONES

@app.route("/eventos/observaciones", methods=["POST"])
# @jwt_required()
def crear_observacion():
    try:
        # Obtener datos del JSON de la solicitud
        datos_observacion = request.json
        nombre = datos_observacion.get("nombre")
        horas = datos_observacion.get("horas")
        fechas = datos_observacion.get("fechas", [])
        horarios = datos_observacion.get("horarios", [])
        inscripcion = datos_observacion.get("inscripcion")
        cupos = datos_observacion.get("cupos")

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
        if not horas:
            campos_faltantes.append("horas")
        if inscripcion is None:
            campos_faltantes.append("inscripcion")
        if not fechas:
            campos_faltantes.append("fechas")
        if not cupos:
            campos_faltantes.append("cupo")
        if not horarios:
            campos_faltantes.append("horarios")

        if campos_faltantes:
            mensaje_error = f"Faltan los siguientes campos obligatorios: {', '.join(campos_faltantes)}"
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": mensaje_error,
                    }
                ),
                400,
            )

        # Crear registro en la tabla Eventos
        nuevo_evento = Evento(
            nombre=nombre,
            horas=horas,
            tipo=4,
            inscripcion=inscripcion,
            cupos=cupos,
        )

        db.session.add(nuevo_evento)
        db.session.flush()  

        # Crear registros en la tabla FechasEvento
        for fecha in fechas:
            nueva_fecha_evento = FechasEvento(
                evento_id=nuevo_evento.id,
                fecha=fecha
            )
            db.session.add(nueva_fecha_evento)

        # Si es de tipo jornada, verificar y crear registros en la tabla Taller
        for horario in horarios:
            dia_semana = horario.get("dia_semana")
            hora_inicio = horario.get("hora_inicio")                
            hora_fin = horario.get("hora_fin")                
            if (
                not dia_semana
                or not hora_inicio
                or not hora_fin
            ):
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "Todas las fechas disponibles deben tener dia, hora_inicio y hora_fin.",
                        }
                    ),
                    400,
                )

            nuevo_horario = HorarioDisponible(
                evento_id=nuevo_evento.id,
                dia_semana=dia_semana,
                hora_fin=hora_fin,
                hora_inicio=hora_inicio                
            )
            db.session.add(nuevo_horario)
            
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Observación Áulica creada exitosamente",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al crear evento: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al crear evento: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eventos/observaciones/<int:evento_id>", methods=["PATCH"])
# @jwt_required()
def actualizar_observacion_parcial(evento_id):
    try:
        datos_observacion = request.json
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        if not evento:
            return jsonify({"estado": False, "respuesta": "", "error": "Evento no encontrado"}), 404

        for campo in ['nombre', 'horas', 'inscripcion', 'cupos']:
            if campo in datos_observacion:
                setattr(evento, campo, datos_observacion[campo])

        if "fechas" in datos_observacion:
            db.session.query(FechasEvento).filter_by(evento_id=evento_id).delete()
            for fecha in datos_observacion['fechas']:
                db.session.add(FechasEvento(evento_id=evento_id, fecha=fecha))

        # Update or add ponentes without removing unmentioned ponentes
        if "horarios" in datos_observacion:
            db.session.query(HorarioDisponible).filter_by(evento_id=evento.id).delete(synchronize_session='fetch')
            for horario in datos_observacion['horarios']:
                dia_semana = horario['dia_semana']
                hora_inicio = horario['hora_inicio']
                hora_fin = horario['hora_fin']
                new_horario_disponible = HorarioDisponible(
                    evento_id=evento.id,
                    dia_semana=dia_semana,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin
                )
                db.session.add(new_horario_disponible)
                    
        db.session.commit()
        return jsonify({"estado": True, "respuesta": "Charla actualizada exitosamente", "error": ""}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "respuesta": "", "error": str(e)}), 400

##GENERAL

@app.route("/eventos/todos", methods=["GET"])
# @jwt_required()
def obtener_eventos():
    try:
        eventos = db.session.query(Evento).all()
        resultados = []

        for evento in eventos:
            evento_info = {
                "id": evento.id,
                "nombre": evento.nombre,
                "horas": evento.horas,
                "inscripcion": evento.inscripcion,
                "cupos": evento.cupos,
                "tipo": evento.tipo,
                "fechas": [ {"fecha": fecha.fecha.strftime('%d-%m-%Y'), "id": fecha.id} for fecha in evento.fechasevento]
            }

            if evento.tipo == 1:  # Jornada
                evento_info["talleres"] = [
                    {
                        "id": taller.id,
                        "nombre": taller.nombre,
                        "sesiones": [
                            {
                                "fecha": sesion.fecha_evento.fecha.strftime('%Y-%m-%d'),
                                "id": sesion.id,
                                "fecha_id": sesion.fecha_evento.id,
                                "hora_inicio": sesion.hora_inicio.strftime('%H:%M'),
                                "duracion": sesion.duracion,
                                "modalidad": modalidades.get(sesion.modalidad, 'Desconocida'),
                                "ubicacion": sesion.ubicacion
                            }
                            for sesion in taller.sesiones  # Asegúrate de que taller.sesiones esté correctamente relacionado y cargado
                        ],
                        "ponentes": [ponente.nombre for ponente in taller.talleres_ponentes],
                        "docentes_inscritos": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres,
                                "correo": inscripcion.docente.correo
                            }
                            for inscripcion in taller.inscripciones
                            if inscripcion.aceptada == True
                        ],
                        "docentes_pendientes": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres,
                                "correo": inscripcion.docente.correo
                            }
                            for inscripcion in taller.inscripciones
                            if inscripcion.aceptada == False
                        ]
                    }
                    for taller in evento.talleres
                ]

                
            elif evento.tipo == 2:  # Charla
                charla = evento.charla
                evento_info.update({
                    "hora_inicio": charla.hora_inicio.strftime('%H:%M'),
                    "duracion": charla.duracion,
                    "modalidad": modalidades.get(charla.modalidad, 'Desconocida'),
                    "ubicacion": charla.ubicacion,
                    "ponentes": [
                        {
                            "nombre": charla_ponente.nombre,
                            "titulo_charla": charla_ponente.titulo_charla
                        } for charla_ponente in charla.charlas_ponentes
                    ],
                    "docentes_inscritos": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo
                        }
                        for inscripcion in evento.inscripciones
                        if inscripcion.aceptada == True
                    ],
                    "docentes_pendientes": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo
                        }
                        for inscripcion in evento.inscripciones
                        if inscripcion.aceptada == False
                    ]
                })

            elif evento.tipo == 3:  # Microtaller
                microtaller = evento.microtaller
                evento_info.update({
                    "hora_inicio": microtaller.hora_inicio.strftime('%H:%M'),
                    "duracion": microtaller.duracion,
                    "modalidad": modalidades.get(microtaller.modalidad, 'Desconocida'),
                    "ubicacion": microtaller.ubicacion,
                    "ponentes": [ponente.nombre for ponente in microtaller.microtalleres_ponentes],
                    "docentes_inscritos": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo
                        }
                        for inscripcion in evento.inscripciones
                        if inscripcion.aceptada == True
                    ],
                    "docentes_pendientes": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo
                        }
                        for inscripcion in evento.inscripciones
                        if inscripcion.aceptada == False
                    ]
                })

            elif evento.tipo == 4:  # Observación Áulica
                evento_info.update({
                    "horarios" : [
                        {
                            "dia_semana": horario.dia_semana,
                            "hora_inicio": horario.hora_inicio.strftime('%H:%M'),
                            "hora_fin": horario.hora_fin.strftime('%H:%M')
                        } for horario in evento.horariosdisponibles
                    ],
                    "docentes_inscritos": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo
                        }
                        for inscripcion in evento.inscripciones
                        if inscripcion.aceptada == True
                    ],
                    "docentes_pendientes": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo
                        }
                        for inscripcion in evento.inscripciones
                        if inscripcion.aceptada == False
                    ]
                })
                

            resultados.append(evento_info)

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": {"eventos": resultados},
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al obtener los eventos: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener los eventos: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eventos/<int:evento_id>", methods=["GET"])
# @jwt_required()
def obtener_evento_por_id(evento_id):
    try:
        # Query the database for the Event with the given ID
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()

        # If no event is found with the given ID, return a 404 Not Found response
        if evento is None:
            return jsonify({"estado": False, "respuesta": "", "error": "Evento no encontrado"}), 404

        # Prepare a dictionary to store event data
        evento_info = {
            "id": evento.id,
            "nombre": evento.nombre,
            "horas": evento.horas,
            "inscripcion": evento.inscripcion,
            "cupos": evento.cupos,
            "tipo": evento.tipo,
            "fechas": [ {"fecha": fecha.fecha.strftime('%d-%m-%Y'), "id": fecha.id} for fecha in evento.fechasevento]
        }

        # Depending on the type of event, additional details are included
        if evento.tipo == 1:  # Jornada
            evento_info["talleres"] = [
                {
                    "id": taller.id,
                    "nombre": taller.nombre,
                    "sesiones": [
                        {
                            "fecha": sesion.fecha_evento.fecha.strftime('%Y-%m-%d'),
                            "id": sesion.id,
                            "fecha_id": sesion.fecha_evento.id,
                            "hora_inicio": sesion.hora_inicio.strftime('%H:%M'),
                            "duracion": sesion.duracion,
                            "modalidad": modalidades.get(sesion.modalidad, 'Desconocida'),
                            "ubicacion": sesion.ubicacion
                        }
                        for sesion in taller.sesiones  # Asegúrate de que taller.sesiones esté correctamente relacionado y cargado
                    ],
                    "ponentes": [{"nombre": ponente.nombre} for ponente in taller.talleres_ponentes],
                    "docentes_inscritos": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo,
                            "id_inscripcion": inscripcion.id
                        }
                        for inscripcion in taller.inscripciones
                        if inscripcion.aceptada == True
                    ],
                    "docentes_pendientes": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres,
                            "correo": inscripcion.docente.correo,
                            "id_inscripcion": inscripcion.id
                        }
                        for inscripcion in taller.inscripciones
                        if inscripcion.aceptada == False
                    ]
                }
                for taller in evento.talleres
            ]

        elif evento.tipo == 2:  # Charla
            charla = evento.charla
            evento_info.update({
                "hora_inicio": charla.hora_inicio.strftime('%H:%M'),
                "duracion": charla.duracion,
                "modalidad": modalidades.get(charla.modalidad, 'Desconocida'),
                "ubicacion": charla.ubicacion,
                "ponentes": [
                    {
                        "nombre": charla_ponente.nombre,
                        "titulo_charla": charla_ponente.titulo_charla
                    } for charla_ponente in charla.charlas_ponentes
                ],
                "docentes_inscritos": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres,
                        "correo": inscripcion.docente.correo,
                        "id_inscripcion":inscripcion.id
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == True
                ],
                "docentes_pendientes": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres,
                        "correo": inscripcion.docente.correo,
                            "id_inscripcion":inscripcion.id
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == False
                ]
            })
        elif evento.tipo == 3:  # Microtaller
            microtaller = evento.microtaller
            evento_info.update({
                "hora_inicio": microtaller.hora_inicio.strftime('%H:%M'),
                "duracion": microtaller.duracion,
                "modalidad": modalidades.get(microtaller.modalidad, 'Desconocida'),
                "ubicacion": microtaller.ubicacion,
                "ponentes": [ponente.nombre for ponente in microtaller.microtalleres_ponentes],
                "docentes_inscritos": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres,
                        "correo": inscripcion.docente.correo,
                        "id_inscripcion":inscripcion.id

                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == True
                ],
                "docentes_pendientes": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres,
                        "correo": inscripcion.docente.correo,
                            "id_inscripcion":inscripcion.id
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == False
                ]
            })
        elif evento.tipo == 4:  # Observación Áulica
            evento_info.update({
                "horarios" : [
                    {
                        "dia_semana": horario.dia_semana,
                        "hora_inicio": horario.hora_inicio.strftime('%H:%M'),
                        "hora_fin": horario.hora_fin.strftime('%H:%M')
                    } for horario in evento.horariosdisponibles
                ],
                "docentes_inscritos": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres,
                        "correo": inscripcion.docente.correo,
                        "id_inscripcion":inscripcion.id
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == True
                ],
                "docentes_pendientes": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres,
                        "correo": inscripcion.docente.correo,
                            "id_inscripcion":inscripcion.id
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == False
                ]
            })

        # Return the event data with a 200 OK response
        return jsonify({"estado": True, "respuesta": {"evento":evento_info}, "error": ""}), 200

    except Exception as e:
        app.logger.error(f"Error al obtener el evento: {str(e)}")
        return jsonify({"estado": False, "respuesta": "", "error": f"Error interno del servidor: {str(e)}"}), 500

@app.route("/eventos/<int:evento_id>", methods=["DELETE"])
# @jwt_required()
def eliminar_evento(evento_id):
    try:
        # Obtener el evento existente
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        
        if not evento:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Evento no encontrado",
                    }
                ),
                404,
            )
        fechas_evento_ids = db.session.query(FechasEvento.id).filter_by(evento_id=evento.id).all()
        fechas_evento_ids = [id for (id,) in fechas_evento_ids]
        db.session.query(SesionesTalleres).filter(SesionesTalleres.fecha_evento_id.in_(fechas_evento_ids)).delete()
        db.session.query(FechasEvento).filter_by(evento_id=evento.id).delete()
        db.session.query(Inscripcion).filter_by(evento_id=evento.id).delete()

        if evento.tipo == 1:
            # Encontrar todos los talleres asociados con este evento
            talleres = db.session.query(Talleres).filter_by(evento_id=evento.id).all()
            # Recorrer todos los talleres encontrados y eliminar los TalleresPonente relacionados
            for taller in talleres:
                # Eliminar TalleresPonente relacionados con este taller
                db.session.query(TalleresPonente).filter_by(taller_id=taller.id).delete()
                db.session.query(SesionesTalleres).filter_by(taller_id=taller.id).delete()
            # Eliminar todos los talleres encontrados
            db.session.query(Talleres).filter_by(evento_id=evento.id).delete()
            
        elif evento.tipo == 2:
            # Encontrar todas las charlas asociadas con este evento
            charla = db.session.query(Charla).filter_by(evento_id=evento.id).one_or_none()
            # Recorrer todas las charlas encontrados y eliminar las CharlasPonente relacionados
            db.session.query(CharlasPonente).filter_by(charla_id=charla.id).delete()
            # Eliminar todas las charlas encontrados
            db.session.query(Charla).filter_by(evento_id=evento.id).delete()
        
        elif evento.tipo == 3:
            # Encontrar todos los microtalleres asociadas con este evento
            microtaller = db.session.query(Microtalleres).filter_by(evento_id=evento.id).one_or_none()
            # Recorrer todos los microtalleres encontrados y eliminar los MicrotalleresPonente relacionados
            db.session.query(MicrotalleresPonente).filter_by(microtaller_id=microtaller.id).delete()
            # Eliminar todos los microtalleres encontrados
            db.session.query(Microtalleres).filter_by(evento_id=evento.id).delete()
            
        elif evento.tipo == 4:
            db.session.query(HorarioDisponible).filter_by(evento_id=evento.id).delete()

        
        # Eliminar el evento de la base de datos
        db.session.delete(evento)
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Evento eliminado exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al eliminar evento: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al eliminar evento: {str(e)}",
                }
            ),
            500,
        )

##PENTAGONO

@app.route("/terminos/<competencia>", methods=["GET"])
# @jwt_required()
def obtener_terminos(competencia):
    try:
        # Determinar la tabla correspondiente según el nombre de la competencia
        tabla_terminos = None
        if competencia.lower() == "pedagogica":
            tabla_terminos = TermsCompetenciaPedagogica
        elif competencia.lower() == "comunicativa":
            tabla_terminos = TermsCompetenciaComunicativa
        elif competencia.lower() == "tecnologica":
            tabla_terminos = TermsCompetenciaTecnologica
        elif competencia.lower() == "investigativa":
            tabla_terminos = TermsCompetenciaInvestigativa
        elif competencia.lower() == "gestion":
            tabla_terminos = TermsCompetenciaGestion
        else:
            return (
                jsonify(
                    {"estado": False, "respuesta": "", "error": "Competencia no válida"}
                ),
                400,
            )

        # Obtener todos los registros de la tabla correspondiente
        terminos = tabla_terminos.query.all()

        # Construir la respuesta
        datos_terminos = [
            {
                "id": termino.id,
                "palabra": termino.palabra,
                "isvalid": termino.isvalid,
                "isapproved": termino.isapproved,
            }
            for termino in terminos
        ]

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": {"terminos": datos_terminos},
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al obtener términos: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener términos: {str(e)}",
                }
            ),
            500,
        )

@app.route("/actualizar_termino/<competencia>/<int:termino_id>", methods=["PUT"])
# @jwt_required()
def actualizar_isapproved(competencia, termino_id):
    try:
        # Determinar la tabla correspondiente según el nombre de la competencia
        tabla_terminos = None
        if competencia.lower() == "pedagogica":
            tabla_terminos = TermsCompetenciaPedagogica
        elif competencia.lower() == "comunicativa":
            tabla_terminos = TermsCompetenciaComunicativa
        elif competencia.lower() == "tecnologica":
            tabla_terminos = TermsCompetenciaTecnologica
        elif competencia.lower() == "investigativa":
            tabla_terminos = TermsCompetenciaInvestigativa
        elif competencia.lower() == "gestion":
            tabla_terminos = TermsCompetenciaGestion
        else:
            return (
                jsonify(
                    {"estado": False, "respuesta": "", "error": "Competencia no válida"}
                ),
                400,
            )

        # Obtener el término específico por ID
        termino = tabla_terminos.query.get(termino_id)

        # Verificar si el término existe
        if not termino:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se encontró el término especificado",
                    }
                ),
                404,
            )

        # Actualizar la columna isapproved
        nuevo_estado = request.json.get("isapproved")
        nueva_palabra = request.json.get("palabra")

        termino.isapproved = nuevo_estado
        termino.palabra = nueva_palabra
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Término actualizado exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al actualizar isapproved: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al actualizar el estado del termino: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eliminar_termino/<competencia>/<int:termino_id>", methods=["DELETE"])
# @jwt_required()
def eliminar_termino(competencia, termino_id):
    try:
        # Determinar la tabla correspondiente según el nombre de la competencia
        tabla_terminos = None
        if competencia.lower() == "pedagogica":
            tabla_terminos = TermsCompetenciaPedagogica
        elif competencia.lower() == "comunicativa":
            tabla_terminos = TermsCompetenciaComunicativa
        elif competencia.lower() == "tecnologica":
            tabla_terminos = TermsCompetenciaTecnologica
        elif competencia.lower() == "investigativa":
            tabla_terminos = TermsCompetenciaInvestigativa
        elif competencia.lower() == "gestion":
            tabla_terminos = TermsCompetenciaGestion
        else:
            return (
                jsonify(
                    {"estado": False, "respuesta": "", "error": "Competencia no válida"}
                ),
                400,
            )

        # Obtener el término específico por ID
        termino = tabla_terminos.query.get(termino_id)

        # Verificar si el término existe
        if not termino:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se encontró el término especificado",
                    }
                ),
                404,
            )

        # Eliminar el término de la base de datos
        db.session.delete(termino)
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Término eliminado exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al eliminar término: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al eliminar término: {str(e)}",
                }
            ),
            500,
        )

@app.route("/certificados", methods=["GET"])
# @jwt_required()
def obtener_certificados():
    try:
        # Realizar la consulta uniendo las tablas Certificado y Curso
        certificados = (
            db.session.query(Certificado, Curso)
            .join(Curso, Certificado.id_curso == Curso.id_curso)
            .all()
        )

        # Construir la respuesta
        datos_certificados = [
            {
                "id_certificado": certificado.id_certificado,
                "user_id": certificado.user_id,
                "file_name": certificado.file_name,
                "path_to_file": certificado.path_to_file,
                "fecha_creacion": certificado.fecha_creacion,
                "isapproved": certificado.isapproved,
                "nombre_curso": curso.titulo,
                "url_curso": curso.url,
                "url_imagen": curso.urlimagen,
                "url_logo": curso.urllogo,
            }
            for certificado, curso in certificados
        ]

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": {"certificados": datos_certificados},
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al obtener certificados: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener certificados: {str(e)}",
                }
            ),
            500,
        )

@app.route("/descargar_certificado/<int:id_certificado>", methods=["GET"])
# @jwt_required()
def descargar_certificado(id_certificado):
    try:
        certificado = Certificados.query.get(id_certificado)

        if certificado:
            path_to_file = certificado.path_to_file
            print(path_to_file)
            if os.path.exists(path_to_file):
                return send_file(path_to_file, as_attachment=True)
            else:
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "Archivo no encontrado",
                        }
                    ),
                    404,
                )
        else:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Certificado no encontrado",
                    }
                ),
                404,
            )

    except Exception as e:
        app.logger.error(f"Error al descargar el certificado: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al descargar el certificado: {str(e)}",
                }
            ),
            500,
        )

@app.route("/actualizar_certificado/<int:id_certificado>", methods=["PUT"])
# @jwt_required()
def actualizar_certificado(id_certificado):
    try:
        # Obtener el nuevo valor para isapproved desde el cuerpo de la solicitud
        datos = request.get_json()
        nuevo_isapproved = datos.get("isapproved")

        # Validar que se proporcionó el nuevo valor de isapproved
        if nuevo_isapproved is None:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El valor 'isapproved' no está presente",
                    }
                ),
                400,
            )

        # Buscar el certificado por su ID
        certificado = Certificados.query.get(id_certificado)
        if not certificado:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Certificado no encontrado",
                    }
                ),
                404,
            )

        # Actualizar el campo isapproved
        certificado.isapproved = nuevo_isapproved
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Certificado actualizado con éxito",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al actualizar el certificado: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al actualizar el certificado: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eventos/docentes/<int:id_evento>", methods=["GET"])
def docentes_disponibles(id_evento):
    try:
        # Obtener todos los docentes
        todos_los_docentes = db.session.query(Docente).all()

        # Obtener los ID de los docentes que tienen inscripción en la capacitación
        docentes_inscritos_ids = db.session.query(Inscripcion.evento_id).filter(Inscripcion.evento_id == id_evento).all()
        docentes_inscritos_ids = {id[0] for id in docentes_inscritos_ids}  # Extraer los IDs de la tupla resultante

        # Filtrar los docentes que no están inscritos en la capacitación
        docentes_disponibles = [
            docente for docente in todos_los_docentes if docente.uid_firebase not in docentes_inscritos_ids
        ]

        # Convertir a formato JSON
        docentes_json = [
            {
                "id": docente.uid_firebase,
                "nombre": docente.nombres,
                "correo": docente.correo,
            }
            for docente in docentes_disponibles
        ]

        return jsonify({"estado": True, "respuesta": docentes_json, "error": ""}), 200

    except Exception as e:
        app.logger.error(f"Error al obtener docentes disponibles: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener docentes disponibles: {str(e)}",
                }
            ),
            500,
        )

##INSCRIPCIONES

@app.route("/eventos/inscripcion", methods=["POST"])
def agregar_inscripciones():
    try:
        datos = request.get_json()
        evento_id = datos.get("evento_id")
        docentes_uid_firebase = datos.get("docentes_uid_firebase")  # Array de UIDs de Firebase
        taller_id = datos.get("taller_id")
        aceptada = datos.get("aceptada", True)  # default to True if not provided

        if not evento_id or not docentes_uid_firebase:
            return jsonify({"estado": False, "error": "Evento y docentes son campos obligatorios"}), 400

        evento = db.session.query(Evento).get(evento_id)
        if not evento:
            return jsonify({"estado": False, "error": "Evento no encontrado"}), 404

        if taller_id:
            taller = db.session.query(Talleres).filter_by(id=taller_id, evento_id=evento_id).first()
            if not taller:
                return jsonify({"estado": False, "error": "Taller no válido o no pertenece al evento"}), 400

        inscripciones_creadas = []
        for uid_firebase in docentes_uid_firebase:
            docente = db.session.query(Docente).filter_by(uid_firebase=uid_firebase).first()
            if not docente:
                continue  # Si no encuentra el docente, salta a la siguiente iteración

            # Verificar si ya existe una inscripción
            inscripcion_existente = db.session.query(Inscripcion).filter_by(
                evento_id=evento_id, docente_uid_firebase=uid_firebase, taller_id=taller_id).first()
            if inscripcion_existente:
                continue  # Si ya está inscrito, salta a la siguiente iteración

            nueva_inscripcion = Inscripcion(
                evento_id=evento_id,
                docente_uid_firebase=uid_firebase,
                taller_id=taller_id,
                aceptada=aceptada
            )
            db.session.add(nueva_inscripcion)
            inscripciones_creadas.append(nueva_inscripcion.docente_uid_firebase)

        db.session.commit()

        if not inscripciones_creadas:
            return jsonify({"estado": False, "error": "Ninguna inscripción fue creada, posiblemente todos los docentes ya estaban inscritos o no encontrados"}), 400

        return jsonify({"estado": True, "respuesta": f"Inscripciones creadas exitosamente para {len(inscripciones_creadas)} docentes."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al crear las inscripciones: {str(e)}"}), 500
    
@app.route("/eventos/inscripcion/<int:id_inscripcion>", methods=["DELETE"])
# @jwt_required()
def eliminar_inscripcion(id_inscripcion):
    try:
        # Buscar la inscripción a eliminar
        inscripcion = db.session.query(Inscripcion).get(id_inscripcion)
        if not inscripcion:
            return jsonify({"estado": False, "error": "Inscripción no encontrada"}), 404

        # Eliminar la inscripción
        db.session.delete(inscripcion)
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Inscripción eliminada exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al eliminar la inscripción: {str(e)}"}), 500

@app.route("/eventos/inscripcion/estado/<int:id_inscripcion>", methods=["PATCH"])
# @jwt_required()
def actualizar_inscripcion(id_inscripcion):
    try:
        datos = request.get_json()
        nuevo_estado = datos.get("aceptada")

        # Validar que el nuevo estado esté presente y sea un booleano
        if nuevo_estado is None or not isinstance(nuevo_estado, bool):
            return jsonify({"estado": False, "error": "Es necesario especificar un estado válido ('aceptada': true o false)"}), 400

        # Buscar la inscripción a actualizar
        inscripcion = db.session.query(Inscripcion).get(id_inscripcion)
        if not inscripcion:
            return jsonify({"estado": False, "error": "Inscripción no encontrada"}), 404

        # Actualizar el estado de 'aceptada'
        inscripcion.aceptada = nuevo_estado
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Estado de inscripción actualizado exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al actualizar el estado de la inscripción: {str(e)}"}), 500
    
    
@app.route("/eventos/<int:evento_id>/inscritos", defaults={'taller_id': None}, methods=["GET"])
@app.route("/eventos/<int:evento_id>/inscritos/<int:taller_id>", methods=["GET"])
def descargar_inscritos(evento_id, taller_id):
    try:
        # Obtener el evento
        evento = db.session.query(Evento).filter_by(id=evento_id).one_or_none()
        if not evento:
            return jsonify({"estado": False, "respuesta": "", "error": "Evento no encontrado"}), 404

        # Inicializar nombre del archivo con el nombre del evento
        nombre_archivo = f'inscritos_evento_{evento.nombre.replace(" ", "_")}'

        # Construir la consulta base
        query = db.session.query(Inscripcion).join(Docente).filter(Inscripcion.evento_id == evento_id)

        # Si hay taller_id, filtrar por él y obtener el nombre del taller
        if taller_id:
            taller = db.session.query(Talleres).filter_by(id=taller_id).one_or_none()
            if not taller:
                return jsonify({"estado": False, "respuesta": "", "error": "Taller no encontrado"}), 404
            query = query.filter(Inscripcion.taller_id == taller_id)
            nombre_archivo += f'_taller_{taller.nombre.replace(" ", "_")}'

        inscritos = query.all()

        # Crear lista de diccionarios con los datos necesarios
        data = []
        for inscrito in inscritos:
            data.append({
                "Evento ID": inscrito.evento_id,
                "Taller ID": inscrito.taller_id,
                "Inscripcion ID": inscrito.id,
                "Docente UID Firebase": inscrito.docente_uid_firebase,
                "Nombres": inscrito.docente.nombres,
                "Correo": inscrito.docente.correo,
                "Aceptada": inscrito.aceptada,
            })

        # Convertir a DataFrame de pandas
        df = pd.DataFrame(data)

        # Crear un archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Inscritos')

        output.seek(0)

        return send_file(
            output,
            download_name=f'{nombre_archivo}.xlsx',
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        app.logger.error(f"Error al generar el archivo Excel: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al generar el archivo Excel: {str(e)}",
                }
            ),
            500,
        )
