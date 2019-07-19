from flask import Blueprint, request, json, jsonify
from flask_cors import CORS
from docs import conf # , sparql_templates as sparqlt
from app.mod_auth.models import User
# from SPARQLWrapper import SPARQLWrapper, JSON
import urllib

mod_github = Blueprint('github', __name__)
CORS(mod_github)


@mod_github.route('/github/', methods=['GET', 'OPTIONS'])
def github_auth():
    auth_code = request.args.get('github_auth_code')
    orcid = request.args.get('orcid')
    params = {'client_id': conf.GITHUB_CLIENT_ID,
              'client_secret': conf.GITHUB_SECRET,
              'code': auth_code
              }
    data = urllib.parse.urlencode(params)
    data = data.encode('ascii') # data should be bytes
    req = urllib.request.Request(conf.GITHUB_API_URL, data)
    req.add_header('Accept', 'application/json')
    response = urllib.request.urlopen(req)
    user_data = json.loads(response.read())
    repositories = get_repositories(user_data['access_token'], orcid)
    return jsonify(repositories)


def get_repositories(access_token, orcid):
    req = urllib.request.Request(conf.GITHUB_USER_API_URL + '?access_token=' + access_token)
    response = urllib.request.urlopen(req)
    user_data = json.loads(response.read())
    req = urllib.request.Request(user_data['repos_url'])
    req.add_header('Accept', 'application/json')
    response = urllib.request.urlopen(req)
    repos_data = json.loads(response.read())
    # for repo in repos_data:
    #     repo['claimed'] = repo_exists(repo['html_url'], orcid)
    return repos_data


def repo_exists(repo_url, orcid):
    sparql = SPARQLWrapper(conf.SPARQL_QUERY_ENDPOINT)
    orcid = 'http://orcid.org/' + orcid
    query = sparqlt.RO_EXIST.format(orcid=orcid, share_url=repo_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return bool(sparql.query().convert()['boolean'])
