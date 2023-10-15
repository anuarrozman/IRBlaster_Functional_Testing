import tkinter as tk
from tkinter import ttk
import serial
from tkinter import messagebox
import threading
import queue
import serial.tools.list_ports
import configparser
import json
import os
import base64
#from cryptography import fernet
import time
import sys
from datetime import datetime

class SerialConfigurationWindow:
    def __init__(self, parent):
        self.parent = parent
        self.config_window = tk.Toplevel(self.parent)
        self.config_window.title("Serial Configuration")
        self.selected_baud_rate = tk.StringVar(value="19200")
        self.selected_data_bits = tk.StringVar(value="8")
        self.selected_stop_bits = tk.StringVar(value="1")
        self.selected_parity = tk.StringVar(value="None")

        self.create_configuration_widgets()
        self.load_settings()  # Load saved settings

    def create_configuration_widgets(self):
        self.baud_rate_label = ttk.Label(self.config_window, text="Baud Rate:")
        self.baud_rate_label.pack(padx=10, pady=5)

        baud_rate_options = ["9600", "19200", "38400", "57600", "115200"]
        self.baud_rate_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_baud_rate, values=baud_rate_options)
        self.baud_rate_combobox.pack(padx=10, pady=5)

        # Add other configuration widgets here
        self.data_bits_label = ttk.Label(self.config_window, text="Data Bits:")
        self.data_bits_label.pack(padx=10, pady=5)

        data_bits_options = ["5", "6", "7", "8"]
        self.data_bits_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_data_bits, values=data_bits_options)
        self.data_bits_combobox.pack(padx=10, pady=5)

        self.stop_bits_label = ttk.Label(self.config_window, text="Stop Bits:")
        self.stop_bits_label.pack(padx=10, pady=5)

        stop_bits_options = ["1", "1.5", "2"]
        self.stop_bits_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_stop_bits, values=stop_bits_options)
        self.stop_bits_combobox.pack(padx=10, pady=5)

        self.parity_label = ttk.Label(self.config_window, text="Parity:")
        self.parity_label.pack(padx=10, pady=5)

        parity_options = ["None", "Even", "Odd", "Mark", "Space"]
        self.parity_combobox = ttk.Combobox(self.config_window, textvariable=self.selected_parity, values=parity_options)
        self.parity_combobox.pack(padx=10, pady=5)

        self.save_button = ttk.Button(self.config_window, text="Save", command=self.save_settings)
        self.save_button.pack(padx=10, pady=10)

        self.set_default_button = ttk.Button(self.config_window, text="Set to Default", command=self.set_default_settings)
        self.set_default_button.pack(padx=10, pady=10)
        
    def save_settings(self):
        config = configparser.ConfigParser()
        config["Serial"] = {
            "baud_rate": self.selected_baud_rate.get(),
            "data_bits": self.selected_data_bits.get(),
            "stop_bits": self.selected_stop_bits.get(),
            "parity": self.selected_parity.get()
        }
        with open("settings.ini", "w") as config_file:
            config.write(config_file)

        tk.messagebox.showinfo("Success", "Settings saved successfully!")

    def load_settings(self):
        config = configparser.ConfigParser()
        if "Serial" in config:
            serial_config = config["Serial"]
            self.selected_baud_rate.set(serial_config.get("baud_rate", "19200"))
            self.selected_data_bits.set(serial_config.get("data_bits", "8"))
            self.selected_stop_bits.set(serial_config.get("stop_bits", "1"))
            self.selected_parity.set(serial_config.get("parity", "None"))
                
    def set_default_settings(self):
        self.selected_baud_rate.set("19200")
        self.selected_data_bits.set("8")
        self.selected_stop_bits.set("1")
        self.selected_parity.set("None")
    #
class SerialCommunicationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BW16 Interfacing App")
        self.root.geometry("750x550")
        self.after_id = None
        self.root.lift()
        if not os.path.exists('config.ini'):
            self.create_password()
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.prompt_window = None
        self.configuration_window = None
        self.command_panel_window = None
        self.sending_data = True  # Set the flag to True while sending data
        self.receive_thread_running = False
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        self.data_queue = queue.Queue()  # Initialize data_queue here
        self.load_serial_settings() 
        self.frontend_frame = ttk.LabelFrame(self.root, text="Frontend Window")
        self.frontend_frame.grid(row=0, column=0, columnspan=3, sticky = "NSEW")
        self.pause_receiving = False  # Initialize as not paused
        self.target_baud_rate = 19200
      #  self.root.grid_rowconfigure(1, weight=1)
      #  self.root.grid_columnconfigure(2, weight=1)
        self.available_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.selected_port = tk.StringVar(value=self.available_ports[0] if self.available_ports else "")
        baud_rate = int(self.serial_config["baud_rate"].get())  # Use the loaded value
        
       # self.current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.auto_prompt_window()
        self.prompt_window.lift()
        self.root.grab_release()
        self.backend_frame = None
        self.total_commands = 0  # Total number of commands to send
        self.current_command_index = 0
        self.data_send_monitor = tk.Text(self.backend_frame, height=10, width=40)
        self.front_window()
        self.port_name = self.selected_port.get()
        self.serial_port = serial.Serial()    
      #  self.response_timeout = 2
        self.decode_complete = False
        self.command_queue = queue.Queue()
