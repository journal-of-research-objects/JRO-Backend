from flask import Blueprint, request, json, jsonify
from flask_cors import CORS
from docs import conf # , sparql_templates as sparqlt
# Import the database object from the main app module
from app.app import db
from app.mod_github.models import Repository
# from SPARQLWrapper import SPARQLWrapper, JSON
import urllib
import ssl
# This restores the same behavior as before.
context = ssl._create_unverified_context()
import requests
import re
from git import Repo
import json
import math
import threading
from datetime import datetime
from app.mod_github.toipynb import verify_files_nb, create_ipynb, create_venv, install_libs, add_venv_gitignore
from app.mod_github.topdf import verify_files_pdf, create_pdf_file
import errno, os, stat, shutil
from github import Github
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    get_jwt_identity,
)
# or using an access token
g = Github(conf.GITHUB_TOKEN)

import logging
logger = logging.getLogger("app.access")

mod_github = Blueprint('github', __name__)
CORS(mod_github)


@mod_github.route('/github/', methods=['GET'])
@jwt_required
def github_auth():
    auth_code = request.args.get('github_auth_code')
    # orcid = request.args.get('orcid')
    params = {'client_id': conf.GITHUB_CLIENT_ID,
              'client_secret': conf.GITHUB_SECRET,
              'code': auth_code
              }
    data = urllib.parse.urlencode(params)
    data = data.encode('ascii') # data should be bytes
    try: 
        req = urllib.request.Request(conf.GITHUB_API_URL, data)
        req.add_header('Accept', 'application/json')
        response = urllib.request.urlopen(req, context=context)
        user_data = json.loads(response.read().decode('utf-8'))
        logger.info(str(user_data))
        # repositories = get_repositories(user_data['access_token'], orcid)
        return jsonify(user_data)
    except Exception as error:
        logger.error(str(error))
        return jsonify(status="error"), 500



# def get_repositories(access_token, orcid):
@mod_github.route('/get_repositories/', methods=['GET'])
@jwt_required
def get_repositories():
    access_token = request.args.get('access_token')
    try:
        req = urllib.request.Request(conf.GITHUB_REPOS_API_URL+'user' + '?access_token=' + access_token)
        response = urllib.request.urlopen(req, context=context)
        user_data = json.loads(response.read().decode('utf-8'))

        params = {'page': 1, 'per_page':100}
        another_page = True
        repos_url = user_data['repos_url']
        repos_data = []
        hdr = {
                'Accept': 'application/json'
                }
        while another_page: #the list of repos is paginated
            r = requests.get(repos_url, params=params, headers=hdr)
            json_response = json.loads(r.text)
            repos_data+= json_response
            if 'next' in r.links: #check if there is another page of repos
                params['page'] = params['page']+1
            else:
                another_page=False
        
        for repo in repos_data:
            repo['status'] = repo_stat(repo['html_url'])
            repo['forked_url'] = repo_fork_url(repo['html_url'])
            if repo['status'] == "published":
                response = urllib.request.urlopen(conf.GITHUB_RAW_URL+conf.GITHUB_ORGANIZATION_NAME+"/"+repo['owner']['login']+"-"+repo['name']+"/master/metadata.json", context=context)
                metadata = json.loads(response.read().decode('utf-8'))
                repo['metadata'] = metadata
        return jsonify(repos_data)
    except Exception as error:
        logger.error(str(error))
        return jsonify(status="error"), 500


def repo_stat(repo_url):
    try: 
        status = "initial"
        repo = Repository.query.filter_by(ori_url=repo_url).first()
        if repo:
            status = repo.status
            if ("error" in status):
                colon = [m.start() for m in re.finditer(r":",status)][1] # 2nd colon
                status = status[:colon]
        return status
    except Exception as error:
        logger.error(str(error))
        return jsonify(status="error"), 500

def repo_fork_url(repo_url):
    try:
        fork_url = ''
        repo = Repository.query.filter_by(ori_url=repo_url).first()
        if repo:
            fork_url = repo.fork_url
        return fork_url
    except Exception as error:
        logger.error(str(error))
        return jsonify(status="error"), 500

@mod_github.route('/get_status_repo/', methods=['GET'])
@jwt_required
def get_status_repo():
    try: 
        repo_url = request.args.get('repo_url')
        status = repo_stat(repo_url)
        return jsonify(status=status)
    except Exception as error:
        logger.error(str(error))
        return jsonify(status="error"), 500


