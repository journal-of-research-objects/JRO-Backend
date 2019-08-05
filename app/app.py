# Import flask and template operators
from flask import Flask, render_template, session
from flask_session import Session

import os
from docs import conf
# Import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy

# Define the WSGI application object
app = Flask(__name__)
sess = Session()

# Configurations
app.config.from_object('docs.conf')

app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'

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

def main():
    """Main entry point of the app."""
    try:

        sess.init_app(app)
        app.run(host='0.0.0.0', debug=True, port=8008, use_reloader=True,threaded=True)
    except Exception as exc:
        print(exc.message)
    finally:
        # get last entry and insert build appended if not completed
        # Do something here
        pass
