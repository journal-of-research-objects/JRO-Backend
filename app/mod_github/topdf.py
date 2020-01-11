import os
import random
import requests
import time
from docs import conf

MD_PATH = "paper.md"
REF_PATH = "references.bib"
PDF_PATH = "paper.pdf"

#path with slash at the end
def verify_files_pdf(path):
    return os.path.exists(path+MD_PATH) and os.path.exists(path+REF_PATH)

def create_pdf_file(path, repo_url):
    ran = random.randrange(10**80)
    myhex = "%064x" % ran
    hash = myhex[:24]
    url = conf.WHEDON_URL
    payload = {'repository': repo_url,
    'journal': 'biohackrxiv',
    'commit': 'Compile paper',
    'sha': hash
    }
    requests.post(url, data = payload) # compile paper

    params = {'id': hash}
    resp = requests.get(url, params=params, stream=True)
    content_type = resp.headers.get('content-type')
    while not 'application/pdf' in content_type: # the paper is not compiled instantly
        time.sleep(3) 
        resp = requests.get(url, params=params, stream=True)
        content_type = resp.headers.get('content-type')

    with open(path+PDF_PATH, 'wb') as f:
        f.write(resp.raw.read())