"""
Multimodal processing utilities for AI chat assistant
Handles image analysis, document processing, and multimodal AI interactions
"""
import os
import logging
import mimetypes
from typing import Dict, Any, Optional, List
from PIL import Image
import io
import tempfile

from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger('agent')


def detect_content_type(file_content: bytes, filename: str) -> str:
    """
    Detect the type of content from file data and filename
    
    Args:
        file_content: Raw file bytes
        filename: Original filename
        
    Returns:
        Content type string: 'image', 'document', 'audio', 'video', 'unknown'
    """
    
    # Get MIME type from filename
    mime_type, _ = mimetypes.guess_type(filename)
    
    if not mime_type:
        # Try to detect from file content (magic bytes)
        if file_content.startswith(b'\xFF\xD8\xFF'):
            return 'image'  # JPEG
        elif file_content.startswith(b'\x89PNG'):
            return 'image'  # PNG
        elif file_content.startswith(b'GIF8'):
            return 'image'  # GIF
        elif file_content.startswith(b'%PDF'):
            return 'document'  # PDF
        elif file_content.startswith(b'PK'):
            return 'document'  # ZIP-based formats (DOCX, XLSX, etc.)
        else:
            return 'unknown'
    
    # Classify by MIME type
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('audio/'):
        return 'audio'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type in ['application/pdf', 'text/plain', 
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       'application/vnd.ms-excel', 'text/csv']:
        return 'document'
    else:
        return 'unknown'


