import os
import random
import requests
import time
import json
from docs import conf

import logging
logger = logging.getLogger("app.access")

MD_PATH = "paper.md"
REF_PATH = "paper.bib"
PDF_PATH = "paper.pdf"

#path with slash at the end
def verify_files_pdf(path):
    return os.path.exists(path+MD_PATH) and os.path.exists(path+REF_PATH)

def create_pdf_file(path, repo_url):
    url = conf.WHEDON_URL
    payload = {'repository': repo_url,
    'branch': 'master',
    'journal': 'biohackrxiv',
    'commit': 'Compile paper',
    'retid': 'true'
    }
    hdr= {
        'Content-Type':'application/json'
    }
    resp_id = requests.post(url, params = payload, headers=hdr) # compile paper
    logger.info(resp_id.text)
    job_id = json.loads(resp_id.text)['job_id']
    
    time.sleep(6) 
    params = {'id': job_id}
    resp = requests.get(url, params=params, stream=True)
    content_type = resp.headers.get('content-type')
    counter = 1
    while not 'application/pdf' in content_type: # the paper is not compiled instantly
        time.sleep(3) 
        resp = requests.get(url, params=params, stream=True)
        content_type = resp.headers.get('content-type')
        if counter == 18:
            raise Exception ("error generating pdf")
        counter+=1

    with open(path+PDF_PATH, 'wb') as f:
        f.write(resp.raw.read())