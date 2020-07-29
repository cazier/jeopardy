from flask_socketio import SocketIO


class LogSocketIO(SocketIO):
    def emit(self, event, *args, **kwargs):
        print(f"EMITTING WEBSOCKET! ==== {event}\n")
        super().emit(event, *args, **kwargs)


socketio = LogSocketIO()
