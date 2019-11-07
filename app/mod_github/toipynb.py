import nbformat as nbf
import os
import subprocess
import io
import virtualenv

REQUIREMENTS_PATH = "requirements.txt"
MD_PATH = "paper.md"
IPYNB_PATH = "paper.ipynb"
REF_PATH = "references.bib"

#path with slash at the end
def verify_files(path):
    return os.path.exists(path+REQUIREMENTS_PATH) and os.path.exists(path+MD_PATH) and os.path.exists(path+REF_PATH)

# create the virtual environment and add it to kernel
def create_venv(path, repo_name):
    venv_dir = os.path.join(path, "venv")
    virtualenv.create_environment(venv_dir)
    python_dir = os.path.join(venv_dir, "bin/python")
    # python_dir = os.path.join(venv_dir, "Scripts/python.exe") # windows
    subprocess.check_call([python_dir, '-m', 'pip', 'install', 'ipykernel']) # install ipykernel
    subprocess.check_call([python_dir, '-m', 'ipykernel', 'install', '--name', repo_name]) # install ipykernel
    # subprocess.check_call([python_dir, '-m', 'ipykernel', 'install', '--user', '--name', repo_name]) # install ipykernel


# add venv folder to gitignore
def add_venv_gitignore(path_gitignore):
    elem = "venv/"
    if os.path.isfile(path_gitignore):
        f=open(path_gitignore, "a+")
        f.write(elem)
    else:
        f= open(path_gitignore,"w+")
        f.write(elem)
        f.close()


#Install libraries
def install_libs(path):
    python_dir = os.path.join(path, "venv/bin/python")
    # python_dir = os.path.join(path, "venv/Scripts/python.exe") # windows
    subprocess.check_call([python_dir, '-m', 'pip', 'install', '-r', path+REQUIREMENTS_PATH]) # install pkg
    # pip.main(['install', '-r', path+REQUIREMENTS_PATH, '--user'])
    # pip.main(['install', '-r', REQUIREMENTS_PATH])



def create_ipynb(path):

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
