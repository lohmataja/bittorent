def bdecode(benstr):
    """
    :param benstr: str
    :return: dict
    """

    def bdecode_string(benstr, i):
        j = benstr.find(':', i)
        str_len = int(benstr[i:j])
        end = j + 1 + str_len
        return benstr[j + 1:end], end

    def bdecode_int(benstr, i):
        j = benstr.find('e', i)
        return int(benstr[i:j]), j + 1

    def bdecode_list(benstr, i):
        res = []
        while benstr[i] != 'e':
            new_el, i = bdecode_element(benstr, i)
            res.append(new_el)
        return res, i + 1

    def bdecode_dict(benstr, i):
        res = {}
        while i < len(benstr) and benstr[i] != 'e':
            new_key, i = bdecode_element(benstr, i)
            new_value, i = bdecode_element(benstr, i)
            res[new_key] = new_value
        return res, i + 1

    def bdecode_element(benstr, i):
        dispatch = {'i': bdecode_int, 'l': bdecode_list, 'd': bdecode_dict}
        return dispatch.get(benstr[i], bdecode_string)(benstr, i + (benstr[i] in 'ild'))

    return bdecode_element(benstr, 0)[0]


def bencode(item):
    """
    :param item: str or dict or list or int
    :return: str
    """

    def bencode_int(i):
        return 'i' + str(i) + 'e'

    def bencode_list(l):
        return 'l' + ''.join([bencode_item(li) for li in l]) + 'e'

    def bencode_str(s):
        return str(len(s)) + ':' + s

    def bencode_dict(d):
        return 'd' + ''.join([bencode_item(key) + bencode_item(value) for key, value in sorted(d.items())]) + 'e'

    def bencode_item(item):
        dispatch = {int: bencode_int, list: bencode_list, str: bencode_str, dict: bencode_dict}
        return dispatch[type(item)](item)

    return bencode_item(item)

