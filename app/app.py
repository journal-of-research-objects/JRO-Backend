# Import flask and template operators
from flask import Flask, render_template, session

import os
from docs import conf
# Import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    get_jwt_identity,
)

# Define the WSGI application object
app = Flask(__name__)

# Configurations
app.config.from_object('docs.conf')
app.config["JWT_SECRET_KEY"] = conf.JWT_SECRET
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = int(conf.JWT_EXPIRES)
jwt = JWTManager(app)

# Define the database object which is imported
# by modules and controllers
db = SQLAlchemy(app)


# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return 'bad request!', 404



# Import a module / component using its blueprint handler variable (mod_auth)
from app.mod_auth.controllers import mod_auth
from app.mod_github.controllers import mod_github

# Register blueprint(s)
app.register_blueprint(mod_auth)
app.register_blueprint(mod_github)


# Build the database:
# This will create the database file using SQLAlchemy
db.create_all()

#
# file_path = os.path.join(app.root_path, conf.TMP_DIR)
# if not os.path.exists(file_path):
#     os.makedirs(file_path)
import logging
def main():
    """Main entry point of the app."""
    try:
        logging.basicConfig(filename='error.log',level=logging.DEBUG)
        app.run(host='0.0.0.0', debug=True, port=8008, use_reloader=True,threaded=True)
    except Exception as exc:
        print(exc.message)
    finally:
        # get last entry and insert build appended if not completed
        # Do something here
        pass
