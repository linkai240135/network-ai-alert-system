from flask import jsonify


def success(data=None, message="ok", status=200):
    return jsonify({"code": 0, "message": message, "data": data or {}}), status


def failure(message="error", status=400):
    return jsonify({"code": 1, "message": message, "data": {}}), status
