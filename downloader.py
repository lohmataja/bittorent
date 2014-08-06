__author__ = 'Liuda'
from torrent import *
from bitstring import BitArray

MSG_IDS = {'keep_alive':None, 'choke':0, 'unchoke':1, 'interested':2, 'not_interested':3,\
           'have':4, 'bitfield':5, 'request':6, 'piece':7, 'cancel':8, 'port':9}
MSG_TYPES = ['choke', 'unchoke', 'interested', 'not_interested', 'have', 'bitfield', 'request', 'piece', 'cancel', 'port']

def download(torrent):
    """
    Takes a Torrent object and downloads the file
    """

    def get_next_request(self, torrent, peer):
        """
        takes Torrent and Peer objects and finds the next block to download
        """
        if not peer.requested_pieces:
            diff = peer.pieces & ~torrent.pieces
            piece_idx = next(i for i in range(len(diff)) if diff[i] == True)
            offset = 0
            peer.requested_pieces.append((piece_idx, BitArray(bin='0'*torrent.piece_len)))
        else:
            piece_idx, blocks = peer.requested_pieces[0]
            block_idx = next(i for i in range(len(blocks)) if blocks[i] == 0)
            offset = block_idx*torrent.BLOCK_LEN
        length = min(torrent.BLOCK_LEN, torrent.piece_len - offset)
        return piece_idx, offset, length

    def encode_msg(msg_type, payload=''):
        if msg_type == 'keep alive':
            msg = ''
        else:
            msg = struct.pack('B', MSG_TYPES.index(msg_type))+payload
        return struct.pack('>I', len(msg))+msg

    def request(peer, piece):
        #send request
        piece_idx, offset, length = piece
        peer.sock.sendall(encode_msg('request', struct.pack('>I I I',  piece_idx, offset, length)))
        #update self.requests

    def connect(peer, torrent):


    while torrent.get_left():
        for peer in torrent.peers:

            if len(peer.requests) < peer.MAX_REQUESTS and not peer.choked:
                new_request = get_next_request(torrent, peer)
                request(peer, new_request)

            elif torrent.num_connected < torrent.MAX_CONNECTIONS and not peer.connected:
                connect(peer, torrent)

            torrent.receive(peer)





# def connect(self, peer):
#     pass

#
# def receive(self, peer):
#     """receive a reply from peer"""
#     try:
#         reply = peer.s.recv(1000)
#         if reply:
#             peer.reply += reply
#             msg_len = struct.unpack('>I', peer.reply[:4])
#             if msg_len == 0:
#                 pass
#             else:
#                 self.msg_processor(peer.reply[4:4+msg_len], peer)
#                 peer.reply = peer.reply[:4+msg_len]
#     except:
#         print len(peer.reply), len(reply)
# def msg_processor(self, msg_str, peer):
#     msg = struct.unpack('B', msg_str[0])
#     #choke
#     if msg == 0:
#         peer.choked = True
#     #unchoke
#     elif msg == 1:
#         peer.choked = False
#     #peer is interested
#     elif msg == 2:
#         self.send_msg('unchoke')
#     #peer is not interested
#     elif msg == 3:
#         pass
#     #peer has piece #x
#     elif msg == 4:
#         #update info about peer's pieces
#         peer.pieces(msg_str[1:]) = True
#     #bitfield msg
#     elif msg == 5:
#         peer.has_pieces = msg_str[1:] #TODO: unpack and convert to a necessary data structure
#     #request for a piece
#     elif msg == 6:
#         pass #TODO: implement sending a piece
#         #locate requested piece, send it; update uploaded, advertise it other peers
#     #piece
#     elif msg == 7:
#         index, begin = struct.unpack('>I I', msg_str[1:9])
#         self.f.seek(index*self.piece_len+begin)
#         self.f.write(msg_str[9:])
#         #update self.pieces, downloaded
#     #cancel piece
#     elif msg == 8:
#         pass
#     #port msg
#     elif msg == 9:
#         pass
#     else:
#         print 'unknown message:', msg, msg_str
#
#
# # torrent_file = 'C:/flagfromserver.torrent'
# # t = Torrent(torrent_file)
# # download(t)