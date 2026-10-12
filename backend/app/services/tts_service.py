import os
import pyttsx3
import threading

class TTSService:
    def __init__(self, output_dir: str = "storage/audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Lock to ensure pyttsx3 engine thread-safety
        self._lock = threading.Lock()

    def synthesize_to_file(self, text: str, filename: str = "response.wav") -> str:
        """
        Converts text response into a local audio file synchronously in a thread-safe manner.
        """
        file_path = os.path.join(self.output_dir, filename)

        with self._lock:
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)  # Speed of speech
            engine.save_to_file(text, file_path)
            engine.runAndWait()
            
        return file_path