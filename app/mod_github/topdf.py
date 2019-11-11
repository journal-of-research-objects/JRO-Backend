# from md2pdf.core import md2pdf


MD_PATH = "paper.md"
REF_PATH = "references.bib"
PDF_PATH = "paper.pdf"

#path with slash at the end
def verify_files_pdf(path):
    return os.path.exists(path+MD_PATH) and os.path.exists(path+REF_PATH)

def create_pdf_file(path):
    pdf_file_path = path+PDF_PATH
    md2pdf(pdf_file_path, md_file_path=path+MD_PATH)