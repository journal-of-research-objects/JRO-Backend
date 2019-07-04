# Import flask and template operators
from flask import Flask, render_template
from docs import conf
# Import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy

# Define the WSGI application object
app = Flask(__name__)

# Configurations
app.config.from_object('docs.conf')


# Define the database object which is imported
# by modules and controllers
db = SQLAlchemy(app)


# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return 'bad request!', 404



# Build the database:
# This will create the database file using SQLAlchemy
db.create_all()


def main():
    """Main entry point of the app."""
    try:
        app.run(host='0.0.0.0', debug=True, port=8000, use_reloader=True)
    except Exception as exc:
        print(exc.message)
    finally:
        # get last entry and insert build appended if not completed
        # Do something here
        pass
