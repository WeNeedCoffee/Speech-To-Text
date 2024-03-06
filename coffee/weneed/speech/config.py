import configparser


class Config:
    def __init__(self, file_name):
        self.file_name = file_name
        print(file_name)

    def get_config(self, section, key):
        config = configparser.ConfigParser()
        config.read(self.file_name)
        if not config.has_option(section, key):
            self.set_config(section, key, key)
            return None
        value = config.get(section, key)

        # Convert booleans read from the ini as strings to proper booleans
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        elif value.lower() == key:
            return None
        try:
            return int(value)  # return int if parsable as int
        except ValueError:
            return value

    def set_config(self, section, key, value):
        config = configparser.ConfigParser()
        config.read(self.file_name)
        if section not in config.sections():
            config.add_section(section)
        config.set(section, key, value)
        with open(self.file_name, 'w') as configfile:
            config.write(configfile)