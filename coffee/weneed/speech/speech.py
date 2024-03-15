from typing import Optional

import winsound
import pyautogui
import string
import speech_recognition as sr
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import threading
import datetime

from deepgram import (
    DeepgramClient,
    LiveOptions,
    LiveTranscriptionEvents,
    Microphone,
    DeepgramClientOptions,
    PrerecordedOptions,
    FileSource,
)

from coffee.weneed.speech.audio_utils import AudioRecorder
from coffee.weneed.speech.config import Config
from coffee.weneed.speech.discord_rpc import DiscordRPClient


class Speech:
    def __init__(self, directory):
        self.observer = Observer()
        self.config = Config(directory + "config.ini")
        self.discord_client = DiscordRPClient(self.config)
        self.microphone = None
        self.dg_connection = None
        self.recording = False
        self.deepgram = None
        self.do_stop = False
        self.last_words = None
        self.last_end = None
        self.dir = directory
        self.prerecord = self.config.get_config("deepgram", "prerecord")
        self.deepgram_api_key = self.config.get_config("deepgram", "api_key")

        event_handler = FileSystemEventHandler()
        event_handler.on_created = self.on_created
        event_handler.on_deleted = self.on_deleted
        self.observer.schedule(event_handler, path=directory, recursive=False)
        self.observer.start()
        self.delete_lock()
        self.recognize_audio()

    def load_strings_from_file(self, filename):
        with open(self.dir + filename, 'r') as file:
            data = file.read().splitlines()
        return data

    def toggle_recording(self):
        if not self.recording:
            print("Start recording")
            self.start_recording()
            self.recording = True
        else:
            print("Stop recording")
            self.stop_recording()
            self.recording = False

    def delete_lock(self):
        filename = self.dir + "enabled.lock"

        file_path = Path(filename)
        if file_path.exists():
            file_path.unlink()

    def start_recording(self):
        live_options: LiveOptions = LiveOptions(
            language=self.config.get_config("deepgram", "language"),
            model=self.config.get_config("deepgram", "model"),
            encoding=self.config.get_config("deepgram", "encoding"),
            channels=self.config.get_config("deepgram", "channels"),
            sample_rate=self.config.get_config("deepgram", "samplerate"),
            smart_format=self.config.get_config("deepgram", "smart_format"),
            utterance_end_ms=self.config.get_config("deepgram", "utterance_end"),
            interim_results=self.config.get_config("deepgram", "interim_results"),
        )
        self.discord_client.toggle_mic(True)
        self.deepgram = DeepgramClient(self.deepgram_api_key)
        self.dg_connection = self.deepgram.listen.live.v("1")
        self.dg_connection.start(live_options)

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Metadata, self.on_metadata)
        self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)

        self.microphone = Microphone(self.dg_connection.send)

        self.last_end = datetime.datetime.now()
        self.last_words = datetime.datetime.now()
        self.recording = True
        self.microphone.start()

        print("Started Recording...")
        winsound.PlaySound("*", winsound.SND_ALIAS)

    def stop_recording(self):
        try:
            self.microphone.finish()
        except:
            pass
        self.discord_client.toggle_mic(False)
        try:
            self.dg_connection.finish()
        except:
            pass
        self.recording = False
        self.delete_lock()
        print("Stopped recording...")

    def check_and_run(self):
        while True:
            time.sleep(1)
            if self.last_words and self.recording and not self.do_stop:
                if datetime.datetime.now() - self.last_words > datetime.timedelta(
                        seconds=12) or datetime.datetime.now() - self.last_end > datetime.timedelta(seconds=3):
                    self.do_stop = True
                    print(
                        "Stopping inactive recording - " + str(
                            (datetime.datetime.now() - self.last_words)) + " - " + str(
                            (datetime.datetime.now() - self.last_end)))
            if self.do_stop:
                self.do_stop = False
                self.stop_recording()

    def prerecorded(self):
        file_options: PrerecordedOptions = PrerecordedOptions(
            language=self.config.get_config("deepgram", "language"),
            model=self.config.get_config("deepgram", "model"),
            smart_format=self.config.get_config("deepgram", "smart_format"),
            keywords=self.load_strings_from_file("keywords.txt")
        )
        # Create a websocket connection to Deepgram
        self.discord_client.toggle_mic(True)
        buffer = AudioRecorder(self.config).record_audio_to_buffer(self.config.get_config("deepgram", "silence_threshold"))
        self.discord_client.toggle_mic(False)
        self.delete_lock()
        payload: FileSource = {
            "buffer": buffer.getvalue(),
        }
        self.deepgram = DeepgramClient(self.deepgram_api_key)
        try:
            response = self.deepgram.listen.prerecorded.v("1").transcribe_file(payload, file_options)
        except:
            print("err")
            winsound.PlaySound("*", winsound.SND_ALIAS)
            return

        self.on_message(result=response.results)

    def on_created(self, event):
        if Path(event.src_path).name == "enabled.lock":
            print("enabled.lock has been created")
            if not self.recording:
                print("Start recording")
                if self.config.get_config("deepgram", "prerecord"):
                    self.prerecorded()
                else:
                    self.start_recording()
                    self.recording = True
        elif Path(event.src_path).name == "prerecord.lock":
            print("Pre")
            prerecord = True

    def on_deleted(self, event):
        if Path(event.src_path).name == "enabled.lock":
            if self.recording:
                print("Stop recording")
                self.stop_recording()
                self.recording = False
        elif Path(event.src_path).name == "prerecord.lock":
            print("Live")
            prerecord = False

    def on_message(self, result=None, **kwargs):
        if self.config.get_config("deepgram", "prerecord"):
            self.delete_lock()
        if result is None:
            return
        if self.config.get_config("deepgram", "prerecord"):
            sentence = result.channels[0].alternatives[0].transcript
        else:
            sentence = result.channel.alternatives[0].transcript
            if not result.is_final:
                return
            elif not self.config.get_config("deepgram", "activity_watch"):
                self.do_stop = True
        if len(sentence) == 0:
            return
        self.last_words = datetime.datetime.now()
        if not self.config.get_config("deepgram", "prerecord") and result.speech_final:
            self.last_end = datetime.datetime.now()

        entercheck = ''.join(ch for ch in sentence if ch not in set(string.punctuation))
        entercheck = entercheck.lower().strip()

        if entercheck == "enter":
            pyautogui.hotkey('enter')
            return
        elif entercheck == "invoke" or entercheck == "evoke":
            self.do_stop = True
            return

        pyautogui.write(sentence + " ")

    def on_metadata(self, metadata=None, **kwargs):
        pass

    def on_error(self, error, **kwargs):
        print(f"Error: {error}")
        self.stop_recording()

    def recognize_audio(self):
        if self.config.get_config("deepgram", "activity_watch"):
            thread = threading.Thread(target=self.check_and_run)
            thread.start()
        try:
            r = sr.Recognizer()
            while True:  # endless loop
                with sr.Microphone() as source:
                    audio = r.listen(source)

                try:
                    # use "sphinx" instead of "google" for offline speech recognition
                    text = r.recognize_sphinx(audio)

                    if "invoke" in text or "evoke" in text:
                        if self.config.get_config("deepgram", "prerecord"):
                            self.prerecorded()
                        else:
                            self.toggle_recording()

                except sr.UnknownValueError:
                    print("Sphinx could not understand audio")
                except sr.RequestError as e:
                    print("Sphinx error; {0}".format(e))

        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

#time.sleep(3)
#pyautogui.write("sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT")
Speech("C:/Users/Dalet/Documents/speech/")
