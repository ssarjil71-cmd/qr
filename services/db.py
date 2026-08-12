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
    """Return a live DB connection. Tries `mysql.connection`, then `mysql.connect()`.

    Raises RuntimeError with a clear message if the extension was not initialized.
    """
    # prefer the exposed connection attribute
    conn = getattr(mysql, 'connection', None)
    if conn:
        return conn
    # some versions expose a connect() factory or a Connection object
    maybe = getattr(mysql, 'connect', None)
    if callable(maybe):
        try:
            return maybe()
        except Exception:
            pass
    elif maybe is not None:
        return maybe
    raise RuntimeError('flask_mysqldb MySQL extension not initialized — call mysql_init(app) before using the DB')
