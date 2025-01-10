from app import app, db, jwt
import os
from app.models import (
    Evento,
    Usuario,
    Talleres,
    Facultad,
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
    Configuracion,
    SesionesMicrotalleres,
    Observadores,
    Acreditacion,
    EncuestaObservacion,
    DistributivoDocente,
    Periodo
)
from flask import jsonify, request, send_file, jsonify
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from flask import send_file
from werkzeug.utils import secure_filename
from datetime import datetime, time
from io import BytesIO
import pandas as pd
from .utils import send_email_async, modalidades, competencias, momentos, get_acceptance_email_content,get_updated_email_content, get_denial_email_content, get_inscription_email_content, get_approved_email_content, get_reproved_email_content, get_observation_email_content, get_accepted_certificate_email_content,get_denied_certificate_email_content,get_unasistance_alert_email_content, get_finish_alert_email_content
from datetime import date
from sqlalchemy import func, or_, and_
from openpyxl import Workbook


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
@jwt_required()
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
            
            nuevo_taller = Talleres(nombre=taller_data["nombre"], evento_id=nueva_jornada.id, 
                                    descripcion=taller_data['descripcion'], competencia=taller_data['competencia'],
                                    momento=taller_data['momento'], cupos_extra=0)
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
@jwt_required()
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
        
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Jornada actualizada parcialmente con éxito", "error": ""}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "respuesta": "", "error": str(e)}), 400

@app.route("/eventos/<int:evento_id>/talleres", methods=["POST"])
@jwt_required()
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
        descripcion = datos_taller.get("descripcion")
        competencia = datos_taller.get("competencia")
        momento = datos_taller.get("momento")
        cupos_extra = datos_taller.get("cupos_extra")
        ponentes = datos_taller.get("ponentes", [])
        sesiones = datos_taller.get("sesiones", [])

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
        if not descripcion:
            campos_faltantes.append("descripcion")
        if not competencia:
            campos_faltantes.append("competencia")
        if not momento:
            campos_faltantes.append("momento")
        if not cupos_extra:
            campos_faltantes.append("cupos_extra")
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
            descripcion=descripcion,
            competencia=competencia,
            momento=momento,
            cupos_extra=cupos_extra
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
@jwt_required()
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
        if 'descripcion' in datos_taller:
            taller.descripcion = datos_taller['descripcion']
        if 'competencia' in datos_taller:
            taller.competencia = datos_taller['competencia']
        if 'momento' in datos_taller:
            taller.momento = datos_taller['momento']
        if 'cupos_extra' in datos_taller:
            taller.cupos_extra = datos_taller['cupos_extra']
             
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
                    
            taller_info = {
                "nombre":taller.evento.nombre,
                "taller":taller.nombre,
                "sesiones": [
                    {
                        "fecha": sesion.fecha_evento.fecha.strftime('%Y-%m-%d') if isinstance(sesion.fecha_evento.fecha, datetime) else sesion.fecha_evento.fecha,
                        "hora_inicio": sesion.hora_inicio.strftime('%H:%M') if isinstance(sesion.hora_inicio, datetime) else sesion.hora_inicio,
                        "duracion": sesion.duracion,
                        "modalidad": modalidades.get(sesion.modalidad, 'Desconocida'),
                        "ubicacion": sesion.ubicacion
                    }
                    for sesion in taller.sesiones
                ],
                "tipo": 1
            }
        
            docentes_inscritos = [
                inscripcion.docente.correo
                for inscripcion in taller.inscripciones
                if inscripcion.aceptada == True
            ]

            # Convertir la lista de correos en una cadena separada por comas para enviar a varios destinatarios
            email_content = get_updated_email_content(taller_info)
            # Enviar el correo
            send_email_async(docentes_inscritos, "Cambios en el evento", email_content, "static/cabecera.png")
                    
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
@jwt_required()
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
@jwt_required()
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
        descripcion = datos_charla.get("descripcion")
        competencia = datos_charla.get("competencia")
        momento = datos_charla.get("momento")

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
        if not descripcion:
            campos_faltantes.append("descripcion")
        if not competencia:
            campos_faltantes.append("competencia")
        if not momento:
            campos_faltantes.append("momento")

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
            ubicacion=ubicacion,
            descripcion=descripcion,
            competencia=competencia,
            momento=momento
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
@jwt_required()
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
            for key in ['modalidad', 'ubicacion', 'hora_inicio', 'duracion', 'descripcion', 'competencia', 'momento']:
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
        
        
        if all(field in datos_charla for field in ['hora_inicio', 'duracion', 'ubicacion', 'modalidad', 'fechas']):
            charla_info = {
                "nombre":charla.evento.nombre,
                "fechas": [ {"fecha": fecha.fecha.strftime('%d-%m-%Y'), "id": fecha.id} for fecha in charla.evento.fechasevento],
                "hora_inicio": charla.hora_inicio.strftime('%H:%M') if isinstance(charla.hora_inicio, datetime) else charla.hora_inicio,
                "duracion": charla.duracion,
                "modalidad": modalidades.get(charla.modalidad, 'Desconocida'),
                "ubicacion": charla.ubicacion,
                "tipo": 2
            }
            
            docentes_inscritos = [
                inscripcion.docente.correo
                for inscripcion in charla.evento.inscripciones
                if inscripcion.aceptada == True
            ]

            # Convertir la lista de correos en una cadena separada por comas para enviar a varios destinatarios
            email_content = get_updated_email_content(charla_info)
            # Enviar el correo
            send_email_async(docentes_inscritos, "Cambios en el evento", email_content, "static/cabecera.png")
        
        db.session.commit()
        return jsonify({"estado": True, "respuesta": "Charla actualizada exitosamente", "error": ""}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "respuesta": "", "error": str(e)}), 400

##MICROTALLERES

@app.route("/eventos/microtalleres", methods=["POST"])
@jwt_required()
def crear_microtaller():
    try:
        # Obtener datos del JSON de la solicitud
        datos_microtaller = request.json
        nombre = datos_microtaller.get("nombre")
        horas = datos_microtaller.get("horas")
        inscripcion = datos_microtaller.get("inscripcion")
        cupos = datos_microtaller.get("cupos")
        ponentes = datos_microtaller.get("ponentes", [])
        sesiones = datos_microtaller.get("sesiones", [])
        descripcion = datos_microtaller.get("descripcion")
        competencia = datos_microtaller.get("competencia")
        momento = datos_microtaller.get("momento")

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
        if not horas:
            campos_faltantes.append("horas")
        if inscripcion is None:
            campos_faltantes.append("inscripcion")
        if not cupos:
            campos_faltantes.append("cupos")
        if not ponentes:
            campos_faltantes.append("ponentes")
        if not sesiones:
            campos_faltantes.append("sesiones")
        if not descripcion:
            campos_faltantes.append("descripcion")
        if not competencia:
            campos_faltantes.append("competencia")
        if not momento:
            campos_faltantes.append("momento")
            
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

        # Crear registro en la tabla Microtalleres
        nuevo_microtaller = Microtalleres(
            evento_id=nuevo_evento.id,
            descripcion=descripcion,
            competencia=competencia,
            momento=momento
        )
        
        db.session.add(nuevo_microtaller)
        db.session.flush()

        # Crear registros en la tabla FechasEvento y SesionesMicrotalleres
        for sesion in sesiones:
            fecha = sesion.get("fecha")
            hora_inicio = sesion.get("hora_inicio")
            duracion = sesion.get("duracion")
            modalidad = sesion.get("modalidad")
            ubicacion = sesion.get("ubicacion")

            if not (fecha and hora_inicio and duracion and modalidad and ubicacion):
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "Cada sesión debe tener los atributos 'fecha', 'hora_inicio', 'duracion', 'modalidad' y 'ubicacion'.",
                        }
                    ),
                    400,
                )

            # Crear registro en la tabla FechasEvento
            nueva_fecha_evento = FechasEvento(
                evento_id=nuevo_evento.id,
                fecha=fecha
            )
            db.session.add(nueva_fecha_evento)
            db.session.flush()  # Obtener el ID de la nueva fecha

            # Crear registro en la tabla SesionesMicrotalleres
            nueva_sesion = SesionesMicrotalleres(
                microtaller_id=nuevo_microtaller.id,
                fecha_evento_id=nueva_fecha_evento.id,
                hora_inicio=hora_inicio,
                duracion=duracion,
                modalidad=modalidad,
                ubicacion=ubicacion
            )
            db.session.add(nueva_sesion)

        # Crear registros en la tabla MicrotalleresPonente
        for ponente in ponentes:
            ponente_nombre = ponente.get("nombre")
            if not ponente_nombre:
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
@jwt_required()
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
        if not microtaller:
            return jsonify({"estado": False, "respuesta": "", "error": "Microtaller no encontrado"}), 404
        else: 
            for key in ['descripcion', 'competencia', 'momento']:
                if key in datos_microtaller:
                    setattr(microtaller, key, datos_microtaller[key])

        if "ponentes" in datos_microtaller:
            db.session.query(MicrotalleresPonente).filter_by(microtaller_id=microtaller.id).delete(synchronize_session='fetch')
            for ponente_data in datos_microtaller['ponentes']:
                nombre = ponente_data.get('nombre')
                if not nombre:
                    return jsonify({"estado": False, "respuesta": "", "error": "Todos los ponentes deben tener el atributo 'nombre'."}), 400
                nuevo_ponente = MicrotalleresPonente(
                    microtaller_id=microtaller.id,
                    nombre=nombre
                )
                db.session.add(nuevo_ponente)

        if "sesiones" in datos_microtaller:
            # Borrar todas las fechas y sesiones anteriores del evento
            db.session.query(SesionesMicrotalleres).filter_by(microtaller_id=microtaller.id).delete(synchronize_session='fetch')
            db.session.query(FechasEvento).filter_by(evento_id=evento_id).delete(synchronize_session='fetch')
            
            for sesion in datos_microtaller['sesiones']:
                fecha = sesion.get("fecha")
                hora_inicio = sesion.get("hora_inicio")
                duracion = sesion.get("duracion")
                modalidad = sesion.get("modalidad")
                ubicacion = sesion.get("ubicacion")
                if not (fecha and hora_inicio and duracion and modalidad and ubicacion):
                    return jsonify({"estado": False, "respuesta": "", "error": "Cada sesión debe tener los atributos 'fecha', 'hora_inicio', 'duracion', 'modalidad' y 'ubicacion'."}), 400
                
                nueva_fecha_evento = FechasEvento(evento_id=evento_id, fecha=fecha)
                db.session.add(nueva_fecha_evento)
                db.session.flush()
                
                nueva_sesion = SesionesMicrotalleres(
                    microtaller_id=microtaller.id,
                    fecha_evento_id=nueva_fecha_evento.id,
                    hora_inicio=hora_inicio,
                    duracion=duracion,
                    modalidad=modalidad,
                    ubicacion=ubicacion
                )
                db.session.add(nueva_sesion)

            microtaller_info = {
                "nombre":microtaller.evento.nombre,
                "sesiones": [
                    {
                        "fecha": sesion.fecha_evento.fecha.strftime('%Y-%m-%d') if isinstance(sesion.fecha_evento.fecha, datetime) else sesion.fecha_evento.fecha,
                        "hora_inicio": sesion.hora_inicio.strftime('%H:%M') if isinstance(sesion.hora_inicio, datetime) else sesion.hora_inicio,
                        "duracion": sesion.duracion,
                        "modalidad": modalidades.get(sesion.modalidad, 'Desconocida'),
                        "ubicacion": sesion.ubicacion
                    }
                    for sesion in microtaller.sesiones
                ],
                "tipo": 3
            }
            
            docentes_inscritos = [
                inscripcion.docente.correo
                for inscripcion in microtaller.evento.inscripciones
                if inscripcion.aceptada == True
            ]

            # Convertir la lista de correos en una cadena separada por comas para enviar a varios destinatarios
            email_content = get_updated_email_content(microtaller_info)
            # Enviar el correo
            send_email_async(docentes_inscritos, "Cambios en el evento", email_content, "static/cabecera.png")
        
        db.session.commit()
        return jsonify({"estado": True, "respuesta": "Microtaller actualizado exitosamente", "error": ""}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al actualizar microtaller: {str(e)}")
        return jsonify({"estado": False, "respuesta": "", "error": f"Error al actualizar microtaller: {str(e)}"}), 500

##OBSERVACIONES

@app.route("/eventos/observaciones", methods=["POST"])
@jwt_required()
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
        """ if not horarios:
            campos_faltantes.append("horarios") """

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
        """ for horario in horarios:
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
            db.session.add(nuevo_horario) """
            
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
@jwt_required()
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
        return jsonify({"estado": True, "respuesta": "Observación Áulica actualizada exitosamente", "error": ""}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "respuesta": "", "error": str(e)}), 400