@mod_github.route('/submit/', methods=['POST'])
@jwt_required
def submit():
    data = request.get_json()
    logger.info(str(data))
    if not ("repo_name" in data and "user_name" in data and "orcid" in data):
        return jsonify(status="error:not elements required in data"), 500
    
    if not "paper_type" in data or data['paper_type'] is None:
        paper_type = 'opensoft'
    else:
        paper_type = data['paper_type']
    
    if not "authors" in data:
        authors = ''
    else:
        authors = data['authors']

    if not "keywords" in data or data['keywords'] is None:
        keywords = ''
    else:
        keywords = data['keywords']

    if not "branch" in data or data['branch'] is None:
        branch = 'master'
    else:
        branch = data['branch']

    repo_name = data['repo_name']
    user_name = data['user_name']
    orcid = data['orcid']

    #FORK
    try:
        repo_url = "https://github.com/"+user_name+"/"+repo_name
        repo_url_fork = conf.GITHUB_REPOS_API_URL+"repos/"+user_name+"/"+repo_name+"/forks"
        params = {
                    'organization': conf.GITHUB_ORGANIZATION_NAME
                }
        hdr = {'Authorization': 'token %s' % conf.GITHUB_TOKEN}
        results = requests.post(repo_url_fork,
                            headers=hdr,
                            params=params)
    except Exception as error:
        logger.error(str(error))
        return jsonify({'status':'error forking'}), 500

    #CHANGE NAME
    try:
        fork_repo_name = user_name+"-"+repo_name
        fork_repo_url = "https://github.com/"+conf.GITHUB_ORGANIZATION_NAME+"/"+fork_repo_name

        fork_repo_ssh = "git@github.com:"+conf.GITHUB_ORGANIZATION_NAME+"/"+fork_repo_name+".git"

        params = {'name': fork_repo_name, 'has_issues': True}
        hdr = {
                'Authorization': 'token %s' % conf.GITHUB_TOKEN,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
                }
        repo_url_api = conf.GITHUB_REPOS_API_URL+"repos/"+conf.GITHUB_ORGANIZATION_NAME+"/"+repo_name
        results = requests.patch(repo_url_api,
                            json=params,
                            headers=hdr)
        repo_data = json.loads(results.text)

        logger.info("---------------repo_data------------------")
        logger.info(str(repo_data))
    except Exception as error:
        delete_repo(fork_repo_url)
        logger.error(str(error))
        return jsonify({'status':'error changing name'}), 500

    try:
        create_repo(fork_repo_name, repo_url, fork_repo_url, "forked", paper_type, orcid)
    except Exception as error:
        delete_repo(fork_repo_url)
        logger.error(str(error))
        return jsonify({'status':'error creating repo in db'}), 500

    if paper_type == 'notebook':
        # creating thread
        thread = threading.Thread(target=clone_create_nb, args=(fork_repo_url, fork_repo_ssh,fork_repo_name, authors, keywords,branch,))
    else:
        # creating thread
        thread = threading.Thread(target=clone_create_pdf, args=(fork_repo_url, fork_repo_ssh,fork_repo_name, authors, keywords,branch,))
    # starting thread
    thread.start()

    # verify asynchronous
    return jsonify(repo_data)



def delete_repo(url):
    try:
        url_shorten = url.replace('https://github.com/', '')
        repo = g.get_repo(url_shorten)
        repo.delete()
    except Exception as error:
        logger.error(str(error))
        return jsonify(status="error"), 500

def create_repo(name, ori_url, fork_url, status, paper_type, owner):
    try:
        repo = Repository(name=name, ori_url=ori_url, fork_url=fork_url, status=status, paper_type=paper_type, owner=owner)
        db.session.add(repo)
        db.session.commit()
    except Exception as error:
        logger.error(str(error))
        return jsonify(status="error"), 500

@mod_github.route('/regenerate_nb/', methods=['GET'])
@jwt_required
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
        logger.error('Error while creating nb'+str(error))
        return jsonify({'status':'Error while creating nb'}), 500
    return jsonify({'status':'success'})

