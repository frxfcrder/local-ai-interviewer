import os
from faster_whisper import WhisperModel

class STTService:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        # Initialize the local Whisper model (downloads on first run, then air-gapped)
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribes local audio files (wav/mp3) into text.
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        segments, info = self.model.transcribe(audio_file_path, beam_size=5)
        
        # Combine all transcribed segments into a single string
        transcript = " ".join([segment.text for segment in segments])
        return transcript.strip()