@app.route("/observadores", methods=["POST"])
@jwt_required()
def crear_observador():
    try:
        # Obtener datos del JSON de la solicitud
        datos_observador = request.json
        nombre = datos_observador.get("nombre")

        # Verificar la presencia de atributos obligatorios
        if not nombre:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El campo 'nombre' es obligatorio",
                    }
                ),
                400,
            )

        # Crear registro en la tabla Observadores
        nuevo_observador = Observadores(nombre=nombre)

        db.session.add(nuevo_observador)
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Observador creado exitosamente",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al crear observador: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al crear observador: {str(e)}",
                }
            ),
            500,
        )

@app.route("/observadores/<int:id>", methods=["PUT"])
@jwt_required()
def editar_observador(id):
    try:
        # Obtener datos del JSON de la solicitud
        datos_observador = request.json
        nombre = datos_observador.get("nombre")

        # Verificar la presencia de atributos obligatorios
        if not nombre:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El campo 'nombre' es obligatorio",
                    }
                ),
                400,
            )

        # Buscar el observador por ID
        observador = db.session.query(Observadores).get(id)
        if not observador:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Observador no encontrado",
                    }
                ),
                404,
            )

        # Actualizar los campos del observador
        observador.nombre = nombre

        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Observador actualizado exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al actualizar observador: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al actualizar observador: {str(e)}",
                }
            ),
            500,
        )

@app.route("/observadores/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar_observador(id):
    try:
        # Buscar el observador por ID
        observador = db.session.query(Observadores).get(id)
        if not observador:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Observador no encontrado",
                    }
                ),
                404,
            )

        # Validate if observer is referenced in EncuestaObservacion
        encuesta_observacion = db.session.query(EncuestaObservacion).filter_by(observador_id=id).first()
        if encuesta_observacion:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se puede eliminar el observador porque está asociado a una encuesta.",
                    }
                ),
                400,
            )
        
        # Eliminar el observador
        db.session.delete(observador)
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Observador eliminado exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al eliminar observador: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al eliminar observador: {str(e)}",
                }
            ),
            500,
        )

@app.route("/observadores", methods=["GET"])
@jwt_required()
def obtener_observadores():
    try:
        # Obtener todos los observadores de la base de datos
        observadores = db.session.query(Observadores).all()

        # Convertir los observadores a una lista de diccionarios
        resultado = [{"id": observador.id, "nombre": observador.nombre} for observador in observadores]

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": resultado,
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al obtener observadores: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener observadores: {str(e)}",
                }
            ),
            500,
        )

