#!/usr/bin/env python
import threading
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from can_interface import CanInterface


CAN_GUI_ID = 0x07B  # CAN-Identifier für diese App


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.attributes('-fullscreen', True)

        # Oberer frame
        self.read_frame = tk.LabelFrame(self, text="CAN-Read")
        self.read_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Ausgabe
        self.scroll = scrolledtext.ScrolledText(self.read_frame, wrap=tk.WORD, bg="black", fg="white", height=10)
        self.scroll.pack(fill=tk.BOTH, expand=1)

        # Unterer frame
        send_frame = tk.LabelFrame(self, text="CAN-Send")
        send_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        # Escape
        self.quit_button = tk.Button(send_frame, text='Beenden', command=self.quit)
        self.quit_button.pack(side="left", anchor="sw",  padx=5, pady=5)
        self.bind('<Escape>', lambda event: self.quit())

        # Senden
        self.send_button = tk.Button(send_frame, text='Senden', command=self.send_can_message)
        self.send_button.pack(side="right", anchor="se",  padx=5, pady=5)

        # Eingabe
        entry_vcmd = (self.register(self.validate_input), '%P')
        self.entry = tk.Entry(send_frame, justify="right", validate="key", validatecommand=entry_vcmd)
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
        self.handle_messages()

    # Handle-Methode im Hauptthread
    def handle_messages(self):
        # Auf neue Nachrichten warten und verarbeiten
        message = None
        with self.can_messages_lock:
            if self.can_messages:
                message = self.can_messages.pop(0)
        if message:
            modified_message = self.modify_message(message)
            self.scroll.insert(tk.END, modified_message)
            self.scroll.see(tk.END)

        # Schleife in 10 Millisekunden erneut aufrufen
        self.after(10, self.handle_messages)

    def validate_input(self, input_text):
        if len(input_text) <= 8:
            return True
        return False

    # Read-Thread
    def read_messages(self):
        while self.running:
            message = self.can_interface.read_message()
            if message:
                # Nachricht im Array speichern
                with self.can_messages_lock:
                    self.can_messages.append(message)

    def send_can_message(self):
        message = self.entry.get()
        if (message):
            self.can_interface.send_message(message, CAN_GUI_ID)

            # Eingabe markieren
            self.entry.selection_range(0, tk.END)

            # Ausgabe
            modified_message = self.modify_message(message, True)
            self.scroll.insert(tk.END, modified_message)
            self.scroll.see(tk.END)

    def modify_message(self, message, sent=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        message_sent = "Gesendet  -->" if sent else "Empfangen <--"
        message_id = CAN_GUI_ID if sent else "{:03d}".format(message.arbitration_id)
        message_data = message if sent else message.data.decode('utf_16', errors='replace')
        modified_text = f"\n{timestamp} \t{message_sent} \tID: {message_id} \tDaten: {message_data}"
        return modified_text

    def quit(self):
        self.running = False  # Signal zum Beenden des Threads
        self.read_thread.join(timeout=0.5)  # Warte auf das Ende des Read-Threads
        self.can_interface.close()  # CanInterface schließen
        super().quit()  # die ursprüngliche quit()-Methode aufrufen


app = App()
app.mainloop()
