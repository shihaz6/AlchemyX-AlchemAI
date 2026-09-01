import os
import docx
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path


# ==========================================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def read_txt_md(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def read_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


def read_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    
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

def chunk_text(text, chunk_size=400, overlap=50):
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.strip()) > 0:
            chunks.append(chunk)
            
    return chunks


def process_corpus(corpus_folder_path):
    all_chunks = []
    
    for root, dirs, files in os.walk(corpus_folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            extracted_text = ""
            
            try:
                if file.endswith(('.txt', '.md')):
                    extracted_text = read_txt_md(file_path)
                elif file.endswith('.docx'):
                    extracted_text = read_docx(file_path)
                elif file.endswith('.pdf'):
                    extracted_text = read_pdf(file_path)
                
                if extracted_text:
                    chunks = chunk_text(extracted_text)
                    for i, chunk in enumerate(chunks):
                        all_chunks.append({
                            "source_file": file,
                            "chunk_id": i,
                            "text": chunk
                        })
                    print(f"✅ Success: {file} -> parts {len(chunks)} divided.")
                    
            except Exception as e:
                print(f"❌ Error: {file} can't read file. Reason: {e}")
                
    return all_chunks


if __name__ == "__main__":
    
    my_corpus_folder = "ashen_era_archive" 
    
    print("Corpus startig reading...")
    final_data = process_corpus(my_corpus_folder)
    
    print(f"\n done! devided in to (Chunks) parts: {len(final_data)}")