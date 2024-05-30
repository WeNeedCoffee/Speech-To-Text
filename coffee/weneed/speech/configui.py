import configparser
import tkinter as tk

import keyboard


class ConfigGUI:
    def __init__(self, config_file):
        self.root = tk.Tk()
        self.root.title("Configuration Interface")
        self.config_file = config_file

        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.entries = {}
        self.checkbuttons = {}

        self.create_gui()

        save_button = tk.Button(self.root, text="Save Config", command=self.save_config)
        save_button.pack(pady=10)
        self.init_keybindings()
        self.root.mainloop()

    def create_gui(self):
        for section in self.config.sections():
            section_frame = tk.LabelFrame(self.root, text=section, padx=10, pady=10)
            section_frame.pack(fill="both", expand="yes", padx=10, pady=5)

            for key, value in self.config[section].items():
                frame = tk.Frame(section_frame)
                frame.pack(fill="x", pady=2)

                label = tk.Label(frame, text=key, width=20, anchor="w")
                label.pack(side="left")

                if value.lower() in ['true', 'false']:
                    var = tk.BooleanVar(value=value.lower() == 'true')
                    checkbox = tk.Checkbutton(frame, variable=var)
                    checkbox.pack(side="left")
                    self.checkbuttons[(section, key)] = var
                else:
                    entry = tk.Entry(frame)
                    entry.pack(side="left", fill="x", expand="yes")
                    entry.insert(0, value)
                    self.entries[(section, key)] = entry

    def save_config(self):
        for (section, key), entry in self.entries.items():
            self.config[section][key] = entry.get()

        for (section, key), var in self.checkbuttons.items():
            self.config[section][key] = str(var.get())

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def toggle_config(self, section, key):
        if (section, key) in self.checkbuttons:
            current_value = self.checkbuttons[(section, key)].get()
            new_value = not current_value
            self.checkbuttons[(section, key)].set(new_value)
            self.config[section][key] = str(new_value)
            self.save_config()

    def register_keybinding(self, key, section, config_key):
        keyboard.add_hotkey(key, self.toggle_config, args=(section, config_key), suppress=True)

    def init_keybindings(self):
        self.register_keybinding('F23', 'options', 'complete')  # Example additional keybinding
        self.register_keybinding('F22', 'options', 'tasker')  # Example additional keybinding
