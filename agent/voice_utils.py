"""
Voice processing utilities for AI chat assistant
Handles speech-to-text, text-to-speech, and voice message processing
"""
import os
import logging
import tempfile
import whisper
import ffmpeg
from typing import Dict, Any, Optional
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger('agent')

# Global Whisper model (loaded once for efficiency)
_whisper_model = None

def get_whisper_model():
    """Get the global Whisper model instance"""
    global _whisper_model
    if _whisper_model is None:
        try:
            # Load the base model (good balance of speed and accuracy)
            _whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            _whisper_model = None
    return _whisper_model


class VoiceProcessor:
    """Handle voice message processing including STT and TTS"""
    
    def __init__(self):
        self.supported_formats = ['webm', 'wav', 'mp3', 'ogg', 'm4a']
        self.max_duration = 300  # 5 minutes max
    
    def process_voice_message(self, voice_message) -> Dict[str, Any]:
        """
        Process a voice message - transcribe audio to text
        
        Args:
            voice_message: VoiceMessage instance
            
        Returns:
            Dict with processing results
        """
        try:
            voice_message.status = 'processing'
            voice_message.save()
            
            # Get audio file
            audio_file = voice_message.audio_file
            if not audio_file:
                return {
                    'success': False,
                    'error': 'No audio file provided'
                }
            
            # Validate duration
            if voice_message.duration and voice_message.duration > self.max_duration:
                voice_message.status = 'failed'
                voice_message.error_message = 'Audio too long (max 5 minutes)'
                voice_message.save()
                return {
                    'success': False,
                    'error': 'Audio file too long'
                }
            
            # Process transcription
            transcription_result = self._transcribe_audio(audio_file)
            
            if transcription_result['success']:
                voice_message.transcription = transcription_result['text']
                voice_message.confidence = transcription_result.get('confidence', 0.8)
                voice_message.detected_language = transcription_result.get('language', 'ru')
                voice_message.emotion = self._detect_emotion(transcription_result['text'])
                voice_message.status = 'completed'
                voice_message.processed_at = timezone.now()
                
                # Update chat message content with transcription
                if voice_message.chat_message:
                    voice_message.chat_message.content = f"🎤 {voice_message.transcription}"
                    voice_message.chat_message.save()
            else:
                voice_message.status = 'failed'
                voice_message.error_message = transcription_result.get('error', 'Transcription failed')
            
            voice_message.save()
            
            return {
                'success': transcription_result['success'],
                'transcription': voice_message.transcription,
                'confidence': voice_message.confidence,
                'language': voice_message.detected_language,
                'emotion': voice_message.emotion,
                'error': voice_message.error_message if voice_message.status == 'failed' else None
            }
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            voice_message.status = 'failed'
            voice_message.error_message = str(e)
            voice_message.save()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _transcribe_audio(self, audio_file) -> Dict[str, Any]:
        """
        Transcribe audio to text using OpenAI Whisper (free, offline)
        """
        
        try:
            # Get Whisper model
            model = get_whisper_model()
            if not model:
                return {
                    'success': False,
                    'error': 'Whisper model not available'
                }
            
            # Save audio file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                # Read audio data
                if hasattr(audio_file, 'read'):
                    audio_data = audio_file.read()
                    audio_file.seek(0)  # Reset file pointer
                else:
                    with open(audio_file, 'rb') as f:
                        audio_data = f.read()
                
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Convert to WAV format if needed using ffmpeg
                wav_path = temp_file_path + '_converted.wav'
                try:
                    (
                        ffmpeg
                        .input(temp_file_path)
                        .output(wav_path, acodec='pcm_s16le', ac=1, ar='16000')
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    audio_path = wav_path
                except Exception as ffmpeg_error:
                    logger.warning(f"FFmpeg conversion failed, using original: {ffmpeg_error}")
                    audio_path = temp_file_path
                
                # Transcribe with Whisper
                logger.info("Starting Whisper transcription...")
                result = model.transcribe(
                    audio_path,
                    language='ru',  # Default to Russian
                    task='transcribe',
                    fp16=False  # Use fp32 for better compatibility
                )
                
                transcription = result['text'].strip()
                detected_language = result.get('language', 'ru')
                
                # Calculate confidence based on Whisper segments
                segments = result.get('segments', [])
                if segments:
                    avg_confidence = sum(seg.get('avg_logprob', -1) for seg in segments) / len(segments)
                    # Convert log probability to confidence score (0-1)
                    confidence = max(0.1, min(0.95, (avg_confidence + 1) * 0.5))
                else:
                    confidence = 0.8
                
                # Get duration
                duration = get_audio_duration(audio_file)
                
                logger.info(f"Whisper transcription successful: '{transcription[:50]}...' (conf: {confidence:.2f})")
                
                return {
                    'success': True,
                    'text': transcription,
                    'confidence': confidence,
                    'language': detected_language,
                    'duration': duration
                }
                
            finally:
                # Cleanup temporary files
                try:
                    os.unlink(temp_file_path)
                    if os.path.exists(wav_path):
                        os.unlink(wav_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp files: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"Whisper STT error: {e}")
            return {
                'success': False,
                'error': f'Speech-to-text failed: {str(e)}'
            }
    
    def _detect_emotion(self, text: str) -> str:
        """
        Simple emotion detection from transcribed text
        
        Args:
            text: Transcribed text
            
        Returns:
            Detected emotion string
        """
        
        if not text:
            return 'neutral'
        
        text_lower = text.lower()
        
        # Simple keyword-based emotion detection
        emotions = {
            'happy': ['спасибо', 'отлично', 'класс', 'здорово', 'радуюсь', 'рад'],
            'sad': ['грустно', 'печально', 'расстроен', 'жаль', 'плохо'],
            'angry': ['злой', 'бесит', 'раздражает', 'достало', 'ненавижу'],
            'excited': ['круто', 'восторг', 'потрясающе', 'вау', 'супер'],
            'confused': ['не понимаю', 'запутался', 'сложно', 'непонятно'],
            'frustrated': ['не работает', 'проблема', 'ошибка', 'не получается']
        }
        
        emotion_scores = {}
        for emotion, keywords in emotions.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        if emotion_scores:
            return max(emotion_scores, key=emotion_scores.get)
        
        return 'neutral'
    
    def synthesize_speech(self, text: str, language: str = 'ru', voice: str = 'female') -> Optional[bytes]:
        """
        Convert text to speech
        
        Args:
            text: Text to synthesize
            language: Language code
            voice: Voice type
            
        Returns:
            Audio bytes or None if failed
        """
        
        try:
            # Demo implementation - returns None
            # In production, integrate with TTS services like:
            # - Google Text-to-Speech
            # - Azure Speech Services
            # - Yandex SpeechKit
            # - ElevenLabs
            
            logger.info(f"TTS request: {len(text)} chars, language: {language}, voice: {voice}")
            
            # For demo, return None to indicate TTS not configured
            return None
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None


def get_audio_duration(audio_file) -> float:
    """
    Get duration of audio file
    
    Args:
        audio_file: Audio file object
        
    Returns:
        Duration in seconds
    """
    
    try:
        # For demo purposes, estimate duration based on file size
        # In production, use proper audio analysis libraries like:
        # - mutagen
        # - pydub
        # - librosa
        
        file_size = audio_file.size if hasattr(audio_file, 'size') else 1000
        
        # Rough estimate: 1KB per second for compressed audio
        estimated_duration = file_size / 1024
        
        # Cap at reasonable values
        return min(max(estimated_duration, 1.0), 300.0)
        
    except Exception as e:
        logger.error(f"Duration calculation error: {e}")
        return 10.0  # Default duration


def detect_audio_language(audio_file) -> str:
    """
    Detect language from audio file
    
    Args:
        audio_file: Audio file object
        
    Returns:
        Language code (default: 'ru')
    """
    
    try:
        # Demo implementation - always returns Russian
        # In production, implement language detection
        return 'ru'
        
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        return 'ru'


def validate_audio_file(audio_file) -> Dict[str, Any]:
    """
    Validate audio file format and properties
    
    Args:
        audio_file: Audio file object
        
    Returns:
        Validation result dictionary
    """
    
    try:
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024
        if hasattr(audio_file, 'size') and audio_file.size > max_size:
            return {
                'valid': False,
                'error': 'File too large (max 10MB)'
            }
        
        # Check file extension
        filename = audio_file.name if hasattr(audio_file, 'name') else ''
        extension = filename.split('.')[-1].lower() if '.' in filename else ''
        
        supported_formats = ['webm', 'wav', 'mp3', 'ogg', 'm4a']
        if extension not in supported_formats:
            return {
                'valid': False,
                'error': f'Unsupported format. Supported: {", ".join(supported_formats)}'
            }
        
        return {
            'valid': True,
            'format': extension,
            'size': audio_file.size if hasattr(audio_file, 'size') else 0
        }
        
    except Exception as e:
        logger.error(f"Audio validation error: {e}")
        return {
            'valid': False,
            'error': str(e)
        }


class VoiceCommandProcessor:
    """Process voice commands and intents"""
    
    def __init__(self):
        self.commands = {
            'search': ['найди', 'поиск', 'найти', 'искать'],
            'schedule': ['расписание', 'пары', 'занятия', 'лекции'],
            'grades': ['оценки', 'баллы', 'результаты', 'экзамен'],
            'help': ['помощь', 'справка', 'как', 'что делать'],
            'clear': ['очистить', 'удалить', 'сброс', 'начать заново']
        }
    
    def detect_intent(self, transcription: str) -> Dict[str, Any]:
        """
        Detect intent from voice transcription
        
        Args:
            transcription: Transcribed text
            
        Returns:
            Intent detection result
        """
        
        if not transcription:
            return {'intent': 'unknown', 'confidence': 0.0}
        
        text_lower = transcription.lower()
        
        intent_scores = {}
        for intent, keywords in self.commands.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                intent_scores[intent] = score / len(keywords)
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
            
            return {
                'intent': best_intent,
                'confidence': confidence,
                'text': transcription
            }
        
        return {
            'intent': 'general',
            'confidence': 0.5,
            'text': transcription
        }