def clone_create_nb(repo_url, repo_ssh, repo_name, authors, keywords, branch):
    path_clone= conf.PATH_CLONE+repo_name+"/"
    
    clone(repo_url, repo_ssh, repo_name, authors, keywords, branch)
    
    #create venv and kernel
    venv(repo_url, repo_name)
    logger.info(repo_name+": venv created")

    #add venv to gitignore
    path_gitignore = os.path.join(path_clone, ".gitignore")
    try:
        add_venv_gitignore(path_gitignore)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:add_venv_gitignore:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:add_venv_gitignore")
        raise Exception ("error:add_venv_gitignore")
    logger.info(repo_name+": venv gitignored")

    #create nb
    create_nb(repo_url, repo_name)


def clone(repo_url, repo_ssh, repo_name, authors, keywords, branch):
    path_clone= conf.PATH_CLONE+repo_name+"/"
    #clone
    try:
        git_repo = Repo.clone_from(repo_ssh, path_clone, branch=branch)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:clone:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:clone:")
        raise Exception ("error:clone:")
    logger.info(repo_name+": cloned")

    #create metadata file
    try:
        create_metadata(authors, keywords, path_clone)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:metadata:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:metadata:")
        raise Exception ("error:metadata:")
    logger.info(repo_name+": metadata file created")
    


@mod_github.route('/regenerate_pdf/', methods=['GET'])
@jwt_required
def regenerate_pdf():
    forked_url = request.args.get('forked_url')
    repo_name = request.args.get('repo_name')

    path_clone = conf.PATH_CLONE+repo_name+"/"
    repo = Repo(path_clone)
    o = repo.remotes.origin
    o.pull()
    branch = repo.active_branch.name
    try:
        create_pdf(forked_url, repo_name, branch)
    except Exception as error:
        logger.error('Error while creating pdf'+str(error))
        return jsonify({'status':'Error while creating pdf'}), 500
    return jsonify({'status':'success'})


def clone_create_pdf(repo_url, repo_ssh, repo_name, authors, keywords, branch):
    #clone and create metadata file
    clone(repo_url, repo_ssh, repo_name, authors, keywords, branch)
    #create pdf
    create_pdf(repo_url, repo_name, branch)

def create_metadata(authors, keywords, path_clone):
    try:
        metadata = {
            "authors": authors,
            "keywords": keywords
        }

        with open(path_clone+'metadata.json', 'w') as outfile:
            json.dump(metadata, outfile)
    except Exception as error:
        logger.error(str(error))
        raise Exception(str(error))


def venv(repo_url, repo_name):
    path_clone= conf.PATH_CLONE+repo_name+"/"
    #create venv and kernel
    try:
        create_venv(path_clone, repo_name)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:venvcreation:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:venvcreation:")
        raise Exception ("error:venvcreation:")



def create_pdf(repo_url, repo_name, branch):
    path_clone= conf.PATH_CLONE+repo_name+"/"
    #verify_files to create pdf
    try:
        flag_ver = verify_files_pdf(path_clone)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:verify:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:verify:")
        raise Exception ("error:verify:")
    if not flag_ver:
        try: 
            repo = Repository.query.filter_by(fork_url=repo_url).first()
            repo.status = "error:verify not exist:"
            db.session.commit()
        except Exception as error:
            repo = Repository.query.filter_by(fork_url=repo_url).first()
            repo.status = "error:verify:"+str(error)
            db.session.commit()
            logger.error(str(error))
            logger.error("error:verify:")
            raise Exception ("error:verify:")
        logger.error("error:verify not exist:")
        raise Exception ("error:verify not exist:")
    
    logger.info(repo_name+": files verified")
    #create pdf
    try:
        create_pdf_file(path_clone, repo_url, branch)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:pdfcreation:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:pdfcreation:")
        raise Exception ("error:pdfcreation:")
    logger.info(repo_name+": pdf created")
    
    repo = Repository.query.filter_by(fork_url=repo_url).first()
    repo.status = "submitted"
    db.session.commit()


def create_nb(repo_url, repo_name):
    path_clone= conf.PATH_CLONE+repo_name+"/"
    #verify_files to create ipynb
    try:
        flag_ver = verify_files_nb(path_clone)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:verify:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:verify:")
        raise Exception ("error:verify:")
    if not flag_ver:
        try: 
            repo = Repository.query.filter_by(fork_url=repo_url).first()
            repo.status = "error:verify not exist:"
            db.session.commit()
        except Exception as error:
            repo = Repository.query.filter_by(fork_url=repo_url).first()
            repo.status = "error:verify:"+str(error)
            db.session.commit()
            logger.error(str(error))
            logger.error("error:verify:")
            raise Exception ("error:verify:")
        logger.error("error:verify not exist:")
        raise Exception ("error:verify not exist:")
    
    logger.info(repo_name+": files verified")

    #install libs
    try:
        install_libs(path_clone)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:libs:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:libs:")
        raise Exception ("error:libs:")

    logger.info(repo_name+": libs installed")

    #create ipynb
    try:
        create_ipynb(path_clone)
    except Exception as error:
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "error:nbcreation:"+str(error)
        db.session.commit()
        logger.error(str(error))
        logger.error("error:nbcreation:")
        raise Exception ("error:nbcreation:")

    logger.info(repo_name+": ipynb created")
    #
    # #GH push
    # path_clone_git = path_clone+".git"
    # commit_msg="review in progress"
    # try:
    #     git_push(path_clone_git, commit_msg)
    # except Exception as error:
    #     repo = Repository.query.filter_by(fork_url=repo_url).first()
    #     repo.status = "error:ghpushing:"+str(error)
    #     db.session.commit()
    #     print(str(error))
    #     raise Exception('Error while gh pushing')
    # print(repo_name+": pushed")
    try: 
        repo = Repository.query.filter_by(fork_url=repo_url).first()
        repo.status = "submitted"
        db.session.commit()
    except Exception as error:
        logger.error(str(error))
        raise Exception(str(error))



def on_rm_error( func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod( path, stat.S_IWRITE )
    os.unlink( path )

@mod_github.route('/deletesubmitted/', methods=['GET'])
@jwt_required
def deletesubmitted():
    forked_url = request.args.get('forked_url')
    #delete from bd
    try:
        repo = Repository.query.filter_by(fork_url=forked_url).first()
        db.session.delete(repo)
        db.session.commit()
    except Exception as error:
        logger.error('Error while deleting db record'+str(error))
        return jsonify({'status':'Error while deleting db record'}), 500

    #delete from github
    try:
        delete_repo(forked_url)
    except Exception as error:
       logger.error('Error while deleting gh repo'+str(error))
       return jsonify({'status':'Error while deleting gh repo'}), 500

    repo_name= forked_url.split("/")[-1]
    #delete clone
    path_clone= conf.PATH_CLONE+repo_name
    try:
       shutil.rmtree(path_clone,  onerror = on_rm_error)
    except Exception as error:
       logger.error('Error while deleting directory'+str(error))
       return jsonify({'status':'Error while deleting directory'}), 500

    return jsonify({'status':'success'})


@mod_github.route('/list/', methods=['GET'])
def list_rep():
    status = request.args.get('status')
    paper_type = request.args.get('paper_type')
    page = request.args.get('page')
    per_page = request.args.get('per_page')

    # default
    if status is None:
        status = 'published'
    if page is None:
        page = 1
    else:
        page = int(page)
    if per_page is None:
        per_page = 10
    else:
        per_page = int(per_page)

    if paper_type is None:
        repos_sub = Repository.query.filter_by(status=status).paginate(page=page, per_page=per_page, max_per_page=100).items
        total_pages = Repository.query.filter_by(status=status).count()
    else:
        repos_sub = Repository.query.filter_by(status=status, paper_type=paper_type).paginate(page=page, per_page=per_page, max_per_page=100).items
        total_pages = Repository.query.filter_by(status=status, paper_type=paper_type).count()
    repos_json = []  
    if status == 'published': # different way to bring the metadata
        for x in repos_sub:
            dic = x.as_dict()
            try: 
                response = urllib.request.urlopen(conf.GITHUB_RAW_URL+conf.GITHUB_ORGANIZATION_NAME+"/"+dic['name']+"/master/metadata.json", context=context)
                metadata = json.loads(response.read().decode('utf-8'))
                dic['metadata'] = metadata
            except Exception as error:
                logger.error(str(error))    
            try: 
                url_shorten = dic['ori_url'].replace('https://github.com/', '')
                response = urllib.request.urlopen(conf.GITHUB_REPOS_API_URL+'repos/'+url_shorten, context=context)
                properties = json.loads(response.read().decode('utf-8'))
                dic['properties'] = properties
            except Exception as error:
                logger.error(str(error))
                return jsonify({'status':'Error requesting to github info'}), 500
            logger.info(str(dic))
            repos_json.append(dic)

    elif status == 'submitted': # different way to bring the metadata
        for x in repos_sub:
            dic = x.as_dict()
            try: 
                path_repo = conf.PATH_CLONE+dic['name']+'/metadata.json'
                with open(path_repo) as json_file:
                    metadata= json.load(json_file)                    
                    dic['metadata'] = metadata
            except Exception as error:
                logger.error(str(error))
            try: 
                url_shorten = dic['ori_url'].replace('https://github.com/', '')
                response = urllib.request.urlopen(conf.GITHUB_REPOS_API_URL+'repos/'+url_shorten, context=context)
                properties = json.loads(response.read().decode('utf-8'))
                dic['properties'] = properties
            except Exception as error:
                logger.error(str(error))
                return jsonify({'status':'Error requesting to github info'}), 500
            logger.info(str(dic))
            repos_json.append(dic)
    else: 
        return jsonify({'status':'status not allowed'}), 500

    return jsonify({'data':repos_json, 'status':'success', 'page':str(page), 'allPages': math.ceil(total_pages/per_page), 'allRecords': total_pages})


@mod_github.route('/get_repo/', methods=['GET'])
def get_repo():
    fork_url = request.args.get('fork_url')
    try: 
        repo = Repository.query.filter_by(fork_url=fork_url).first()
    except Exception as error:
            logger.error(str(error))
            return jsonify({'status':'Error. Repo not in db'}), 500
    repo_dic = repo.as_dict()
    if repo_dic['status'] != 'published':
        return jsonify({'status':'Error. Repo not published'}), 500
    else:
        try: 
            response = urllib.request.urlopen(conf.GITHUB_RAW_URL+conf.GITHUB_ORGANIZATION_NAME+"/"+repo_dic['name']+"/master/metadata.json", context=context)
            metadata = json.loads(response.read().decode('utf-8'))
            repo_dic['metadata'] = metadata
        except Exception as error:
            logger.error(str(error))    
        try: 
            url_shorten = repo_dic['ori_url'].replace('https://github.com/', '')
            response = urllib.request.urlopen(conf.GITHUB_REPOS_API_URL+'repos/'+url_shorten, context=context)
            properties = json.loads(response.read().decode('utf-8'))
            repo_dic['properties'] = properties
        except Exception as error:
            logger.error(str(error))
            return jsonify({'status':'Error requesting to github info'}), 500
        
    return jsonify(repo_dic)

def git_push(path_clone_git, commit_msg):
    repo = Repo(path_clone_git)
    repo.index.add("*")
    repo.index.commit(commit_msg)
    origin = repo.remote(name='origin')
    origin.push("patch-1:master", force=True)

@mod_github.route('/publish/', methods=['GET'])
@jwt_required
def publish():
    fork_url = request.args.get('fork_url')
    repo_name = request.args.get('repo_name')
    #GH push
    path_clone= conf.PATH_CLONE+repo_name+"/"
    path_clone_git = path_clone+".git"
    commit_msg="published version with publication"
    try:
        git_push(path_clone_git, commit_msg)
    except Exception as error:
       logger.error('Error gh pushing'+str(error))
       return jsonify({'status':'Error while gh pushing'}), 500
    logger.info(repo_name+" pushed")
    
    #DB
    try:
        repo = Repository.query.filter_by(fork_url=fork_url).first()
        repo.status = "published"
        db.session.commit()
    except Exception as error:
       logger.error('Error while changing status'+str(error))
       return jsonify({'status':'Error while changing status'}), 500
    logger.info(repo_name+" db published")

    #GH Reelease
    try:
        url_shorten = fork_url.replace('https://github.com/', '')
        repo = g.get_repo(url_shorten)
        repo.create_git_release("v1.0", "v1.0", "v1.0")
    except Exception as error:
       logger.error('Error while gh releasing'+str(error))
       return jsonify({'status':'Error while gh releasing'}), 500
    logger.info(repo_name+" released")

    repo = Repository.query.filter_by(fork_url=fork_url).first()
    repo.date_published = datetime.utcnow()
    db.session.commit()
    return jsonify({'status':'success'})
