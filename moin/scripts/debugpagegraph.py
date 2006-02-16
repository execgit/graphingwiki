#! /usr/bin/env python
# For debugging a single page graph, pagename given in sys.argv[1]

import sys
import os
import cPickle

sys.path.insert(0, CPEDIR)
from graphrepr import GraphRepr

try:
    wikipath = sys.argv[2]
    page = sys.argv[1]
    filepath = os.path.join(wikipath, 'data/pages', page, "graphdata.pickle")
except:
    print "Usage: " + sys.argv[0] + " <pagename> <path-to-wiki>" 
    raise

f = file(filepath)
g = cPickle.load(f)

for i in g.nodes.getall():
    print i[0]
    print [(x, getattr(g.nodes.get(*i), x)) for x in dict(g.nodes.get(*i))]

for i in g.edges.getall():
    print i
    print dict(g.edges.get(*i))

gr = GraphRepr(g, engine='neato')
gr.dot.set(proto='edge', len='3')
g.commit()

from tempfile import mkstemp
no, name = mkstemp()
gr.dot.layout(file=name)
f = file(name)
print f.read()
