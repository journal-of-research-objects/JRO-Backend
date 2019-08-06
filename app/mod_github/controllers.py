from flask import Blueprint, request, json, jsonify
from flask_cors import CORS
from docs import conf # , sparql_templates as sparqlt
# Import the database object from the main app module
from app.app import db
from app.mod_github.models import Repository
# from SPARQLWrapper import SPARQLWrapper, JSON
import urllib
import requests
from git import Repo

mod_github = Blueprint('github', __name__)
CORS(mod_github)


@mod_github.route('/github/', methods=['GET', 'OPTIONS'])
def github_auth():
    auth_code = request.args.get('github_auth_code')
    # orcid = request.args.get('orcid')
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
    print(user_data)
    repositories = get_repositories(user_data['access_token'])
    # repositories = get_repositories(user_data['access_token'], orcid)
    return jsonify(repositories)



# def get_repositories(access_token, orcid):
def get_repositories(access_token):
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

#repo_url_fork is the forks_url att of the repo object
#repo_url_fork = https://api.github.com/repos/<user>/<repo>/forks
@mod_github.route('/submit/', methods=['GET', 'OPTIONS'])
def submit():
    repo_name = request.args.get('repo_name')
    user_name = request.args.get('user_name')
    orcid = request.args.get('orcid')

    #FORK
    repo_url = "https://github.com/"+user_name+"/"+repo_name+".git"
    repo_url_fork = "https://api.github.com/repos/"+user_name+"/"+repo_name+"/forks"
    params = {
                'organization': conf.GITHUB_ORGANIZATION_NAME
              }
    hdr = {'Authorization': 'token %s' % conf.GITHUB_TOKEN}
    results = requests.post(repo_url_fork,
                        headers=hdr,
                        params=params)

    #CHANGE NAME

    fork_repo_name = user_name+"-"+repo_name
    fork_repo_url = "https://github.com/"+conf.GITHUB_ORGANIZATION_NAME+"/"+fork_repo_name+".git"

    params = {'name': fork_repo_name}
    hdr = {
            'Authorization': 'token %s' % conf.GITHUB_TOKEN,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            }
    repo_url_api = "https://api.github.com/repos/"+conf.GITHUB_ORGANIZATION_NAME+"/"+repo_name
    results = requests.patch(repo_url_api,
                        json=params,
                        headers=hdr)
    user_data = json.loads(results.text)
    try:
        create_repo(repo_url, fork_repo_url, "forked", orcid)
    except Exception as error:
         hdr = {
                 'Authorization': 'token %s' % conf.GITHUB_TOKEN,
                 'Content-Type': 'application/json'
                 }
         results = requests.delete(repo_url_api,
                             headers=hdr)
         raise Exception('error creating repo in db: '+str(error))

    # clone asynchronous
    # verify asynchronous



def create_repo(ori_url, fork_url, state, owner):
    repo = Repository(ori_url=ori_url, fork_url=fork_url, state=state, owner=owner)
    db.session.add(repo)
    db.session.commit()

def clone(repo_url):
    Repo.clone_from("repo_url", "../../../")



def repo_exists(repo_url, orcid):
    sparql = SPARQLWrapper(conf.SPARQL_QUERY_ENDPOINT)
    orcid = 'http://orcid.org/' + orcid
    query = sparqlt.RO_EXIST.format(orcid=orcid, share_url=repo_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return bool(sparql.query().convert()['boolean'])
