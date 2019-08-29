import nbformat as nbf
from pip._internal import main
import os
import subprocess
import io


REQUIREMENTS_PATH = "requirements.txt"
MD_PATH = "paper.md"
IPYNB_PATH = "paper.ipynb"

#path with slash at the end
def verify_files(path):
    return os.path.exists(path+REQUIREMENTS_PATH) and os.path.exists(path+MD_PATH)

def create_ipynb(path):
    #Install libraries

    # subprocess.check_call(["python", '-m', 'pip', 'install', '-r', path+REQUIREMENTS_PATH]) # install pkg

    # pip.main(['install', '-r', path+REQUIREMENTS_PATH, '--user'])
    # pip.main(['install', '-r', REQUIREMENTS_PATH])


    #Build Jupyter Notebook

    nb = nbf.v4.new_notebook()

    f = io.open(path+MD_PATH, mode="r", encoding="utf-8")
    # f = open(path+MD_PATH, 'r')

    text = f.read()

    f.close()

    cells = text.split('```')

    nb['cells'] = []

    for index, cell in enumerate(cells):
        if index%2:
            nb['cells'].append(nbf.v4.new_code_cell(cell))
        else:
            nb['cells'].append(nbf.v4.new_markdown_cell(cell))


    nbf.write(nb, path+IPYNB_PATH)
