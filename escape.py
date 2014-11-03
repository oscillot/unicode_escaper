from StringIO import StringIO
from bitstring import BitArray

def parse_initial(binio, bitwidth):
    """Given an initial bitwidth for the unicode character, read that
    many bits from the binary stream and return them, along with a reference
    to the stream.

    :param StringIO binio: the stream of unicode bytes
    :param int bitwidth: how wide the character is in bits
    :rtype: (string, StringIO)"""

    #consume length bits
    binio.read(bitwidth)
    #get first part of data
    char = binio.read(8 - bitwidth)
    return char, binio

def parse_continuation(hexio, binio, char, loops, chars):
    """Parse out the continuation byte in a unicode character, which will
    appear in any character that is wider than 1 byte.  The function has the
    side effect of appending the resulting hex encoding of the character to
    the chars list passed in to the function.

    :param StringIO hexio: the hex stream of the unicode characters
    :param StringIO binio: the binary stream of unicode characters
    :param string char: a buffer for the character
    :param int loops: how many continuation bits need to be read
    :param list chars: a running list of hex data for the unicode
    :rtype: (StringIO, StringIO)"""

    for r in range(0, loops):
        #consume continuation bits
        binio.read(2)
        char += binio.read(6)
        #move hex in step with binary
        hexio.read(2)
    mod = len(char) % 8
    if mod != 0:
        fill = len(char) + (8 - mod)
        char = char.zfill(fill)
    bits = BitArray(bin=char)
    chars.append(bits.hex)
    return hexio, binio

def parse(b):
    """Parse a stream of unicode characters into list of hex encodings for
    each character.

    :param BitArray b: a bitarray of the unicode stream
    :rtype: a list of escaped hex characters"""

    chars = []
    hexio = StringIO(b.hex.upper())
    binio = StringIO(b.bin)

    while hexio.tell() < len(b.hex):
        length = hexio.read(2)
        #char byte width of 1
        # print length
        if length[0] in [str(r) for r in range(0, 8)]:
            #read whole byte like ascii
            char = binio.read(8)
            bits = BitArray(bin=char)
            chars.append(bits.hex)
            continue

        #8, 9, A, B are for continuation bytes, skip those
        #char byte width of 2
        elif length[0] in ['C', 'D']:
            char, binio = parse_initial(binio, 3)
            hexio, binio = parse_continuation(hexio, binio, char, 1, chars)
            continue

        #char byte width of 3
        elif length[0] == 'E':
            char, binio = parse_initial(binio, 4)
            hexio, binio = parse_continuation(hexio, binio, char, 2, chars)
            continue

        #char byte width of 4
        elif length in ['F%s' % str(r) for r in range(0, 8)]:
            char, binio = parse_initial(binio, 5)
            hexio, binio = parse_continuation(hexio, binio, char, 3, chars)
            continue

        #char byte width of 5
        elif length in ['F%s' % [h for h in ['8', '9', 'A', 'B']]]:
            char, binio = parse_initial(binio, 6)
            hexio, binio = parse_continuation(hexio, binio, char, 4, chars)
            continue

        #char byte width of 6
        elif length in ['F%s' % [h for h in ['C', 'D']]]:
            char, binio = parse_initial(binio, 7)
            hexio, binio = parse_continuation(hexio, binio, char, 5, chars)
            continue

        elif length in ['FE', 'FF']:
            byte2 = hexio.read(2)
            bom_check = '%s%s' % (length, byte2)
            bom_check = bom_check.upper()
            #print bom_check
            if bom_check in ['FEFF', 'FFFE']:
                chars.append('EF'.lower())
                chars.append('BB'.lower())
                chars.append('BF'.lower())
                #and make sure the other stream stays in step with it
                binio.read(16)
                continue
            #otherwise
            raise ValueError('Bytes do not represent valid UTF-8 data')

    return chars

def to_hex_string_list(text):
    """Convert a unicode-decoded string into a list of hex encoded characters.

    :param string text: the text to convert
    :rtype: a list of strings"""

    return [str(hex(ord(c)))[2:] for c in text.encode('utf-8')]

def to_hex_string(text):
    """Convert a unicode-decoded string into a list of hex encoded characters.

    :param string text: the text to convert
    :rtype: a list of strings"""

    return ''.join([str(hex(ord(c)))[2:] for c in text.encode('utf-8')])

def selective_escape(chars):
    """Selectively escape only those characters that are out of ascii range.
    Ascii characters will be appended as-is to the return string, while
    non-ascii characters will be hex-encoded.

    :param string chars: the string to escape
    :rtype: a hex-encoded string"""

    escaped = [c for c in chars]
    ascii_only = []
    for i, e in enumerate(escaped):
        #fyi - 20 is the lower bound of printable ascii characters
        #59 is ';', a dumb check to make sure we aren't escaping text that is
        #  already escaped.
        try:
            if int(e, 16) == 38 and \
                    int(escaped[i + 3], 16) != 59 and \
                    int(escaped[i + 4], 16) != 59 and \
                    int(escaped[i + 5], 16) != 59:
                continue
        except IndexError:
            #if we get an IndexError then it can't already be escaped bc it's
            #  not long enough, so escape it
            ascii_only.append('&amp;')
            continue
        if int(e, 16) == 34:
            ascii_only.append('&quot;')
        elif int(e, 16) == 39:
            ascii_only.append('&apos;')
        elif 20 <= int(e, 16) <= 127:
            ascii_only.append(chr(int(e, 16)))
        else:
            ascii_only.append('&#%s;' % str(int(e, 16)))
    return ''.join(ascii_only)


def escape(s):
    print to_hex_string_list(unicode(s))
    return selective_escape(to_hex_string_list(s))
