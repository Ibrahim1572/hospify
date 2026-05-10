"""
backend/app/__init__.py — Flask application factory
"""
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from .config import Config

jwt = JWTManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensions
    jwt.init_app(app)
    CORS(app, supports_credentials=True, origins=app.config["CORS_ORIGINS"])

    # Register blueprints
    from .auth.routes        import auth_bp
    from .patients.routes    import patients_bp
    from .wards.routes       import wards_bp
    from .admissions.routes  import admissions_bp
    from .doctors.routes     import doctors_bp
    from .nurses.routes      import nurses_bp
    from .lab.routes         import lab_bp
    from .pharmacy.routes    import pharmacy_bp
    from .billing.routes     import billing_bp
    from .media.routes       import media_bp
    from .firebase_sync.routes import firebase_sync_bp
    from .admin.routes       import admin_bp

    app.register_blueprint(auth_bp,          url_prefix="/api/auth")
    app.register_blueprint(patients_bp,      url_prefix="/api/patients")
    app.register_blueprint(wards_bp,         url_prefix="/api/wards")
    app.register_blueprint(admissions_bp,    url_prefix="/api/admissions")
    app.register_blueprint(doctors_bp,       url_prefix="/api/doctors")
    app.register_blueprint(nurses_bp,        url_prefix="/api/nurses")
    app.register_blueprint(lab_bp,           url_prefix="/api/lab")
    app.register_blueprint(pharmacy_bp,      url_prefix="/api/pharmacy")
    app.register_blueprint(billing_bp,       url_prefix="/api/billing")
    app.register_blueprint(media_bp,         url_prefix="/api/media")
    app.register_blueprint(firebase_sync_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_bp,         url_prefix="/api/admin")

    # Init DB pool and Firebase inside app context
    from . import db as db_module, firebase as fb_module
    with app.app_context():
        db_module.init_app(app)
        fb_module.init_firebase(app)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}, 200

    return app
