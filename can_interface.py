import can


class CanInterfaceError(Exception):
    pass


class CanInterface:
    def __init__(self, interface):
        self.channel = interface
        self.bitrate = 500000
        self.can_messages = []
        self.running = True
        self.bus = None
        try:
            self.bus = can.interface.Bus(channel=self.channel, bustype='socketcan', bitrate=self.bitrate)
        except can.CanError as e:
            raise CanInterfaceError(f"Fehler beim Erstellen der Busschnittstelle: {str(e)}")

    def send_message(self, message, ID):
        try:
            message = can.Message(arbitration_id=ID, data=message.encode(), is_extended_id=False)
            self.bus.send(message)
        except can.CanError as e:
            raise CanInterfaceError(f"Fehler beim Senden der CAN-Nachricht: {str(e)}")

    def read_message(self, timeout=0.1):
        message = None
        try:
            message = self.bus.recv(timeout)
        except can.CanError as e:
            raise CanInterfaceError(f"Fehler beim Empfangen der CAN-Nachricht: {str(e)}")
        return message

    def close(self):
        self.bus.shutdown()
