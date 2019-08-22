# Import the database object (db) from the main application module
# We will define this inside /app/__init__.py in the next sections.
from app.app import db

from datetime import datetime

def _try(o):
    try: return o.__dict__
    except: return str(o)

# Define a base model for other database tables to inherit
class Base(db.Model):

    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime,  default=db.func.current_timestamp())
    date_modified = db.Column(db.DateTime,  default=db.func.current_timestamp(),
                              onupdate=db.func.current_timestamp())


# Define a User model
class Repository(Base):
    __tablename__ = 'repository'

    name = db.Column(db.String(1000), nullable=False, unique=True)
    ori_url = db.Column(db.String(1000),  nullable=False, unique=True)
    fork_url = db.Column(db.String(1000),  nullable=False, unique=True)
    status = db.Column(db.String(1000),  nullable=True)
    date_submitted = db.Column(db.DateTime,  nullable=False, default=datetime.utcnow)
    owner = db.Column(db.String(128), db.ForeignKey('user.orcid'), nullable=False)

    def __init__(self, name, ori_url, fork_url, status, owner):

        self.name = name
        self.ori_url = ori_url
        self.fork_url = fork_url
        self.status = status
        self.owner = owner

    def __repr__(self):
        return '<Repo %r>' % self.ori_url

    def as_dict(self):
       # return {c.name: getattr(self, c.name) for c in self.__table__.columns}
       return {c.name: str(getattr(self, c.name)) for c in self.__table__.columns}  # to support datetime
