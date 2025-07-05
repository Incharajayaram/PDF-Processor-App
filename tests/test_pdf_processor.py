import pytest
import os
import tempfile
from pdf_processor import PDFProcessor, text_formatter, open_and_read_pdf
from werkzeug.datastructures import FileStorage
from io import BytesIO


class TestPDFProcessor:
    @pytest.fixture
    def pdf_processor(self):
        """Create PDFProcessor instance with temp directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = PDFProcessor(upload_folder=tmpdir)
            yield processor
    
    def test_text_formatter(self):
        """Test text formatting function"""
        # Test newline removal
        text = "Hello\nWorld\nThis is\na test"
        result = text_formatter(text)
        assert result == "Hello World This is a test"
        
        # Test strip whitespace
        text = "  Hello World  "
        result = text_formatter(text)
        assert result == "Hello World"
        
        # Test empty string
        assert text_formatter("") == ""
        assert text_formatter("\n\n") == ""
    
    def test_save_uploaded_file(self, pdf_processor):
        """Test saving uploaded file"""
        # Create mock file
        file_content = b'Mock PDF content'
        file = FileStorage(
            stream=BytesIO(file_content),
            filename='test.pdf',
            content_type='application/pdf'
        )
        
        # Save file
        saved_path = pdf_processor.save_uploaded_file(file, 'test_save.pdf')
        
        # Verify file exists and content matches
        assert os.path.exists(saved_path)
        with open(saved_path, 'rb') as f:
            assert f.read() == file_content
    
    def test_process_pdf_mock(self, pdf_processor, mocker):
        """Test PDF processing with mocked fitz"""
        # Mock the open_and_read_pdf function
        mock_pages = [
            {
                "page_number": 0,
                "page_char_count": 28,
                "page_word_count": 4,
                "page_sentence_count_raw": 1,
                "page_token_count": 7,
                "text": "Page 1 content with newlines"
            },
            {
                "page_number": 1,
                "page_char_count": 16,
                "page_word_count": 3,
                "page_sentence_count_raw": 1,
                "page_token_count": 4,
                "text": "Page 2 content"
            }
        ]
        
        mocker.patch('pdf_processor.open_and_read_pdf', return_value=mock_pages)
        
        # Test processing
        result = pdf_processor.process_pdf('dummy.pdf')
        
        # Should return combined text from all pages
        assert result == "Page 1 content with newlines Page 2 content"
    
    def test_open_and_read_pdf_mock(self, mocker):
        """Test open_and_read_pdf function with mocked fitz"""
        # Mock fitz components
        mock_page = mocker.Mock()
        mock_page.get_text.return_value = "Test content\nwith newlines"
        
        mock_doc = mocker.Mock()
        mock_doc.page_count = 1
        mock_doc.load_page.return_value = mock_page
        
        mock_fitz = mocker.patch('pdf_processor.fitz')
        mock_fitz.open.return_value = mock_doc
        
        # Test function
        result = open_and_read_pdf('test.pdf')
        
        assert len(result) == 1
        assert result[0]['page_number'] == 0
        assert result[0]['text'] == "Test content with newlines"
        assert result[0]['page_word_count'] == 4
    
    def test_process_pdf_error_handling(self, pdf_processor, mocker):
        """Test error handling in process_pdf"""
        # Mock open_and_read_pdf to raise an exception
        mocker.patch('pdf_processor.open_and_read_pdf', side_effect=Exception("PDF read error"))
        
        # Should raise the exception
        with pytest.raises(Exception) as exc_info:
            pdf_processor.process_pdf('bad.pdf')
        
        assert "PDF read error" in str(exc_info.value)