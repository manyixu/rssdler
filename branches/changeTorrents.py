#!/usr/bin/env python2.5

from codecs import getreader, getwriter
from copy import deepcopy
import operator
import optparse
import os
import shutil
import sys
from types import StringType, IntType, LongType, DictType, ListType, \
  TupleType, BooleanType

def bencode(data=None,file=None,outfile=None):
  """returns bencoded data, file may be name or descriptor.
  if outfile specified, data written to file instead of returned."""
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
      encode_string(k,r) # r.extend((str(len(k)), ':', k))
      encode_func[type(v)](v, r)
    r.append('e')
  encode_func = {
    type(Bencached(0)) : encode_bencached,
    IntType : encode_int,
    LongType: encode_int,
    StringType : encode_string,
    ListType : encode_list,
    TupleType : encode_list,
    DictType : encode_dict,
    BooleanType : encode_int, }
  if file != None:
    if hasattr(file, 'read'): data = file.read()
    else: data = open(file,'r').read() # string or binary?
  if data == None: 
    raise ValueError('must provide file (name or descriptor) or data')
  x = data
  r = []
  encode_func[type(x)](x, r)
  if outfile != None:
    if hasattr(outfile,'write'): fd = outfile
    else: fd = open(outfile,'w')
    fd.write(''.join(r))
  else: return ''.join(r)

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
  except (IndexError, KeyError):
    try: 
      x = open(x, 'r').read()
      r, l = decode_func[x[0]](x,0)
    except (OSError, IOError, IndexError, KeyError): raise ValueError
  if l != len(x):  raise ValueError
  return r

# # # # # # # # # # # # # # # #
# Option Parsing and Sanity Checks
def userIntervention(opts,message):
  if opts.quiet: 
    return False
  elif opts.script: 
    print >> sys.stderr, message
    return True
  else:
    print >> sys.stderr, "%s %s" % ('Continue y/N?',message),
    if raw_input().lower() != y: return False
    else: return True

def checkInts(opts):
  rtorrentInts = []
  rtorrentKeys = []
  for x,y in opts.rtorrent_integer:
    if x not in opts.rtorrentInteger and not userIntervention(opts,  
      'Argument %s may not be recognized by rtorrent.' % x):
          raise SystemExit(1)
    try: y = int(y)
    except ValueError:
      if not userIntervention(opts, 
        "Rtorrent expects an integer, you did not give one."):
          raise SystemExit(1)
    rtorrentInts.append(y)
    rtorrentKeys.append(['rtorrent', x])
  opts.rtorrent_integer = rtorrentInts
  opts.rtorrent_integer_key = rtorrentKeys
  return opts

def checkStrings(opts):
  strs = []
  keys = []
  for x,y in opts.rtorrent_string:
    if x not in opts.rtorrentString and not userIntervention(opts, 
      'Argument %s may not be recognized by rtorrent.' % x):
        raise SystemExit(1)
    strs.append(y)
    keys.append(('rtorrent',x))
  opts.rtorrent_string = strs
  opts.rtorrent_string_key = keys
  return opts

def convertKeyValues(f):
  filt = []
  for j in f:
    if j.lower() != 'none':
      try: j = int(j)
      except ValueError: pass
      filt.append(j)
  return filt
  
def checkFilters(opts):
  if opts.move_complete: 
    opts.filter.append(('eq','rtorrent','complete','0'))
    opts.move = opts.move_complete
  elif opts.move_incomplete:
    opts.filter.append(('eq','rtorrent','complete','1'))
    opts.move = opts.move_incomplete
  opts.filter = [ convertKeyValues(x) for x in opts.filter ]
  if not all(hasattr(operator,x[0]) for x in opts.filter):
    raise SystemExit('illegal operator option')
  opts.filter_neg = [ convertKeyValues(x) for x in opts.filter_neg ]
  opts.printkeys = [ convertKeyValues(x) for x in opts.printkeys ]
  opts.set_key = [ convertKeyValues(x) for x in opts.set_key]
  return opts

