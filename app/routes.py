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
    Acreditacion,
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
from flask import jsonify, request, abort
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask import send_file
from sqlalchemy.orm import joinedload


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

        # Crear registros en la tabla FechasEvento
        for fecha in fechas:
            nueva_fecha_evento = FechasEvento(
                evento_id=nueva_jornada.id,
                fecha=fecha
            )
            db.session.add(nueva_fecha_evento)

        # Si es de tipo jornada, verificar y crear registros en la tabla Taller
        for taller_data in talleres:
            taller_nombre = taller_data.get("nombre")
            taller_modalidad = taller_data.get("modalidad")
            taller_ubicacion = taller_data.get("ubicacion")
            taller_hora_inicio = taller_data.get("hora_inicio")
            taller_duracion = taller_data.get("duracion")
            taller_ponentes = taller_data.get("ponentes", [])

            if (
                not taller_nombre
                or not taller_modalidad
                or not taller_hora_inicio
                or not taller_ubicacion
                or not taller_duracion
                or not taller_ponentes
            ):
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "Cada taller en 'talleres' debe tener todos los atributos",
                        }
                    ),
                    400,
                )

            nuevo_taller = Talleres(
                nombre=taller_nombre,
                evento_id=nueva_jornada.id,
                modalidad=taller_modalidad,
                ubicacion=taller_ubicacion,
                hora_inicio=taller_hora_inicio,
                duracion=taller_duracion
            )
            db.session.add(nuevo_taller)
            db.session.flush()
            
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
            db.session.query(FechasEvento).filter_by(evento_id=jornada.id).delete()
            for fecha in datos_jornada['fechas']:
                db.session.add(FechasEvento(evento_id=jornada.id, fecha=fecha))

        if "talleres" in datos_jornada:
            
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
                db.session.add(nuevo_ponente)
                
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
        if evento is None or evento.tipo!=1:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No existe la Jornada de Innovacion requerida",
                    }
                ),
                400,
            )
        
        # Obtener datos del JSON de la solicitud
        datos_taller = request.json
        nombre = datos_taller.get("nombre")
        ponentes = datos_taller.get("ponentes", [])
        modalidad = datos_taller.get("modalidad")
        ubicacion = datos_taller.get("ubicacion")
        hora_inicio = datos_taller.get("hora_inicio")
        duracion = datos_taller.get("duracion")

        # Verificar la presencia de atributos obligatorios
        campos_faltantes = []
        if not nombre:
            campos_faltantes.append("nombre")
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

        # Crear registro en la tabla Talleres
        nuevo_taller = Talleres(
            evento_id=evento_id,
            modalidad=modalidad,
            nombre=nombre,
            ubicacion=ubicacion,
            duracion=duracion,
            hora_inicio=hora_inicio,
        )

        db.session.add(nuevo_taller)
        db.session.flush()  # Esto es importante para obtener el id de la nueva jornada antes de commit.

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
        if 'modalidad' in datos_taller:
            taller.modalidad = datos_taller['modalidad']
        if 'ubicacion' in datos_taller:
            taller.ubicacion = datos_taller['ubicacion']
        if 'hora_inicio' in datos_taller:
            taller.hora_inicio = datos_taller['hora_inicio']
        if 'duracion' in datos_taller:
            taller.duracion = datos_taller['duracion']

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
                "fechas": [fecha.fecha.strftime('%Y-%m-%d') for fecha in evento.fechasevento]
            }

            if evento.tipo == 1:  # Jornada
                evento_info["talleres"] = [
                    {
                        "id": taller.id,
                        "nombre": taller.nombre,
                        "modalidad": taller.modalidad,
                        "ubicacion": taller.ubicacion,
                        "hora_inicio": taller.hora_inicio.strftime('%H:%M'),
                        "duracion": taller.duracion,
                        "ponentes": [ponente.nombre for ponente in taller.talleres_ponentes]
                    }
                    for taller in evento.talleres
                ]
                
            elif evento.tipo == 2:  # Charla
                charla = evento.charla
                evento_info.update({
                    "hora_inicio": charla.hora_inicio.strftime('%H:%M'),
                    "duracion": charla.duracion,
                    "modalidad": charla.modalidad,
                    "ubicacion": charla.ubicacion,
                    "ponentes": [
                        {
                            "nombre": charla_ponente.nombre,
                            "titulo_charla": charla_ponente.titulo_charla
                        } for charla_ponente in charla.charlas_ponentes
                    ]
                })

            elif evento.tipo == 3:  # Microtaller
                microtaller = evento.microtaller
                evento_info.update({
                    "hora_inicio": microtaller.hora_inicio.strftime('%H:%M'),
                    "duracion": microtaller.duracion,
                    "modalidad": microtaller.modalidad,
                    "ubicacion": microtaller.ubicacion,
                    "ponentes": [ponente.nombre for ponente in microtaller.microtalleres_ponentes]
                })

            elif evento.tipo == 4:  # Observación Áulica
                evento_info["horarios"] = [
                    {
                        "dia_semana": horario.dia_semana,
                        "hora_inicio": horario.hora_inicio.strftime('%H:%M'),
                        "hora_fin": horario.hora_fin.strftime('%H:%M')
                    } for horario in evento.horariosdisponibles
                ]

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
            "fechas": [fecha.fecha.strftime('%Y-%m-%d') for fecha in evento.fechasevento]
        }

        # Depending on the type of event, additional details are included
        if evento.tipo == 1:  # Jornada
            evento_info["talleres"] = [
                {
                    "id":taller.id,
                    "nombre": taller.nombre,
                    "modalidad": taller.modalidad,
                    "ubicacion": taller.ubicacion,
                    "hora_inicio": taller.hora_inicio.strftime('%H:%M'),
                    "duracion": taller.duracion,
                    "ponentes": [ponente.nombre for ponente in taller.talleres_ponentes]
                }
                for taller in evento.talleres
            ]
        elif evento.tipo == 2:  # Charla
            charla = evento.charla
            evento_info.update({
                "hora_inicio": charla.hora_inicio.strftime('%H:%M'),
                "duracion": charla.duracion,
                "modalidad": charla.modalidad,
                "ubicacion": charla.ubicacion,
                "ponentes": [
                    {
                        "nombre": charla_ponente.nombre,
                        "titulo_charla": charla_ponente.titulo_charla
                    } for charla_ponente in charla.charlas_ponentes
                ]
            })
        elif evento.tipo == 3:  # Microtaller
            microtaller = evento.microtaller
            evento_info.update({
                "hora_inicio": microtaller.hora_inicio.strftime('%H:%M'),
                "duracion": microtaller.duracion,
                "modalidad": microtaller.modalidad,
                "ubicacion": microtaller.ubicacion,
                "ponentes": [ponente.nombre for ponente in microtaller.microtalleres_ponentes]
            })
        elif evento.tipo == 4:  # Observación Áulica
            evento_info["horarios"] = [
                {
                    "dia_semana": horario.dia_semana,
                    "hora_inicio": horario.hora_inicio.strftime('%H:%M'),
                    "hora_fin": horario.hora_fin.strftime('%H:%M')
                } for horario in evento.horariosdisponibles
            ]

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

        if evento.tipo == 1:
            # Encontrar todos los talleres asociados con este evento
            talleres = db.session.query(Talleres).filter_by(evento_id=evento.id).all()
            # Recorrer todos los talleres encontrados y eliminar los TalleresPonente relacionados
            for taller in talleres:
                # Eliminar TalleresPonente relacionados con este taller
                db.session.query(TalleresPonente).filter_by(taller_id=taller.id).delete()
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
        db.session.query(FechasEvento).filter_by(evento_id=evento.id).delete()
        db.session.query(Inscripcion).filter_by(evento_id=evento.id).delete()
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

