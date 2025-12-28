import os
from typing import List, Union
from PyPDF2 import PdfReader
from docx import Document
import logging

logger = logging.getLogger(__name__)

class DocumentLoader:
    """文档加载器，支持PDF、Word和TXT格式"""
    
    @staticmethod
    def load_pdf(file_path: str) -> str:
        """加载PDF文档"""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Error loading PDF file {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def load_word(file_path: str) -> str:
        """加载Word文档"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error loading Word file {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def load_txt(file_path: str) -> str:
        """加载TXT文档"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error loading TXT file {file_path}: {str(e)}")
            raise
    
    @staticmethod
    def load_document(file_path: str) -> str:
        """根据文件扩展名加载相应类型的文档"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.pdf':
            return DocumentLoader.load_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return DocumentLoader.load_word(file_path)
        elif ext == '.txt':
            return DocumentLoader.load_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")