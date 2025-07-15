from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 Not Found: {request.url}")
        return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(400)
    def bad_request_error(error):
        logger.warning(f"400 Bad Request: {request.url} - {error.description}")
        return jsonify({"message": f"Bad request: {error.description}"}), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        logger.warning(f"401 Unauthorized: {request.url} - {error.description}")
        return jsonify({"message": f"Unauthorized: {error.description}"}), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        logger.warning(f"403 Forbidden: {request.url} - {error.description}")
        return jsonify({"message": f"Forbidden: {error.description}"}), 403

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 Internal Server Error: {request.url} - {error}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500