@app.route("/actualizar_inscripcion/<int:id_inscripcion>", methods=["PUT"])
# @jwt_required()
def actualizar_inscripcion(id_inscripcion):
    try:
        # Obtener el nuevo valor para isaccepted desde el cuerpo de la solicitud
        datos = request.get_json()
        nuevo_isaccepted = datos.get("isaccepted")

        # Validar que se proporcionó el nuevo valor de isaccepted
        if nuevo_isaccepted is None:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El valor 'isaccepted' no está presente",
                    }
                ),
                400,
            )

        # Buscar la inscripción por su ID
        inscripcion = Inscripcion.query.get(id_inscripcion)
        if not inscripcion:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Inscripción no encontrada",
                    }
                ),
                404,
            )

        # Actualizar el campo isaccepted
        inscripcion.isaccepted = nuevo_isaccepted
        db.session.commit()

        # Manejar los registros en Asistencia dependiendo del valor de isaccepted
        if nuevo_isaccepted and not inscripcion.isaccepted:
            nueva_acreditacion = Acreditacion(
                id_inscripcion=id_inscripcion,
                asistencia=False,
                aprobado=False,
                observacion="",
            )
            db.session.add(nueva_acreditacion)
            # Crear registros en Asistencia
            capacitacion = Capacitacion.query.get(inscripcion.id_capacitacion)
            for fecha in capacitacion.fechas:
                nueva_asistencia = Asistencia(
                    asiste_entrada=False,
                    asiste_salida=False,
                    fecha=fecha,
                    id_inscripcion=id_inscripcion,
                )
                db.session.add(nueva_asistencia)
        elif inscripcion.isaccepted and not nuevo_isaccepted:
            # Eliminar registros en Asistencia
            Asistencia.query.filter_by(id_inscripcion=id_inscripcion).delete()
            Acreditacion.query.filter_by(id_inscripcion=id_inscripcion).delete()

        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Inscripción actualizada con éxito",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al actualizar la inscripción: {str(e)}")
        db.session.rollback()  # Hacer rollback en caso de error
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al actualizar la inscripción: {str(e)}",
                }
            ),
            500,
        )

