# Speech-To-Text Program with Whisper API and PyAudio

## Overview
This is a Python program that utilizes multi-threading and various modules like `pyautogui`, `speech_recognition`, `winsound`, `openai`, and `clipboard` to capture and recognize speech through microphone, use OpenAI's Whisper ASR API to transcribe spoken words to text, and then replace the clipboard content with the text and paste it wherever needed.

## Pre-requisites
Make sure you have installed the necessary python packages listed in the `requirements.txt` file. If not, you can install them using pip:
```bash
pip install -r requirements.txt
```

## Special Instructions
The script uses the function key F22 as a hotkey to mute Discord, so you'll need to bind the Discord mute to F22.

## Usage
Make sure you have placed your Whisper API key in a file named openaikey.txt in the same directory as the script. Once done, simply run the script or activate the provided autohotkey script using win + h to use it or numpad div.
```shell
pythonw speech.py
```
## Note
Any text captured is processed to correct punctuation and replace typed-out slang with text-based alternatives for a more natural reading experience.

## Error Handling
In case of any exceptions / errors while recognizing speech, the script will type "error".