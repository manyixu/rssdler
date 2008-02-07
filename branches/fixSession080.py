#!/usr/bin/env python
import getopt
import os
import sys

helpMessage = """Fix the session files from rtorrent 0.7.* to 0.8.0
  rTorrent stores its session files differently now. Unfortunately, code was not
  implemented to make the transition as smooth as it could be. However, the 
  change is minor enough that this script SHOULD reliably fix the issue. 
  
  To use, SHUTDOWN rTorrent, and BACKUP your session directories.
  
  python %s <session directory> [<other> <session> <dirs>]
  
  -h prints this message
  
""" % sys.argv[0]

# # # # # 
# Torrent Handling from BitTorrent by Bram Cohen/Petru Paler
def decode_int(x, f):
    f += 1
    newf = x.index('e', f)
    try:
        n = int(x[f:newf])
    except (OverflowError, ValueError):
        n = long(x[f:newf])
    if x[f] == '-':
        if x[f + 1] == '0':
            raise ValueError
    elif x[f] == '0' and newf != f+1:
        raise ValueError
    return (n, newf+1)

def decode_string(x, f):
    colon = x.index(':', f)
    try:
        n = int(x[f:colon])
    except (OverflowError, ValueError):
        n = long(x[f:colon])
    if x[f] == '0' and colon != f+1:
        raise ValueError
    colon += 1
    return (x[colon:colon+n], colon+n)

def decode_list(x, f):
    r, f = [], f+1
    while x[f] != 'e':
        v, f = decode_func[x[f]](x, f)
        r.append(v)
    return (r, f + 1)

def decode_dict(x, f):
    r, f = {}, f+1
    lastkey = None
    while x[f] != 'e':
        k, f = decode_string(x, f)
        if lastkey >= k:
            raise ValueError
        lastkey = k
        r[k], f = decode_func[x[f]](x, f)
    return (r, f + 1)

decode_func = {}
decode_func['l'] = decode_list
decode_func['d'] = decode_dict
decode_func['i'] = decode_int
decode_func['0'] = decode_string
decode_func['1'] = decode_string
decode_func['2'] = decode_string
decode_func['3'] = decode_string
decode_func['4'] = decode_string
decode_func['5'] = decode_string
decode_func['6'] = decode_string
decode_func['7'] = decode_string
decode_func['8'] = decode_string
decode_func['9'] = decode_string

def bdecode(x):
    try:
        r, l = decode_func[x[0]](x, 0)
    except (IndexError, KeyError):
        raise ValueError
    if l != len(x):
        raise ValueError
    return r

from types import StringType, IntType, LongType, DictType, ListType, TupleType

class Bencached(object):
    __slots__ = ['bencoded']

    def __init__(self, s):
        self.bencoded = s

def encode_bencached(x,r):
    r.append(x.bencoded)

def encode_int(x, r):
    r.extend(('i', str(x), 'e'))

def encode_string(x, r):
    r.extend((str(len(x)), ':', x))

def encode_list(x, r):
    r.append('l')
    for i in x:
        encode_func[type(i)](i, r)
    r.append('e')

def encode_dict(x,r):
    r.append('d')
    ilist = x.items()
    ilist.sort()
    for k, v in ilist:
        r.extend((str(len(k)), ':', k))
        encode_func[type(v)](v, r)
    r.append('e')

encode_func = {}
encode_func[type(Bencached(0))] = encode_bencached
encode_func[IntType] = encode_int
encode_func[LongType] = encode_int
encode_func[StringType] = encode_string
encode_func[ListType] = encode_list
encode_func[TupleType] = encode_list
encode_func[DictType] = encode_dict

try:
    from types import BooleanType
    encode_func[BooleanType] = encode_int
except ImportError:
    pass

def bencode(x):
    r = []
    encode_func[type(x)](x, r)
    return ''.join(r)



# # # # # 
def parseArgs(args):
  try: 
    (argp, rest) =  getopt.gnu_getopt(args, ",h", ['help'])
  except  getopt.GetoptError:
    print >> sys.stderr, helpMessage
    sys.exit(1)
  if not rest: 
    print helpMessage
    raise SystemExit
  return rest

def checkArgs(directories):
    error=''
    for directory in directories:
        if not os.path.isdir(directory): 
            error += '%s is not a directory!%s' % (directory, os.linesep)
    if error:
        print >> sys.stderr, error
        raise SystemExit(1)

def getTorNames(dir):
    return [os.path.join(dir, x) for x in os.listdir(dir) if x.endswith('.torrent')]
  
def main():
    errors = ''
    directories =  parseArgs(sys.argv[1:])
    checkArgs(directories)
    for dir in directories:
        tors = getTorNames(dir)
        for tor in tors:
            fdr = open( tor, 'r')
            try: tord = bdecode(fdr.read())
            except ValueError, m:
                errors += '%s not a valid torrent%s' % (tor, os.linesep)
                continue
            fdr.close()
            if 'files' not in tord['info']: continue #single file torrent
            if 'rtorrent' not in tord: 
                errors += "file %s appears to not be a session file" % tor
                errors += os.linesep
                continue
            if tord['rtorrent']['directory'].endswith('/'):
                tord['rtorrent']['directory'] += tord['info']['name'] 
            else: tord['rtorrent']['directory'] += '/%s' % tord['info']['name']
            fdw = open(tor, 'w')
            fdw.write( bencode(tord) )
            fdw.close()
    if errors: print >> sys.stderr, errors
        

if __name__ == '__main__': main()