##GENERAL
@app.route("/eventos/todos", methods=["GET"])
@jwt_required()
def obtener_eventos():
    try:
        eventos = db.session.query(Evento).all()
        resultados = []

        for evento in eventos:
            if evento.tipo != 5:
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
                            "descripcion": taller.descripcion,
                            "competencia": competencias.get(taller.competencia, 'Desconocida'),
                            "momento": momentos.get(taller.momento, 'Desconocido'),
                            "cupos_extra": taller.cupos_extra,
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
                                    "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                                    "correo": inscripcion.docente.correo
                                }
                                for inscripcion in taller.inscripciones
                                if inscripcion.aceptada == True
                            ],
                            "docentes_pendientes": [
                                {
                                    "uid_firebase": inscripcion.docente.uid_firebase,
                                    "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
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
                        "descripcion": charla.descripcion,
                        "competencia": competencias.get(charla.competencia, 'Desconocida'),
                        "momento": momentos.get(charla.momento, 'Desconocido'),
                        "ponentes": [
                            {
                                "nombre": charla_ponente.nombre,
                                "titulo_charla": charla_ponente.titulo_charla
                            } for charla_ponente in charla.charlas_ponentes
                        ],
                        "docentes_inscritos": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                                "correo": inscripcion.docente.correo
                            }
                            for inscripcion in evento.inscripciones
                            if inscripcion.aceptada == True
                        ],
                        "docentes_pendientes": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                                "correo": inscripcion.docente.correo
                            }
                            for inscripcion in evento.inscripciones
                            if inscripcion.aceptada == False
                        ]
                    })

                elif evento.tipo == 3:  # Microtaller
                    microtaller = evento.microtaller
                    evento_info.update({
                        "descripcion": microtaller.descripcion,
                        "competencia": competencias.get(microtaller.competencia, 'Desconocida'),
                        "momento": momentos.get(microtaller.momento, 'Desconocido'),
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
                                for sesion in microtaller.sesiones  # Asegúrate de que taller.sesiones esté correctamente relacionado y cargado
                            ],
                        "ponentes": [ponente.nombre for ponente in microtaller.microtalleres_ponentes],
                        "docentes_inscritos": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                                "correo": inscripcion.docente.correo
                            }
                            for inscripcion in evento.inscripciones
                            if inscripcion.aceptada == True
                        ],
                        "docentes_pendientes": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                                "correo": inscripcion.docente.correo
                            }
                            for inscripcion in evento.inscripciones
                            if inscripcion.aceptada == False
                        ]
                    })

                elif evento.tipo == 4:  # Observación Áulica
                    evento_info.update({
                        
                        "docentes_inscritos": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                                "correo": inscripcion.docente.correo,
                            }
                            for inscripcion in evento.inscripciones
                            if inscripcion.aceptada == True
                        ],
                        "docentes_pendientes": [
                            {
                                "uid_firebase": inscripcion.docente.uid_firebase,
                                "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
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
@jwt_required()
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
                    "descripcion": taller.descripcion,
                    "competencia": competencias.get(taller.competencia, 'Desconocida'),
                    "momento": momentos.get(taller.momento, 'Desconocido'),
                    "cupos_extra": taller.cupos_extra,
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
                            "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                            "correo": inscripcion.docente.correo,
                            "id_inscripcion": inscripcion.id
                        }
                        for inscripcion in taller.inscripciones
                        if inscripcion.aceptada == True
                    ],
                    "docentes_pendientes": [
                        {
                            "uid_firebase": inscripcion.docente.uid_firebase,
                            "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
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
                "competencia": competencias.get(charla.competencia, 'Desconocida'),
                "momento": momentos.get(charla.momento, 'Desconocido'),
                "ubicacion": charla.ubicacion,
                "descripcion": charla.descripcion,
                "ponentes": [
                    {
                        "nombre": charla_ponente.nombre,
                        "titulo_charla": charla_ponente.titulo_charla
                    } for charla_ponente in charla.charlas_ponentes
                ],
                "docentes_inscritos": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                        "correo": inscripcion.docente.correo,
                        "id_inscripcion":inscripcion.id
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == True
                ],
                "docentes_pendientes": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
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
                        for sesion in microtaller.sesiones  # Asegúrate de que taller.sesiones esté correctamente relacionado y cargado
                    ],
                "ponentes": [ponente.nombre for ponente in microtaller.microtalleres_ponentes],
                "descripcion": microtaller.descripcion,
                "competencia": competencias.get(microtaller.competencia, 'Desconocida'),
                "momento": momentos.get(microtaller.momento, 'Desconocido') ,
                "docentes_inscritos": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                        "correo": inscripcion.docente.correo,
                        "id_inscripcion":inscripcion.id

                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == True
                ],
                "docentes_pendientes": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                        "correo": inscripcion.docente.correo,
                            "id_inscripcion":inscripcion.id
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == False
                ]
            })
        elif evento.tipo == 4:  # Observación Áulica
            evento_info.update({
                
                "docentes_inscritos": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                        "correo": inscripcion.docente.correo,
                        "id_inscripcion":inscripcion.id,
                        "observador":inscripcion.encuesta.observador.nombre,
                    }
                    for inscripcion in evento.inscripciones
                    if inscripcion.aceptada == True
                ],
                "docentes_pendientes": [
                    {
                        "uid_firebase": inscripcion.docente.uid_firebase,
                        "nombre": inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}",
                        "correo": inscripcion.docente.correo,
                        "id_inscripcion":inscripcion.id,
                        "encuesta":{
                            "anios_ejercicio":inscripcion.encuesta.anios_ejercicio,
                            "numero_celular":inscripcion.encuesta.numero_celular,
                            "facultad":inscripcion.encuesta.facultad.nombre,
                            "carrera":inscripcion.encuesta.carrera.nombre,
                            "asignatura":inscripcion.encuesta.asignatura,
                            "ciclo_carrera":inscripcion.encuesta.ciclo_carrera,
                            "inclusion":inscripcion.encuesta.inclusion,
                            "campus":inscripcion.encuesta.campus,
                            "duracion_clase":inscripcion.encuesta.duracion_clase,
                            "numero_estudiantes":inscripcion.encuesta.numero_estudiantes,
                            "comentarios":inscripcion.encuesta.comentarios,
                            "horarios_disponibles":[
                                {
                                    "dia":horario.dia,
                                    "hora_inicio":horario.hora_inicio.strftime('%H:%M'),
                                    "hora_fin":horario.hora_fin.strftime('%H:%M')
                                }
                                for horario in inscripcion.encuesta.horarios
                                ]
                        }
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
@jwt_required()
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
        db.session.query(SesionesMicrotalleres).filter(SesionesMicrotalleres.fecha_evento_id.in_(fechas_evento_ids)).delete()
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

##INSCRIPCIONES

@app.route("/eventos/inscripcion", methods=["POST"])
@jwt_required()
def agregar_inscripciones():
    try:
        datos = request.get_json()
        evento_id = datos.get("evento_id")
        docentes_uid_firebase = datos.get("docentes_uid_firebase")  # Array de UIDs de Firebase
        taller_id = datos.get("taller_id")

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
            print(docente.uid_firebase)
            if not docente:
                continue  # Si no encuentra el docente, salta a la siguiente iteración

            # Verificar si ya existe una inscripción
            inscripcion_existente = db.session.query(Inscripcion).filter_by(
                evento_id=evento_id, docente_uid_firebase=uid_firebase, taller_id=taller_id).first()
            if not inscripcion_existente:
                inscripcion_existente = db.session.query(Inscripcion).filter_by(
                evento_id=evento_id, docente_uid_firebase=uid_firebase).first()
            if inscripcion_existente:
                continue  # Si ya está inscrito, salta a la siguiente iteración

            nueva_inscripcion = Inscripcion(
                evento_id=evento_id,
                docente_uid_firebase=uid_firebase,
                taller_id=taller_id,
                aceptada=True
            )
            db.session.add(nueva_inscripcion)
            db.session.flush()
            
            nueva_acreditacion = Acreditacion(
                inscripcion_id=nueva_inscripcion.id,
                aprobo=False,  # Inicialmente no aprobado
                asistio=False,  # Inicialmente no asistido
                comentario=""  # Inicialmente sin comentarios
            )
            db.session.add(nueva_acreditacion)
            
            inscripciones_creadas.append(nueva_inscripcion.docente_uid_firebase)
            
            docente_nombre = nueva_inscripcion.docente.nombres if nueva_inscripcion.docente.apellidos is None else f"{nueva_inscripcion.docente.nombres} {nueva_inscripcion.docente.apellidos}"

            # Llamar a la función con o sin `taller_nombre` según el tipo de evento
            if nueva_inscripcion.evento.tipo == 1:
                email_content = get_inscription_email_content(docente_nombre, nueva_inscripcion.evento.nombre, nueva_inscripcion.evento.tipo, taller_nombre=nueva_inscripcion.taller.nombre)
            else:
                email_content = get_inscription_email_content(docente_nombre, nueva_inscripcion.evento.nombre, nueva_inscripcion.evento.tipo)

            # Enviar el correo
            send_email_async(nueva_inscripcion.docente.correo, "Inscripción Aceptada", email_content, "static/cabecera.png")
            
        db.session.commit()

        
        if len(inscripciones_creadas) < len(docentes_uid_firebase):
            if not inscripciones_creadas:
                return jsonify({"estado": False, "error": "Ninguna inscripción fue creada, todos los docentes ya estaban inscritos en el evento"}), 400
            return jsonify({"estado": True, "respuesta": f"Inscripciones creadas exitosamente para {len(inscripciones_creadas)} docentes. Ya estaban inscritos en el evento {len(docentes_uid_firebase)-len(inscripciones_creadas)} docentes"}), 200
        else:
            return jsonify({"estado": True, "respuesta": f"Inscripciones creadas exitosamente para {len(inscripciones_creadas)} docentes."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al crear las inscripciones: {str(e)}"}), 500
    
@app.route("/eventos/inscripcion/<int:id_inscripcion>", methods=["DELETE"])
@jwt_required()
def eliminar_inscripcion(id_inscripcion):
    try:
        # Buscar la inscripción a eliminar
        inscripcion = db.session.query(Inscripcion).get(id_inscripcion)
        if not inscripcion:
            return jsonify({"estado": False, "error": "Inscripción no encontrada"}), 404       
        
        encuesta = db.session.query(EncuestaObservacion).filter_by(inscripcion_id=id_inscripcion).first()
        acreditaciones = db.session.query(Acreditacion).filter_by(inscripcion_id=id_inscripcion).all()

        if encuesta:
            # Eliminar la inscripción
            horarios = db.session.query(HorarioDisponible).filter_by(encuesta_id=encuesta.id).all()
            for horario in horarios:
                db.session.delete(horario)
            db.session.delete(encuesta)
            db.session.delete(inscripcion)
            # Obtener el nombre completo del docente
        else:
            # Eliminar la inscripción
            db.session.delete(inscripcion)

        # Eliminar las acreditaciones relacionadas
        for acreditacion in acreditaciones:
            db.session.delete(acreditacion)
            
        docente_nombre = inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}"

        # Llamar a la función con o sin `taller_nombre` según el tipo de evento
        if inscripcion.evento.tipo == 1:
            email_content = get_denial_email_content(docente_nombre, inscripcion.evento.nombre, inscripcion.evento.tipo, taller_nombre=inscripcion.taller.nombre)
        else:
            email_content = get_denial_email_content(docente_nombre, inscripcion.evento.nombre, inscripcion.evento.tipo)

        # Enviar el correo
        send_email_async(inscripcion.docente.correo, "Inscripción Anulada", email_content, "static/cabecera.png")
        
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Inscripción negada exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al eliminar la inscripción: {str(e)}"}), 500

@app.route("/eventos/inscripcion/estado/<int:id_inscripcion>", methods=["PATCH"])
@jwt_required()
def actualizar_inscripcion(id_inscripcion):
    try:
        datos = request.get_json()
        nuevo_estado = datos.get("aceptada")
        observador_id = datos.get("observador_id")

        # Validar que el nuevo estado esté presente y sea un booleano
        if nuevo_estado is None or not isinstance(nuevo_estado, bool):
            return jsonify({"estado": False, "error": "Es necesario especificar un estado válido ('aceptada': true o false)"}), 400

        # Validar el observador_id si está presente
        if observador_id is not None:
            if not isinstance(observador_id, int) or observador_id <= 0:
                return jsonify({"estado": False, "error": "El observador_id debe ser un entero"}), 400

            # Verificar si el observador existe
            observador = db.session.query(Observadores).get(observador_id)
            if not observador:
                return jsonify({"estado": False, "error": "Observador no encontrado"}), 404

        # Buscar la inscripción a actualizar
        inscripcion = db.session.query(Inscripcion).get(id_inscripcion)
        if not inscripcion:
            return jsonify({"estado": False, "error": "Inscripción no encontrada"}), 404

        # Verificar si el evento tiene cupos disponibles si se está aceptando la inscripción
        if nuevo_estado:
            evento = db.session.query(Evento).get(inscripcion.evento_id)
            if not evento:
                return jsonify({"estado": False, "error": "Evento no encontrado"}), 404
            
            if evento.tipo == 1:
                
                taller = db.session.query(Talleres).get(inscripcion.taller_id)
                if not taller:
                    return jsonify({"estado": False, "error": "Taller no encontrado"}), 404

                inscripciones_aceptadas = db.session.query(Inscripcion).filter_by(evento_id=evento.id, taller_id=taller.id, aceptada=True).count()
                if inscripciones_aceptadas >= evento.cupos + (taller.cupos_extra or 0):
                    return jsonify({"estado": False, "error": "No hay cupos disponibles para este evento"}), 400
            else:
                inscripciones_aceptadas = db.session.query(Inscripcion).filter_by(evento_id=evento.id, aceptada=True).count()
                if inscripciones_aceptadas >= evento.cupos:
                    return jsonify({"estado": False, "error": "No hay cupos disponibles para este evento"}), 400

        
        # Buscar la encuesta observación a actualizar
        encuesta_observacion = db.session.query(EncuestaObservacion).filter_by(inscripcion_id=id_inscripcion).first()
        if observador_id is not None:
            if not encuesta_observacion:
                return jsonify({"estado": False, "error": "Encuesta observación no encontrada para la inscripción dada"}), 404
            encuesta_observacion.observador_id = observador_id

        # Actualizar el estado de 'aceptada'
        inscripcion.aceptada = nuevo_estado

        # Crear el registro de acreditación si la inscripción es aceptada
        if nuevo_estado:
            nueva_acreditacion = Acreditacion(
                inscripcion_id=id_inscripcion,
                aprobo=False,  # Inicialmente no aprobado
                asistio=False,  # Inicialmente no asistido
                comentario=""  # Inicialmente sin comentarios
            )
            db.session.add(nueva_acreditacion)
            
            # Obtener el nombre completo del docente
            docente_nombre = inscripcion.docente.nombres if inscripcion.docente.apellidos is None else f"{inscripcion.docente.nombres} {inscripcion.docente.apellidos}"

            # Llamar a la función con o sin `taller_nombre` según el tipo de evento
            if evento.tipo == 1:
                email_content = get_acceptance_email_content(docente_nombre, evento.nombre, evento.tipo, taller_nombre=inscripcion.taller.nombre)
            else:
                email_content = get_acceptance_email_content(docente_nombre, evento.nombre, evento.tipo)

            # Enviar el correo
            send_email_async(inscripcion.docente.correo, "Inscripción Aceptada", email_content, "static/cabecera.png")


        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Estado de inscripción actualizado exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al actualizar el estado de la inscripción: {str(e)}"}), 500

@app.route("/eventos/acreditaciones", methods=["POST"])
@jwt_required()
def cargar_acreditacion():
    try:
        id_evento = request.form.get('id_evento')
        id_taller = request.form.get('id_taller')  # Si es necesario

        # Verificar si el archivo está en la solicitud
        if 'file' not in request.files:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se encontró ningún archivo en la solicitud",
                    }
                ),
                400,
            )
        
        file = request.files['file']
        
        # Verificar si el archivo tiene un nombre seguro
        if file.filename == '':
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El nombre del archivo no es válido",
                    }
                ),
                400,
            )

        # Guardar el archivo en el servidor
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_ACREDITACIONES'], filename)
        file.save(file_path)

        # Leer el archivo con pandas
        if file_path.endswith('.csv'):
            data = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            data = pd.read_excel(file_path)
        else:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El formato del archivo no es soportado (Se admite .xlsx o .csv). ",
                    }
                ),
                400,
            )

        # Verificar si las inscripciones existen basadas en el correo y id_evento/id_taller
        inscripciones = {}
        for correo in data['correo']:
            inscripcion = db.session.query(Inscripcion).filter(
                Inscripcion.docente.has(correo=correo),
                Inscripcion.evento_id == id_evento,
                Inscripcion.aceptada == True,
                (Inscripcion.taller_id == id_taller if id_taller else True)
            ).first()
            if inscripcion:
                inscripciones[correo] = inscripcion.id
            else:
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": f"No se encontró una inscripción para el correo: {correo}",
                        }
                    ),
                    400,
                )

        # Iterar sobre las filas del dataframe e insertar o actualizar los registros en la base de datos
        actualizadas=0
        for index, row in data.iterrows():
            inscripcion_id = inscripciones[row['correo']]
            acreditacion = db.session.query(Acreditacion).filter_by(inscripcion_id=inscripcion_id).first()
            # Actualizar la acreditación existente
            acreditacion.asistio = row['asistio']
            acreditacion.aprobo = row['aprobo']
            acreditacion.comentario = row['comentario']
            actualizadas=actualizadas+1
            
            docente_nombre = acreditacion.inscripcion.docente.nombres if acreditacion.inscripcion.docente.apellidos is None else f"{acreditacion.inscripcion.docente.nombres} {acreditacion.inscripcion.docente.apellidos}"
            evento_nombre = acreditacion.inscripcion.evento.nombre
            evento_tipo = acreditacion.inscripcion.evento.tipo
            
            if acreditacion.aprobo:
                # Llamar a la función con o sin `taller_nombre` según el tipo de evento
                if acreditacion.inscripcion.evento.tipo == 1:
                    email_content = get_approved_email_content(docente_nombre, evento_nombre, evento_tipo, taller_nombre=acreditacion.inscripcion.taller.nombre)
                else:
                    email_content = get_approved_email_content(docente_nombre, evento_nombre, evento_tipo)
                    
                # Enviar el correo
                send_email_async(acreditacion.inscripcion.docente.correo, "Evento aprobado", email_content, "static/cabecera.png")
                
                horas_aprobadas = db.session.query(func.sum(Evento.horas)).join(Inscripcion).join(Acreditacion).filter(
                    Inscripcion.docente_uid_firebase == acreditacion.inscripcion.docente.uid_firebase,
                    Acreditacion.aprobo == True
                ).scalar()
                
                if horas_aprobadas >= 140:
                    # Consulta principal para obtener las facultades del docente en el último periodo
                    facultades = db.session.query(Facultad.nombre).join(DistributivoDocente).filter(
                        DistributivoDocente.docente_uid_firebase == acreditacion.inscripcion.docente.uid_firebase,
                    ).distinct().all()

                    # Formatea la lista de nombres de facultades
                    nombres_facultades = ', '.join([facultad[0] for facultad in facultades])
                    email_content = get_finish_alert_email_content(docente_nombre, acreditacion.inscripcion.docente.correo, nombres_facultades)
                    # Enviar el correo
                    send_email_async('capacitaciones.die@ucuenca.edu.ec', "Alerta Programa Finalizado", email_content, "static/cabecera.png")
            else:
                # Llamar a la función con o sin `taller_nombre` según el tipo de evento
                if acreditacion.inscripcion.evento.tipo == 1:
                    email_content = get_reproved_email_content(docente_nombre, evento_nombre, evento_tipo, acreditacion.asistio, acreditacion.aprobo, taller_nombre=acreditacion.inscripcion.taller.nombre)
                else:
                    email_content = get_reproved_email_content(docente_nombre, evento_nombre, evento_tipo, acreditacion.asistio, acreditacion.aprobo)
                    
                # Enviar el correo
                send_email_async(acreditacion.inscripcion.docente.correo, "Evento reprobado", email_content, "static/cabecera.png") 
            
            if not acreditacion.asistio:
                fecha_min_subquery = db.session.query(
                    FechasEvento.evento_id,
                    func.min(FechasEvento.fecha).label('fecha')
                ).group_by(FechasEvento.evento_id).subquery()

                # Consulta principal usando la fecha mínima para cada evento
                inasistencias_query = db.session.query(Evento.nombre).join(Inscripcion).join(Acreditacion).join(fecha_min_subquery, fecha_min_subquery.c.evento_id == Evento.id).filter(
                    Inscripcion.docente_uid_firebase == acreditacion.inscripcion.docente.uid_firebase,
                    Acreditacion.asistio == False,
                    fecha_min_subquery.c.fecha < date.today()  # Solo fechas anteriores a la fecha actual
                ).distinct().all()
                
                nombres_eventos = [evento[0] for evento in inasistencias_query]
                inasistencias = len(nombres_eventos)
                
                if inasistencias >= 3:
                    email_content = get_unasistance_alert_email_content(docente_nombre, acreditacion.inscripcion.docente.correo, nombres_eventos)
                    send_email_async('capacitaciones.die@ucuenca.edu.ec', "Alerta Inasistencia", email_content, "static/cabecera.png")
                
            
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": f"Datos cargados exitosamente. Actualizados:{actualizadas}",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al cargar datos de acreditación: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al cargar datos de acreditación: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eventos/acreditaciones/pdf/<int:id_acreditacion>", methods=["PATCH"])
@jwt_required()
def guardar_pdf(id_acreditacion):
    try:
        if 'archivo_pdf' not in request.files:
            return jsonify({"estado": False, "error": "Archivo PDF no encontrado en la solicitud"}), 400

        archivo_pdf = request.files['archivo_pdf']
        filename = secure_filename(archivo_pdf.filename)
        filepath = os.path.join(app.config['UPLOAD_PDF'], filename)
        archivo_pdf.save(filepath)

        # Verificar si la acreditación existe
        acreditacion = db.session.query(Acreditacion).get(id_acreditacion)
        if not acreditacion:
            return jsonify({"estado": False, "error": "Acreditación no encontrada"}), 404

        # Guardar la ruta del archivo PDF en la acreditación
        acreditacion.archivo_pdf = filepath
        acreditacion.asistio = True
        acreditacion.aprobo = True
        docente_nombre = acreditacion.inscripcion.docente.nombres if acreditacion.inscripcion.docente.apellidos is None else f"{acreditacion.inscripcion.docente.nombres} {acreditacion.inscripcion.docente.apellidos}"
        evento_nombre = acreditacion.inscripcion.evento.nombre
        email_content = get_observation_email_content(docente_nombre, evento_nombre)
        send_email_async(acreditacion.inscripcion.docente.correo, "Acompañamiento Áulico Finalizado", email_content, "static/cabecera.png")
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Archivo PDF guardado exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al guardar el archivo PDF: {str(e)}"}), 500

