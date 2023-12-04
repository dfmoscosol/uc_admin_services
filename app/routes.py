from app import app, db, jwt
import os
from app.models import (
    Capacitacion,
    Usuario,
    Taller,
    TermsCompetenciaPedagogica,
    TermsCompetenciaComunicativa,
    TermsCompetenciaTecnologica,
    TermsCompetenciaInvestigativa,
    TermsCompetenciaGestion,
    Acreditacion,
    Asistencia,
    Carrera,
    Certificados,
    Cursos,
    Docente,
    Encuesta,
    Facultad,
    Inscripcion,
    Periodo,
    Pregunta,
    Puntuacion,
    Resultado,
    Universidad,
)
from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask import send_file

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


@app.route("/crear_capacitacion", methods=["POST"])
# @jwt_required()
def crear_capacitacion():
    try:
        # Obtener datos del JSON de la solicitud
        datos_capacitacion = request.json
        nombre = datos_capacitacion.get("nombre")
        horas = datos_capacitacion.get("horas")
        tipo = datos_capacitacion.get("tipo")
        fechas = datos_capacitacion.get("fechas", [])
        nombre_tutor = datos_capacitacion.get("nombre_tutor")
        allow_inscripcion = datos_capacitacion.get("allow_inscripcion")
        allow_asistencia_entrada = datos_capacitacion.get("allow_asistencia_entrada")
        allow_asistencia_salida = datos_capacitacion.get("allow_asistencia_salida")
        presencial = datos_capacitacion.get("presencial")
        direccion = datos_capacitacion.get("direccion")
        cupo = datos_capacitacion.get("cupo")
        talleres = datos_capacitacion.get("talleres", [])

        # Verificar la presencia de atributos obligatorios
        if (
            not nombre
            or not horas
            or not tipo
            or allow_inscripcion is None
            or allow_asistencia_entrada is None
            or allow_asistencia_salida is None
            or not fechas
            or not nombre_tutor
            or not cupo
        ):
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Todos los atributos son obligatorios",
                    }
                ),
                400,
            )

        if tipo == "jornada":
            if not talleres:
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "El atributo 'talleres' no puede estar vacío en una jornada",
                        }
                    ),
                    400,
                )
        else:
            if talleres:
                return (
                    jsonify(
                        {
                            "estado": False,
                            "respuesta": "",
                            "error": "El atributo 'talleres' debe estar vacío si no es una jornada",
                        }
                    ),
                    400,
                )

        # Crear registro en la tabla Capacitacion
        nueva_capacitacion = Capacitacion(
            nombre=nombre,
            horas=horas,
            tipo=tipo,
            fechas=fechas,
            nombre_tutor=nombre_tutor,
            allow_inscripcion=allow_inscripcion,
            allow_asistencia_entrada=allow_asistencia_entrada,
            allow_asistencia_salida=allow_asistencia_salida,
            presencial=presencial,
            direccion=direccion,
            cupo=cupo,
        )

        db.session.add(nueva_capacitacion)
        db.session.commit()

        # Si es de tipo jornada, verificar y crear registros en la tabla Taller
        if tipo == "jornada" and talleres:
            for taller_data in talleres:
                taller_nombre = taller_data.get("nombre")
                if not taller_nombre:
                    return (
                        jsonify(
                            {
                                "estado": False,
                                "respuesta": "",
                                "error": "Cada taller en 'talleres' debe tener el atributo 'nombre'",
                            }
                        ),
                        400,
                    )

                nuevo_taller = Taller(
                    nombre=taller_nombre,
                    id_capacitacion=nueva_capacitacion.id_capacitacion,
                )
                db.session.add(nuevo_taller)
            db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Capacitación creada exitosamente",
                    "error": "",
                }
            ),
            201,
        )

    except Exception as e:
        app.logger.error(f"Error al crear capacitación: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al crear capacitación: {str(e)}",
                }
            ),
            500,
        )


