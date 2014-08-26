import select
import socket
import pickle
from torrent import Torrent
from peer import Peer

def main_loop(torrent):
    """
    :param torrent: Torrent object
    downloads the torrent
    """
    # initialize
    inputs = []
    outputs = []

    # main loop
    # Add peers to connect to
    while torrent.get_left():
        while len(inputs) < torrent.MAX_CONNECTIONS and torrent.peers:
            peer = torrent.peers.pop() #get a new peer
            peer.sock = socket.socket() #create a socket for him
            peer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #set socket reuse
            peer.sock.setblocking(False) #make the socket non-blocking
            try:
                peer.sock.connect((peer.ip, peer.port)) #connect
            except:
                print 'connection failed', peer.ip
            inputs.append(peer)
            outputs.append(peer)

        #get what is ready
        to_read, to_write, errors = select.select(inputs, outputs, inputs)
        for peer in to_read:
            peer.update_reply()
            peer.process_reply()
        for peer in to_write:
            peer.enqueue_msg()
            peer.send_msg()

def serialize(object, filename):
    with open(filename, 'wb') as f:
        pickle.dump(object, f)
def deserialize(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

tor_f = 'C:/flagfromserver.torrent'
t = Torrent(tor_f)
# serialize(t, './torrentObj')
main_loop(t)
# t = deserialize('./torrentObj')
