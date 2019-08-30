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
import json
import threading
from app.mod_github.toipynb import verify_files, create_ipynb
import errno, os, stat, shutil
from github import Github
# or using an access token
g = Github(conf.GITHUB_TOKEN)


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
    user_data = json.loads(response.read().decode('utf-8'))
    print(user_data)
    # repositories = get_repositories(user_data['access_token'], orcid)
    return jsonify(user_data)



# def get_repositories(access_token, orcid):
@mod_github.route('/get_repositories/', methods=['GET', 'OPTIONS'])
def get_repositories():
    access_token = request.args.get('access_token')
    req = urllib.request.Request(conf.GITHUB_USER_API_URL + '?access_token=' + access_token)
    response = urllib.request.urlopen(req)
    user_data = json.loads(response.read().decode('utf-8'))
    req = urllib.request.Request(user_data['repos_url']+'?per_page=1000')
    req.add_header('Accept', 'application/json')
    response = urllib.request.urlopen(req)
    repos_data = json.loads(response.read().decode('utf-8'))
    for repo in repos_data:
        repo['status'], repo['forked_url'] = repo_stat(repo['html_url'])
    return jsonify(repos_data)


def repo_stat(repo_url):
    status = "initial"
    fork_url = ''
    repo = Repository.query.filter_by(ori_url=repo_url).first()
    if repo:
        status = repo.status
        fork_url = repo.fork_url
    return status, fork_url