@app.route("/eventos/acreditaciones/pdf/<int:id_acreditacion>", methods=["GET"])
@jwt_required()
def descargar_pdf(id_acreditacion):
    try:
        # Verificar si la acreditación existe
        acreditacion = db.session.query(Acreditacion).get(id_acreditacion)
        if not acreditacion or not acreditacion.archivo_pdf:
            return jsonify({"estado": False, "error": "Acreditación no encontrada o archivo PDF no disponible"}), 404

        return send_file(acreditacion.archivo_pdf, as_attachment=True)

    except Exception as e:
        return jsonify({"estado": False, "error": f"Error al descargar el archivo PDF: {str(e)}"}), 500

@app.route("/eventos/acreditaciones/pdf/<int:id_acreditacion>", methods=["DELETE"])
@jwt_required()
def eliminar_pdf(id_acreditacion):
    try:
        # Verificar si la acreditación existe
        acreditacion = db.session.query(Acreditacion).get(id_acreditacion)
        if not acreditacion or not acreditacion.archivo_pdf:
            return jsonify({"estado": False, "error": "Acreditación no encontrada o archivo PDF no disponible"}), 404

        # Eliminar el archivo PDF del sistema de archivos
        if os.path.exists(acreditacion.archivo_pdf):
            os.remove(acreditacion.archivo_pdf)

        # Eliminar la ruta del archivo PDF de la acreditación
        acreditacion.archivo_pdf = None
        acreditacion.asistio = False
        acreditacion.aprobo = False
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Archivo PDF eliminado exitosamente"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al eliminar el archivo PDF: {str(e)}"}), 500

