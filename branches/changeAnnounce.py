#!/usr/bin/env python

import codecs
import optparse
import os
import sys
import traceback

from types import StringType, IntType, LongType, DictType, ListType, TupleType
try: from types import BooleanType
except ImportError: BooleanType = None

def bencode(data=None,file=None):
  "returns bencoded data, file may be name or descriptor, data encoded directly"
  class Bencached(object):
    __slots__ = ['bencoded']
    def __init__(self, s):
      self.bencoded = s
  def encode_bencached(x,r): r.append(x.bencoded)
  def encode_int(x, r): r.extend(('i', str(x), 'e'))
  def encode_string(x, r): r.extend((str(len(x)), ':', x))
  def encode_list(x, r):
    r.append('l')
    for i in x: encode_func[type(i)](i, r)
    r.append('e')
  def encode_dict(x,r):
    r.append('d')
    for k, v in sorted(list(x.items())):
      r.extend((str(len(k)), ':', k))
      encode_func[type(v)](v, r)
    r.append('e')
  encode_func = {}
  encode_func[type(Bencached(0))] = encode_bencached
  encode_func[IntType] = encode_func[LongType] = encode_int
  encode_func[StringType] = encode_string
  encode_func[ListType] = encode_func[TupleType] = encode_list
  encode_func[DictType] = encode_dict
  if BooleanType: encode_func[BooleanType] = encode_int
  if file is not None:
    if hasattr(file, 'read'): data = file.read()
    else: data = open(file,'rb').read() # string or binary?
  elif data is None: 
    raise ValueError('must provide file (name or descriptor) or data')
  x = data
  r = []
  encode_func[type(x)](x, r)
  return ''.join(r)


def bdecode(x):
  """This function decodes torrent data. 
  It comes (modified) from the GPL Python BitTorrent implementation"""
  def decode_int(x, f):
    f += 1
    newf = x.index('e', f)
    try: n = int(x[f:newf])
    except (OverflowError, ValueError):  n = long(x[f:newf])
    if x[f] == '-':
        if x[f + 1] == '0': raise ValueError
    elif x[f] == '0' and newf != f+1:  raise ValueError
    return (n, newf+1)
  def decode_string(x, f):
    colon = x.index(':', f)
    try:  n = int(x[f:colon])
    except (OverflowError, ValueError):  n = long(x[f:colon])
    if x[f] == '0' and colon != f+1:  raise ValueError
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
      if lastkey >= k:   raise ValueError
      lastkey = k
      r[k], f = decode_func[x[f]](x, f)
    return (r, f + 1)
  decode_func = {
    'l' : decode_list ,
    'd' : decode_dict,
    'i' : decode_int}
  for i in range(10): decode_func[str(i)] = decode_string
  if hasattr(x, 'read'): x = x.read()
  try:  r, l = decode_func[x[0]](x, 0)
  except (IndexError, KeyError, ValueError):
    try: 
      fd = open(x, 'r')
      x = fd.read()
      r, l = decode_func[x[0]](x,0)
      fd.close()
    except (OSError, IOError, IndexError, KeyError): raise ValueError
  if l != len(x):  raise ValueError
  return r


def parseArgs():
  usage = """%prog [OPTIONS] "old tracker url fragment" "new tracker url" directory [directory ..."""
  description = """Change the tracker announce of the torrents which contain the\
  string specified by "old tracker url fragment" to new tracker url.
  Works only on single tracker torrents."""
  parser = optparse.OptionParser(usage=usage)
  parser.description = description
  parser.add_option('-e', '--extension',default='.torrent',
    help="Set custom file extension (case insensitive) [Default: %default]")
  parser.add_option('-n', '--new-directory',default=None, 
    dest='directory',
    help="""do not overwrite torrent. write it to specified directory instead. \
this is done in a flat manner, even with -R""")
  parser.add_option('-p', '--print', action='store_true', default=False,
    dest='printonly',
    help="""just print the tracker urls and exit. include old tracker fragment,\
 do not include new tracker url""")
  parser.add_option('-R', '--recursive',action="store_true",
    default=False, 
    help="go through specified directories recursively")
  opts, args = parser.parse_args()
  if opts.printonly:
    if len(args) < 2:
      raise SystemExit('still need to specify old tracker fragment')
    old = args.pop(0)
    new = None
    dirs =args
  else:
    if len(args) < 3: raise SystemExit('not enough arguments')
    old = args.pop(0)
    new = args.pop(0)
    dirs = args
  return opts, old, new, dirs

def writeNewTorrent(opts, file, dir, tordata):
  if opts.directory: directory = opts.directory
  else: directory=dir
  bt = bencode(data=tordata)
  try: 
    fd = open(os.path.join(directory,file), 'w')
    fd.write(bt)
    fd.close()
  except (OSError, IOError): 
    print >> sys.stderr, file, directory, os.path.join(directory,file)
    print >> sys.stderr, traceback.format_exc()
    exit = raw_input('Do you want to continue y/N')
    if exit.lower() != 'y': raise SystemExit('user said exit')

def findTorrents(opts, dir):
  if opts.recursive:
    for subdir, _d, files in os.walk(dir):
      for file in files:
        if file.lower().endswith(opts.extension):
          yield subdir, file
  else:
    for file in os.listdir(dir):
      if (os.path.isfile(os.path.join(dir,file)) and 
        file.lower().endswith(opts.extension)): 
          yield dir, file

def main(opts, oldtrack, newtrack, dirs):
  for dir in dirs:
    for subdir, file in findTorrents(opts, dir):
      try: bt = bdecode(os.path.join(os.path.join(subdir, file)))
      except ValueError:
        print >> sys.stderr, "invalid torrent file %s" % os.path.join(subdir, file)
        continue
      if oldtrack in bt['announce']:
        if opts.printonly: print bt['announce']
        else:
          bt['announce'] = newtrack
          writeNewTorrent(opts,file,subdir,bt)  

if __name__ == '__main__':
  sys.stdout = codecs.getwriter("utf-8")(sys.stdout,"replace")
  sys.stderr = codecs.getwriter("utf-8")(sys.stderr,"replace")
  main(*parseArgs())
  