@app.route("/capacitaciones", methods=["GET"])
# @jwt_required()
def get_capacitaciones():
    try:
        # Obtener todas las capacitaciones de la base de datos
        capacitaciones = Capacitacion.query.all()

        # Ordenar las capacitaciones
        capacitaciones_ordenadas = sorted(
            capacitaciones,
            key=lambda capacitacion: capacitacion.id_capacitacion,
            reverse=True,
        )

        # Lista para almacenar la información a devolver
        lista_capacitaciones = []

        # Iterar sobre las capacitaciones ordenadas
        for capacitacion in capacitaciones_ordenadas:
            # Obtener los talleres si la capacitación es de tipo "jornada"
            talleres = []
            if capacitacion.tipo == "jornada":
                talleres_db = Taller.query.filter_by(
                    id_capacitacion=capacitacion.id_capacitacion
                ).all()
                talleres = [
                    {"id_taller": taller.id_taller, "nombre": taller.nombre}
                    for taller in talleres_db
                ]

            # Formatear las fechas en 'dd/mm/aaaa'
            fechas_formateadas = [
                fecha.strftime("%d-%m-%Y") for fecha in capacitacion.fechas
            ]

            # Construir el diccionario de capacitación
            capacitacion_dict = {
                "id_capacitacion": capacitacion.id_capacitacion,
                "nombre": capacitacion.nombre,
                "horas": capacitacion.horas,
                "tipo": capacitacion.tipo,
                "fechas": fechas_formateadas,
                "nombre_tutor": capacitacion.nombre_tutor,
                "allow_inscripcion": capacitacion.allow_inscripcion,
                "allow_asistencia_entrada": capacitacion.allow_asistencia_entrada,
                "allow_asistencia_salida": capacitacion.allow_asistencia_salida,
                "presencial": capacitacion.presencial,
                "direccion": capacitacion.direccion,
                "cupo": capacitacion.cupo,
            }

            # Agregar el atributo "talleres" solo si la capacitación es de tipo "jornada"
            if capacitacion.tipo == "jornada":
                capacitacion_dict["talleres"] = talleres

            # Agregar la capacitación a la lista
            lista_capacitaciones.append(capacitacion_dict)

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": {"capacitaciones": lista_capacitaciones},
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al obtener capacitaciones: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener capacitaciones: {str(e)}",
                }
            ),
            500,
        )


@app.route("/capacitacion/<int:capacitacion_id>", methods=["GET"])
# @jwt_required()
def obtener_capacitacion(capacitacion_id):
    try:
        # Obtener la capacitación por ID
        capacitacion = Capacitacion.query.get(capacitacion_id)

        # Verificar si la capacitación existe
        if not capacitacion:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se encontró la capacitación especificada",
                    }
                ),
                404,
            )

        fechas_formateadas = [
            fecha.strftime("%d-%m-%Y") for fecha in capacitacion.fechas
        ]

        # Obtener todos los datos de la capacitación
        datos_capacitacion = {
            "id_capacitacion": capacitacion.id_capacitacion,
            "nombre": capacitacion.nombre,
            "horas": capacitacion.horas,
            "tipo": capacitacion.tipo,
            "fechas": fechas_formateadas,
            "nombre_tutor": capacitacion.nombre_tutor,
            "allow_inscripcion": capacitacion.allow_inscripcion,
            "allow_asistencia_entrada": capacitacion.allow_asistencia_entrada,
            "allow_asistencia_salida": capacitacion.allow_asistencia_salida,
            "presencial": capacitacion.presencial,
            "direccion": capacitacion.direccion,
            "cupo": capacitacion.cupo,
        }

        # Si es de tipo jornada, obtener los talleres asociados
        if capacitacion.tipo == "jornada":
            talleres = Taller.query.filter_by(
                id_capacitacion=capacitacion.id_capacitacion
            ).all()
            datos_talleres = [
                {"nombre": taller.nombre, "id_taller": taller.id_taller}
                for taller in talleres
            ]
            datos_capacitacion["talleres"] = datos_talleres

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": {"capacitacion": datos_capacitacion},
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al obtener capacitación: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener capacitación {str(e)}",
                }
            ),
            500,
        )


