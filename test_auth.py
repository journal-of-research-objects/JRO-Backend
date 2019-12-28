from flask_testing import TestCase
import unittest
from app.app import db
from app.app import app
import json

from app.mod_auth.models import User

class MyTest(unittest.TestCase):

    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    # def create_app(self):

    #     # pass in test configuration
    #     return app.main()

    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.client.testing = True
        db.create_all()

    def tearDown(self):

        db.session.remove()
        db.drop_all()

    def test_login(self):
        # sends HTTP GET request to the application
        # on the specified path
        response = self.client.get('/login/', query_string={'orcid_auth_code':'hpX9ul'}) 
        # print(response.data)
        json_data = json.loads(response.data)

        # assert the response data
        assert 'status' in json_data
        assert json_data['status']=='success'

if __name__ == '__main__':
    unittest.main()