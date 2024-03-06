from math import ceil
import pyaudio
import wave
import io
import audioop

from coffee.weneed.speech.config import Config


class AudioRecorder:

    def __init__(self, config: Config):
        self.config = config
        self.chunk = 1024

    def record_audio_to_buffer(self, silence_duration_ms: int) -> io.BytesIO:

        # set audio configurations
        audio_format = pyaudio.paInt16  # 16 bit integer
        channels = self.config.get_config("deepgram", "channels")  # mono audio
        rate = self.config.get_config("deepgram", "samplerate")

        # calculate number of chunks equivalent to silence_duration_ms
        num_silent_chunks = self.calculate_silent_chunks(silence_duration_ms, rate)

        # create PyAudio object
        p = pyaudio.PyAudio()

        stream = p.open(format=audio_format, channels=channels, rate=rate, input=True,
                        frames_per_buffer=self.chunk)

        print("Recording...")

        frames = []
        silence_threshold = 500  # silence threshold
        silent_chunks_counter = 0  # counter for silent chunks

        while True:
            data = stream.read(self.chunk)
            frames.append(data)

            rms = audioop.rms(data, 2)  # get rms value
            if rms < silence_threshold:
                silent_chunks_counter += 1
                print(str(silent_chunks_counter) + " / " + str(self.calculate_ms_from_silent_chunks(silent_chunks_counter, rate)))
            else:
                silent_chunks_counter = 0

            if silent_chunks_counter == num_silent_chunks:
                break

        print("Recording complete.")

        # stop and close stream
        stream.stop_stream()
        stream.close()
        p.terminate()

        # create BytesIO object for in-memory file writing
        buffer = io.BytesIO()

        # write frames to in-memory file
        wf = wave.open(buffer, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(audio_format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        # set buffer position to start
        buffer.seek(0)
        return buffer

    def calculate_silent_chunks(self, silence_duration_ms: int, rate) -> int:
        silence_duration_seconds = silence_duration_ms / 1000
        num_silent_chunks = ceil(
            silence_duration_seconds * rate / self.chunk)  # ceil to make sure not to miss short silences
        return num_silent_chunks

    def calculate_ms_from_silent_chunks(self, silent_chunk_count: int, rate) -> float:
        duration_sec = (silent_chunk_count * self.chunk) / rate
        duration_ms = duration_sec * 1000
        return duration_ms