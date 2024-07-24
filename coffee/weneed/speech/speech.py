import datetime
import string
import threading
import time
from pathlib import Path

import clipboard
import keyboard
import pyautogui
import speech_recognition as sr
import winsound
from deepgram import (
    DeepgramClient,
    LiveOptions,
    LiveTranscriptionEvents,
    Microphone,
    PrerecordedOptions,
    FileSource,
)
from openai import OpenAI
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from coffee.weneed.speech.audio_utils import AudioRecorder
from coffee.weneed.speech.config import Config
from coffee.weneed.speech.configui import ConfigGUI
from coffee.weneed.speech.discord_rpc import DiscordRPClient


class Speech:
    def run_gui(self):
        self.configui = ConfigGUI(self.directory + "config.ini")

    def __init__(self, directory):
        self.directory = directory
        self.observer = Observer()
        self.config = Config(directory + "config.ini")
        self.oro = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.config.get_config("options", "openrouter_key"),
        )
        gui_thread = threading.Thread(target=self.run_gui)
        gui_thread.start()

        self.discord_client = DiscordRPClient(self.config)
        self.microphone = None
        self.dg_connection = None
        self.recording = False
        self.deepgram = None
        self.do_stop = False
        self.last_words = None
        self.last_end = None
        self.dir = directory
        self.toggle2 = False
        self.prerecord = self.config.get_config("deepgram", "prerecord")
        self.deepgram_api_key = self.config.get_config("deepgram", "api_key")
        self.init_keybindings()
        event_handler = FileSystemEventHandler()
        event_handler.on_created = self.on_created
        event_handler.on_deleted = self.on_deleted
        self.observer.schedule(event_handler, path=directory, recursive=False)
        self.observer.start()
        self.delete_lock()
        self.recognize_audio()
        # Keep the main thread alive to listen for global key events
        keyboard.wait()  #

    def load_strings_from_file(self, filename):
        with open(self.dir + filename, 'r') as file:
            data = file.read().splitlines()
        return data

    def init_keybindings(self):
        # keyboard.unregister_hotkey('f5')
        keyboard.add_hotkey("f8", self.do)
        keyboard.add_hotkey("f24", self.do)  # Block the original F24 key event

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
            vad_events=True,
            endpointing=300,
        )
        self.discord_client.toggle_mic(True)
        self.deepgram = DeepgramClient(self.deepgram_api_key)
        self.dg_connection = self.deepgram.listen.live.v("1")

        addons = {
            # Prevent waiting for additional numbers
            "no_delay": "true"
        }
        # self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_open)
        self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Metadata, self.on_metadata)
        # self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, self.on_speech_started)
        # self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, self.on_utterance_end)
        # self.dg_connection.on(LiveTranscriptionEvents.Close, self.on_close)
        # self.dg_connection.on(LiveTranscriptionEvents.Unhandled, self.on_unhandled)
        self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)

        self.dg_connection.start(live_options, addons)
        self.microphone = Microphone(self.dg_connection.send)

        self.last_end = datetime.datetime.now()
        self.last_words = datetime.datetime.now()
        self.recording = True
        self.microphone.start()

        print("Started Recording...")
        winsound.PlaySound("*", winsound.SND_ALIAS)

    def on_speech_started(self, speech_started, **kwargs):
        print(f"Speech Started")

    def on_utterance_end(self, utterance_end, **kwargs):
        print(f"Utterance End")
        global is_finals
        if len(is_finals) > 0:
            utterance = " ".join(is_finals)
            print(f"Utterance End: {utterance}")
            is_finals = []

    def on_open(self, open, **kwargs):
        print(f"Connection Open")

    def on_close(self, close, **kwargs):
        print(f"Connection Closed")

    def on_metadata(self, metadata, **kwargs):
        print(f"Metadata: {metadata}")

    def on_unhandled(self, unhandled, **kwargs):
        print(f"Unhandled Websocket Message: {unhandled}")

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

    def mic(self, mic):
        try:
            self.discord_client.toggle_mic(mic)
        except:
            winsound.PlaySound("*", winsound.SND_ALIAS)

    def prerecorded(self):
        if not self.config.get_config("deepgram", "use"):
            return self.prerecorded_oai()
        else:
            return self.prerecorded_dg()

    def process(self, text):
        if self.config.get_config("options", "complete") and ((self.config.get_config("deepgram",
                                                                                      "use") and self.config.get_config(
            "deepgram", "prerecord")) or not self.config.get_config("deepgram", "use")):
            try:
                completion = self.oro.chat.completions.create(
                    model=self.config.get_config("options", "model"),
                    messages=[

                        {"role": "system",
                         "content": self.config.get_config("options", "sys")},
                        {"role": "user", "content": text}

                    ],
                )
                text = completion.choices[0].message.content
            except Exception as e:
                print(e)
                try:
                    completion = self.oro.chat.completions.create(
                        model=self.config.get_config("options", "backup_model"),
                        messages=[

                            {"role": "system",
                             "content": self.config.get_config("options", "sys")},
                            {"role": "user", "content": text}

                        ],
                    )
                    text = completion.choices[0].message.content
                except Exception as ee:
                    print(ee)
        if self.config.get_config("options", "tasker"):
            try:
                completion = self.oro.chat.completions.create(
                    model=self.config.get_config("options", "backup_model"),
                    messages=[

                        {"role": "system",
                         "content": self.config.get_config("options", "sys2")},
                        {"role": "user", "content": text}

                    ],
                )
                text = completion.choices[0].message.content
            except Exception as e:
                print(e)
        print(text)
        entercheck = ''.join(ch for ch in text if ch not in set(string.punctuation))
        entercheck = entercheck.lower().strip()

        if entercheck == "enter":
            pyautogui.hotkey('enter')
            return
        if self.config.get_config("options", "paste"):
            old_clipboard_content = clipboard.paste()
            clipboard.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            clipboard.copy(old_clipboard_content)
        else:
            pyautogui.write(text + " ")

    def prerecorded_oai(self):

        r = sr.Recognizer()
        OPENAI_API_KEY = self.config.get_config("options", "openai_api_key")
        try:
            with sr.Microphone() as source:

                self.mic(True)
                audio = r.listen(source)
                self.mic(False)
                self.delete_lock()
                text = r.recognize_whisper_api(audio, api_key=OPENAI_API_KEY)
                self.process(text)

        except Exception as e:
            print(e)
            self.recording = False
            self.delete_lock()
            self.discord_client.toggle_mic(False)
            print("Stopped recording...")

    def prerecorded_dg(self):
        file_options: PrerecordedOptions = PrerecordedOptions(
            language=self.config.get_config("deepgram", "language"),
            model=self.config.get_config("deepgram", "model"),
            smart_format=self.config.get_config("deepgram", "smart_format"),
            keywords=self.load_strings_from_file("keywords.txt"),
            utterances=True,
            punctuate=True,
        )
        # Create a websocket connection to Deepgram
        self.mic(True)

        buffer = AudioRecorder(self.config).record_audio_to_buffer(
            self.config.get_config("deepgram", "silence_threshold"))
        self.mic(False)
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
        try:
            text = response.results.channels[0].alternatives[0].paragraphs.transcript
            if text.startswith("\n"):
                text = text[1:]

            self.process(text)
        except Exception as e:
            print(e)
            winsound.PlaySound("*", winsound.SND_ALIAS)
            return

    def do(self):
        if not self.recording:
            print("Start recording")
            if self.config.get_config("deepgram", "prerecord"):
                self.prerecorded()
            elif self.config.get_config("deepgram", "use"):
                self.toggle_recording()
            else:
                self.start_recording()
                self.recording = True

    def on_created(self, event):
        if Path(event.src_path).name == "enabled.lock":
            print("enabled.lock has been created")
            self.do()
        elif Path(event.src_path).name == "prerecord.lock":
            print("Pre")
            self.toggle2 = True

    def on_deleted(self, event):
        if Path(event.src_path).name == "enabled.lock":
            if self.recording:
                print("Stop recording")
                self.stop_recording()
                self.recording = False
        elif Path(event.src_path).name == "prerecord.lock":
            print("Live")
            self.toggle2 = False

    def on_message(self, result, **kwargs):
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

        #        pyautogui.write(sentence + " ")
        self.process(sentence)

    def on_error(self, error, **kwargs):
        print(f"Error: {error}")
        self.stop_recording()

    def recognize_audio(self):
        if self.config.get_config("deepgram", "activity_watch"):
            thread = threading.Thread(target=self.check_and_run)
            thread.start()
        # try:
        #     r = sr.Recognizer()
        #     while True:  # endless loop
        #         with sr.Microphone() as source:
        #             audio = r.listen(source)
        #
        #         try:
        #             # use "sphinx" instead of "google" for offline speech recognition
        #             text = r.recognize_sphinx(audio)
        #
        #             if "invoke" in text or "evoke" in text:
        #                 if self.config.get_config("deepgram", "prerecord"):
        #                     self.prerecorded()
        #                 else:
        #                     self.toggle_recording()
        #
        #         except sr.UnknownValueError:
        #             print("Sphinx could not understand audio")
        #         except sr.RequestError as e:
        #             print("Sphinx error; {0}".format(e))

        # except KeyboardInterrupt:
        #     self.observer.stop()
        # self.observer.join()


def run():
    Speech("C:/Users/Dalet/Documents/speech/")


if __name__ == "__main__":
    # t = threading.Thread(target=run)
    # t.start()
    run()
