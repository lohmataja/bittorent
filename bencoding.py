__author__ = 'Liuda'
import collections, hashlib
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

def bencode_int(i):
    return 'i'+str(i)+'e'

def bencode_list(l):
    return 'l'+''.join([bencode(li) for li in l])+'e'

def bencode_str(s):
    return str(len(s))+':'+s

def bencode_dict(d):
    return 'd'+''.join([bencode(key)+bencode(value) for key, value in d.items()])+'e'

def bencode(item):
    dispatch = {int:bencode_int, list:bencode_list, str:bencode_str}
    return dispatch.get(type(item), bencode_dict)(item)

def tests():
    # bdecoding tests
    assert bdecode("4:spam") == 'spam'

    assert bdecode("i3e") == 3
    assert bdecode("i235e") == 235

    assert bdecode("l4:spam4:eggse") ==['spam', 'eggs']
    assert bdecode("d4:spaml1:a1:bee") == collections.OrderedDict({'spam': ['a', 'b']})
    assert bdecode("d3:cow3:moo4:spam4:eggse") == collections.OrderedDict({'cow': 'moo', 'spam': 'eggs'})
    assert bdecode("d9:publisher3:bob17:publisher-webpage15:www.example.com18:publisher.location4:homee") ==\
           collections.OrderedDict({'publisher': 'bob', 'publisher-webpage': 'www.example.com', 'publisher.location': 'home'})

    # bencoding tests

    assert bencode('spam') == '4:spam'
    assert bencode('ham') == '3:ham'

    assert bencode(3) == 'i3e'
    assert bencode(235) == 'i235e'
    assert bencode(['spam', 'eggs']) == "l4:spam4:eggse"
    assert bencode({'spam': ['a', 'b']}) == 'd4:spaml1:a1:bee'
    assert bencode({'cow': 'moo', 'spam': 'eggs'}) == 'd3:cow3:moo4:spam4:eggse'
    assert bencode({'publisher': 'bob', 'publisher-webpage': 'www.example.com', 'publisher.location': 'home'}) == "d9:publisher3:bob17:publisher-webpage15:www.example.com18:publisher.location4:homee"
    with open("C:/flagfromserver.torrent", 'rb') as t:
        d = bdecode(t.read())
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(d)
    return d
# with open("C:/flagfromserver.torrent", 'rb') as t:
#     a = t.read()
#     b = bencode(read_element(a, 0)[0])
#     print a
#     for i in range(len(a)):
#         if a[i] != b[i]:
#             print i, ord(a[i]), ord(b[i])

def torrent_file_to_dict(filename):
    """takes a filename
    returns an ordered dictionary with parsed info"""
    with open(filename, 'rb') as f:
        return bdecode(f.read())
for torrent in ['C:/flagfromserver.torrent', 'C:/mininova.torrent', 'C:/rutorrent.torrent']:
    print hashlib.sha1(bencode(torrent_file_to_dict(torrent)['info'])).hexdigest()

def get_params(info):
    """takes a dictionary parsed from a torrent file
    returns a dictionary of parameters for request to server"""
    info_hash = hashlib.sha1(bencode(info['info'])).hexdigest()
    peer_id = '1406230005.05tom+cli'
    uploaded = 0
    compact = 1
    event = 'started'
    downloaded = 0
    port = 6881
    left = info['info']['length']
    
# peer_id =
# params = {'info_hash', 'peer_id', 'port', 'uploaded', 'downloaded', 'left', 'compact',\
#           'no_peer_id', 'event'}
#
# import requests
# from_tracker = requests.get(announce)
# client_list = r.text

