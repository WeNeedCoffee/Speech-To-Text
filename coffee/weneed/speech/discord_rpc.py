import pypresence
import requests

from coffee.weneed.speech.config import Config


class DiscordRPClient:
    def __init__(self, config: Config, client_id=None, client_secret=None, access_token=None):
        self.config = config
        self.discord_dead = False
        self.client_id = client_id if client_id else self.config.get_config('discord', 'client_id')
        self.client_secret = client_secret if client_secret else self.config.get_config('discord',
                                                                                        'client_secret')
        self.access_token = access_token if access_token else self.config.get_config('discord', 'access_token')
        self.client = pypresence.Client(self.client_id)
        self.start()

    def authorize(self):
        code = self.client.authorize(self.client_id, ["rpc.voice.read", "rpc.voice.write", "rpc"])['data'][
            'code']
        return code

    def auth(self):
        if not self.access_token:
            self.access_token = self.obtain_token_from_discord()
            self.config.set_config('discord', 'access_token', self.access_token)

    def obtain_token_from_discord(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post('https://discord.com/api/oauth2/token', data=self.get_token_data(), headers=headers)
        access_token = response.json()['access_token']

        return access_token

    def get_token_data(self):
        code = self.authorize()
        return {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://localhost:3012/auth',
            'scope': 'rpc'
        }

    def start(self):
        try:
            self.client.start()
            self.auth()
            if not self.authenticate_client():
                self.auth()
                self.authenticate_client()
        except:
            return

    def authenticate_client(self):
        try:
            self.client.authenticate(self.access_token)
            self.discord_dead = False
            return True
        except pypresence.exceptions.ServerError:
            self.discord_dead = True
            return False

    def toggle_mic(self, enabling=False):
        try:
            return False if self.discord_dead else self.client.set_voice_settings(mute=enabling)
        except pypresence.exceptions.PipeClosed:
            self.client = pypresence.Client(self.client_id)
            self.start()
            try:
                return False if self.discord_dead else self.client.set_voice_settings(mute=enabling)
            except:
                pass
