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
    Microphone
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

# Create a websocket connection to Deepgram
options = LiveOptions(
    language="en-US",
    model="nova-2",
    encoding="linear16",
    channels=1,
    sample_rate=16000,
    smart_format=True,
    utterance_end_ms=1500,
    interim_results=True,
)


def preprocess(enabling=False):

    if discord_dead or disable_discord.lower() == "true":
        winsound.PlaySound("*", winsound.SND_ALIAS)
    else:
        client.set_voice_settings(mute=enabling)



def on_message(self, result=None, **kwargs):
    if result is None:
        return
    if not result.is_final:
        return
    sentence = result.channel.alternatives[0].transcript
    if len(sentence) == 0:
        return

    print(result)
    entercheck = ''.join(ch for ch in sentence if ch not in set(string.punctuation))
    entercheck = entercheck.lower().strip()

    if entercheck == "enter":
        pyautogui.hotkey('enter')
        return
    elif entercheck == "invoke":
        return
    pyautogui.write(sentence + " ")
    if result.speech_final:
        stop_recording()
    #print(f"Transcription: {sentence}")

def on_metadata(self, metadata=None,  **kwargs):
    if metadata is None:
        return
    #print(f"\n{metadata}\n")


def on_error(self, error, **kwargs):
  print(f"Error: {error}")

microphone = None
dg_connection = None
def start_recording():
    global microphone
    global dg_connection
    global recording
    dg_connection = deepgram.listen.live.v("1")
    dg_connection.start(options)

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    # create microphone
    microphone = Microphone(dg_connection.send)

    # start microphone
    preprocess(True)
    recording = True
    microphone.start()

    print("Started Recording...")

def stop_recording():
    global microphone
    global dg_connection
    global recording
    # Wait for the microphone to close
    microphone.finish()
    preprocess(False)
    # Indicate that we've finished
    dg_connection.finish()
    recording = False

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
    if recording:
        print("Stop recording")
        stop_recording()  # Stop the recording
        recording = False
    else:
        print("Start recording")
        start_recording()  # Start the recording
        recording = True

# Start listening for the activation phrase
r = sr.Recognizer()

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler



def on_created(event):
    global recording
    if Path(event.src_path).name == "enabled.lock":
        print("enabled.lock has been created")
        if not recording:
            print("Start recording")
            start_recording()  # Start the recording
            recording = True


def on_deleted(event):
    global recording
    if Path(event.src_path).name == "enabled.lock":
        print("enabled.lock has been deleted")
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

try:
    while True:  # endless loop
        with sr.Microphone() as source:
            audio = r.listen(source)

        try:
            # use "sphinx" instead of "google" for offline speech recognition
            text = r.recognize_sphinx(audio)
            #print('You said : {}'.format(text))

            if "invoke" in text:
                toggle_recording()  # Assuming toggle_recording() can handle a None argument

        except sr.UnknownValueError:
            print("Sphinx could not understand audio")
        except sr.RequestError as e:
            print("Sphinx error; {0}".format(e))

except KeyboardInterrupt:
    observer.stop()
observer.join()