@app.route("/actualizar_capacitacion/<int:id_capacitacion>", methods=["PUT"])
# @jwt_required()
def actualizar_capacitacion(id_capacitacion):
    try:
        # Obtener la capacitación existente
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

        # Obtener datos del JSON de la solicitud
        datos_actualizacion = request.json

        # Verificar si se están actualizando atributos no permitidos
        atributos_permitidos = [
            "nombre",
            "horas",
            "tipo",
            "fechas",
            "nombre_tutor",
            "allow_inscripcion",
            "allow_asistencia_entrada",
            "allow_asistencia_salida",
            "talleres",
            "presencial",
            "direccion",
            "cupo",
        ]
        atributos_invalidos = [
            atributo
            for atributo in datos_actualizacion.keys()
            if atributo not in atributos_permitidos
        ]

        if atributos_invalidos:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": f"Atributos no permitidos: {', '.join(atributos_invalidos)}",
                    }
                ),
                400,
            )

        tipo = datos_actualizacion.get("tipo")
        talleres = datos_actualizacion.get("talleres")

        # Verificar la actualización del tipo y talleres
        if tipo and tipo != capacitacion.tipo:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se permite actualizar el tipo de capacitación",
                    }
                ),
                400,
            )

        if tipo == "jornada" and talleres:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "No se permite actualizar 'talleres' para una jornada existente",
                    }
                ),
                400,
            )
        if 'fechas' in datos_actualizacion:
            nuevas_fechas = datos_actualizacion['fechas']

            # Eliminar registros de asistencia antiguos
            inscripciones = Inscripcion.query.filter_by(id_capacitacion=id_capacitacion).all()
            for inscripcion in inscripciones:
                Asistencia.query.filter_by(id_inscripcion=inscripcion.id_inscripcion).delete()

            # Crear nuevos registros de asistencia
            for inscripcion in inscripciones:
                for fecha in nuevas_fechas:
                    nueva_asistencia = Asistencia(
                        asiste_entrada=False, 
                        asiste_salida=False, 
                        fecha=fecha, 
                        id_inscripcion=inscripcion.id_inscripcion
                    )
                    db.session.add(nueva_asistencia)

        capacitacion.nombre = datos_actualizacion.get("nombre", capacitacion.nombre)
        capacitacion.horas = datos_actualizacion.get("horas", capacitacion.horas)
        capacitacion.fechas = datos_actualizacion.get("fechas", capacitacion.fechas)
        capacitacion.cupo = datos_actualizacion.get("cupo", capacitacion.cupo)
        capacitacion.nombre_tutor = datos_actualizacion.get(
            "nombre_tutor", capacitacion.nombre_tutor
        )
        capacitacion.allow_inscripcion = datos_actualizacion.get(
            "allow_inscripcion", capacitacion.allow_inscripcion
        )
        capacitacion.allow_asistencia_entrada = datos_actualizacion.get(
            "allow_asistencia_entrada", capacitacion.allow_asistencia_entrada
        )
        capacitacion.allow_asistencia_salida = datos_actualizacion.get(
            "allow_asistencia_salida", capacitacion.allow_asistencia_salida
        )
        capacitacion.presencial = datos_actualizacion.get(
            "presencial", capacitacion.presencial
        )
        capacitacion.direccion = datos_actualizacion.get(
            "direccion", capacitacion.direccion
        )

        # Actualizar la base de datos
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Capacitación actualizada exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al actualizar capacitación: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al obtener capacitaciones: {str(e)}",
                }
            ),
            500,
        )


@app.route("/eliminar_capacitacion/<int:id_capacitacion>", methods=["DELETE"])
# @jwt_required()
def eliminar_capacitacion(id_capacitacion):
    try:
        # Obtener la capacitación existente
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

        # Eliminar la capacitación de la base de datos
        db.session.delete(capacitacion)
        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Capacitación eliminada exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al eliminar capacitación: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al eliminar capacitación: {str(e)}",
                }
            ),
            500,
        )


@app.route("/crear_taller", methods=["POST"])
# @jwt_required()
def crear_taller():
    try:
        # Obtener datos del JSON de la solicitud
        datos_taller = request.json
        nombre = datos_taller.get("nombre")
        id_capacitacion = datos_taller.get("id_capacitacion")

        # Verificar la presencia de atributos obligatorios
        if not nombre or not id_capacitacion:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Los atributos 'nombre' y 'capacitacion_id' son obligatorios",
                    }
                ),
                400,
            )

        # Verificar si la capacitación es de tipo jornada
        capacitacion = Capacitacion.query.get(id_capacitacion)
        if not capacitacion or capacitacion.tipo != "jornada":
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Solo se pueden agregar talleres a capacitaciones de tipo jornada",
                    }
                ),
                400,
            )

        # Crear registro en la tabla Taller
        nuevo_taller = Taller(nombre=nombre, id_capacitacion=id_capacitacion)

        db.session.add(nuevo_taller)
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
        # Capturar errores y devolver un mensaje de error
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


@app.route("/actualizar_taller/<int:taller_id>", methods=["PUT"])
# @jwt_required()
def actualizar_taller(taller_id):
    try:
        # Obtener datos del JSON de la solicitud
        datos_taller = request.json
        nuevo_nombre = datos_taller.get("nombre")

        # Verificar la presencia del nuevo nombre
        if not nuevo_nombre:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El atributo 'nombre' es obligatorio para la actualización",
                    }
                ),
                400,
            )

        atributos_permitidos = ["nombre"]
        atributos_invalidos = [
            atributo
            for atributo in datos_taller.keys()
            if atributo not in atributos_permitidos
        ]

        if atributos_invalidos:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": f"Atributos no permitidos: {', '.join(atributos_invalidos)}",
                    }
                ),
                400,
            )
        # Obtener el taller a actualizar
        taller = Taller.query.get(taller_id)

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

        # Actualizar el nombre del taller
        taller.nombre = nuevo_nombre

        db.session.commit()

        return (
            jsonify(
                {
                    "estado": True,
                    "respuesta": "Taller actualizado exitosamente",
                    "error": "",
                }
            ),
            200,
        )

    except Exception as e:
        # Capturar errores y devolver un mensaje de error
        app.logger.error(f"Error al actualizar taller: {str(e)}")
        return (
            jsonify(
                {
                    "estado": False,
                    "respuesta": "",
                    "error": f"Error al actualizar taller: {str(e)}",
                }
            ),
            500,
        )


