# Import the database object (db) from the main application module
# We will define this inside /app/__init__.py in the next sections.
from app.app import db

# Define a base model for other database tables to inherit
class Base(db.Model):

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime,  default=db.func.current_timestamp())
    date_modified = db.Column(db.DateTime,  default=db.func.current_timestamp(),
                              onupdate=db.func.current_timestamp())


# Define a User model
class User(Base):
    __tablename__ = 'user'

    # User Name
    name = db.Column(db.String(128),  nullable=False)

    # Identification Data: email & password
    orcid = db.Column(db.String(128),  nullable=False, unique=True)
    token = db.Column(db.String(192),  nullable=False)
    aka = db.Column(db.String(1000),  nullable=True)
    role = db.Column(db.String(128),  nullable=True)
    repos = db.relationship('Repository', backref='user', lazy=True)

    def __init__(self, name, orcid, aka, token):

        self.name = name
        self.orcid = orcid
        self.token = token
        self.aka = aka

    def __repr__(self):
        return '<User %r>' % self.name
        
    def as_dict(self):
       # return {c.name: getattr(self, c.name) for c in self.__table__.columns}
       return {c.name: str(getattr(self, c.name)) for c in self.__table__.columns}  # to support datetime