@app.route("/eventos/acreditaciones/<int:evento_id>", methods=["GET"])
@app.route("/eventos/acreditaciones/<int:evento_id>/<int:taller_id>", methods=["GET"])
@jwt_required()
def obtener_acreditaciones(evento_id, taller_id=None):
    try:
        # Filtrar inscripciones por evento_id y opcionalmente por taller_id
        if taller_id:
            inscripciones = db.session.query(Inscripcion).filter_by(evento_id=evento_id, taller_id=taller_id).all()
        else:
            inscripciones = db.session.query(Inscripcion).filter_by(evento_id=evento_id).all()
            
        # Obtener acreditaciones asociadas a las inscripciones
        acreditaciones = []
        for inscripcion in inscripciones:
            acreditacion = db.session.query(Acreditacion).filter_by(inscripcion_id=inscripcion.id).first()
            if acreditacion:
                docente = db.session.query(Docente).filter_by(uid_firebase=inscripcion.docente_uid_firebase).first()
                if docente:
                    acreditaciones.append({
                        "id": acreditacion.id,
                        "name": docente.nombres if docente.apellidos is None else f"{docente.nombres} {docente.apellidos}",
                        "email": docente.correo,
                        "attended": acreditacion.asistio,
                        "passed": acreditacion.aprobo,
                        "comments": acreditacion.comentario,
                        "has_pdf": acreditacion.archivo_pdf is not None and acreditacion.archivo_pdf != "",
                        "horas": inscripcion.evento.horas if inscripcion.evento.horas is not None else 0,
                        "evento_id": inscripcion.evento.id
                    })

        return jsonify({"estado": True, "respuesta": acreditaciones}), 200

    except Exception as e:
        return jsonify({"estado": False, "error": f"Error al obtener las acreditaciones: {str(e)}"}), 500

@app.route("/eventos/acreditaciones", methods=["PUT"])
@jwt_required()
def actualizar_acreditaciones():
    try:
        datos = request.get_json()
        for item in datos:
            acreditacion = db.session.query(Acreditacion).get(item['id'])
            if not acreditacion:
                continue
            
            cambio_aprobo = item.get("passed") is not None and item["passed"] != acreditacion.aprobo
            cambio_asistio = item.get("attended") is not None and item["attended"] != acreditacion.asistio
            
            acreditacion.asistio = item.get("attended", acreditacion.asistio)
            acreditacion.aprobo = item.get("passed", acreditacion.aprobo)
            acreditacion.comentario = item.get("comments", acreditacion.comentario)
            
            docente_nombre = acreditacion.inscripcion.docente.nombres if acreditacion.inscripcion.docente.apellidos is None else f"{acreditacion.inscripcion.docente.nombres} {acreditacion.inscripcion.docente.apellidos}"
            evento_nombre = acreditacion.inscripcion.evento.nombre
            evento_tipo = acreditacion.inscripcion.evento.tipo
            
            if cambio_aprobo:
                if acreditacion.aprobo:
                    # Llamar a la función con o sin `taller_nombre` según el tipo de evento
                    if acreditacion.inscripcion.evento.tipo == 1:
                        email_content = get_approved_email_content(docente_nombre, evento_nombre, evento_tipo, taller_nombre=acreditacion.inscripcion.taller.nombre)
                    else:
                        email_content = get_approved_email_content(docente_nombre, evento_nombre, evento_tipo)
                        
                    # Enviar el correo
                    send_email_async(acreditacion.inscripcion.docente.correo, "Evento aprobado", email_content, "static/cabecera.png")
                    
                    horas_aprobadas = db.session.query(func.sum(Evento.horas)).join(Inscripcion).join(Acreditacion).filter(
                        Inscripcion.docente_uid_firebase == acreditacion.inscripcion.docente.uid_firebase,
                        Acreditacion.aprobo == True
                    ).scalar()
                    
                    if horas_aprobadas >= 140:
                        # Consulta principal para obtener las facultades del docente en el último periodo
                        facultades = db.session.query(Facultad.nombre).join(DistributivoDocente).filter(
                            DistributivoDocente.docente_uid_firebase == acreditacion.inscripcion.docente.uid_firebase,
                        ).distinct().all()

                        # Formatea la lista de nombres de facultades
                        nombres_facultades = ', '.join([facultad[0] for facultad in facultades])
                        email_content = get_finish_alert_email_content(docente_nombre, acreditacion.inscripcion.docente.correo, nombres_facultades)
                        # Enviar el correo
                        send_email_async('capacitaciones.die@ucuenca.edu.ec', "Alerta Programa Finalizado", email_content, "static/cabecera.png")
                    
                else:
                    # Llamar a la función con o sin `taller_nombre` según el tipo de evento
                    if acreditacion.inscripcion.evento.tipo == 1:
                        email_content = get_reproved_email_content(docente_nombre, evento_nombre, evento_tipo, acreditacion.asistio, acreditacion.aprobo, taller_nombre=acreditacion.inscripcion.taller.nombre)
                    else:
                        email_content = get_reproved_email_content(docente_nombre, evento_nombre, evento_tipo, acreditacion.asistio, acreditacion.aprobo)
                        
                    # Enviar el correo
                    send_email_async(acreditacion.inscripcion.docente.correo, "Evento reprobado", email_content, "static/cabecera.png")
            
            if cambio_asistio:
                if not acreditacion.asistio:
                    fecha_min_subquery = db.session.query(
                        FechasEvento.evento_id,
                        func.min(FechasEvento.fecha).label('fecha')
                    ).group_by(FechasEvento.evento_id).subquery()

                    # Consulta principal usando la fecha mínima para cada evento
                    inasistencias_query = db.session.query(Evento.nombre).join(Inscripcion).join(Acreditacion).join(fecha_min_subquery, fecha_min_subquery.c.evento_id == Evento.id).filter(
                        Inscripcion.docente_uid_firebase == acreditacion.inscripcion.docente.uid_firebase,
                        Acreditacion.asistio == False,
                        fecha_min_subquery.c.fecha < date.today()  # Solo fechas anteriores a la fecha actual
                    ).distinct().all()
                    
                    nombres_eventos = [evento[0] for evento in inasistencias_query]
                    inasistencias = len(nombres_eventos)
                    
                    if inasistencias >= 3:
                        email_content = get_unasistance_alert_email_content(docente_nombre, acreditacion.inscripcion.docente.correo, nombres_eventos)
                        send_email_async('capacitaciones.die@ucuenca.edu.ec', "Alerta Inasistencia", email_content, "static/cabecera.png")
            
        db.session.commit()
        
        return jsonify({"estado": True, "respuesta": "Acreditaciones actualizadas correctamente"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"estado": False, "error": f"Error al actualizar las acreditaciones: {str(e)}"}), 500