@app.route("/eliminar_taller/<int:taller_id>", methods=["DELETE"])
# @jwt_required()
def eliminar_taller(taller_id):
    try:
        # Obtener el taller a eliminar
        taller = Taller.query.get(taller_id)

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
        if nuevo_estado is not None:
            termino.isapproved = nuevo_estado
            db.session.commit()

            return (
                jsonify(
                    {
                        "estado": True,
                        "respuesta": "Estado del término actualizado exitosamente",
                        "error": "",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "El parámetro 'isapproved' es requerido",
                    }
                ),
                400,
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
#@jwt_required()
def obtener_certificados():
    try:
        # Realizar la consulta uniendo las tablas Certificado y Curso
        certificados = (
            db.session.query(Certificados, Cursos)
            .join(Cursos, Certificados.id_curso == Cursos.id_curso)
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
            jsonify({"estado": True, "respuesta": {"certificados":datos_certificados}, "error": ""}),
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
#@jwt_required()
def descargar_certificado(id_certificado):
    try:
        certificado = Certificados.query.get(id_certificado)

        if certificado:
            path_to_file = certificado.path_to_file
            print(path_to_file)
            if os.path.exists(path_to_file):
                return send_file(path_to_file, as_attachment=True)
            else:
                return jsonify({"estado": False, "respuesta": "", "error": "Archivo no encontrado"}), 404
        else:    
            return jsonify({"estado": False, "respuesta": "", "error": "Certificado no encontrado"}), 404

    except Exception as e:
        app.logger.error(f"Error al descargar el certificado: {str(e)}")
        return jsonify({"estado": False, "respuesta": "", "error": f"Error al descargar el certificado: {str(e)}"}), 500
    
@app.route("/actualizar_certificado/<int:id_certificado>", methods=["PUT"])
#@jwt_required()
def actualizar_certificado(id_certificado):

    try:
        # Obtener el nuevo valor para isapproved desde el cuerpo de la solicitud
        datos = request.get_json()
        nuevo_isapproved = datos.get('isapproved')

        # Validar que se proporcionó el nuevo valor de isapproved
        if nuevo_isapproved is None:
            return jsonify({"estado": False, "respuesta": "", "error": "El valor 'isapproved' no está presente"}), 400

        # Buscar el certificado por su ID
        certificado = Certificados.query.get(id_certificado)
        if not certificado:
            return jsonify({"estado": False, "respuesta": "", "error": "Certificado no encontrado"}), 404

        # Actualizar el campo isapproved
        certificado.isapproved = nuevo_isapproved
        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Certificado actualizado con éxito", "error": ""}), 200

    except Exception as e:
        app.logger.error(f"Error al actualizar el certificado: {str(e)}")
        return jsonify({"estado": False, "respuesta": "", "error": f"Error al actualizar el certificado: {str(e)}"}), 500
    
@app.route("/actualizar_inscripcion/<int:id_inscripcion>", methods=["PUT"])
#@jwt_required()
def actualizar_inscripcion(id_inscripcion):
    try:
        # Obtener el nuevo valor para isaccepted desde el cuerpo de la solicitud
        datos = request.get_json()
        nuevo_isaccepted = datos.get('isaccepted')

        # Validar que se proporcionó el nuevo valor de isaccepted
        if nuevo_isaccepted is None:
            return jsonify({"estado": False, "respuesta": "", "error": "El valor 'isaccepted' no está presente"}), 400

        # Buscar la inscripción por su ID
        inscripcion = Inscripcion.query.get(id_inscripcion)
        if not inscripcion:
            return jsonify({"estado": False, "respuesta": "", "error": "Inscripción no encontrada"}), 404

        # Actualizar el campo isaccepted
        inscripcion.isaccepted = nuevo_isaccepted
        db.session.commit()

        # Manejar los registros en Asistencia dependiendo del valor de isaccepted
        if nuevo_isaccepted:
            # Crear registros en Asistencia
            capacitacion = Capacitacion.query.get(inscripcion.id_capacitacion)
            for fecha in capacitacion.fechas:
                nueva_asistencia = Asistencia(asiste_entrada=False, asiste_salida=False, fecha=fecha, id_inscripcion=id_inscripcion)
                db.session.add(nueva_asistencia)
        else:
            # Eliminar registros en Asistencia
            Asistencia.query.filter_by(id_inscripcion=id_inscripcion).delete()

        db.session.commit()

        return jsonify({"estado": True, "respuesta": "Inscripción actualizada con éxito", "error": ""}), 200

    except Exception as e:
        app.logger.error(f"Error al actualizar la inscripción: {str(e)}")
        return jsonify({"estado": False, "respuesta": "", "error": f"Error al actualizar la inscripción: {str(e)}"}), 500