#Variable for window = self.prompt_window
    def front_window(self):
        self.port_status = tk.StringVar()
        self.mode_status = tk.StringVar()
        self.config_file = tk.StringVar()
        self.mode_status.set("None")
        self.port_status.set("Port Closed")
        self.config_file.set("")
        self.mode_status_label = ttk.Label(self.frontend_frame, textvariable=self.mode_status)
        self.mode_status_label.configure(font=("Georgia", 12, "bold"))
        self.mode_status_label.place(x=40, y=8)
        self.port_status_label = ttk.Label(self.frontend_frame, textvariable=self.port_status)
        self.port_status_label.grid(row=9, rowspan=2, column=1, columnspan=2, padx=5, pady=5, sticky="S")
        self.config_file_label = ttk.Label(self.root, textvariable=self.config_file)
        self.config_file_label.configure(font=("Calibri", 8))
        self.config_file_label.place(x=670, y=530)
        self.port_open_button = ttk.Button(self.frontend_frame, text="Start", command=self.open_port)
        self.port_open_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        self.auto_manual_button = ttk.Button(self.frontend_frame, text="Auto/Manual", command=self.auto_prompt_window)
        self.auto_manual_button.grid(row=5, column=0, sticky="E")
        self.pause_button = ttk.Button(self.frontend_frame, text="Pause/Resume", command=self.toggle_data_receive)
        self.pause_button.place(x=320, y=5)
        self.port_close_button = ttk.Button(self.frontend_frame, text="Stop", command=self.closed_port)
        self.port_close_button.grid(row=0, column=3, columnspan=2, padx=5, pady=5)
        self.data_send_label_frontend = ttk.Label(self.frontend_frame,text = "Command Line")
        self.data_send_label_frontend.grid(row=1, column=0, columnspan=1)
        self.data_send_monitor_front_end = tk.Text(self.frontend_frame, height=20, width=42)
        self.data_send_monitor_front_end.grid(row=2, rowspan=2, column=0, columnspan=2, padx=5, pady=5)
        self.data_send_monitor_front_end.configure()
        self.data_send_label_frontend = ttk.Label(self.frontend_frame,text = "Response")
        self.data_send_label_frontend.grid(row=1, column=2, columnspan=1)
        self.data_receive_monitor = tk.Text(self.frontend_frame, height=20, width=43)
        self.data_receive_monitor.grid(row=2, column=2, columnspan=4, padx=5, pady=5, sticky="E")
      #  x_scrollbar = tk.Scrollbar(root, orient=tk.HORIZONTAL, command=self.data_receive_monitor.xview)
      #  x_scrollbar.place(x=500, y=400, width=200) 
        self.clear_log_button = ttk.Button(self.frontend_frame, text="Clear Log", command=self.clear_log_frontend)
        self.clear_log_button.grid(row=5, column=1, columnspan=2)
        self.password_label = ttk.Label(root, text="Password:")
        self.password_label.place(x=220, y=485)
        scrollbar = tk.Scrollbar(self.frontend_frame, command=self.data_send_monitor_front_end.yview)
        scrollbar.place(x=340, y=55, height=330)
        self.data_send_monitor_front_end.config(yscrollcommand=scrollbar.set)
        scrollbar2 = tk.Scrollbar(self.frontend_frame, command=self.data_receive_monitor.yview)
        scrollbar2.place(x=700, y=55, height=330)
        self.data_receive_monitor.config(yscrollcommand=scrollbar2.set)
        self.password_entry = ttk.Entry(root, show="*")
        self.password_entry.grid(row=6, column=1, padx=5, pady=5, sticky="")
        self.backend_button = ttk.Button(root, text="Open Settings Window", command=self.open_backend_window)
        self.backend_button.grid(row=7, column=1, pady=10)
        self.empty_text = ttk.Label(self.frontend_frame, text="  ")
        self.empty_text.grid(column=6)
        self.receive_thread = None
