from app import app, db, jwt
from app.models import Capacitacion, Usuario, Taller
from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, JWTManager
from flask_bcrypt import generate_password_hash, check_password_hash


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"estado": False, "respuesta": "", "error": "Token inválido"}), 401


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
@jwt_required()
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
        allow_asistencia = datos_capacitacion.get("allow_asistencia")
        talleres = datos_capacitacion.get("talleres", [])

        # Verificar la presencia de atributos obligatorios
        print(not nombre)
        print(not horas)
        print(not horas)
        print(not tipo)
        print(allow_inscripcion is None)
        print(allow_asistencia is None)
        print(not fechas)
        print(not nombre_tutor)
        if (
            not nombre
            or not horas
            or not tipo
            or allow_inscripcion is None
            or allow_asistencia is None
            or not fechas
            or not nombre_tutor
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

        if tipo == "Jornada":
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
            allow_asistencia=allow_asistencia,
        )

        db.session.add(nueva_capacitacion)
        db.session.commit()

        # Si es de tipo Jornada, verificar y crear registros en la tabla Taller
        if tipo == "Jornada" and talleres:
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
@jwt_required()
def get_capacitaciones():
    try:
        # Obtener todas las capacitaciones de la base de datos
        capacitaciones = Capacitacion.query.all()
        # Lista para almacenar la información a devolver
        lista_capacitaciones = []

        # Iterar sobre las capacitaciones
        for capacitacion in capacitaciones:
            # Obtener los talleres si la capacitación es de tipo "Jornada"
            talleres = []
            if capacitacion.tipo == "Jornada":
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
            }

            # Agregar el atributo "talleres" solo si la capacitación es de tipo "Jornada"
            if capacitacion.tipo == "Jornada":
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


@app.route("/actualizar_capacitacion/<int:id_capacitacion>", methods=["PUT"])
@jwt_required()
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
            "allow_asistencia",
            "talleres",
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

        if tipo == "Jornada" and talleres:
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

        # Actualizar otros atributos según sea necesario
        capacitacion.nombre = datos_actualizacion.get("nombre", capacitacion.nombre)
        capacitacion.horas = datos_actualizacion.get("horas", capacitacion.horas)
        capacitacion.fechas = datos_actualizacion.get("fechas", capacitacion.fechas)
        capacitacion.nombre_tutor = datos_actualizacion.get(
            "nombre_tutor", capacitacion.nombre_tutor
        )
        capacitacion.allow_inscripcion = datos_actualizacion.get(
            "allow_inscripcion", capacitacion.allow_inscripcion
        )
        capacitacion.allow_asistencia = datos_actualizacion.get(
            "allow_asistencia", capacitacion.allow_asistencia
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
@jwt_required()
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
@jwt_required()
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

        # Verificar si la capacitación es de tipo Jornada
        capacitacion = Capacitacion.query.get(id_capacitacion)
        if not capacitacion or capacitacion.tipo != "Jornada":
            return (
                jsonify(
                    {
                        "estado": False,
                        "respuesta": "",
                        "error": "Solo se pueden agregar talleres a capacitaciones de tipo Jornada",
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
@jwt_required()
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
@jwt_required()
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
