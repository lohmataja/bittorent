import bencoding
import hashlib
import requests
from bitstring import BitArray
import socket
import struct

MAX_REQUESTS = 2
MAX_CONNECTIONS = 2
MSG_TYPES = ['choke', 'unchoke', 'interested', 'not_interested', 'have', 'bitfield', 'request', 'piece', 'cancel', 'port']
class Torrent():
    """
    Keeps track of all information associated with a particular torrent file.
    Gets and processes info from tracker, finding peers.
    Keeps track of the pieces under download, figures out what to download next, writes to file.
    """

    def __init__(self, torrent_file):
        self.torrent_data = bencoding.bdecode(open(torrent_file, 'rb').read())
        self.announce = self.torrent_data['announce']
        self.info = self.torrent_data['info']
        self.info_hash = hashlib.sha1(bencoding.bencode(self.torrent_data['info'])).digest()
        self.peer_id = 'liutorrent1234567890'
        self.uploaded = 0
        self.downloaded = 0
        self.port = 6881 #how do I choose a port? randomly within the unreserved range?
        self.filename = './'+self.info['name'] #for now, single file only

        #handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
        self.handshake = ''.join([chr(19), 'BitTorrent protocol', chr(0)*8, self.info_hash, self.peer_id])

        self.length = self.info['length'] if 'length' in self.info.keys() \
            else sum([f['length'] for f in self.info['files']])
        self.piece_len = self.info['piece length']
        self.BLOCK_LEN = 2**14
        self.num_pieces = self.length/self.piece_len + 1
        self.last_piece_len = self.length % self.piece_len
        self.last_block_len = self.piece_len % self.BLOCK_LEN
        self.blocks_per_piece = self.piece_len / self.BLOCK_LEN + 1 * (self.last_block_len != 0)
        #Pieces/blocks data: pieces BitArray represents the pieces that I have;
        #blocks is a list of BitArray, each of which keeps track of downloaded blocks
        self.pieces = BitArray(bin='0'*self.num_pieces)
        self.blocks = [BitArray(bin='0'*self.blocks_per_piece) for i in range(len())]

        self.info_from_tracker = self.update_info_from_tracker()
        self.peers = self.get_peers()
        self.active_peers = []

        self.num_connected = 0
        self.MAX_CONNECTIONS = MAX_CONNECTIONS
        self.requests = []

    def get_left(self):
        return self.length - self.downloaded

    def get_params(self):
        return {'info_hash':self.info_hash,
                'peer_id':self.peer_id,
                'uploaded':self.uploaded,
                'downloaded':self.downloaded,
                'port':self.port,
                'left':self.get_left(),
                'compact':1,
                'event':'started'}

    def update_info_from_tracker(self):
        tracker_response = requests.get(self.announce, params=self.get_params())
        return bencoding.bdecode(tracker_response.text)

    def get_peers(self):
        peer_bytes = [ord(byte) for byte in self.info_from_tracker['peers']]
        # assert len(peer_bytes)%6 == 0
        peers = []
        for i in range(len(peer_bytes)/6):
            ip = '.'.join([str(byte) for byte in peer_bytes[i*6:i*6+4]])
            port = peer_bytes[i*6+4]*256+peer_bytes[i*6+5]
            peers.append(Peer(ip, port))
        return peers

    def write(self, index, begin, data):
        #write data to file
        with open(self.filename, 'wb') as f:
            f.seek(index*self.piece_len+begin)
            f.write(data)
        #update downloaded (blocks and pieces are updated when request is made or fails)
        self.downloaded += len(data)


    def get_next_request(self, peer):
        """
        takes Torrent and Peer objects and finds the next block to download
        """
        diff = peer.pieces & ~self.pieces
        #find next piece that the peer has and I don't have
        piece_idx = next(i for i in range(len(diff)) if diff[i] == True)
        #find next block in that piece that I don't have
        block_idx = next(i for i in range(self.blocks_per_piece) if self.blocks[piece_idx][i] == False)
        offset = block_idx * self.BLOCK_LEN
        length = min(self.BLOCK_LEN, self.piece_len - offset)
        #update blocks and pieces
        self.blocks[piece_idx][block_idx] = True
        if self.blocks[piece_idx].int == self.BLOCK_LEN:
            self.pieces[piece_idx] = True
        return piece_idx, offset, length


class Peer():

    def __init__(self, torrent, ip, port, peer_id = None):
        self.torrent = torrent
        self.ip = ip
        self.port = port
        self.peer_id = peer_id
        self.sock = None

        self.connected = False
        self.choked = True
        self.interested = False

        self.pieces = ''
        self.reply = ''

        self.requests = [] #array of tuples: piece, offset
        self.requested_pieces = [] #array of tuples representing pieces currently in work: (piece index, BitArray of blocks)
        self.MAX_REQUESTS = MAX_REQUESTS

    def encode_msg(self, msg_type, payload=''):
        if msg_type == 'keep alive':
            msg = ''
        else:
            msg = struct.pack('B', MSG_TYPES.index(msg_type))+payload
        return struct.pack('>I', len(msg))+msg

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #make socket non-blocking
        self.sock.setblocking(0)
        self.sock.sendall(self.torrent.handshake)
        try:
            peer_handshake = self.sock.recv(68)
            #TODO: verify peer_handshake
            #update peer's status:
            self.connected = True
        except:
            pass

    def unchoke(self):
        self.sock.sendall(self.encode_msg('unhoke'))
    def request(self, piece):
        #send request
        index, begin, length = piece
        self.sock.sendall(self.encode_msg('request', struct.pack('>I I I',  piece_idx, offset, length)))
        #update self.requests
        self.requests.append((index, begin))

    def receive(self):
        """receive a reply from peer"""
        try:
            self.reply += self.sock.recv(1024)
            while self.reply:
                msg_len = struct.unpack('>I', self.reply[:4])
                if msg_len == 0:
                    #TODO: keep alive: reset the timeout; update self.reply
                    self.reply = self.reply[:4]
                elif len(self.reply) >= msg_len+4:
                    self.msg_processor(self.reply[4:4+msg_len])
                    self.reply = self.reply[4+msg_len:]
                else:
                    break
        except:
            print len(self.reply)

    def msg_processor(self, msg_str):
        msg = struct.unpack('B', msg_str[0])

        #choke
        if msg == 0:
            self.choked = True

        #unchoke
        elif msg == 1:
            self.choked = False

        #peer is interested
        elif msg == 2:
            self.sock.sendall(self.encode_msg('unchoke'))

        #peer is not interested
        elif msg == 3:
            pass

        #peer has piece #x
        elif msg == 4:
            #update info about peer's pieces
            piece_idx = struct.unpack('>I', msg_str[1:])
            self.pieces[piece_idx] = True

        #bitfield msg
        elif msg == 5:
            self.pieces = BitArray(bytes=msg_str[1:])
            del self.pieces[self.torrent.num_pieces:] #cut out unnecessary bits

        #request for a piece
        elif msg == 6:
            pass #TODO: implement sending a piece
            #locate requested piece, send it; update uploaded, advertise it other peers

        #piece
        elif msg == 7:
            index, begin = struct.unpack('>I I', msg_str[1:9])
            #write the file
            self.torrent.write(index, begin, msg_str[9:])
            #update the peer's queue
            self.requests.remove((index, begin))

        #cancel piece
        elif msg == 8:
            pass

        #port msg
        elif msg == 9:
            pass

        else:
            print 'unknown message:', msg, msg_str

