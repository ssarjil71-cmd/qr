from flask import has_app_context
from flask_mysqldb import MySQL

mysql = MySQL()


def mysql_init(app):
    app.config['MYSQL_HOST'] = app.config.get('MYSQL_HOST')
    app.config['MYSQL_USER'] = app.config.get('MYSQL_USER')
    app.config['MYSQL_PASSWORD'] = app.config.get('MYSQL_PASSWORD')
    app.config['MYSQL_DB'] = app.config.get('MYSQL_DB')
    mysql.init_app(app)


def get_db():
    return mysql


def get_conn():
    """Return a live DB connection. Must be used inside a Flask app context."""
    if not has_app_context():
        raise RuntimeError('Database access attempted outside a Flask application context. Call this inside app.app_context() or a request.')

    conn = getattr(mysql, 'connection', None)
    if conn:
        return conn
    maybe = getattr(mysql, 'connect', None)
    if callable(maybe):
        try:
            return maybe()
        except Exception:
            pass
    elif maybe is not None:
        return maybe
    raise RuntimeError('flask_mysqldb MySQL extension not initialized — call mysql_init(app) before using the DB')