@mod_github.route('/submit/', methods=['GET', 'OPTIONS'])
def submit():
    repo_name = request.args.get('repo_name')
    user_name = request.args.get('user_name')
    orcid = request.args.get('orcid')

    #FORK
    repo_url = "https://github.com/"+user_name+"/"+repo_name
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
    fork_repo_url = "https://github.com/"+conf.GITHUB_ORGANIZATION_NAME+"/"+fork_repo_name

    fork_repo_ssh = "git@github.com:"+conf.GITHUB_ORGANIZATION_NAME+"/"+fork_repo_name+".git"

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
    repo_data = json.loads(results.text)
    try:
        create_repo(fork_repo_name, repo_url, fork_repo_url, "forked", orcid)
    except Exception as error:
        delete_repo(fork_repo_url)
        print(str(error))
        return jsonify({'status':'error creating repo in db')

    # creating thread
    t_verify = threading.Thread(target=clone_create_nb, args=(fork_repo_url, fork_repo_ssh,fork_repo_name,))
    # starting thread
    t_verify.start()

    # verify asynchronous
    return jsonify(repo_data)



def delete_repo(url):
    url_shorten = url.replace('https://github.com/', '')
    repo = g.get_repo(url_shorten)
    repo.delete()

def create_repo(name, ori_url, fork_url, status, owner):
    repo = Repository(name=name, ori_url=ori_url, fork_url=fork_url, status=status, owner=owner)
    db.session.add(repo)
    db.session.commit()

@mod_github.route('/regenerate_nb/', methods=['GET', 'OPTIONS'])
def regenerate_nb():
    forked_url = request.args.get('forked_url')
    repo_name = request.args.get('repo_name')

    path_clone = conf.PATH_CLONE+repo_name+"/"
    repo = Repo(path_clone)
    o = repo.remotes.origin
    o.pull()
    try:
        create_nb(forked_url, repo_name)
    except Exception as error:
        print('Error while creating nb'+str(error))
        return jsonify({'status':'Error while creating nb'}), 500
    return jsonify({'status':'success'})

def clone_create_nb(repo_url, repo_ssh, repo_name):
    path_clone= conf.PATH_CLONE+repo_name+"/"
    #clone
    try:
        Repo.clone_from(repo_ssh, path_clone)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:clone:"+str(error)
        db.session.commit()
        print(str(error))
        raise Exception("error:clone:")
    create_nb(repo_url, repo_name)


def create_nb(repo_url, repo_name):
    path_clone= conf.PATH_CLONE+repo_name+"/"
    #verify_files to create ipynb
    try:
        if not verify_files(path_clone):
            repo = Repository.query.filter_by(fork_url=repo_url).first()
            repo.status = "error:verify not exist:"
            db.session.commit()
            raise Exception("error:verify not exist:")
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:verify:"+str(error)
        db.session.commit()
        print(str(error))
        raise Exception("error:verify:")

    #create ipynb
    try:
        create_ipynb(path_clone)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:nbcreation:"+str(error)
        db.session.commit()
        print(str(error))
        raise Exception("error:nbcreation:")

    #GH push
    path_clone_git = path_clone+".git"
    commit_msg="review in progress"
    try:
        git_push(path_clone_git, commit_msg)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:ghpushing:"+str(error)
        db.session.commit()
        print(str(error))
        raise Exception('Error while gh pushing')

    repo = Repository.query.filter_by(fork_url=repo_url).first()
    repo.status = "submitted"
    db.session.commit()


def on_rm_error( func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod( path, stat.S_IWRITE )
    os.unlink( path )

@mod_github.route('/deletesubmitted/', methods=['GET', 'OPTIONS'])
def deletesubmitted():
    forked_url = request.args.get('forked_url')
    #delete from github
    try:
        delete_repo(forked_url)
    except Exception as error:
       print('Error while deleting gh repo'+str(error))
       return jsonify({'status':'Error while deleting gh repo'}), 500

    #delete from bd
    try:
        repo = Repository.query.filter_by(fork_url=forked_url).first()
        db.session.delete(repo)
        db.session.commit()
    except Exception as error:
        print('Error while deleting db record'+str(error))
        return jsonify({'status':'Error while deleting db record'}), 500

    repo_name= forked_url.split("/")[-1]
    #delete clone
    path_clone= conf.PATH_CLONE+repo_name
    # Delete all contents of a directory using shutil.rmtree() and  handle exceptions
    try:
       shutil.rmtree(path_clone,  onerror = on_rm_error)
    except Exception as error:
       print('Error while deleting directory'+str(error))
       return jsonify({'status':'Error while deleting directory'}), 500

    return jsonify({'status':'success'})


@mod_github.route('/list/', methods=['GET', 'OPTIONS'])
def list():
    status = request.args.get('status')
    repos_sub = Repository.query.filter_by(status=status).all()
    repos_json = [x.as_dict() for x in repos_sub]
    return jsonify(repos_json)


def git_push(path_clone_git, commit_msg):
    repo = Repo(path_clone_git)
    repo.index.add("*")
    repo.index.commit(commit_msg)
    origin = repo.remote(name='origin')
    origin.push()

@mod_github.route('/publish/', methods=['GET', 'OPTIONS'])
def publish():
    fork_url = request.args.get('fork_url')
    repo_name = request.args.get('repo_name')
    #GH push
    path_clone= conf.PATH_CLONE+repo_name+"/"
    path_clone_git = path_clone+".git"
    commit_msg="published version with notebook"
    try:
        git_push(path_clone_git, commit_msg)
    except Exception as error:
       print('Error gh pushing'+str(error))
       return jsonify({'status':'Error while gh pushing'}), 500
    #DB
    try:
        repo = Repository.query.filter_by(fork_url=fork_url).first()
        repo.status = "published"
        db.session.commit()
    except Exception as error:
       print('Error while changing status'+str(error))
       return jsonify({'status':'Error while changing status'}), 500

    #GH Reelease
    try:
        url_shorten = fork_url.replace('https://github.com/', '')
        repo = g.get_repo(url_shorten)
        repo.create_git_release("v1.0", "v1.0", "v1.0")
    except Exception as error:
       print('Error while gh releasing'+str(error))
       return jsonify({'status':'Error while gh releasing'}), 500

    return jsonify({'status':'success'})