def parseOpts():
  usage = "%prog [OPTIONS] directory [directories...]"
  description = """A script that will edit some features of torrent files,
but mainly for editing session files in rtorrent. Shut down rtorrent (or your
other torrent program) before running this script on any file already loaded
into rtorrent (or your torrent program).  Backing up your files is a) easy and
b) a good idea! DO IT!."""
  rtorrentInteger = set(['chunks_done', 'complete', 'hashing', 
    'ignore_commands', 'key', 'priority', 'state', 'state_changed', 
    'total_uploaded'])
  rtorrentString = set(['custom1', 'custom2', 'custom3', 'custom4', 'custom5', 
    'directory', 'tied_to_file'])
  parser = optparse.OptionParser(usage=usage)
  parser.description = description
  parser.add_option('-e', '--extension',default='.torrent',
    help="Set custom file extension. Use lower case! [Default: %default]")
  parser.add_option('-f','--filter',action='append',default=[],nargs=6,
    help="""a string of an operator action, 4 keys/list indices, and then a 
value to compare against. If you do not need to go that deep, specify none 
(case insensitive) and that level will be ignored. the last non-none argument
will be interpreted as the value. integers will be converted automatically. 
Filtering is done as an AND aka intersection aka all the filters must match 
(instead of just one). Can be specified more than once. Valid operator actions
are (though not all are sane, see pydoc for more information): %s""" % 
    str(tuple(sorted([x for x in dir(operator) if not x.startswith('_')])))[1:-1])
  parser.add_option('-F','--filter-neg',action='append',
    default=[],nargs=6,
    help="""like filter, with two differences: 1) is that it checks for the
boolean inverse, e.g. eq would imply not eq, contains would be not contains and
2) is that it does an OR match, so that ANYTHING that matches means this is
filtered out.""")
  parser.add_option('-m','--move', default=None,
    help="""Move file(s) associated with the torrents to this directory and
set rtorrent key 'directory' to this option. does nothing if no rtorrent
dictionary""")
  parser.add_option('--move-incomplete', default=None,
    help="""Move files that rtorrent believes to believe incomplete to directory
and set rtorrent key directory to this option. If rtorrent key does not exist,
those torrents will be moved.""")
  parser.add_option('--move-complete', default=None,
    help="""Move files that rtorrent believes to believe complete to directory
and set rtorrent key directory to this option. If rtorrent key does not exist,
those torrents will be moved.""")
  parser.add_option('-o','--old-tracker',default=None,
    help="Filter torrents for this string existing in the announce url. An easier filter")
  parser.add_option('-p','--print',default=[],action='append',nargs=4,dest='printkeys',
    help="""Takes 4 arguments, print out the specified key/list indices. Can be
specified more than once for multiple values to print. Behaves like --filter.""")
  parser.add_option('-q','--quiet', default=False,action='store_true',
    help="supress error messages. all confirmation messages will be assumed no.")
  parser.add_option('--rtorrent-integer',default=[],action='append',nargs=2,
    help="""Takes two arguments. Will set the key (first argument) to an integer
value (second argument). Keys that rtorrent recognizes as taking integer values
are: %s. Values other than these will produce error messages that the user must
confirm unless --scripting is supplied""" % str(sorted(list(rtorrentInteger)))[1:-1])
  parser.add_option('--rtorrent-string',default=[],action='append',nargs=2,
    help="""Like --rtorrent-integer, only sets a string argument. String keys:
%s.""" % str(sorted(list(rtorrentString)))[1:-1])
  parser.add_option('-r','--recursive',action="store_true", default=False,
    help="search recusively through the directorities specified")
  parser.add_option('-s','--script',action="store_true",default=False,
    help="When passed, all confirmation messages will be assumed 'yes'. CAREFUL")
  parser.add_option('-S','--set-key',action='append',default=[],nargs=5,
    help="""takes 5 arguments, like filter. Only instead of comparing with
equality, sets to the given value.""")
  parser.add_option('-t', '--tracker', default=None,
    help="set announce/tracker to this value. Does no""t work for multi-tracker torrents")
  parser.add_option('-v', '--verbose', default=False,action='store_true',
    help="""print success messages. Note that if both -q and -v are given, errors 
will be suppressed and success messages will be displayed""")
  opts, dirs = parser.parse_args()
  if len(filter(None, (opts.move_complete, opts.move_incomplete, opts.move))) > 1:
    raise SystemExit('can only specify one of --move, --move-complete, --move-incomplete')
  opts.rtorrentInteger = rtorrentInteger
  opts.rtorrentString = rtorrentString
  return checkFilters(checkStrings(checkInts(opts))), dirs

# # # # # # # # # # # # # # # #
# Filtering
def findTorrents(opts,dirs):
  m = "dir specified is not a dir %s, skipping"
  if opts.recursive:
    for dir in dirs:
      if os.path.isdir(dir):
        for subdir, _d, files in os.walk(dir):
          for file in files:
            if file.lower().endswith(opts.extension):
              yield subdir, file
      elif not opt.quiet:
        print >> sys.stderr,  m % dir
  else:
    for dir in dirs:
      if os.path.isdir(dir):
        for file in os.listdir(dir):
          if (os.path.isfile(os.path.join(dir,file)) and 
            file.lower().endswith(opts.extension)): 
              yield dir, file
      elif not opt.quiet:
        print >> sys.stderr,  m % dir

def filterTorrents(opts,bt):
  if opts.filter and not filterKeys(opts.filter, bt):
    return False
  if opts.filter_neg and filterKeys(opts.filter_neg, bt):
    return False
  return filterTracker(opts,bt)

def filterKeys(ops,bt):
  "ops,keys,checks need to be same length. if empty, returns False"
  return all( getattr(operator,x[0])(items_getter(bt,x[1:-1]), x[-1]) for x in ops )

def filterTracker(opts, bt):
  try: return opts.old_tracker in bt['announce']
  except TypeError: return True