#####################################################
    def auto_prompt_window(self):
        if self.prompt_window is None:
            self.prompt_window = tk.Toplevel(self.root)
            self.prompt_window_open = True
            self.prompt_window.geometry("200x120+200+200")
            self.prompt_window.title("Operating Mode")
            self.prompt_window_label = ttk.Label(self.prompt_window, text="Please select operating mode")
            self.prompt_window_label.place(x=10, y=20)
            self.prompt_window.focus_force()
            self.auto_mode_button = ttk.Button(self.prompt_window, text="Auto", command=self.auto_mode)
            self.auto_mode_button.place(x=10, y=50)
            self.manual_mode_button = ttk.Button(self.prompt_window, text="Manual", command=self.manual_mode)
            self.manual_mode_button.place(x=10, y=80)
            self.prompt_window.lift()
            self.prompt_window.grab_set()
            self.prompt_window.protocol("WM_DELETE_WINDOW", self.close_prompt_window)
            self.root.wm_attributes('-disabled', True)  # Disable main window

    def find_config_file(self):
        self.find_config_file_window = tk.Toplevel(self.prompt_window)
        self.find_config_file_label = ttk.Label(self.find_config_file_window, text="Please select config file for operation:")
        self.find_config_file_label.place(x=10, y=0)
        script_dir = os.path.dirname(os.path.abspath(__file__)) #retrieve path of py file, 
        executable_dir = os.path.dirname(sys.executable)
        configuration_file = [filename for filename in os.listdir(script_dir) if filename.endswith(".ini")] #read the config file available at
        configuration_file2 = [filename for filename in os.listdir(executable_dir) if filename.endswith(".ini")] #read the config file 
        self.find_config_file_window.geometry("250x240")
        self.find_config_file_window.title("Select Config File")
        config_listbox = tk.Listbox(self.find_config_file_window)
        for config_file in configuration_file:
            config_listbox.insert(tk.END, config_file)
        for config_file in configuration_file2:
            config_listbox.insert(tk.END, config_file)
        config_listbox.grid(padx=40, pady=20)
        select_button = ttk.Button(self.find_config_file_window, text="Select Config File", command=self.compiled_select_config_close)
        select_button.place(x=50, y=200)
        #determine if user close directly the window
        self.find_config_file_window.protocol("WM_DELETE_WINDOW", self.force_close_config_file_window)

    def apply_config_file(self):    #used for apply config file and prompt a find port window
        #check if config file is loaded
        #Permission error: config file not loaded, raise flag 
        self.selected_config = self.find_config_file_window.winfo_children()[1].get(self.find_config_file_window.winfo_children()[1].curselection())
        print(self.selected_config)
        config = configparser.ConfigParser()
        config.read(self.selected_config)
        self.configuration_data = {}
        for section in config.sections():
            self.configuration_data[section] = {}
            for key, value in config.items(section):
                self.configuration_data[section][key] = value
                #value = value of key 
        if self.selected_config and self.selected_port:
            self.port_open_button.config(command=self.test_print)
            self.root.focus_force()
            self.config_load = True
    #########################################################
 #   def calculate_total_commands(self):
        # Calculate the total number of commands to send
   #     for section, options in self.configuration_data.items():
    #        self.total_commands += len(options)

    def test_print(self):
        if self.selected_port:
            for section, options in self.configuration_data.items():           
                for key, value in options.items():
                    value2 = value.encode()
                    self.command_queue.put(value2)  # Put the command in the queue
                    self.data_send_monitor_front_end.insert(tk.END, f"{key}\n")
                    self.data_send_monitor.insert(tk.END, f">> Sent: {value2}\n")
                    self.data_send_monitor.see(tk.END)  

                    # Set a timeout for waiting for decode completion (e.g., 5 seconds)
                    # Wait for decode completion or handle timeout
                    self.wait_for_decode(1)
                    # After decoding is complete, check if there are more commands in the queue
                    if not self.command_queue.empty():
                        next_command = self.command_queue.get()
                        self.serial_port.write(next_command + b'\r\n')
               # Reset the flag for the next command
                    self.decode_complete = False
        elif self.selected_port is None:    
            self.open_port()

    def auto_mode(self):
        self.close_prompt_window()
        self.find_config_file()

    def manual_mode(self):
        self.selected_config = None
        self.mode_status.set("Manual")
        self.mode_status_label.configure(foreground="blue")
        if self.selected_config == None:
                self.port_open_button.config(command=self.open_port)
        self.config_file.set("")
        self.close_prompt_window()

    def compiled_select_config_close(self):
     #  if not serial.SerialException: (if don have permission error)
        try:
            self.apply_config_file()
            self.close_find_config_file_window() #close window
            self.create_port_connection_window() #prompt connect to port window
       #     self.mode_status.set("Auto")
        #    self.mode_status_label.configure(foreground="blue")
        #    self.config_file.set(self.selected_config)

        except serial.SerialException:
                self.close_find_config_file_window() #close window
                tk.messagebox.showerror("Permission error", f"{self.port_name} is opened.")

       #  except:
       #     pass
     #self.serial_port get from self.port_name
     #   self.config_file_label.configure(foreground="black")
      #  self.permission_error()
            
    def create_port_connection_window(self):
        self.port_window = tk.Toplevel(self.find_config_file_window)
        self.port_window.geometry("+200+200")
        self.port_window.lift()
        self.label = ttk.Label(self.port_window, text="Searching for Port")
        self.label.pack(padx=20, pady=20)
        self.running = True
        def animate():
            # Update the label's text
            current_text = self.label["text"]
            new_text = current_text + "." if len(current_text) < 10 else "Searching for port"
            self.label["text"] = new_text
            # Schedule the next animation frame
            if self.available_ports is None:
                self.root.after(5, animate)
            else:
                self.open_port()
                
        animate()
        self.close_port_connection_window()
        self.mode_status.set("Auto")
        self.mode_status_label.configure(foreground="blue")
        self.config_file.set(self.selected_config)

    def open_command_panel(self):
        if hasattr(self, "command_panel_window") and self.command_panel_window is not None and self.command_panel_window.winfo_exists():
            self.command_panel_button.config(state=tk.DISABLED)
            tk.messagebox.showinfo("Error", "Command panel is already open.")
            self.command_panel_button.config(state=tk.NORMAL)
            self.command_panel_window.lift()

        elif self.command_panel_window is None:
            self.command_panel_window = tk.Toplevel(self.root)
            self.command_panel_window.title("Command Panel")
            self.command_panel_window.protocol("WM_DELETE_WINDOW", self.close_command_panel)
            data = {
                    "power": "on",
                    "fan": "high",
                    "mode": "heat",
                "hlouver": "off",
                    "vlouver": "off",
                    "temperature": "22.0",
                    "fid": "power"
                }
            json_data = json.dumps(data).encode()
            read_frame = ttk.LabelFrame(self.command_panel_window, text="Read Buttons")
            read_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

            command_frame = ttk.LabelFrame(self.command_panel_window, text="Command Buttons")
            command_frame.grid(row=0, column=1, columnspan=2, padx=10, pady=10, sticky="nsew")

            wifi_frame = ttk.LabelFrame(self.command_panel_window, text="WiFi Control")
            wifi_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

            IR_frame = ttk.LabelFrame(self.command_panel_window, text="IR Control")
            IR_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

            control_frame = ttk.LabelFrame(self.command_panel_window, text="Control Mode")
            control_frame.grid(row=0, column=4, columnspan=1, padx=10, pady=10, sticky="nsew")

            vflap_frame = ttk.LabelFrame(self.command_panel_window, text="Vflap")
            vflap_frame.grid(row=0, column=6, columnspan=1, padx=10, pady=10, sticky="nsew")

            hflap_frame = ttk.LabelFrame(self.command_panel_window, text="Hflap")
            hflap_frame.grid(row=0, column=7, columnspan=1, padx=10, pady=10, sticky="nsew")

            command_file = 'command.ini'
            if os.path.exists(command_file):
                # If it exists, read the configuration file
                self.command = configparser.ConfigParser()
                self.command.read(command_file)
            else:
                # If it doesn't exist, create a new ConfigParser object
                self.command = configparser.ConfigParser()
                ini_file = "command.ini"
                self.command.read(ini_file)
                
            read_command = [
                ("Product Info", b"3:PRD?\r\n"),
                ("Firmware Version", b"3:FWV?\r\n"),
                ("Hardware Version", b"3:HWV?\r\n"),
                ("DID", b"3:DID?\r\n"),
                ("Device info", b"3:deviceinfo?\r\n"),
                ("Current state",b"3:current_state?\r\n"),
                ("Current status", b"3:current_status?\r\n"),
                ("IR device configuration", b"3:irdevconf?\r\n"),
                ]
            
            command_control = [
            ("reboot",b"3:reboot-\r\n"),
            ("Factory Reset", b"3:factoryRST-\r\n"),
            ("Revert Firmware", b"3:revertFW-\r\n"),
            ("New Firmware", b"3:newFW-\r\n"),
            ("test_bcastM", b"3:test_bcastM-\r\n"),
            ("test_httpc",b"3:test_httpc-\r\n"),
            ("hello", b"3:hello-\r\n"),
            ("upgrade firmware", b"3:upgradeFW-\r\n"),
            ("FileIDFW", b"3:FileIDFW-\r\n"),
            ("Save Data", b"3:saveData-\r\n"),
            ("Read Data", b"3:readData-\r\n"),
            ("Debug Data", b"3:debugData-\r\n"),
            ("Erase Data", b"3:eraseData-\r\n"),
            ("Flash", b"3:flash-\r\n"),
            ("Write Product info", b"3:PRD-\r\n"),
            ("Write Hardmware Version", b"3:HWV-\r\n"),
            ("SRN0", b"3:SRN0-\r\n"),
            ("SRN1", b"3:SRN1-\r\n"),
            ("Debug0", b"3:Debug0-\r\n"),
            ("SRN1", b"3:SRN1-\r\n"),
            ("AID", b"3:AID-\r\n"),
            ("send", b"3:send-\r\n"),
            ("temperature", b"3:temp-\r\n"),
            ("run status", b"3:runStatus-\r\n"),
            ]
            wifi_control = [
                ("connectwifi", b"3:connectwifi-\r\n"),
                ("disconnectwifi", b"3:disconnectwifi-\r\n"),
                ("erasewifi", b"3:erasewifi-\r\n"),
                ("showwifi", b"3:showwifi-\r\n"),
                ("startap", b"3:startap-\r\n"),
            ]

            IR_control = [
            ("Set IR Library", b"3:irdev-B079010FE20FE20FE20F000100103600240ED80100000000100010001000320100000200051E0900001003C900860041090800100536008600410910001005360086004100240011DA2700C50000D711DA27004200005411DA270000392000A0000006600000C18000C5151E051501D4D80F051502D4D800081E003840004048D7081E013840104048E70B1003C8CC0A03C8CC0303C8CC0503C8CC071616045F004806043F003606083F04123704153F091E37040C0803CCD00F03CCD00000D4070104000216080605040111232302030217020A1A03B0B40303B0B40403B0B40006B0B406B8C03206B0B402B8C0C0170A1E05010300051E010100147F04090A081205036108064807801603F016010A078089C008890B06200100021B1C4149C13C007800B400F0002C016801A401E0011C0258029402D002010505036109063607801603F016010D078089C009890B061A0100021C1D414991C6038607460B060FC6128616461A061EC6210105060001A11E0001060001B1210084\r\n"),
            ("Send IR Signal", json_data),
            ("IR device configuration",b"3:irdevconf-\r\n"),
            ("IR transmit configuration", b"3:irtxconf-\r\n"),
            ("IR transmit data", b"3:irtxdata-\r\n"),
            ("IR library", b"3:irlib-\r\n"),
            ]

            control_buttons_command=[
                ("on aircon", b"3:on_ac-\r\n"),
                ("off aircon", b"3:off_ac-\r\n"),
                ("cool mode", b"3:cool_mode-\r\n"),
                ("heat mode", b"3:heat_mode-\r\n"),
                ("auto mode", b"3:auto_mode-\r\n"),
                ("fan mode", b"3:fan_mode-\r\n"),
                ("dry mode", b"3:dry_mode-\r\n")
            ]

            fan_mode_control=[
                ("auto fan", b"3:auto_fan-\r\n"),
                ("turbo fan", b"3:turbo_fan-\r\n"),
                ("high fan", b"3:high_fan-\r\n"),
                ("medium fan", b"3:med_fan-\r\n"),
                ("low fan", b"3:low_fan-\r\n"),
                ("quiet fan", b"3:quiet_fan-\r\n"),
            ]

            vflap_control=[
                ("ON vflap", b"3:on_vflap-\r\n"),
                ("OFF vflap", b"3:off_vlap-\r\n"),
                ("top vflap", b"3:top_vflap-\r\n"),
                ("bottom vflap", b"3:bottom_vflap-\r\n"),
            ]

            hflap_control=[
                ("ON hflap", b"3:on_hflap-\r\n"),
                ("OFF hflap", b"3:off_hlap-\r\n"),
                ("left hflap", b"3:top_hflap-\r\n"),
                ("midleft hflap", b"3:bottom_hflap-\r\n"),
                ("mid hflap", b"3:mid_hflap-\r\n"),
                ("midright hflap", b"3:midright_hflap-\r\n"),
                ("right hflap", b"3:right_hflap-\r\n"),
            ]
            if not self.command.has_section('ReadButtons'):
                self.command.add_section('ReadButtons')
                for label, command in read_command:
                    self.command.set('ReadButtons', label, command.decode())

            if not self.command.has_section('CommandButtons'):
                self.command.add_section('CommandButtons')
                for label, command in command_control:
                    self.command.set('CommandButtons', label, command.decode())

            if not self.command.has_section('WifiButtons'):
                self.command.add_section('WifiButtons')
                for label, command in wifi_control:
                    self.command.set('WifiButtons', label, command.decode())

            if not self.command.has_section("IRControl"):
                self.command.add_section("IRControl")
                for label, command in IR_control:
                    self.command.set("IRControl", label, command.decode())

            if not self.command.has_section("ControlButtons"):
                self.command.add_section("ControlButtons")
                for label, command in control_buttons_command:
                    self.command.set("ControlButtons", label, command.decode())
            
            if not self.command.has_section("FanMode"):
                self.command.add_section("FanMode")
                for label, command in fan_mode_control:
                    self.command.set("FanMode", label, command.decode())
            
            if not self.command.has_section("VFlap"):
                self.command.add_section("VFlap")
                for label, command in vflap_control:
                    self.command.set("VFlap", label, command.decode())
            
            if not self.command.has_section("HFlap"):
                self.command.add_section("HFlap")
                for label, command in hflap_control:
                    self.command.set("HFlap", label, command.decode())

            with open('command.ini', 'w') as configfile:
                self.command.write(configfile)

            read_buttons = self.command.items('ReadButtons')
            command_buttons = self.command.items('CommandButtons')
            wifi_buttons = self.command.items('WifiButtons')
            IR_buttons = self.command.items('IRControl')
            Control_buttons = self.command.items('ControlButtons')
            fan_mode_buttons = self.command.items('FanMode')
            Vflap_buttons = self.command.items('VFlap')
            Hflap_buttons = self.command.items('HFlap')
            
            row_read, col_read = 0, 0
            row_command, col_command = 0, 1
            row_IR, col_IR = 1,1
            row_wifi, col_wifi = 0, 4
            row_control, col_control = 0,5
            row_fan, col_fan = 0,6
            row_vflap, col_vflap = 0,7
            row_hflap, col_hflap = 0,8
            command_align = len(command_buttons)//3

            for key, value in read_buttons:
                button = ttk.Button(read_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_read, column=col_read, padx=5, pady=5)
                row_read += 1

            for key, value in command_buttons[:command_align]:
                button = ttk.Button(command_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_command, column=col_command, padx=5, pady=5)
                row_command += 1
            col_command = 2
            row_command = 0

            for key, value in command_buttons[command_align:2*command_align]:
                button = ttk.Button(command_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_command, column=col_command, padx=5, pady=5)
                row_command += 1

            col_command = 3
            row_command = 0
            for key, value in command_buttons[2*command_align:]:
                button = ttk.Button(command_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_command, column=col_command, padx=5, pady=5)
                row_command += 1

            for key, value in wifi_buttons:
                button = ttk.Button(wifi_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_wifi, column=col_wifi, padx=5, pady=5)
                row_wifi += 1

            for key, value in Control_buttons:
                button = ttk.Button(control_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_control, column=col_control, padx=5, pady=5)
                row_control += 1

            for key, value in IR_buttons:
                button = ttk.Button(IR_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_IR, column=col_IR, padx=5, pady=5)
                row_IR += 1

            for key, value in fan_mode_buttons:
                button = ttk.Button(control_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_fan, column=col_fan, padx=5, pady=5)
                row_fan += 1

            for key, value in Vflap_buttons:
                button = ttk.Button(vflap_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_vflap, column=col_vflap, padx=5, pady=5)
                row_vflap += 1

            for key, value in Hflap_buttons:
                button = ttk.Button(hflap_frame, text=key, command=lambda l=key, d=value: self.compiled_function(l, d))
                button.grid(row=row_hflap, column=col_hflap, padx=5, pady=5)
                row_hflap += 1

    def compiled_function(self, key, value):
        self.frontend_display(key)
        self.send_command_data(value+'\r\n')

    def frontend_display(self, label):
        self.data_send_monitor_front_end.insert(tk.END,label+'\n')
        self.data_send_monitor_front_end.see(tk.END)

    def create_password(self):
        self.config = configparser.ConfigParser()
        self.config['Authentication'] = {'password': 'MTIz'}
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
#MTIz = 123
    def send_command_data(self, value):
        if self.serial_port and self.serial_port.is_open:
            value2 = value.encode()
            self.serial_port.write(value2)
            self.data_send_monitor.insert(tk.END, f">> {value2}\n")
            self.data_send_monitor.see(tk.END)
            self.sending_data = True
        elif self.serial_port is None and not self.serial_port:
            tk.messagebox.showerror("Error", "Unable to send data, port is not open")
            
    def update_port_status(self):
        selected_port = self.selected_port.get()
        if self.serial_port and self.serial_port.is_open:
            self.port_status.set(f"Port {selected_port} is Open")
            self.port_status_label.configure(foreground="green")
        else:
            self.port_status.set(f"Port {selected_port} is Closed")
            self.port_status_label.configure(foreground="red")
    
    def receive_data(self):
        self.receive_thread_running = True
        self.receive_data_in_progress = True
        
        while self.serial_port and self.port_name and self.serial_port.is_open:
                if self.pause_receiving:
                    self.pause_event.wait()  # Wait until the event is cleared (resumed)
                else:
                    try:
                        if self.serial_port.baudrate == self.target_baud_rate:
                            data_received = self.serial_port.readline().decode()
                            if data_received:
                                self.data_queue.put(data_received)
                                print(data_received)
                                self.decode_complete = True  # Set the flag when decoding is complete
                            elif data_received is None:
                                pass
                        else:
                            tk.messagebox.showerror("Error", "Incorrect baud rate used. Please use 19200 for baud.")
                            break
                    except serial.SerialException:
                        self.closed_port()
                if not self.serial_port.is_open:
                    break
                        
    def wait_for_decode(self, timeout):
        start_time = time.time()
        while not self.decode_complete: #when not decode complete
            if time.time() - start_time > timeout: 
                time.sleep(0.05)
                break

    def start_receive_thread(self):
        if self.receive_thread_running:
            return  # The thread is already running
        self.pause_event = threading.Event()
        self.receive_thread_running = False
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        self.root.after(1, self.update_received_data) #timeout on reading data input 

    def toggle_data_receive(self):
        if not self.pause_receiving:
            self.pause_event.clear()  # Resume the thread
            self.pause_button.configure()
        else:
            self.pause_event.set()  # Pause the thread
            self.pause_button.configure()
        self.pause_receiving = not self.pause_receiving

    def pause_receiving_process(self):
        self.pause_receiving = True
        
    def resume_receiving_process(self):
        self.pause_receiving = False

    def stop_receive_thread(self):
        if not self.receive_thread_running:
            return  # Verify the thread is running

        def stop_receive_data():
            self.receive_thread_running = False
            print(self.serial_port)
            if self.serial_port and not self.serial_port.is_open:
                print("Serial port closed.")

        stop_thread = threading.Thread(target=stop_receive_data)
        stop_thread.daemon = True
        stop_thread.start()
        self.root.after(0, self.update_received_data)
        
    def update_received_data(self):
        while not self.data_queue.empty():
                if self.backend_frame:
                    self.received_data = self.data_queue.get()
                    self.data_receive_monitor.insert(tk.END, self.received_data + '\n')
                    self.data_receive_monitor_backend.insert(tk.END, self.received_data + '\n')
                    self.data_receive_monitor.see(tk.END)
                    self.data_receive_monitor_backend.see(tk.END)
                    if self.serial_port and self.serial_port.is_open:
                            while self.received_data.strip() == ".":
                                if self.button_prompt_window is None:
                                    self.process_incoming_data(self.received_data)                                   
                                elif self.button_prompt_window:
                                    self.close_button_press_window()
                                    self.process_incoming_data(self.received_data)
                                break

                elif self.backend_frame is None:
                    self.received_data = self.data_queue.get()
                    self.data_receive_monitor.insert(tk.END, self.received_data + '\n')
                    self.data_receive_monitor.see(tk.END)
                    if self.serial_port and self.serial_port.is_open:
                            if self.received_data.strip() == ".":
                                if self.button_prompt_window:
                                    self.close_button_press_window()
                                    self.process_incoming_data(self.received_data)                                   
                                elif self.button_prompt_window is None:
                                    self.process_incoming_data(self.received_data)
        self.root.after(10, self.update_received_data)
    
    #data receive
   # def update_data_monitors(self):
   #     while not self.data_queue.empty():
   #         received_data = self.data_queue.get()
    #        self.data_receive_monitor.insert(tk.END, received_data+'\n')
    #        self.data_receive_monitor_backend.insert(tk.END, received_data+'\n')
    #        self.data_receive_monitor_backend.see(tk.END)

     #   if not self.sending_data and self.serial_port and self.serial_port.is_open:
     #       sent_data = self.send_data_entry.get()
     #       if sent_data:
     #           self.data_send_monitor.insert(tk.END, sent_data + '\n')
     #           self.data_send_monitor.see(tk.END)
     #           self.twoe_byte_detected = False

     #   self.update_data_job = self.root.after(1, self.update_data_monitors)

    def clear_log_frontend(self):
        self.data_receive_monitor.delete('1.0', tk.END)
        self.data_send_monitor_front_end.delete(1.0, tk.END)

    def open_port(self):
        ini_file = "settings.ini"
        self.port_name = self.selected_port.get()   

      #  print(self.port_name)
        while not self.available_ports:
            tk.messagebox.showerror("Error", "No port detected.")
            self.close_port_connection_window()
            break
        try:
            if not self.serial_port or not self.serial_port.is_open and os.path.exists(ini_file): 
                config = configparser.ConfigParser()
                config.read("settings.ini")
                baud_rate = int(self.serial_config["baud_rate"].get())  # Use the loaded value
                self.serial_port = serial.Serial(self.port_name, baud_rate, timeout=0.01)
                self.update_port_status() #update UI
                self.wait_for_button_press() 
                self.start_receive_thread()

            elif self.serial_port.closed:
                print("abc")
        except serial.SerialException as e:
            ##########close_find_config_file_window(self)
            self.manual_mode()
            self.mode_status.set("None")
            self.mode_status_label.configure(foreground="black")
            self.config_file.set("")
            tk.messagebox.showerror("Permission Error", f"{str(e)}")
            return None
    
    def wait_for_button_press(self):
            self.button_prompt_window = tk.Toplevel(self.root)
            self.button_prompt_window.title("Instruction Window")
            self.button_prompt_window_label = ttk.Label(self.button_prompt_window, text="Port opened, Please press the RESET button")
            self.button_prompt_window_label.place(x=10, y=20)
            self.button_prompt_window.geometry("250x50+300+300")
            self.button_prompt_window.focus_force()
            self.button_prompt_window.protocol("WM_DELETE_WINDOW", self.force_close_button_press_window)
            self.root.wm_attributes('-disabled', True)
            
    def force_close_button_press_window(self):
        self.button_prompt_window.destroy()
        self.button_prompt_window = None
        self.root.wm_attributes('-disabled', False)
        self.root.focus_force()
        self.stop_receive_thread()
        self.auto_prompt_window()

    def close_button_press_window(self):
        self.button_prompt_window.destroy()
        self.button_prompt_window = None
        self.root.wm_attributes('-disabled', False)
        self.root.focus_force()
        self.stop_receive_thread()

    def closed_port(self):
        if self.serial_port.is_open:
            print(self.serial_port)
       #     self.stop_receive_thread()
            self.serial_port.close()
            self.serial_port = None
            self.update_port_status()
            self.manual_mode()
            self.mode_status.set("None")
            self.mode_status_label.configure(foreground="black")
            self.config_file.set("")            

   # def permission_error(self):
    #    self.mode_status.set("None")
     #   self.mode_status_label.configure(foreground="black")
     #   self.config_file.set("")

    def open_backend_window(self):
        entered_password = self.password_entry.get()
        if 'Authentication' in self.config and 'password' in self.config['Authentication']:
            encoded_password = self.config['Authentication']['password']
            saved_password = base64.b64decode(encoded_password).decode()
            self.data_receive_monitor_backend = tk.Text(self.backend_frame, height=10, width=40)
        while True:
            if entered_password == saved_password:
                        if hasattr(self, "backend_frame") and self.backend_frame is not None and self.backend_frame.winfo_exists():
                            tk.messagebox.showinfo("Info", "Backend window is already open.")
                            self.backend_frame.lift()

                        elif self.backend_frame is None:
                            self.backend_frame = tk.Toplevel(self.root)
                            self.backend_frame.title("Settings Window")
                            self.backend_frame.geometry("360x600")
                            self.send_data_label = ttk.Label(self.backend_frame, text="Send Data:")
                            self.send_data_label.place(x=20, y=7)
                            self.send_data_entry = ttk.Entry(self.backend_frame)
                            self.send_data_entry.grid(row=0, column=1, padx=5, pady=5)
                            self.data_format_var = tk.StringVar(value="String")
                            self.data_format_label = ttk.Label(self.backend_frame, text="Data Format:")
                            self.data_format_label.grid(row=1, column=0, padx=5, pady=5)
                   #        self.after_id = self.root.after(1, self.update_received_data)  # Store the after_id
                            self.config_button = ttk.Button(self.backend_frame, text="Configuration Window", command=app.open_configuration_window)
                            self.config_button.place(x=45, y=97)
                            self.command_panel_button = ttk.Button(self.backend_frame, text="Open Command Panel", command=self.open_command_panel)
                            self.command_panel_button.place(x=180, y=97)

                            data_format_options = ["Hex", "String"]
                            for idx, data_format in enumerate(data_format_options):
                                rb = ttk.Radiobutton(self.backend_frame, text=data_format, variable=self.data_format_var, value=data_format)
                                rb.grid(row=1, column=idx + 1, padx=5, pady=5)

                            self.add_crlf_var = tk.BooleanVar(value=True)
                            self.add_crlf_checkbox = ttk.Checkbutton(self.backend_frame, text="Add Carriage Return and Line Feed", variable=self.add_crlf_var)
                            self.add_crlf_checkbox.grid(row=2, columnspan=4, padx=5, pady=5)

                            self.send_button = ttk.Button(self.backend_frame, text="Send", command=self.send_data)
                            self.send_button.grid(row=0, column=2, padx=5, pady=5)
                        
                            # Data Sending Monitor Section
                            self.data_send_label = ttk.Label(self.backend_frame, text="Data Sending Monitor:")
                            self.data_send_label.place(x=100, y=180)
                            
                            self.data_send_monitor = tk.Text(self.backend_frame, height=10, width=40)
                            self.data_send_monitor.place(x=10, y=200)

                            scrollbar = tk.Scrollbar(self.backend_frame, command=self.data_send_monitor.yview)
                            scrollbar.place(x=333, y=195, height=170)
                            self.data_send_monitor.config(yscrollcommand=scrollbar.set)

                            # Data Receiving Monitor Section
                            self.data_receive_label = ttk.Label(self.backend_frame, text="Data Receiving Monitor:")
                            self.data_receive_label.place(x=100, y=380)
                            
                            self.data_receive_monitor_backend = tk.Text(self.backend_frame, height=10, width=40)
                            self.data_receive_monitor_backend.place(x=10, y=400)

                            scrollbar = tk.Scrollbar(self.backend_frame, command=self.data_receive_monitor_backend.yview)
                            scrollbar.place(x=333, y=395, height=170)
                            self.data_receive_monitor_backend.config(yscrollcommand=scrollbar.set)

                            self.clear_log_button_backend = ttk.Button(self.backend_frame, text="Clear Log", command=self.clear_log_backend)
                            self.clear_log_button_backend.place(x=120, y=570)

                            self.port_label = ttk.Label(self.backend_frame, text="Select COM Port:")
                            self.port_label.place(x=50, y=140)

                            self.available_ports = [port.device for port in serial.tools.list_ports.comports()]
                            self.selected_port = tk.StringVar(value=self.available_ports[0] if self.available_ports else "")

                            self.port_combobox = ttk.Combobox(self.backend_frame, textvariable=self.selected_port, values=self.available_ports)
                            self.port_combobox.place(x=150, y=140)
                            self.backend_frame.protocol("WM_DELETE_WINDOW", self.close_backend_window)
                            self.update_received_data()
                            self.root.after(5000, self.update_ports)
            else:
                tk.messagebox.showerror("Error", "Invalid password, Please Insert Again")
            break
            
    def update_ports(self):
        self.selected_port.set(self.available_ports)         

    def clear_log_backend(self):
        self.data_receive_monitor_backend.delete('1.0', tk.END)
        self.data_send_monitor.delete('1.0', tk.END)

    def send_data(self):
        if self.serial_port and self.serial_port.is_open:
                data = self.send_data_entry.get()
                if data:
                    if self.add_crlf_var.get():
                        data += "\r\n"
                    data_format = self.data_format_var.get()

                    # Convert data to the selected format
                    if data_format == "Hex":
                        data = bytes.fromhex(data)
                    elif data_format == "String":
                        data = data.encode()

                    self.serial_port.write(data)
                    self.data_send_monitor.insert(tk.END, f">> Sent: {data}\n")
                    self.data_send_monitor.see(tk.END)
                    self.sending_data = True  # Set the flag to True while sending data
