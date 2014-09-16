import select
import socket
import pickle
from torrent import Torrent
from peer import Peer

HOST = '0.0.0.0'
PORT = 6886

def main_loop(torrent):
    """
    :param torrent: Torrent object
    downloads the torrent
    """
    # initialize
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(5)

    inputs = [sock]
    outputs = [sock]


    # event loop
    while torrent.get_left():
        while len(inputs) < torrent.MAX_CONNECTIONS and torrent.peers:
            peer = torrent.peers.pop() #get a new peer
            peer.sock = socket.socket() #create a socket for him
            peer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #set socket reuse
            peer.sock.setblocking(False) #make the socket non-blocking
            try:
                peer.sock.connect((peer.ip, peer.port)) #connect
            except socket.error:
                print('connection failed', peer.ip)
            inputs.append(peer)
            outputs.append(peer)

        #get what is ready
        to_read, to_write, errors = select.select(inputs, outputs, inputs)
        for peer in to_read:
            peer.receive_data()
            peer.process_reply()
        for peer in to_write:
            peer.enqueue_msg()
            peer.send_msg()
        for peer in errors:
            #remove peer from select's queue
            inputs.remove(peer)
            outputs.remove(peer)
            #put the peer in the back of the torrent's queue of peers
            torrent.peers.appendleft(peer)
            #reset peer's values and queues
            peer.teardown()

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