# # # # # # # # # # # # # # # #
# GETTERS, SETTERS
def fapply(object, funcs, exceptions=None, failObj=None):
  """apply iterable of callables to the given object,
  with each function acting on the output of the other until the list is exhausted
  then the object is returned. 
  two keywords are taken: exceptions would be a tuple of exceptions to catch
  if an exception is raised and caught, failObj is returned"""
  def applynext(object, funcs,exceptions, failObj):
    try: return applynext(funcs.next()(object), funcs, exceptions, failObj)
    except StopIteration: return object
    except exceptions: return failObj
  return applynext(object,iter(funcs), exceptions,failObj)

def items_setter(item, keys, value):
  try: operator.setitem(items_getter(item,keys[:-1]), keys[-1], value)
  except TypeError: pass #should return failObj of None, None[x] raises this
  return item

def items_setters(obj, keyslist, values):
  for keys, value in zip(keyslist, values):
    items_setter(obj, keys, value)
  return obj

def items_getter(item, keys):
  return fapply(item, map(operator.itemgetter, keys))

def items_getters(item,keyslist):
  return [ items_getter(item, keys) for keys in keyslist ]
  #map(items_getter, repeat(item,len(keyslist)), keyslist)

# # # # # # # # # # # # # # # #
# Substance
def editTorrent(opts, bt):
  old = new = None
  if opts.tracker: operator.setitem(bt,'announce',opts.tracker)
  for keys in opts.set_key: 
    try: items_setter(bt,keys[:-1],keys[-1])
    except (KeyError, IndexError):
      if not userIntervention(opts, 'could not set some attributes for %s' % bt['info']['name']):
        return bt, old, new
  if 'rtorrent' in bt:
    try: items_setters(bt, 
      opts.rtorrent_integer_key + opts.rtorrent_string_key,
      opts.rtorrent_integer + opts.rtorrent_string)
    except (KeyError, IndexError):
      if not userIntervention(opts, 'could not set some attributes for %s' % bt['info']['name']):
        return bt, old, new
    if opts.move:  #lots of pre 0.8 and post 0.8 bs goig on here for rtorrent
      if bt['rtorrent']['directory'].rstrip('/').endswith(bt['info']['name']):
        old = bt['rtorrent']['directory']
        items_setter(bt, ['rtorrent','directory'],'/'.join((opts.move.rtsrip('/'),bt['info']['name'])))
        new = bt['rtorrent']['directory']
      else: # since rtorrent is *nix only, '/' is used as path separator
        old = '/'.join((bt['rtorrent']['directory'].rstrip('/'), bt['info']['name']))
        items_setter(bt, ['rtorrent','directory'], opts.move)
        new = '/'.join((opts.move.rstrip('/'),bt['rtorrent']['info']['name']))
  return bt, old, new

def writeTorrent(opts, bt, file, old, new):
  mwrite = "Failed to write torrent %s"
  mmake = "Failed to create torrent, invalid data got introduced %s"
  m = "\nFailed. Proceeding to the next torrent, no further action on this one"
  try: bencode(data=bt, outfile=file)
  except (OSError, IOError):
    if not opts.quiet:
      print >> sys.stderr, ''.join((mwrite % file, m))
  except (TypeError, ValueError):
    if not opts.quiet:
      print >> sys.stderr, ''.join((mmake % file,m))
  else:
    if opts.verbose: print('Changed %s' % file)
    moveData(opts,old,new)

def moveData(opts, old, new):
  if old != new:
    if not os.path.exists(old):
      if not opts.quiet: 
        print >> sys.stderr, "could not find data at %s. Not moving" % old
    elif os.path.exists(new):
      if not opts.quiet: 
        print >> sys.stderr, "data already exists at %s. Not moving" % new
    else:
      try: shutil.move(old, new)
      except (OSError, IOError):
        if not opts.quiet:
          print >> sys.stderr, "Failed to move files from %s to %s" % (old,new)
      else:
        if opts.verbose: print 'Moved %s to %s' % (old,new)

def main(opts, dirs):
  for dir, file in findTorrents(opts,dirs):
    dfil = os.path.join(dir,file)
    try: bt = bdecode(dfil)
    except (ValueError, TypeError):
      if not opts.quiet:
        print >> sys.stderr,"invalid torrent data in %s" % dfil
      continue
    if filterTorrents(opts, bt):
      if opts.printkeys:
        print dfil
        for i in items_getters(bt, opts.printkeys): print '\t%s' % i
      else:
        btn, oldfd, newfd = editTorrent(opts, deepcopy(bt))
        if btn != bt:
          writeTorrent(opts, btn,dfil, oldfd, newfd)

if __name__ == '__main__':
  sys.stdin = getreader("utf-8")(sys.stdin,"replace")
  sys.stdout = getwriter("utf-8")(sys.stdout,"replace")
  sys.stderr = getwriter("utf-8")(sys.stderr,"replace")
  main(*parseOpts())
