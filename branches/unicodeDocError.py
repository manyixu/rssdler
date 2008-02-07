#!/usr/bin/env python
# -*- coding: utf-8 -*-

#test = u'\u2208'
#test = u'∈'
#test = u'\u2215'
#test = u'ℕ'
test = u'hello'

u"""import unicodeDocError
help(unicodeDocError)
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
  File "/usr/lib/python2.4/site.py", line 333, in __call__
    return pydoc.help(*args, **kwds)
  File "/usr/lib/python2.4/pydoc.py", line 1656, in __call__
    self.help(request)
  File "/usr/lib/python2.4/pydoc.py", line 1700, in help
    else: doc(request, 'Help on %%s:')
  File "/usr/lib/python2.4/pydoc.py", line 1483, in doc
    pager(title %% desc + '\n\n' + text.document(object, name))
  File "/usr/lib/python2.4/pydoc.py", line 1311, in pager
    pager(text)
  File "/usr/lib/python2.4/pydoc.py", line 1331, in <lambda>
    return lambda text: pipepager(text, 'less')
  File "/usr/lib/python2.4/pydoc.py", line 1352, in pipepager
    pipe.write(text)
UnicodeEncodeError: 'ascii' codec can't encode character u'deleted to make testcase work' in position 1225: ordinal not in range(128)
remove the below line to get help(thismodule) to work
%s
""" % test
