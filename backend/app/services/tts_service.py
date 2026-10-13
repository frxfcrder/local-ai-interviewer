import os
import pyttsx3
import threading

class TTSService:
    def __init__(self, output_dir: str = "storage/audio", voice: str | None = None):
        self.output_dir = output_dir
        self.voice = voice
        os.makedirs(self.output_dir, exist_ok=True)

        # Lock to ensure pyttsx3 engine thread-safety
        self._lock = threading.Lock()

    def _apply_voice(self, engine: pyttsx3.Engine) -> None:
        """Selects a voice by case-insensitive substring of name or id."""
        if not self.voice:
            return
        needle = self.voice.lower()
        for available in engine.getProperty("voices"):
            if needle in available.name.lower() or needle in available.id.lower():
                engine.setProperty("voice", available.id)
                return
        names = [v.name for v in engine.getProperty("voices")]
        raise RuntimeError(f"TTS voice {self.voice!r} not found. Available: {names}")

    def synthesize_to_file(self, text: str, filename: str = "response.wav") -> str:
        """
        Converts text response into a local audio file synchronously in a thread-safe manner.
        """
        file_path = os.path.join(self.output_dir, filename)

        with self._lock:
            engine = pyttsx3.init()
            self._apply_voice(engine)
            engine.setProperty('rate', 175)  # Speed of speech
            engine.save_to_file(text, file_path)
            engine.runAndWait()

        return file_path
