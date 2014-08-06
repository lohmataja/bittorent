import collections
import hashlib
import requests
from bitstring import BitArray
import socket
import struct


MAX_REQUESTS = 2

def bdecode(benstr):
    """takes a bencoded string
    returns a dictionary"""
    def bdecode_string(benstr, i):
        j = benstr.find(':', i)
        str_len = int(benstr[i:j])
        end = j+1+str_len
        return benstr[j+1:end], end

    def bdecode_int(benstr, i):
        j = benstr.find('e', i)
        return int(benstr[i:j]), j+1

    def bdecode_list(benstr, i):
        res = []
        while benstr[i] != 'e':
            new_el, i = bdecode_element(benstr, i)
            res.append(new_el)
        return res, i+1

    def bdecode_dict(benstr, i):
        res = collections.OrderedDict()
        while i < len(benstr) and benstr[i] != 'e':
            new_key, i = bdecode_element(benstr, i)
            new_value, i = bdecode_element(benstr, i)
            res[new_key] = new_value
        return res, i+1

    def bdecode_element(benstr, i):
        dispatch = {'i':bdecode_int, 'l':bdecode_list, 'd':bdecode_dict}
        return dispatch.get(benstr[i], bdecode_string)(benstr, i+(benstr[i] in 'ild'))

    return bdecode_element(benstr, 0)[0]

def bencode(item):
    def bencode_int(i):
        return 'i'+str(i)+'e'

    def bencode_list(l):
        return 'l'+''.join([bencode_item(li) for li in l])+'e'

    def bencode_str(s):
        return str(len(s))+':'+s

    def bencode_dict(d):
        return 'd'+''.join([bencode_item(key)+bencode_item(value) for key, value in d.items()])+'e'

    def bencode_item(item):
        dispatch = {int:bencode_int, list:bencode_list, str:bencode_str}
        return dispatch.get(type(item), bencode_dict)(item)

    return bencode_item(item)


class Torrent():

    def __init__(self, torrent_file):
        #TODO: decide on data structure to keep track of pieces
        self.torrent_data = bdecode(open(torrent_file, 'rb').read())
        self.announce = self.torrent_data['announce']
        self.info = self.torrent_data['info']
        self.info_hash = hashlib.sha1(bencode(self.torrent_data['info'])).digest()
        self.peer_id = 'liutorrent1234567890'
        self.uploaded = 0
        self.downloaded = 0
        self.port = 6881 #how do I choose a port? randomly within the unreserved range?
        self.filename = self.info['name'] #for now, single file only

        self.length = self.info['length'] if 'length' in self.info.keys() \
            else sum([f['length'] for f in self.info['files']])
        self.piece_len = self.info['piece length']
        self.BLOCK_LEN = 2**14
        self.num_blocks = self.piece_len / self.BLOCK_LEN
        self.num_pieces = self.length/self.piece_len + 1
        self.last_piece_len = self.length % self.piece_len
        self.last_block_len = self.piece_len % self.BLOCK_LEN
        self.pieces = BitArray(bin='0'*self.num_pieces)

        self.info_from_tracker = self.update_info_from_tracker()
        self.peers = self.get_peers()

        self.num_connected = 0
        self.MAX_CONNECTIONS = 2
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
        return bdecode(tracker_response.text)

    def get_peers(self):
        peer_bytes = [ord(byte) for byte in self.info_from_tracker['peers']]
        # assert len(peer_bytes)%6 == 0
        peers = []
        for i in range(len(peer_bytes)/6):
            ip = '.'.join([str(byte) for byte in peer_bytes[i*6:i*6+4]])
            port = peer_bytes[i*6+4]*256+peer_bytes[i*6+5]
            peers.append(Peer(ip, port))
        return peers


class Peer():

    def __init__(self, ip, port, peer_id = None):
        self.ip = ip
        self.port = port
        self.peer_id = peer_id

        self.connected = False
        self.choked = True
        self.interested = False

        self.pieces = []
        self.reply = ''

        self.requests = [] #array of tuples: piece, offset
        self.requested_pieces = [] #array of tuples representing pieces currently in work: (piece index, BitArray of blocks)
        self.MAX_REQUESTS = MAX_REQUESTS




