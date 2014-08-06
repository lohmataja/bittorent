
from torrent import *
from bitstring import BitArray

def download(torrent):
    """
    Takes a Torrent object and downloads the file
    """
    while torrent.get_left():
        #up the connections
        if torrent.num_connected < torrent.MAX_CONNECTIONS:
            try:
                new_peer = torrent.peers.pop(0)
                new_peer.connect()
                if new_peer.connected:
                    torrent.active_peers.append(new_peer)
                else:
                    torrent.peers.append(new_peer)
            except:
                print 'connection problem'

        #talk to active peers
        for peer in torrent.active_peers:
            if not peer.choked and len(peer.requests) < peer.MAX_REQUESTS:
                new_request = torrent.get_next_request(peer)
                peer.request(new_request)
            else:
                peer.unchoke()

            peer.receive(torrent)


# torrent_file = 'C:/flagfromserver.torrent'
# t = Torrent(torrent_file)
# download(t)