@app.route("/eventos/<int:evento_id>/inscritos", defaults={'taller_id': None}, methods=["GET"])
@app.route("/eventos/<int:evento_id>/inscritos/<int:taller_id>", methods=["GET"])
@jwt_required()
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
            query = query.filter(Inscripcion.taller_id == taller_id,Inscripcion.aceptada == True)
            nombre_archivo += f'_taller_{taller.nombre.replace(" ", "_")}'

        inscritos = query.all()
        
        #Ultimo periodo del que se tiene distributivo cargado en el sistema
        max_id_periodo = (
            db.session.query(func.max(Periodo.id))
            .join(DistributivoDocente, Periodo.id == DistributivoDocente.periodo_lectivo_id)
            .scalar()
        )
        
        # Crear lista de diccionarios con los datos necesarios
        data = []
        for inscrito in inscritos:
            facultades = db.session.query(Facultad.nombre).join(DistributivoDocente, DistributivoDocente.facultad_id == Facultad.id_facultad)\
            .filter(
                DistributivoDocente.docente_uid_firebase == inscrito.docente_uid_firebase,
                DistributivoDocente.periodo_lectivo_id == max_id_periodo
            ).all()
            data.append({
                "Nombres": inscrito.docente.nombres,
                "Apellidos": "" if inscrito.docente.apellidos is None else inscrito.docente.apellidos,
                "Correo": inscrito.docente.correo,
                "Cedula": inscrito.docente.cedula,
                "Sexo": inscrito.docente.sexo,
                "Facultades": ' - '.join([facultad[0] for facultad in facultades])
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
  
@app.route("/eventos/docentes/<int:id_evento>", methods=["GET"])
@jwt_required()
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
                "nombre": docente.nombres if docente.apellidos is None else f"{docente.nombres} {docente.apellidos}",
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

##CERTIFICADOS
@app.route("/certificados", methods=["GET"])
@jwt_required()
def obtener_certificados():
    try:
        # Realizar la consulta uniendo las tablas Certificado y Curso
        certificados = (
            db.session.query(Certificado).all()
        )

        # Construir la respuesta
        datos_certificados = [
            {
                "id": certificado.id,
                "docente_uid_firebase": certificado.docente_uid_firebase,
                "archivo_pdf": certificado.archivo_pdf,
                "fecha_creacion": certificado.fecha_carga.strftime("%Y-%m-%d") if certificado.fecha_carga else None,
                "nombre_curso": certificado.nombre_curso,
                "horas_acredita": certificado.horas_acredita,
                "horas_certificado": certificado.horas_certificado,
                "institucion": certificado.institucion,
                "nombres": certificado.docente.nombres if certificado.docente.apellidos is None else f"{certificado.docente.nombres} {certificado.docente.apellidos}",
                "correo": certificado.docente.correo,
                "aceptada": certificado.aceptada
            }
            for certificado in certificados
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
        
@app.route("/certificados/<int:certificado_id>", methods=["PUT"])
@jwt_required()
def actualizar_estado_certificado(certificado_id):
    try:
        # Obtener el JSON del cuerpo de la solicitud
        data = request.get_json()
        nuevo_estado = data.get("aceptada")

        # Verificar que el nuevo estado fue proporcionado
        if nuevo_estado is None:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El campo 'aceptada' es requerido.",
                    }
                ),
                400,
            )

        # Buscar el certificado por su ID
        certificado = db.session.query(Certificado).filter(Certificado.id == certificado_id).first()


        # Verificar si el certificado existe
        if not certificado:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Certificado no encontrado.",
                    }
                ),
                404,
            )

        # Actualizar el estado de aceptación del certificado
        certificado.aceptada = nuevo_estado
        
        docente_nombre = certificado.docente.nombres if certificado.docente.apellidos is None else f"{certificado.docente.nombres} {certificado.docente.apellidos}"
        evento_nombre = certificado.nombre_curso
        
        # Obtiene la suma de horas acreditadas, o usa 0 si es None
        total_horas_acredita = db.session.query(func.sum(Certificado.horas_acredita)).filter(
            Certificado.docente_uid_firebase == certificado.docente_uid_firebase,
            Certificado.aceptada == True
        ).scalar() or 0

        # Asegúrate de que porcentaje_programa y horas_programa no sean None
        porcentaje_programa = db.session.query(Configuracion.valor).filter(
            Configuracion.nombre_parametro == 'porcentaje_programa'
        ).scalar() or 0

        horas_programa = db.session.query(Configuracion.valor).filter(
            Configuracion.nombre_parametro == 'horas_programa'
        ).scalar() or 0

        # Calcula las horas disponibles asegurando que todas las variables tienen un valor válido
        horas_disponibles = (porcentaje_programa * horas_programa) - total_horas_acredita
        
        if nuevo_estado:
            email_content = get_accepted_certificate_email_content(docente_nombre, evento_nombre, certificado.horas_acredita, int(horas_disponibles))
            send_email_async(certificado.docente.correo, "Certificado Aprobado", email_content, "static/cabecera.png")
        else:
            email_content = get_denied_certificate_email_content(docente_nombre, evento_nombre)
            send_email_async(certificado.docente.correo, "Certificado Denegado", email_content, "static/cabecera.png")
        
        
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": f"Estado del certificado actualizado correctamente.",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al actualizar estado del certificado: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al actualizar estado del certificado: {str(e)}",
                }
            ),
            500,
        )

@app.route("/descargar_certificado/<int:id_certificado>", methods=["GET"])
@jwt_required()
def descargar_certificado(id_certificado):
    try:
        certificado = db.session.query(Certificado).filter(Certificado.id == id_certificado).first()

        if certificado:
            path_to_file = certificado.archivo_pdf
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

@app.route("/parametros", methods=["GET"])
@jwt_required()
def obtener_parametros():
    try:
        # Fetch all parameters from the configuracion table
        parametros = db.session.query(Configuracion).all()

        # Build the response
        datos_parametros = [
            {
                "id": parametro.id,
                "nombre_parametro": parametro.nombre_parametro,
                "valor": float(parametro.valor),
                "descripcion": parametro.descripcion,
            }
            for parametro in parametros
        ]

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": {"parametros": datos_parametros},
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capture errors and return an error message
        app.logger.error(f"Error al obtener parámetros: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener parámetros: {str(e)}",
                }
            ),
            500,
        )

@app.route("/parametros", methods=["PUT"])
@jwt_required()
def actualizar_parametros():
    try:
        # Get JSON data from the request
        data = request.get_json()

        # Extract the list of parameters to update
        parametros = data.get('parametros', [])

        for parametro in parametros:
            nombre_parametro = parametro.get('nombre_parametro')
            valor = parametro.get('valor')

            # Fetch the parameter from the database
            configuracion = db.session.query(Configuracion).filter_by(nombre_parametro=nombre_parametro).first()

            if configuracion:
                # Update the parameter's value
                configuracion.valor = valor
            else:
                # Optionally, create a new parameter if it doesn't exist
                new_parametro = Configuracion(
                    nombre_parametro=nombre_parametro,
                    valor=valor,
                    descripcion=parametro.get('descripcion', '')
                )
                db.session.add(new_parametro)

        # Commit the changes to the database
        db.session.commit()

        return jsonify({
            "estado": True,
            "respuesta": "Parámetros actualizados correctamente.",
            "error": ""
        }), 200

    except Exception as e:
        # Log the error and return an error message
        app.logger.error(f"Error al actualizar parámetros: {str(e)}")
        return jsonify({
            "estado": False,
            "respuesta": "",
            "error": f"Error al actualizar parámetros: {str(e)}"
        }), 500


##REPORTES
@app.route("/reportes/horas", methods=["GET"])
@jwt_required()
def obtener_docentes_horas():
    try:
        # Parámetros de búsqueda y filtros
        busqueda = request.args.get("busqueda", type=str)
        facultad_nombre = request.args.get("facultad", type=str)
        horas_min = request.args.get("horas_min", type=int)
        horas_max = request.args.get("horas_max", type=int)
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # Subquery para obtener el último periodo lectivo de cada docente
        ultimo_distributivo = (
            db.session.query(
                DistributivoDocente.docente_uid_firebase,
                func.max(DistributivoDocente.periodo_lectivo_id).label("ultimo_periodo")
            )
            .group_by(DistributivoDocente.docente_uid_firebase)
            .subquery()
        )

        certificados_subquery = (
            db.session.query(
                Certificado.docente_uid_firebase,
                func.coalesce(func.sum(Certificado.horas_acredita), 0).label("horas_certificados")
            )
            .filter(Certificado.aceptada == True)
            .group_by(Certificado.docente_uid_firebase)
            .subquery()
        )

        # Subconsulta para horas acreditadas por eventos con acreditaciones aprobadas
        eventos_subquery = (
            db.session.query(
                Inscripcion.docente_uid_firebase,
                func.coalesce(func.sum(Evento.horas), 0).label("horas_eventos")
            )
            .join(Acreditacion, and_(
                Inscripcion.id == Acreditacion.inscripcion_id,
                Acreditacion.aprobo == True
            ))
            .join(Evento, Evento.id == Inscripcion.evento_id)
            .group_by(Inscripcion.docente_uid_firebase)
            .subquery()
        )

        # Consulta principal
        query = db.session.query(
            Docente.uid_firebase,
            Docente.nombres,
            Docente.apellidos,
            Docente.correo,
            Docente.cedula,
            func.array_agg(func.distinct(Facultad.nombre)).label("facultades"),
            func.coalesce(certificados_subquery.c.horas_certificados, 0).label("horas_certificados"),
            func.coalesce(eventos_subquery.c.horas_eventos, 0).label("horas_eventos"),
            (func.coalesce(certificados_subquery.c.horas_certificados, 0) + 
            func.coalesce(eventos_subquery.c.horas_eventos, 0)).label("horas_totales")
        ).join(
            DistributivoDocente, Docente.uid_firebase == DistributivoDocente.docente_uid_firebase
        ).join(
            Facultad, DistributivoDocente.facultad_id == Facultad.id_facultad
        ).outerjoin(
            certificados_subquery, Docente.uid_firebase == certificados_subquery.c.docente_uid_firebase
        ).outerjoin(
            eventos_subquery, Docente.uid_firebase == eventos_subquery.c.docente_uid_firebase
        ).filter(
            DistributivoDocente.periodo_lectivo_id == ultimo_distributivo.c.ultimo_periodo
        ).group_by(
            Docente.uid_firebase, Docente.nombres, Docente.apellidos, Docente.correo, Docente.cedula,
            certificados_subquery.c.horas_certificados, eventos_subquery.c.horas_eventos
        )

        # Aplicar filtros
        if busqueda:
            query = query.filter(
                or_(
                    Docente.nombres.ilike(f"%{busqueda}%"),
                    Docente.apellidos.ilike(f"%{busqueda}%"),
                    Docente.correo.ilike(f"%{busqueda}%"),
                    Docente.cedula.ilike(f"%{busqueda}%")
                )
            )
        # Filtro por facultad (si se proporciona)
        if facultad_nombre:
            query = query.having(
                func.array_to_string(func.array_agg(func.distinct(Facultad.nombre)), ',').ilike(f"%{facultad_nombre}%")
            )
        # Filtros por rango de horas
        if horas_min is not None:
            query = query.having(
                (func.coalesce(certificados_subquery.c.horas_certificados, 0) + 
                func.coalesce(eventos_subquery.c.horas_eventos, 0)) >= horas_min
            )
        if horas_max is not None:
            query = query.having(
                (func.coalesce(certificados_subquery.c.horas_certificados, 0) + 
                func.coalesce(eventos_subquery.c.horas_eventos, 0)) <= horas_max
            )

        # Aplicar paginación
        paginacion = query.paginate(page=page, per_page=per_page, error_out=False)

        # Construir la respuesta
        resultado = []
        for docente in paginacion.items:
            resultado.append({
                "docente": {
                    "uid_firebase": docente.uid_firebase,
                    "nombre": docente.nombres if docente.apellidos is None else f"{docente.nombres} {docente.apellidos}",
                    "correo": docente.correo,                   
                    "cedula": docente.cedula
                },
                "facultades": docente.facultades,
                "horas_acreditadas": {
                    "certificados": docente.horas_certificados,
                    "eventos": docente.horas_eventos,
                    "total": docente.horas_certificados + docente.horas_eventos
                }
            })

        return jsonify({
            "estado": True,
            "respuesta": resultado,
            "paginacion": {
                "pagina_actual": paginacion.page,
                "total_paginas": paginacion.pages,
                "total_resultados": paginacion.total
            },
            "error": ""
        }), 200

    except Exception as e:
        app.logger.error(f"Error al obtener docentes: {str(e)}")
        return jsonify({
            "estado": False,
            "respuesta": "",
            "error": f"Error al obtener docentes: {str(e)}"
        }), 500

