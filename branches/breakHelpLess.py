#!/usr/bin/env python

"""A test case breaking the less-like behavior of help(python_object)
replacing sys.stdout with the utfWriter seems to be causing the issue
commenting it out should fix the problem.
These are just extra lines
to trigger the less-like behavior of help()
we have to fill the 
terminal otherwise less
will not get activated 
and the test case is difficult to observe










the end.
"""

import codecs
import sys
utfWriter = codecs.getwriter( "utf-8" )
sys.stdout = utfWriter( sys.stdout, "replace" )



