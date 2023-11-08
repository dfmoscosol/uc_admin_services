from app import app, db
from app.models import Capacitacion
from flask import request, jsonify

@app.route('/capacitaciones', methods=['GET'])
def get_capacitaciones():
    capacitaciones = Capacitacion.query.all()
    return jsonify([capacitacion.__dict__ for capacitacion in capacitaciones])