@app.route("/facultades", methods=["GET"])
@jwt_required()
def obtener_facultades():
    try:
        # Consultar todas las facultades
        facultades = db.session.query(Facultad).all()

        # Construir la respuesta
        datos_facultades = [
            {
                "id": facultad.id_facultad,
                "nombre": facultad.nombre,
            }
            for facultad in facultades
        ]

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": {"facultades": datos_facultades},
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al obtener facultades: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener facultades: {str(e)}",
                }
            ),
            500,
        )

@app.route("/reportes/horas/detalle", methods=["POST"])
@jwt_required()
def obtener_detalle_docente():
    try:
        # Obtener el UID del docente desde el cuerpo de la solicitud
        data = request.get_json()
        uid_firebase = data.get("uid_firebase")

        if not uid_firebase:
            return jsonify({
                "estado": False,
                "respuesta": "",
                "error": "El UID de Firebase es obligatorio."
            }), 400

        # Consultar el docente
        docente = db.session.query(Docente).filter_by(uid_firebase=uid_firebase).first()

        if not docente:
            return jsonify({
                "estado": False,
                "respuesta": "",
                "error": "Docente no encontrado."
            }), 404

        # Consultar inscripciones y eventos acreditados
        inscripciones = db.session.query(Inscripcion).filter_by(docente_uid_firebase=uid_firebase).all()

        eventos = [
            {
                "nombre_evento": inscripcion.evento.nombre,
                "horas_evento": inscripcion.evento.horas
            }
            for inscripcion in inscripciones if inscripcion.acreditacion and inscripcion.acreditacion.aprobo
        ]

        # Consultar certificados externos acreditados
        certificados = db.session.query(Certificado).filter_by(docente_uid_firebase=uid_firebase, aceptada=True).all()
        total_horas_certificados = sum(certificado.horas_acredita for certificado in certificados)

        # Agregar evento "certificados_externos"
        if total_horas_certificados > 0:
            eventos.append({
                "nombre_evento": "Certificados Externos",
                "horas_evento": total_horas_certificados
            })

        return jsonify({
            "estado": True,
            "respuesta": {
                "total_horas": sum(evento["horas_evento"] for evento in eventos),
                "docente": {
                    "uid_firebase": docente.uid_firebase,
                    "nombre": docente.nombres if docente.apellidos is None else f"{docente.nombres} {docente.apellidos}",
                    "correo": docente.correo
                },
                "eventos": eventos
            },
            "error": ""
        }), 200

    except Exception as e:
        app.logger.error(f"Error al obtener detalle del docente: {str(e)}")
        return jsonify({
            "estado": False,
            "respuesta": "",
            "error": f"Error al obtener detalle del docente: {str(e)}"
        }), 500
        
@app.route("/reportes/horas/excel", methods=["GET"])
@jwt_required()
def descargar_docentes_horas_excel_todo():
    try:
        # ======== Lógica de filtros y consulta (igual que en 'obtener_docentes_horas') ========
        busqueda = request.args.get("busqueda", type=str)
        facultad_nombre = request.args.get("facultad", type=str)
        horas_min = request.args.get("horas_min", type=int)
        horas_max = request.args.get("horas_max", type=int)
        
        # Subquery para obtener el último periodo lectivo de cada docente
        ultimo_distributivo = (
            db.session.query(
                DistributivoDocente.docente_uid_firebase,
                func.max(DistributivoDocente.periodo_lectivo_id).label("ultimo_periodo")
            )
            .group_by(DistributivoDocente.docente_uid_firebase)
            .subquery()
        )

        certificados_subquery = (
            db.session.query(
                Certificado.docente_uid_firebase,
                func.coalesce(func.sum(Certificado.horas_acredita), 0).label("horas_certificados")
            )
            .filter(Certificado.aceptada == True)
            .group_by(Certificado.docente_uid_firebase)
            .subquery()
        )

        # Subconsulta para horas acreditadas por eventos con acreditaciones aprobadas
        eventos_subquery = (
            db.session.query(
                Inscripcion.docente_uid_firebase,
                func.coalesce(func.sum(Evento.horas), 0).label("horas_eventos")
            )
            .join(Acreditacion, and_(
                Inscripcion.id == Acreditacion.inscripcion_id,
                Acreditacion.aprobo == True
            ))
            .join(Evento, Evento.id == Inscripcion.evento_id)
            .group_by(Inscripcion.docente_uid_firebase)
            .subquery()
        )

        # Consulta principal
        query = db.session.query(
            Docente.uid_firebase,
            Docente.nombres,
            Docente.apellidos,
            Docente.correo,
            Docente.cedula,
            func.array_agg(func.distinct(Facultad.nombre)).label("facultades"),
            func.coalesce(certificados_subquery.c.horas_certificados, 0).label("horas_certificados"),
            func.coalesce(eventos_subquery.c.horas_eventos, 0).label("horas_eventos"),
            (
                func.coalesce(certificados_subquery.c.horas_certificados, 0) + 
                func.coalesce(eventos_subquery.c.horas_eventos, 0)
            ).label("horas_totales")
        ).join(
            DistributivoDocente, Docente.uid_firebase == DistributivoDocente.docente_uid_firebase
        ).join(
            Facultad, DistributivoDocente.facultad_id == Facultad.id_facultad
        ).outerjoin(
            certificados_subquery, Docente.uid_firebase == certificados_subquery.c.docente_uid_firebase
        ).outerjoin(
            eventos_subquery, Docente.uid_firebase == eventos_subquery.c.docente_uid_firebase
        ).filter(
            DistributivoDocente.periodo_lectivo_id == ultimo_distributivo.c.ultimo_periodo
        ).group_by(
            Docente.uid_firebase,
            Docente.nombres,
            Docente.apellidos,
            Docente.correo,
            Docente.cedula,
            certificados_subquery.c.horas_certificados,
            eventos_subquery.c.horas_eventos
        )

        # Aplicar filtros (búsqueda, facultad, horas_min, horas_max)
        if busqueda:
            query = query.filter(
                or_(
                    Docente.nombres.ilike(f"%{busqueda}%"),
                    Docente.apellidos.ilike(f"%{busqueda}%"),
                    Docente.correo.ilike(f"%{busqueda}%"),
                    Docente.cedula.ilike(f"%{busqueda}%")
                )
            )
        if facultad_nombre:
            query = query.having(
                func.array_to_string(func.array_agg(func.distinct(Facultad.nombre)), ',').ilike(f"%{facultad_nombre}%")
            )
        if horas_min is not None:
            query = query.having(
                (
                    func.coalesce(certificados_subquery.c.horas_certificados, 0) + 
                    func.coalesce(eventos_subquery.c.horas_eventos, 0)
                ) >= horas_min
            )
        if horas_max is not None:
            query = query.having(
                (
                    func.coalesce(certificados_subquery.c.horas_certificados, 0) + 
                    func.coalesce(eventos_subquery.c.horas_eventos, 0)
                ) <= horas_max
            )

        # ======== Obtenemos TODOS los resultados (sin paginación) ========
        resultados = query.all()

        # ======== Construimos el archivo Excel con openpyxl ========
        wb = Workbook()
        ws = wb.active
        ws.title = "Docentes Horas"

        # Encabezados
        headers = [
            "Nombres y Apellidos", 
            "Correo",
            "Cédula", 
            "Facultades",
            "Horas por Certificados",
            "Horas por Eventos", 
            "Horas Totales"
        ]
        ws.append(headers)

        # Llenamos las filas con los datos
        for docente in resultados:
            facultades_str = ", ".join(docente.facultades) if docente.facultades else ""
            nombre_completo = (
                f"{docente.nombres} {docente.apellidos}"
                if docente.apellidos
                else docente.nombres
            )
            row_data = [
                nombre_completo,
                docente.correo,
                docente.cedula,
                facultades_str,
                docente.horas_certificados,
                docente.horas_eventos,
                docente.horas_totales
            ]
            ws.append(row_data)

        # (Opcional) Ajustar anchos de columna
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 50
        ws.column_dimensions['E'].width = 20
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 20

        # Guardar el archivo en un objeto BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # ======== Retornar el Excel como adjunto ========
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="reporte_docentes_horas_completo.xlsx"
        )

    except Exception as e:
        app.logger.error(f"Error al generar Excel: {str(e)}")
        return jsonify({
            "estado": False,
            "respuesta": "",
            "error": f"Error al generar Excel: {str(e)}"
        }), 500