#data send
    def process_incoming_data(self, incoming_data):
        # Add logic to process incoming_data and generate response_data
            response_data = b'\x1B\x1B\x1B\x1B\x1B'
            if self.backend_frame:
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.write(response_data)
                    
                    self.data_send_monitor.insert(tk.END, f">> Sent: {response_data}\n")
                    self.data_send_monitor.see(tk.END)
                    self.sending_data = True  # Set the data sending flag
                    tk.messagebox.showinfo("Success", "MCU in listening mode.")
                    self.data_receive_monitor.delete('1.0', tk.END)

            else: 
                 self.serial_port.write(response_data)
                 self.sending_data = True  # Set the data sending flag
                 tk.messagebox.showinfo("Success", "MCU in listening mode!")
                 self.data_receive_monitor.delete('1.0', tk.END)

    def open_configuration_window(self):
        if self.configuration_window is None:
            self.configuration_window = SerialConfigurationWindow(self.root)
            self.configuration_window.config_window.protocol("WM_DELETE_WINDOW", self.close_configuration_window)

        elif hasattr(self, "configuration_window") and self.configuration_window.config_window is not None and self.configuration_window.config_window.winfo_exists():
            self.configuration_window.config_window.lift()
            self.config_button.config(state=tk.DISABLED)
            tk.messagebox.showinfo("Error", "Configuration window already opened")
            self.config_button.config(state=tk.NORMAL)

    def close_prompt_window(self):
        if self.prompt_window:
            self.prompt_window.destroy()
            self.prompt_window = None
            self.root.lift()
            self.root.wm_attributes('-disabled', False) 

    def close_find_config_file_window(self):
        if self.find_config_file_window:
            self.find_config_file_window.destroy()
            self.find_config_file_window = None
            self.root.lift()
            self.root.focus_force()

    def force_close_config_file_window(self):
        if self.find_config_file_window:
            self.find_config_file_window.destroy()
            self.find_config_file_window = None
            self.root.lift()
            self.root.focus_force()
            self.auto_prompt_window()
            
    def close_backend_window(self):
        self.backend_frame.destroy()  # Destroy the window
        self.backend_frame = None

    def close_configuration_window(self):
        self.configuration_window.config_window.destroy()
        self.configuration_window = None

    def close_command_panel(self):
        self.command_panel_window.destroy()  # Destroy the window
        self.command_panel_window = None

    def close_port_connection_window(self):
        self.port_window.destroy()
        self.port_window = None

    def load_serial_settings(self):
        config = configparser.ConfigParser()
        ini_file = "settings.ini"
        config.read("settings.ini")
        if not os.path.exists(ini_file):
            self.create_serial_settings()
            
        elif os.path.exists(ini_file):
            self.serial_config = {
                "baud_rate": tk.StringVar(value=config.get("Serial", "baud_rate")),
                "data_bits": tk.StringVar(value=config.get("Serial", "data_bits")),
                "stop_bits": tk.StringVar(value=config.get("Serial", "stop_bits")),
                "parity": tk.StringVar(value=config.get("Serial", "parity"))
                }
        
    def create_serial_settings(self):
        ini_file = "settings.ini"
        if not os.path.exists(ini_file):
            config = configparser.ConfigParser()
            config["Serial"] = {"baud_rate": "19200", "data_bits": "8", "stop_bits": "1", "parity":"None"}
        with open(ini_file, "w") as configfile:
                config.write(configfile)
        self.serial_config = {
                "baud_rate": tk.StringVar(value=config.get("Serial", "baud_rate")),
                "data_bits": tk.StringVar(value=config.get("Serial", "data_bits")),
                "stop_bits": tk.StringVar(value=config.get("Serial", "stop_bits")),
                "parity": tk.StringVar(value=config.get("Serial", "parity"))
                }
    def confirm_exit(self):
        result = tk.messagebox.askyesno("Confirm Exit", "Are you sure you want to exit?")
        if result:
            self.root.destroy()
####################################################################################
if __name__ == "__main__":
    root = tk.Tk()
    app = SerialCommunicationApp(root)
    root.mainloop()