import select
import socket
from torrent import Torrent


class Downloader():
    def __init__(self, filename):
        self.torrent = Torrent(filename)
        self.host = '0.0.0.0'
        self.port = 6886
        # self.listener = self.create_listener()
        self.inputs = []
        self.outputs = []

    def create_listener(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.host, self.port))
        listener.listen(5)
        return listener

    def add_peer(self):
        # TODO: accept connection
        #connect to a new peer
        peer = self.torrent.peers.pop()  # get a new peer
        peer.connect()
        self.inputs.append(peer)
        self.outputs.append(peer)

    def remove(self, peer):
        # remove peer from select's queue
        self.inputs.remove(peer)
        self.outputs.remove(peer)
        # put the peer in the back of the torrent's queue of peers
        self.torrent.peers.appendleft(peer)
        #reset peer's values and queues
        peer.teardown()

    def main_loop(self):
        while self.torrent.is_incomplete:  # TODO: rename better
            while len(self.inputs) < self.torrent.max_connections and self.torrent.peers:
                self.add_peer()

            # get what is ready
            to_read, to_write, errors = select.select(self.inputs, self.outputs, self.inputs)
            for peer in to_read:
                peer.read()
            for peer in to_write:
                peer.store()
            for peer in errors:
                self.remove(peer)

tor_f = 'C:/flagfromserver.torrent'
d = Downloader(tor_f)
# d.main_loop()