@app.route("/reportes/eventos", methods=["GET"])
#@jwt_required()
def obtener_reporte_eventos():
    try:
        # Obtener parámetros de búsqueda y filtrado
        nombre_evento = request.args.get("nombre", type=str)
        tipo_evento = request.args.get("tipo", type=int)
        competencia = request.args.get("competencia", type=str)
        momento = request.args.get("momento", type=str)
        fecha_inicio = request.args.get("fecha_inicio", type=str)
        fecha_fin = request.args.get("fecha_fin", type=str)
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # Construcción de la consulta base
        query = db.session.query(
            Evento.id,
            Evento.nombre,
            Evento.tipo,
            func.min(FechasEvento.fecha).label("primera_fecha"),
            Charla.competencia.label("charla_competencia"),
            Charla.momento.label("charla_momento"),
            Microtalleres.competencia.label("microtaller_competencia"),
            Microtalleres.momento.label("microtaller_momento")
        ).outerjoin(FechasEvento, FechasEvento.evento_id == Evento.id
        ).outerjoin(Charla, Charla.evento_id == Evento.id
        ).outerjoin(Microtalleres, Microtalleres.evento_id == Evento.id
        ).group_by(Evento.id, Charla.competencia, Charla.momento, Microtalleres.competencia, Microtalleres.momento)


        # Aplicar filtros básicos
        if nombre_evento:
            query = query.filter(Evento.nombre.ilike(f"%{nombre_evento}%"))
        if tipo_evento is not None:
            query = query.filter(Evento.tipo == tipo_evento)
        if fecha_inicio and fecha_fin:
            query = query.filter(FechasEvento.fecha.between(fecha_inicio, fecha_fin))

        # Obtener paginación
        total_resultados = query.count()
        eventos = query.limit(per_page).offset((page - 1) * per_page).all()
        total_paginas = (total_resultados // per_page) + (1 if total_resultados % per_page > 0 else 0)

        # Construcción de la respuesta
        resultado_eventos = []

        for evento in eventos:
            if evento.tipo == 1:  # Jornada de Innovación - manejar talleres por separado
                talleres_query = db.session.query(
                    Talleres.id.label("id_taller"),
                    Talleres.nombre.label("nombre_taller"),
                    Talleres.competencia,
                    Talleres.momento,
                    func.count(Inscripcion.id).label("total_inscripciones"),
                    func.count(Acreditacion.id).filter(Acreditacion.aprobo == True).label("inscritos_aprobados"),
                    func.count(Acreditacion.id).filter(Acreditacion.aprobo == False).label("inscritos_no_aprobados")
                ).outerjoin(Inscripcion, Inscripcion.taller_id == Talleres.id
                ).outerjoin(Acreditacion, Acreditacion.inscripcion_id == Inscripcion.id
                ).filter(Talleres.evento_id == evento.id
                ).group_by(Talleres.id)

                # Aplicar filtros de competencia y momento en talleres
                if competencia:
                    talleres_query = talleres_query.filter(Talleres.competencia == competencia)
                if momento:
                    talleres_query = talleres_query.filter(Talleres.momento == momento)

                talleres = talleres_query.all()

                for taller in talleres:
                    resultado_eventos.append({
                        "id": evento.id,
                        "id_taller": taller.id_taller,
                        "nombre": f"{evento.nombre} - {taller.nombre_taller}",
                        "tipo": evento.tipo,
                        "primera_fecha": evento.primera_fecha.strftime("%Y-%m-%d") if evento.primera_fecha else None,
                        "competencia": taller.competencia if taller.competencia else "No aplica",
                        "momento": taller.momento if taller.momento else "No aplica",
                        "total_inscripciones": taller.total_inscripciones,
                        "inscritos_aprobados": taller.inscritos_aprobados if taller.inscritos_aprobados else 0,
                        "inscritos_no_aprobados": taller.inscritos_no_aprobados if taller.inscritos_no_aprobados else 0
                    })
            else:
                # Obtener datos generales del evento
                inscripcion_data = db.session.query(
                    func.count(Inscripcion.id).label("total_inscripciones"),
                    func.count(Acreditacion.id).filter(Acreditacion.aprobo == True).label("inscritos_aprobados"),
                    func.count(Acreditacion.id).filter(Acreditacion.aprobo == False).label("inscritos_no_aprobados")
                ).outerjoin(Acreditacion, Acreditacion.inscripcion_id == Inscripcion.id
                ).filter(Inscripcion.evento_id == evento.id
                ).group_by(Inscripcion.evento_id).first()

                evento_data = {
                    "id": evento.id,
                    "nombre": evento.nombre,
                    "tipo": evento.tipo,
                    "primera_fecha": evento.primera_fecha.strftime("%Y-%m-%d") if evento.primera_fecha else None,
                    "total_inscripciones": inscripcion_data.total_inscripciones if inscripcion_data else 0,
                    "inscritos_aprobados": inscripcion_data.inscritos_aprobados if inscripcion_data else 0,
                    "inscritos_no_aprobados": inscripcion_data.inscritos_no_aprobados if inscripcion_data else 0,
                    "competencia": (
                        evento.charla_competencia if evento.tipo == 2 else
                        evento.microtaller_competencia if evento.tipo == 3 else
                        "No aplica"
                    ),
                    "momento": (
                        evento.charla_momento if evento.tipo == 2 else
                        evento.microtaller_momento if evento.tipo == 3 else
                        "No aplica"
                    )
                }

                resultado_eventos.append(evento_data)

        return jsonify({
            "estado": True,
            "respuesta": resultado_eventos,
            "paginacion": {
                "pagina_actual": page,
                "total_paginas": total_paginas,
                "total_resultados": total_resultados,
                "por_pagina": per_page
            },
            "error": ""
        }), 200

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al obtener eventos: {str(e)}")
        return jsonify({
            "estado": False,
            "respuesta": "",
            "error": f"Error al obtener eventos: {str(e)}"
        }), 500
        
##PENTAGONO
""" 
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


 """

""" @app.route("/eventos/correos_sin_inscripcion", methods=["POST"])
@jwt_required()
def obtener_correos_sin_inscripcion():
    try:
        id_evento = request.form.get('id_evento')
        id_taller = request.form.get('id_taller')  # Si es necesario

        # Verificar si el archivo está en la solicitud
        if 'file' not in request.files:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se encontró ningún archivo en la solicitud",
                    }
                ),
                400,
            )
        
        file = request.files['file']
        
        # Verificar si el archivo tiene un nombre seguro
        if file.filename == '':
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El nombre del archivo no es válido",
                    }
                ),
                400,
            )

        # Guardar el archivo en el servidor
        filename = secure_filename(file.filename)
        file_path = os.path.join("C:\\Users\\diego\\Documents\\DIE\\repo", filename)
        file.save(file_path)

        # Leer el archivo con pandas
        if file_path.endswith('.csv'):
            data = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            data = pd.read_excel(file_path)
        else:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El formato del archivo no es soportado (Se admite .xlsx o .csv).",
                    }
                ),
                400,
            )

        # Verificar si las inscripciones existen basadas en el correo y id_evento/id_taller
        correos_sin_inscripcion = []
        for correo in data['correo']:
            inscripcion = db.session.query(Inscripcion).filter(
                Inscripcion.docente.has(correo=correo),
                Inscripcion.evento_id == id_evento,
                (Inscripcion.taller_id == id_taller if id_taller else True)
            ).first()
            if not inscripcion:
                correos_sin_inscripcion.append(correo)

        # Guardar la lista de correos sin inscripción en un archivo
        output_filename = f'correos_sin_inscripcion_{id_evento}{"_taller_" + id_taller if id_taller else ""}.txt'
        output_path = os.path.join("C:\\Users\\diego\\Documents\\DIE\\repo", output_filename)
        
        with open(output_path, 'w') as output_file:
            for correo in correos_sin_inscripcion:
                output_file.write(f"{correo}\n")

        # Devolver la lista de correos sin inscripción y la ruta del archivo
        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": correos_sin_inscripcion,
                    "archivo": output_path,
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al obtener correos sin inscripción: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener correos sin inscripción: {str(e)}",
                }
            ),
            500,
        )
 """