import winsound
import pyautogui
import string
import pypresence
from pypresence import Client
import configparser
import requests
import speech_recognition as sr

from deepgram import (
    DeepgramClient,
    LiveOptions,
    LiveTranscriptionEvents,
    Microphone,
    DeepgramClientOptions,
    PrerecordedOptions,
    FileSource,
)
## Configs and vars


config = configparser.ConfigParser()
config.read('settings.properties')

for section in config.sections():
    for key in config[section]:
        globals()[key] = config[section][key]
recording=False
deepgram = DeepgramClient(deepgram_api_key)
discord_dead = False
on = False
client = Client(discord_client_id)
client.start()
file_options: PrerecordedOptions = PrerecordedOptions(
    model="nova-2-general",
    smart_format=True,
    punctuate=True,
    language="en",
)
# Create a websocket connection to Deepgram
live_options = LiveOptions(
    language="en-US",
    model="nova-2",
    encoding="linear16",
    channels=1,
    sample_rate=16000,
    smart_format=True,
    utterance_end_ms=1000,
    interim_results=True,
)


def preprocess(enabling=False):

    if discord_dead or disable_discord.lower() == "true":
        pass
    else:
        client.set_voice_settings(mute=enabling)
import datetime

do_stop = False
last_words = None
last_end = None
def on_message(self, result=None, **kwargs):
    global do_stop
    global last_words
    global last_end
    if result is None:
        return
    if not result.is_final:
        return
    sentence = result.channel.alternatives[0].transcript
    if len(sentence) == 0:
        return
    last_words = datetime.datetime.now()
    if result.speech_final:
        last_end = datetime.datetime.now()
    #print(result)
    entercheck = ''.join(ch for ch in sentence if ch not in set(string.punctuation))
    entercheck = entercheck.lower().strip()

    if entercheck == "enter":
        pyautogui.hotkey('enter')
        return
    elif entercheck == "invoke" or entercheck == "evoke":
        do_stop = True
        return
    pyautogui.write(sentence + " ")
    #print(f"Transcription: {sentence}")

def on_metadata(self, metadata=None,  **kwargs):
    if metadata is None:
        return
    #print(f"\n{metadata}\n")


def on_error(self, error, **kwargs):
  print(f"Error: {error}")
  stop_recording()

microphone = None
dg_connection = None
def start_recording():

    preprocess(True)
    global microphone
    global dg_connection
    global recording
    dg_connection = deepgram.listen.live.v("1")
    dg_connection.start(live_options)

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    # create microphone
    microphone = Microphone(dg_connection.send)

    # start microphone
    global last_words
    global last_end
    last_end = datetime.datetime.now()
    last_words = datetime.datetime.now()
    recording = True
    microphone.start()

    print("Started Recording...")
    winsound.PlaySound("*", winsound.SND_ALIAS)

def stop_recording():
    global microphone
    global dg_connection
    global recording

    try:
        # Wait for the microphone to close
        microphone.finish()
    except:
        pass
    preprocess(False)
    try:
        # Indicate that we've finished
        dg_connection.finish()
    except:
        pass
    recording = False

    filename = "enabled.lock"

    file_path = Path(filename)
    if file_path.exists():
        file_path.unlink()
    print("Stopped recording...")

def auth():
    global discord_access_token
    global config
    code = client.authorize(discord_client_id,["rpc.voice.read","rpc.voice.write","rpc"])['data']['code']
    data = {
        'client_id': discord_client_id,
        'client_secret': discord_client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'http://localhost:3012/auth',
        'scope': 'rpc'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    token_response = response.json()

    discord_access_token = token_response['access_token']

    config.set('options', 'discord_access_token', discord_access_token)

    with open('settings.properties', 'w') as configfile:
        config.write(configfile)

if 'discord_access_token' not in globals() or not globals()['discord_access_token']:
    auth()
try:
    client.authenticate(discord_access_token)
except pypresence.exceptions.ServerError:
    auth()
    try:
        client.authenticate(discord_access_token)
    except pypresence.exceptions.ServerError:
        discord_dead = True


def toggle_recording():
    global recording
    if not recording:
        print("Start recording")
        start_recording()  # Start the recording
        recording = True

# Start listening for the activation phrase
r = sr.Recognizer()

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

prerecord = False

def on_created(event):
    global recording
    if Path(event.src_path).name == "enabled.lock":
        print("enabled.lock has been created")
        if not recording:
            print("Start recording")
            if prerecord:
                prerecorded()
            else:
                start_recording()  # Start the recording
                recording = True


def on_deleted(event):
    global recording
    if Path(event.src_path).name == "enabled.lock":
        if recording:
            print("Stop recording")
            stop_recording()  # Stop the recording
            recording = False


event_handler = FileSystemEventHandler()
event_handler.on_created = on_created
event_handler.on_deleted = on_deleted

observer = Observer()
observer.schedule(event_handler, path='.', recursive=False)
observer.start()

print("Listening...")
import threading
import io
import pyaudio
import audioop
import wave

from math import ceil

def record_audio_to_buffer(silence_duration_ms):

    # set audio configurations
    chunk = 1024  # chunk of audio to read at a time
    format = pyaudio.paInt16  # 16 bit integer
    channels = 1  # mono audio
    rate = 44100  # sample rate

    # calculate number of chunks equivalent to silence_duration_ms
    silence_duration_seconds = silence_duration_ms / 1000
    num_silent_chunks = ceil(silence_duration_seconds * rate / chunk)  # ceil to make sure not to miss short silences

    # create PyAudio object
    p = pyaudio.PyAudio()

    stream = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

    print("Recording...")

    frames = []
    silence_threshold = 1000  # silence threshold
    silent_chunks_counter = 0  # counter for silent chunks

    while True:
        data = stream.read(chunk)
        frames.append(data)

        rms = audioop.rms(data, 2)  # get rms value
        if rms < silence_threshold:
            silent_chunks_counter += 1
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
    wf.setsampwidth(p.get_sample_size(format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

    # set buffer position to start
    buffer.seek(0)

    return buffer


def prerecorded():
    preprocess(True)
    payload: FileSource = {
        "buffer": record_audio_to_buffer(3000),
    }
    preprocess(False)

    response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, file_options)

    print(response.to_json(indent=4))
def check_and_run():
    global do_stop
    global last_end
    global last_words
    while True:
        time.sleep(1)
        #Ensure we don't get dinged 200$ for leaving the mic open
        if last_words and recording and not do_stop:
            if datetime.datetime.now() - last_words > datetime.timedelta(seconds=12) or datetime.datetime.now() - last_end > datetime.timedelta(seconds=12):
                do_stop = True
                print("Stopping inactive recording - " + str(((datetime.datetime.now() - last_words))) + " - " + str(((datetime.datetime.now() - last_end))))
        if do_stop:
            do_stop = False
            stop_recording()

activity_watch = False
if activity_watch:
    thread = threading.Thread(target=check_and_run)
    thread.start()
try:
    while True:  # endless loop
        with sr.Microphone() as source:
            audio = r.listen(source)

        try:
            # use "sphinx" instead of "google" for offline speech recognition
            text = r.recognize_sphinx(audio)
            #print('You said : {}'.format(text))

            if "invoke" in text or "evoke" in text:
                if prerecord:
                    prerecorded()
                else:
                    toggle_recording()  # Assuming toggle_recording() can handle a None argument

        except sr.UnknownValueError:
            print("Sphinx could not understand audio")
        except sr.RequestError as e:
            print("Sphinx error; {0}".format(e))

except KeyboardInterrupt:
    observer.stop()
observer.join()