class ImageAnalyzer:
    """Handle image analysis and processing"""
    
    def __init__(self):
        self.max_image_size = (1920, 1080)  # Max resolution
        self.supported_formats = ['JPEG', 'PNG', 'GIF', 'WEBP', 'BMP']
    
    def analyze_image(self, image_file, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze image content and extract information
        
        Args:
            image_file: Image file object
            prompt: Optional analysis prompt
            
        Returns:
            Analysis results dictionary
        """
        
        try:
            # Load and validate image
            image_data = self._load_and_validate_image(image_file)
            if not image_data['valid']:
                return {
                    'success': False,
                    'error': image_data['error']
                }
            
            image = image_data['image']
            
            # Basic image information
            basic_info = self._get_basic_image_info(image)
            
            # Extract text from image (OCR)
            extracted_text = self._extract_text_from_image(image)
            
            # Analyze image content (for demo)
            content_analysis = self._analyze_image_content(image, prompt)
            
            return {
                'success': True,
                'description': content_analysis['description'],
                'extracted_text': extracted_text,
                'image_info': basic_info,
                'objects': content_analysis.get('objects', []),
                'colors': content_analysis.get('colors', []),
                'tags': content_analysis.get('tags', [])
            }
            
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _load_and_validate_image(self, image_file) -> Dict[str, Any]:
        """Load and validate image file"""
        
        try:
            # Read image data
            if hasattr(image_file, 'read'):
                image_data = image_file.read()
                image_file.seek(0)  # Reset file pointer
            else:
                with open(image_file, 'rb') as f:
                    image_data = f.read()
            
            # Load with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Validate format
            if image.format not in self.supported_formats:
                return {
                    'valid': False,
                    'error': f'Unsupported image format: {image.format}'
                }
            
            # Resize if too large
            if image.size[0] > self.max_image_size[0] or image.size[1] > self.max_image_size[1]:
                image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
                logger.info(f"Image resized to {image.size}")
            
            return {
                'valid': True,
                'image': image,
                'original_size': image.size,
                'format': image.format
            }
            
        except Exception as e:
            logger.error(f"Image loading error: {e}")
            return {
                'valid': False,
                'error': f'Failed to load image: {str(e)}'
            }
    
    def _get_basic_image_info(self, image: Image.Image) -> Dict[str, Any]:
        """Extract basic image information"""
        
        return {
            'width': image.size[0],
            'height': image.size[1],
            'format': image.format,
            'mode': image.mode,
            'has_transparency': image.mode in ('RGBA', 'LA') or 'transparency' in image.info
        }
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """
        Extract text from image using OCR
        
        For demo purposes, returns placeholder.
        In production, integrate with:
        - Tesseract OCR
        - Google Vision API
        - Azure Computer Vision
        - AWS Textract
        """
        
        try:
            # Demo implementation - returns placeholder
            # In production, implement actual OCR here
            
            # Check if image likely contains text (heuristic)
            width, height = image.size
            
            # Convert to grayscale for analysis
            gray_image = image.convert('L')
            
            # Simple heuristic: if image has good contrast, might contain text
            # In production, use proper OCR service
            
            return "[Для извлечения текста из изображений требуется настройка OCR сервиса]"
            
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""
    
    def _analyze_image_content(self, image: Image.Image, prompt: str = None) -> Dict[str, Any]:
        """
        Analyze image content and generate description
        
        For demo purposes, returns basic analysis.
        In production, integrate with:
        - OpenAI Vision API
        - Google Vision AI
        - Azure Computer Vision
        - Claude 3 Vision
        """
        
        try:
            # Demo implementation - basic analysis
            width, height = image.size
            mode = image.mode
            
            # Basic color analysis
            colors = self._get_dominant_colors(image)
            
            # Generate description based on image properties
            description_parts = []
            
            # Image size description
            if width > 1000 or height > 1000:
                description_parts.append("Высокое разрешение изображения")
            elif width < 300 or height < 300:
                description_parts.append("Небольшое изображение")
            else:
                description_parts.append("Изображение среднего размера")
            
            # Aspect ratio
            aspect_ratio = width / height
            if aspect_ratio > 1.5:
                description_parts.append("широкого формата")
            elif aspect_ratio < 0.7:
                description_parts.append("вертикального формата")
            else:
                description_parts.append("квадратного формата")
            
            # Color info
            if colors:
                description_parts.append(f"с преобладающими цветами: {', '.join(colors[:3])}")
            
            description = ", ".join(description_parts) + "."
            
            # Add prompt-specific analysis if provided
            if prompt and "текст" in prompt.lower():
                description += " Для точного анализа содержимого и извлечения текста требуется настройка сервиса компьютерного зрения."
            
            return {
                'description': description,
                'objects': [],  # Would be populated by vision API
                'colors': colors,
                'tags': self._generate_basic_tags(image)
            }
            
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            return {
                'description': "Не удалось проанализировать содержимое изображения",
                'objects': [],
                'colors': [],
                'tags': []
            }
    
    def _get_dominant_colors(self, image: Image.Image, num_colors: int = 5) -> List[str]:
        """Get dominant colors from image"""
        
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize for faster processing
            image_small = image.resize((100, 100))
            
            # Get colors (simplified approach)
            colors = image_small.getcolors(maxcolors=256)
            if not colors:
                return []
            
            # Sort by frequency
            colors.sort(key=lambda x: x[0], reverse=True)
            
            # Convert to color names (simplified)
            color_names = []
            for count, color in colors[:num_colors]:
                r, g, b = color
                color_name = self._rgb_to_color_name(r, g, b)
                if color_name not in color_names:
                    color_names.append(color_name)
            
            return color_names
            
        except Exception as e:
            logger.error(f"Color analysis error: {e}")
            return []
    
    def _rgb_to_color_name(self, r: int, g: int, b: int) -> str:
        """Convert RGB values to color name"""
        
        # Simple color name mapping
        if r > 200 and g > 200 and b > 200:
            return "белый"
        elif r < 50 and g < 50 and b < 50:
            return "черный"
        elif r > g and r > b:
            if r > 150:
                return "красный"
            else:
                return "темно-красный"
        elif g > r and g > b:
            if g > 150:
                return "зеленый"
            else:
                return "темно-зеленый"
        elif b > r and b > g:
            if b > 150:
                return "синий"
            else:
                return "темно-синий"
        elif r > 150 and g > 150:
            return "желтый"
        elif r > 150 and b > 150:
            return "розовый"
        elif g > 150 and b > 150:
            return "голубой"
        else:
            return "серый"
    
    def _generate_basic_tags(self, image: Image.Image) -> List[str]:
        """Generate basic tags for image"""
        
        tags = []
        width, height = image.size
        
        # Add format tag
        if image.format:
            tags.append(image.format.lower())
        
        # Add size tags
        if width > 1000 or height > 1000:
            tags.append("высокое_разрешение")
        
        # Add orientation tag
        aspect_ratio = width / height
        if aspect_ratio > 1.5:
            tags.append("панорамное")
        elif aspect_ratio < 0.7:
            tags.append("портретное")
        
        return tags


class MultimodalChatProcessor:
    """Process multimodal chat interactions"""
    
    def __init__(self):
        self.image_analyzer = ImageAnalyzer()
    
    def process_multimodal_message(self, text: str, attachments: List[Any]) -> Dict[str, Any]:
        """
        Process a message with text and attachments
        
        Args:
            text: User's text message
            attachments: List of file attachments
            
        Returns:
            Processing results
        """
        
        try:
            results = {
                'text_analysis': self._analyze_text(text),
                'attachment_analysis': [],
                'combined_context': '',
                'suggestions': []
            }
            
            # Process each attachment
            for attachment in attachments:
                attachment_result = self._process_attachment(attachment)
                results['attachment_analysis'].append(attachment_result)
            
            # Combine context
            results['combined_context'] = self._combine_context(text, results['attachment_analysis'])
            
            # Generate suggestions
            results['suggestions'] = self._generate_suggestions(results)
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Multimodal processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text content"""
        
        return {
            'length': len(text),
            'word_count': len(text.split()),
            'language': 'ru',  # Simple detection
            'intent': self._detect_text_intent(text),
            'entities': self._extract_entities(text)
        }
    
    def _process_attachment(self, attachment) -> Dict[str, Any]:
        """Process individual attachment"""
        
        try:
            attachment_type = attachment.get('type', 'unknown')
            
            if attachment_type == 'image':
                return self.image_analyzer.analyze_image(
                    attachment['file'], 
                    attachment.get('prompt')
                )
            elif attachment_type == 'document':
                return self._process_document(attachment['file'])
            else:
                return {
                    'success': False,
                    'error': f'Unsupported attachment type: {attachment_type}'
                }
                
        except Exception as e:
            logger.error(f"Attachment processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_document(self, document_file) -> Dict[str, Any]:
        """Process document attachment"""
        
        # Placeholder for document processing
        # In production, implement document parsing for PDF, DOCX, etc.
        
        return {
            'success': True,
            'content': '[Обработка документов требует настройки парсера]',
            'type': 'document',
            'page_count': 1,
            'text_length': 0
        }
    
    def _detect_text_intent(self, text: str) -> str:
        """Detect intent from text"""
        
        text_lower = text.lower()
        
        intents = {
            'question': ['что', 'как', 'когда', 'где', 'почему', 'зачем', '?'],
            'request': ['можешь', 'помоги', 'нужно', 'требуется', 'сделай'],
            'greeting': ['привет', 'здравствуй', 'добро пожаловать', 'хай'],
            'gratitude': ['спасибо', 'благодарю', 'спс', 'thanks'],
            'complaint': ['не работает', 'ошибка', 'проблема', 'баг']
        }
        
        for intent, keywords in intents.items():
            if any(keyword in text_lower for keyword in keywords):
                return intent
        
        return 'statement'
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract entities from text"""
        
        # Simple entity extraction
        entities = []
        
        # Look for dates, times, numbers
        import re
        
        # Dates
        date_pattern = r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b'
        dates = re.findall(date_pattern, text)
        entities.extend([f"date:{date}" for date in dates])
        
        # Times
        time_pattern = r'\b\d{1,2}:\d{2}\b'
        times = re.findall(time_pattern, text)
        entities.extend([f"time:{time}" for time in times])
        
        # Numbers
        number_pattern = r'\b\d+\b'
        numbers = re.findall(number_pattern, text)
        entities.extend([f"number:{num}" for num in numbers[:5]])  # Limit to 5
        
        return entities
    
    def _combine_context(self, text: str, attachment_analysis: List[Dict]) -> str:
        """Combine text and attachment context"""
        
        context_parts = [f"Пользователь написал: {text}"]
        
        for i, analysis in enumerate(attachment_analysis):
            if analysis.get('success'):
                if 'description' in analysis:
                    context_parts.append(f"Прикрепленное изображение {i+1}: {analysis['description']}")
                if 'extracted_text' in analysis and analysis['extracted_text']:
                    context_parts.append(f"Текст из изображения {i+1}: {analysis['extracted_text']}")
                if 'content' in analysis:
                    context_parts.append(f"Содержимое документа {i+1}: {analysis['content'][:200]}...")
        
        return " ".join(context_parts)
    
    def _generate_suggestions(self, results: Dict[str, Any]) -> List[str]:
        """Generate response suggestions based on analysis"""
        
        suggestions = []
        
        text_intent = results['text_analysis'].get('intent')
        
        if text_intent == 'question':
            suggestions.append("Ответить на вопрос пользователя")
        elif text_intent == 'request':
            suggestions.append("Выполнить запрос пользователя")
        
        # Add suggestions based on attachments
        for analysis in results['attachment_analysis']:
            if analysis.get('success'):
                if 'extracted_text' in analysis and analysis['extracted_text']:
                    suggestions.append("Проанализировать текст из изображения")
                if analysis.get('type') == 'document':
                    suggestions.append("Обработать содержимое документа")
        
        return suggestions[:3]  # Limit to 3 suggestions


class DocumentProcessor:
    """Process various document types"""
    
    def __init__(self):
        self.supported_formats = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'text/csv'
        }
    
    def process_document(self, document_file, file_type: str) -> Dict[str, Any]:
        """
        Process document and extract content
        
        Args:
            document_file: Document file object
            file_type: Type of document
            
        Returns:
            Processing results
        """
        
        try:
            if file_type == 'pdf':
                return self._process_pdf(document_file)
            elif file_type == 'docx':
                return self._process_docx(document_file)
            elif file_type == 'txt':
                return self._process_txt(document_file)
            elif file_type == 'xlsx':
                return self._process_xlsx(document_file)
            elif file_type == 'csv':
                return self._process_csv(document_file)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported document type: {file_type}'
                }
                
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_pdf(self, pdf_file) -> Dict[str, Any]:
        """Process PDF document"""
        
        # Placeholder - in production use PyPDF2, pdfplumber, or similar
        return {
            'success': True,
            'content': '[PDF обработка требует настройки библиотеки PyPDF2]',
            'page_count': 1,
            'text_length': 0,
            'metadata': {}
        }
    
    def _process_docx(self, docx_file) -> Dict[str, Any]:
        """Process DOCX document"""
        
        # Placeholder - in production use python-docx
        return {
            'success': True,
            'content': '[DOCX обработка требует настройки библиотеки python-docx]',
            'word_count': 0,
            'paragraph_count': 0
        }
    
    def _process_txt(self, txt_file) -> Dict[str, Any]:
        """Process plain text file"""
        
        try:
            if hasattr(txt_file, 'read'):
                content = txt_file.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
            else:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            return {
                'success': True,
                'content': content,
                'character_count': len(content),
                'word_count': len(content.split()),
                'line_count': len(content.splitlines())
            }
            
        except Exception as e:
            logger.error(f"TXT processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_xlsx(self, xlsx_file) -> Dict[str, Any]:
        """Process Excel spreadsheet"""
        
        # Placeholder - in production use openpyxl or pandas
        return {
            'success': True,
            'content': '[Excel обработка требует настройки библиотеки openpyxl]',
            'sheet_count': 1,
            'row_count': 0,
            'column_count': 0
        }
    
    def _process_csv(self, csv_file) -> Dict[str, Any]:
        """Process CSV file"""
        
        try:
            import csv
            import io
            
            if hasattr(csv_file, 'read'):
                content = csv_file.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                csv_file = io.StringIO(content)
            
            reader = csv.reader(csv_file)
            rows = list(reader)
            
            if rows:
                headers = rows[0] if rows else []
                data_rows = rows[1:] if len(rows) > 1 else []
                
                return {
                    'success': True,
                    'content': f'CSV файл с {len(headers)} колонками и {len(data_rows)} строками данных',
                    'headers': headers,
                    'row_count': len(data_rows),
                    'column_count': len(headers),
                    'sample_data': data_rows[:3] if data_rows else []
                }
            else:
                return {
                    'success': True,
                    'content': 'Пустой CSV файл',
                    'headers': [],
                    'row_count': 0,
                    'column_count': 0
                }
                
        except Exception as e:
            logger.error(f"CSV processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }