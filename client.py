from threading import Thread
from gui import MainWindow
import socket as s
import select as sel


class ChatClient(Thread):
    def __init__(self, port, ip, window):
        """
        port: port to connect to.
        cert: public certificate (task 3)
        ip: IP to bind to (task 3)
        """
        super().__init__()

        self.window = window
        self.port = port
        self.ip = ip

        self.wake_socket = self.window.wake_thread
        self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.socket.connect((ip, port))

    def run(self):
        while not self.window.quit_event.is_set():
            try:
                readable, _, _ = sel.select([self.socket, self.wake_socket],
                                            [], [])
                for sock in readable:
                    if sock is self.wake_socket:
                        self.socket.close()
                        exit(0)
                    data = sock.recv(1024)
                    if data:
                        self.window.write(data.decode())
                    else:
                        sock.close()
            except Exception:
                self.socket.close()
                break

    def text_entered(self, line):
        try:
            self.socket.send(line.encode())
        except Exception:
            mess = "Cannot send message. You might have been kicked or IP"
            mess += " banned."
            self.window.writeln(mess)


# Command line argument parser.
if __name__ == '__main__':
    import sys
    import argparse
    p = argparse.ArgumentParser()

    p.add_argument('--port', help='port to connect to',
                   default=12345, type=int)
    p.add_argument('--ip', help='IP to bind to', default='127.0.0.1', type=str)
    args = p.parse_args(sys.argv[1:])

    w = MainWindow()
    client = ChatClient(args.port, args.ip, w)
    w.set_client(client)
    client.start()
    w.start()