@app.route("/docentes_disponibles/<int:id_capacitacion>", methods=["GET"])
def docentes_disponibles(id_capacitacion):
    try:
        # Obtener todos los docentes
        todos_los_docentes = Docente.query.all()

        # Obtener los ID de los docentes que tienen inscripción en la capacitación
        docentes_inscritos_en_capacitacion = {
            inscripcion.id_docente
            for inscripcion in Inscripcion.query.filter_by(
                id_capacitacion=id_capacitacion
            )
        }

        # Filtrar los docentes que no están inscritos en la capacitación
        docentes_disponibles = [
            docente
            for docente in todos_los_docentes
            if docente.uid_firebase not in docentes_inscritos_en_capacitacion
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

@app.route("/agregar_inscripciones", methods=["POST"])
def agregar_inscripciones():
    try:
        datos = request.get_json()
        id_capacitacion = datos.get("id_capacitacion")
        ids_docentes = datos.get("ids_docentes")  # Un array de IDs de docentes
        id_taller = datos.get("id_taller")

        if not id_capacitacion or not ids_docentes:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "La capacitación y los docentes son campos obligatorios",
                    }
                ),
                400,
            )

        # Obtener la capacitación
        capacitacion = Capacitacion.query.get(id_capacitacion)
        if not capacitacion:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Capacitación no encontrada",
                    }
                ),
                404,
            )

        # Validación para capacitaciones de tipo jornada
        if not id_taller and capacitacion.tipo == "jornada":
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Se requiere un taller para inscripciones en capacitaciones de tipo jornada",
                    }
                ),
                400,
            )

        if id_taller:
            taller = Taller.query.filter_by(
                id_taller=id_taller, id_capacitacion=id_capacitacion
            ).first()
            if not taller:
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "El taller proporcionado no pertenece a la capacitación indicada",
                        }
                    ),
                    400,
                )

        for id_docente in ids_docentes:
            # Verificar si ya existe una inscripción
            inscripcion_existente = Inscripcion.query.filter_by(
                id_capacitacion=id_capacitacion, id_docente=id_docente
            ).first()
            if inscripcion_existente:
                continue  # Saltar este docente si ya está inscrito
            nueva_inscripcion = Inscripcion(
                id_capacitacion=id_capacitacion,
                id_taller=id_taller if id_taller else None,
                id_docente=id_docente,
                isaccepted=True,
            )
            db.session.add(nueva_inscripcion)
            db.session.commit()  # Hacer commit después de cada inscripción

            capacitacion = Capacitacion.query.get(id_capacitacion)
            if capacitacion:
                nueva_acreditacion = Acreditacion(
                    id_inscripcion=nueva_inscripcion.id_inscripcion,
                    asistencia=False,
                    aprobado=False,
                    observacion="",
                )
                db.session.add(nueva_acreditacion)
                for fecha in capacitacion.fechas:
                    nueva_asistencia = Asistencia(
                        asiste_entrada=False,
                        asiste_salida=False,
                        fecha=fecha,
                        id_inscripcion=nueva_inscripcion.id_inscripcion,
                    )
                    db.session.add(nueva_asistencia)
                db.session.commit()  # Hacer commit después de agregar asistencias

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Inscripciones y asistencias agregadas exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error al agregar inscripciones: {str(e)}")
        db.session.rollback()  # Hacer rollback en caso de error
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al agregar inscripciones: {str(e)}",
                }
            ),
            500,
        )

@app.route("/eliminar_inscripcion/<int:id_inscripcion>", methods=["DELETE"])
# @jwt_required()
def eliminar_inscripcion(id_inscripcion):
    try:
        # Obtener la capacitación existente
        inscripcion = Inscripcion.query.get(id_inscripcion)

        if not inscripcion:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Inscripcion no encontrada",
                    }
                ),
                404,
            )

        # Eliminar la capacitación de la base de datos
        db.session.delete(inscripcion)
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Inscripcion eliminada exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al eliminar inscripcion: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al eliminar inscripcion: {str(e)}",
                }
            ),
            500,
        )
