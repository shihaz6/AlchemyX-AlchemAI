import os
from dataclasses import dataclass, field


SUPPORTED_EXTENSIONS = ('.txt', '.md', '.docx', '.pdf')
TESSERACT_CMD_ENV = "TESSERACT_CMD"
WINDOWS_TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


@dataclass
class IngestionResult:
    ingested: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def read_txt_md(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def read_docx(file_path):
    import docx

    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


def read_pdf(file_path):
    import fitz  # PyMuPDF
    import pytesseract
    from pdf2image import convert_from_path

    tesseract_cmd = os.getenv(TESSERACT_CMD_ENV)
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    elif os.name == "nt":
        pytesseract.pytesseract.tesseract_cmd = WINDOWS_TESSERACT_CMD

    text = ""

    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
        
    if len(text.strip()) < 50:
        print(f"[OCR] Scanned file detected...Processing: {file_path}")
        images = convert_from_path(file_path)
        ocr_text = ""
        for img in images:
            ocr_text += pytesseract.image_to_string(img)
        return ocr_text
        
    return text


def extract_text(file_path):
    normalized_path = file_path.lower()

    if normalized_path.endswith(('.txt', '.md')):
        return read_txt_md(file_path)
    if normalized_path.endswith('.docx'):
        return read_docx(file_path)
    if normalized_path.endswith('.pdf'):
        return read_pdf(file_path)

    return ""


def make_doc_id(corpus_folder_path, file_path):
    relative_path = os.path.relpath(file_path, corpus_folder_path)
    return relative_path.replace(os.sep, "/")


def ingest_corpus(corpus_folder_path, pipeline, bm25_store):
    try:
        from alchemyx.retrieval.main import add_document_to_indexes
    except ImportError:
        from src.alchemyx.retrieval.main import add_document_to_indexes

    result = IngestionResult()

    for root, _dirs, files in os.walk(corpus_folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            extracted_text = ""

            try:
                if not file.lower().endswith(SUPPORTED_EXTENSIONS):
                    result.skipped.append(make_doc_id(corpus_folder_path, file_path))
                    print(f"Skipped unsupported file: {file}")
                    continue

                extracted_text = extract_text(file_path)

                if extracted_text:
                    doc_id = make_doc_id(corpus_folder_path, file_path)
                    add_document_to_indexes(
                        pipeline=pipeline,
                        bm25_store=bm25_store,
                        doc_id=doc_id,
                        text=extracted_text,
                    )
                    result.ingested.append(doc_id)
                    print(f"✅ Success: {file} ingested.")
                else:
                    result.skipped.append(make_doc_id(corpus_folder_path, file_path))
                    print(f"Skipped empty file: {file}")

            except Exception as e:
                result.failed[make_doc_id(corpus_folder_path, file_path)] = str(e)
                print(f"❌ Error: {file} can't read file. Reason: {e}")

    return result


def print_ingestion_summary(result):
    print("\nIngestion summary:")
    print(f"Ingested: {len(result.ingested)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Failed: {len(result.failed)}")

    if result.failed:
        print("\nFailed files:")
        for doc_id, reason in result.failed.items():
            print(f"- {doc_id}: {reason}")


if __name__ == "__main__":
    try:
        from alchemyx.retrieval.main import create_retrieval_stack
    except ImportError:
        from src.alchemyx.retrieval.main import create_retrieval_stack
    
    my_corpus_folder = "ashen_era_archive" 
    pipeline, bm25_store, _hybrid_search, _reranker = create_retrieval_stack()
    
    print("Corpus startig reading...")
    result = ingest_corpus(my_corpus_folder, pipeline, bm25_store)
    print_ingestion_summary(result)
    
    print("\nDone! Corpus ingestion completed.")
