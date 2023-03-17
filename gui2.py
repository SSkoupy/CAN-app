#!/usr/bin/env python
import os
import traceback
import threading
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from can_interface import CanInterface


CAN_GUI_ID = 0x07B  # CAN-Identifier für diese App
HEART_BEAT = {'id': 269492224, 'data': b'\x04\x02\x00\x00\x00\x00\x01\x00'}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.attributes('-fullscreen', True)

        # Oberer frame
        self.read_frame = tk.LabelFrame(self, text="CAN-Read")
        self.read_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Ausgabe
        self.scroll = scrolledtext.ScrolledText(self.read_frame, wrap=tk.WORD, bg="black", fg="white", height=10, padx=15)
        self.scroll.pack(fill=tk.BOTH, expand=1)

        # Unterer frame
        self.send_frame = tk.LabelFrame(self, text="CAN-Send")
        self.send_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        # Escape
        self.quit_button = tk.Button(self.send_frame, text='Beenden', command=self.quit)
        self.quit_button.pack(side="left", anchor="w",  padx=5, pady=5)
        self.bind('<Escape>', lambda event: self.quit())

        self.connection = tk.Label(self.send_frame, text="Status Sonde:")
        self.connection.pack(side="left", anchor="w", padx=5, pady=5)

        # Verbindung zur Sonde (heartbeat wird empfangen)
        self.canvas = tk.Canvas(self.send_frame, width=20, height=20)
        self.canvas.pack(side="left", anchor="w")

        self.circle1 = self.canvas.create_oval(3, 3, 18, 18, fill="red", outline="#333333", width=1)

        # Senden
        self.send_button = tk.Button(self.send_frame, text='Senden', command=self.send_can_message)
        self.send_button.pack(side="right", anchor="se",  padx=5, pady=5)

        # Eingabe
        entry_vcmd = (self.register(self.validate_input), '%P')
        self.entry = tk.Entry(self.send_frame, justify="right", validate="key", validatecommand=entry_vcmd)
        self.entry.pack(side="right", anchor="se", fill="y", expand=True, padx=5, pady=5)
        self.entry.bind('<Return>', lambda event: self.send_can_message())

        # Array für die empfangenen CAN-Nachrichten
        self.can_messages = []

        # Read-Thread
        self.running = True
        self.can_interface = CanInterface("can0")
        self.can_messages_lock = threading.Lock()

        # Read-Thread
        self.read_thread = threading.Thread(target=self.read_messages, daemon=True)
        self.read_thread.start()

        # Handle-Funktion
        self.heart_beats = False
        self.handle_heartbeat()
        self.handle_messages()

        self.entry.focus

    def validate_input(self, input_text):
        if len(input_text) <= 8:
            return True
        return False

    def send_can_message(self):
        try:
            message = self.entry.get()
            if (message):
                self.can_interface.send_message(message, CAN_GUI_ID)

                self.entry.selection_range(0, tk.END)

                modified_message = self.modify_message(message, True)
                self.scroll.insert(tk.END, modified_message)
                self.scroll.see(tk.END)
        except Exception as e:
            self.handle_error(e)

    # Read-Thread
    def read_messages(self):
        while self.running:
            try:
                message = self.can_interface.read_message()
                if message:
                    with self.can_messages_lock:
                        self.can_messages.append(message)
            except Exception as e:
                self.handle_error(e)

    def modify_message(self, message, sent=False):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        message_sent = "Gesendet  -->" if sent else "Empfangen <--"
        message_id = CAN_GUI_ID if sent else "{:03d}".format(message.arbitration_id)
        message_data = message if sent else ' '.join(format(byte, '02X') for byte in message.data)
        modified_text = f"\n{timestamp} \t{message_sent} \tID: {message_id} \tDaten: {message_data}"
        lines = int(self.scroll.index('end-1c').split('.')[0])
        if lines >= 200:
            self.scroll.delete("1.0", "2.0")
        return modified_text
    
    # Handle-Methode im Hauptthread
    def handle_messages(self):
        try:
            message = None
            with self.can_messages_lock:
                if self.can_messages:
                    message = self.can_messages.pop(0)
            if message:
                if message.arbitration_id == HEART_BEAT['id'] and message.data == HEART_BEAT['data']:
                    self.heart_beats = True
                else:
                    modified_message = self.modify_message(message)
                    self.scroll.insert(tk.END, modified_message)
                    self.scroll.see(tk.END)

            self.after(100, self.handle_messages)
        except Exception as e:
            self.handle_error(e)

    def handle_heartbeat(self):
        if self.heart_beats:
            self.canvas.itemconfig(self.circle1, fill="green")
            self.heart_beats = False
        else:
            self.canvas.itemconfig(self.circle1, fill="red")
            self.scroll.insert(tk.END, "\nHeartbeat unterbrochen!")
            self.scroll.see(tk.END)
        self.after(600, self.handle_heartbeat)

    def handle_error(self, error):
        timestamp = datetime.now().strftime("%H:%M:%S")
        traceback_text = traceback.format_exc()
        error_text = f"\n{timestamp} \tERROR: {error}\n{traceback_text}"
        self.scroll.insert(tk.END, error_text)
        self.scroll.see(tk.END)
        
        # Pfad zur Traceback-Datei erstellen
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Traceback.log")
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                pass
        with open("Traceback.log", "a") as f:
            f.write(error_text)
            f.write("\n")
        self.quit()

    def quit(self):
        self.running = False  # Signal zum Beenden des Threads
        self.read_thread.join(timeout=0.5)  # Warte auf das Ende des Read-Threads
        self.can_interface.close()  # CanInterface schließen
        super().quit()  # die ursprüngliche quit()-Methode aufrufen


app = App()
app.mainloop()
