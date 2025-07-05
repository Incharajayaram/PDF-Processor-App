import fitz  
from tqdm.auto import tqdm
import os
import logging

logger = logging.getLogger(__name__)

def text_formatter(text: str) -> str:
    cleaned_text = text.replace("\n", " ").strip()
    return cleaned_text

def open_and_read_pdf(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages_and_texts = []
    for page_number in tqdm(range(doc.page_count)):
        page = doc.load_page(page_number)
        text = page.get_text("text", sort=True)
        text = text_formatter(text)
        pages_and_texts.append({
            "page_number": page_number,
            "page_char_count": len(text),
            "page_word_count": len(text.split()),
                                "page_sentence_count_raw": len(text.split(". ")),
                                "page_token_count": len(text) / 4,
                                "text": text
                                })
    return pages_and_texts

class PDFProcessor:
    def __init__(self, upload_folder='uploads'):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)
    
    def process_pdf(self, pdf_path: str) -> str:
        """Process PDF and return combined text from all pages"""
        try:
            logger.info(f"Processing PDF: {pdf_path}")
            pages_data = open_and_read_pdf(pdf_path)
            
            #combine all page texts
            combined_text = " ".join([page['text'] for page in pages_data])
            
            logger.info(f"Successfully processed PDF with {len(pages_data)} pages")
            return combined_text
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    def save_uploaded_file(self, file, filename):
        """Save uploaded file to disk"""
        file_path = os.path.join(self.upload_folder, filename)
        file.save(file_path)
        return file_path