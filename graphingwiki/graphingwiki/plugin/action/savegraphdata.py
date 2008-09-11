# -*- coding: utf-8 -*-"
"""
    savegraphdata class for saving the semantic data of pages

    @copyright: 2006 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

import re
import os
import cPickle
import shelve
from time import time

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.wiki import Parser
from MoinMoin.wikiutil import importPlugin
from MoinMoin.util.lock import WriteLock

# graphlib imports
from graphingwiki import graph
from graphingwiki.patterns import special_attrs
from graphingwiki.editing import parse_categories

# Page names cannot contain '//'
url_re = re.compile(u'^(%s)%%3A//' % (Parser.url_pattern))

# We only want to save linkage data releted to pages in this wiki,
# Is this still relevant: "Interwiki links will have ':' in their
# names (this will not affect pages as their names are url quoted at
# this stage)"
def local_page(pagename):
    if url_re.search(pagename) or ':' in pagename:
        return False
    return True

# Add in-links from current node to local nodes
def shelve_add_in(shelve, (frm, to), linktype, nodeurl=''):
    if not linktype:
        linktype = '_notype'
    if local_page(to):
         temp = shelve.get(to, {})

         if not temp.has_key('in'):
             temp['in'] = {linktype: [frm]}
         elif not temp['in'].has_key(linktype):
             temp['in'][linktype] = [frm]
         else:
             temp['in'][linktype].append(frm)

         # Adding gwikiurl
         if nodeurl:
             if not temp.has_key('meta'):
                 temp['meta'] = {'gwikiURL': set([nodeurl])}
             else:
                 temp['meta']['gwikiURL'] = set([nodeurl])

         # Notification that the destination has changed
         temp['mtime'] = time()
         
         shelve[to] = temp

# Add out-links from local nodes to current node
def shelve_add_out(shelve, (frm, to), linktype, hit):
    if not linktype:
        linktype = '_notype'
    if local_page(frm):
         temp = shelve.get(frm, {})

         # Also add literal text (hit) for each link
         # eg, if out it SomePage, lit can be ["SomePage"]
         if not temp.has_key('out'):
             temp['out'] = {linktype: [to]}
             temp['lit'] = {linktype: [hit]}
         elif not temp['out'].has_key(linktype):
             temp['out'][linktype] = [to]
             temp['lit'][linktype] = [hit]
         else:
             temp['out'][linktype].append(to)
             temp['lit'][linktype].append(hit)

         shelve[frm] = temp

# Respectively, remove in-links
def shelve_remove_in(shelve, (frm, to), linktype):
    import sys
#    sys.stderr.write('Starting to remove in\n')
    temp = shelve.get(to, {})
    if local_page(to) and temp.has_key('in'):
        for type in linktype:
#            sys.stderr.write("Removing %s %s %s\n" % (frm, to, linktype))
            # eg. when the shelve is just started, it's empty
            if not temp['in'].has_key(type):
#                sys.stderr.write("No such type: %s\n" % type)
                continue
            while frm in temp['in'][type]:
                temp['in'][type].remove(frm)

                # Notification that the destination has changed
                temp['mtime'] = time()

            if not temp['in'][type]:
                del temp['in'][type]
                
#                sys.stderr.write("Hey man, I think I did it!\n")
        shelve[to] = temp

# Respectively, remove out-links
def shelve_remove_out(shelve, (frm, to), linktype):
#    print 'Starting to remove out'
    temp = shelve.get(frm, {})
    if local_page(frm) and temp.has_key('out'):
        for type in linktype:
#            print "Removing %s %s %s" % (frm, to, linktype)
            # eg. when the shelve is just started, it's empty
            if not temp['out'].has_key(type):
#                print "No such type: %s" % type
                continue
            while to in temp['out'][type]:
                # As the literal text values for the links
                # are added at the same time, they have the
                # same index value
                i = temp['out'][type].index(to)
                temp['out'][type].remove(to)
                del temp['lit'][type][i]

#                print "removed %s" % (repr(to))

            if not temp['out'][type]:
                del temp['out'][type]
                del temp['lit'][type]
#                print "%s empty" % (type)
#            print "Hey man, I think I did it!"

        shelve[frm] = temp

def strip_meta(key, val):
    key = key.strip()
    if key != 'gwikilabel':
        val = val.strip()
    return key, val

def node_set_attribute(pagenode, key, val):
    key, val = strip_meta(key, val)
    vars = getattr(pagenode, key, None)
    if not vars:
        setattr(pagenode, key, set([val]))
    else:
        vars.add(val)
        setattr(pagenode, key, vars)

def shelve_unset_attributes(shelve, node):
    temp = shelve.get(node, {})

    if temp.has_key('meta'):
        temp['meta'] = {}
    if temp.has_key('acl'):
        temp['acl'] = ''
    if temp.has_key('include'):
        temp['include'] = set()

    if temp:
        shelve[node] = temp

def shelve_set_attribute(shelve, node, key, val):
    key, val = strip_meta(key, val)

    temp = shelve.get(node, {})

    if not temp.has_key('meta'):
        temp['meta'] = {key: set([val])}
    elif not temp['meta'].has_key(key):
        temp['meta'][key] = set([val])
    # a page can not have more than one label, shapefile etc
    elif key in special_attrs:
        temp['meta'][key] = set([val])
    else:
        temp['meta'][key].add(val)

    shelve[node] = temp

def getlinktype(augdata):
    linktype = ''
    if len(augdata) > 1:
        linktype = augdata[0]
    return linktype

def add_meta(globaldata, pagenode, pagename, hit):
    hit = hit[11:-3]
    args = hit.split(',')

    # If no data, continue
    if len(args) < 2:
        return

    key = args[0]
    val = ','.join(args[1:])

    # Do not handle empty metadata, except empty labels
    if key != 'gwikilabel':
        val = val.strip()
    if not val:
        return

    # Values to be handed to dot
    if key in special_attrs:
        setattr(pagenode, key, val)
        shelve_set_attribute(globaldata, pagename, key, val)
        # If color defined� set page as filled
        if key == 'fillcolor':
            setattr(pagenode, 'style', 'filled')
            shelve_set_attribute(globaldata, pagename, 'style', 'filled')
        return

    # Save to pagegraph and shelve's metadata list
    node_set_attribute(pagenode, key, val)
    shelve_set_attribute(globaldata, pagename, key, val)

def add_include(globaldata, pagenode, pagename, hit):
    hit = hit[11:-3]
    pagearg = hit.split(',')[0]

    # If no data, continue
    if not pagearg:
        return

    temp = globaldata.get(pagename, {})
    temp.setdefault('include', set()).add(pagearg)
    globaldata[pagename] = temp

def parse_link(wikiparse, hit, type):
    replace = getattr(wikiparse, '_' + type + '_repl')
    attrs = replace(hit)

    if len(attrs) == 4:
        # Attachments, eg:
        # URL   = Page?action=AttachFile&do=get&target=k.txt
        # name  = Page/k.txt        
        nodename = attrs[1]
        nodeurl = attrs[0]
    elif len(attrs) == 3:
        # Local pages
        # Name of node for local nodes = pagename
        nodename = attrs[1]
        nodeurl = attrs[0]
        # To prevent subpagenames from sucking
        if nodeurl.startswith('/'):
            nodeurl = './' + nodename
    elif len(attrs) == 2:
        # Name of other nodes = url
        nodeurl = attrs[0]
        nodename = nodeurl

        # Change name for different type of interwikilinks
        if type == 'interwiki':
            nodename = hit
        elif type == 'url_bracket':
            # Interwikilink in brackets?
            iw = re.search(r'\[(?P<iw>.+?)[\] ]',
                           hit).group('iw')

            if iw.split(":")[0] == 'wiki':
                iw = iw.split(None, 1)[0]
                iw = iw[5:].replace('/', ':', 1)
                nodename = iw
        # Interwikilink turned url?
        elif type == 'url':
            if hit.split(":")[0] == 'wiki':
                iw = hit[5:].replace('/', ':', 1)
                nodename = iw
    else:
        # Catch-all
        return "", "", ""

    # augmented links, eg. [:PaGe:Ooh: PaGe]
    augdata = [x.strip() for x in attrs[-1].split(': ')]

    linktype = getlinktype(augdata)

    return nodename, nodeurl, linktype

def add_link(globaldata, pagename, pagegraph,
             nodename, nodeurl, linktype, hit):
    # Add node if not already added
    if not pagegraph.nodes.get(nodename):
        n = pagegraph.nodes.add(nodename)
        n.gwikiURL = nodeurl

    edge = [pagename, nodename]

    # in-links
    if linktype.endswith('From'):
        linktype = linktype[:-4]
        edge.reverse()

    shelve_add_in(globaldata, edge, linktype, nodeurl)
    shelve_add_out(globaldata, edge, linktype, hit)

    # Add edge if not already added
    e = pagegraph.edges.get(*edge)
    if not e:
        e = pagegraph.edges.add(*edge)

    if not linktype:
        linktype = '_notype'

    if hasattr(e, 'linktype'):
        e.linktype.add(linktype)
    else:
        e.linktype = set([linktype])


def parse_text(request, globaldata, page, text):
    pagename = page.page_name

    # import text_url -formatter
    try:
        Formatter = importPlugin(request.cfg, 'formatter',
                                 'text_url', "Formatter")
    except:
        # default to plain text
        from MoinMoin.formatter.text_plain import Formatter

    urlformatter = Formatter(request)

    # Get formatting rules from Parser/wiki
    # Regexps used below are also from there
    wikiparse = Parser(text, request)
    wikiparse.formatter = urlformatter
    urlformatter.setPage(page)

    rules = wikiparse.formatting_rules.replace('\n', '|')

    if request.cfg.bang_meta:
        rules = ur'(?P<notword>!%(word_rule)s)|%(rules)s' % {
            'word_rule': wikiparse.word_rule,
            'rules': rules,
            }

    # For versions with the deprecated config variable allow_extended_names
    if not '?P<wikiname_bracket>' in rules:
        rules = rules + ur'|(?P<wikiname_bracket>\[".*?"\])'

    all_re = re.compile(rules, re.UNICODE)
    eol_re = re.compile(r'\r?\n', re.UNICODE)
    # end space removed from heading_re, it means '\n' in parser/wiki
    heading_re = re.compile(r'\s*(?P<hmarker>=+)\s.*\s(?P=hmarker)',
                            re.UNICODE)

    # These are the match types that really should be noted
    linktypes = ["wikiname_bracket", "word",
                  "interwiki", "url", "url_bracket"]

    # Get lines of raw wiki markup
    lines = eol_re.split(text)

    # status: are we in preprocessed areas?
    inpre = False
    pretypes = ["pre", "processor"]

    # status: have we just entered a link with dict,
    # we should not enter it again
    dicturl = False

    # Init pagegraph
    pagegraph = graph.Graph()
    pagegraph.charset = config.charset

    # add a node for current page
    pagenode = pagegraph.nodes.add(pagename)
    in_processing_instructions = True

    for line in lines:

        # Have to handle the whole processing instruction shebang
        # in order to handle ACL:s correctly
        if in_processing_instructions:
            found = False
            for pi in ("##", "#format", "#refresh", "#redirect", "#deprecated",
                       "#pragma", "#form", "#acl", "#language"):
                if line.lower().startswith(pi):
                    found = True
                    if pi == '#acl':
                        temp = globaldata.get(pagename, {})
                        temp['acl'] = line[5:]
                        globaldata[pagename] = temp

            if not found:
                in_processing_instructions = False
            else:
                continue

        # Comments not processed
        if line[0:2] == "##":
            continue

        # Headings not processed
        if heading_re.match(line):
            continue
        for match in all_re.finditer(line):
            for type, hit in match.groupdict().items():
                #if hit:
                #    print hit, type

                # Skip empty hits
                if hit is None:
                    continue

                # We don't want to handle anything inside preformatted
                if type in pretypes:
                    inpre = not inpre
                    #print inpre

                # Handling of MetaData- and Include-macros
                elif type == 'macro' and not inpre:
                    if hit.startswith('[[MetaData'):
                        add_meta(globaldata, pagenode, pagename, hit)

                    if hit.startswith('[[Include'):
                        add_include(globaldata, pagenode, pagename, hit)

                # Handling of links
                elif type in linktypes and not inpre:
                    # If we just came from a dict, which saved a typed
                    # link, do not save it again
                    if dicturl:
                        dicturl = False
                        continue

                    name, url, linktype = parse_link(wikiparse, hit, type)

                    if name:
                        add_link(globaldata, pagename, pagegraph,
                                 name, url, linktype, hit)

                # Links and metadata defined in a definition list
                elif type == 'dl' and not inpre:
                    data = line.split('::')
                    key, val = data[0], '::'.join(data[1:])
                    key = key.lstrip()

                    if not key:
                        continue

                    # Try to find if the value points to a link
                    matches = all_re.match(val.lstrip())
                    if matches:
                        # Take all matches if hit non-empty
                        # and hit type in linktypes
                        match = [(type, hit) for type, hit in
                                 matches.groupdict().iteritems()
                                 if hit is not None \
                                 and type in linktypes]

                        # If link, 
                        if match:
                            type, hit = match[0]

                            # and nothing but link, save as link
                            if hit == val.strip():

                                val = val.strip()
                                name, url, linktype = parse_link(wikiparse,\
                                                                 hit, type)

                                # Take linktype from the dict key
                                linktype = getlinktype([x for x in key, val])

                                if name:
                                    add_link(globaldata, pagename,
                                             pagegraph,
                                             name, url, linktype, hit)

                                    # The val will also be parsed by
                                    # Moin's link parser -> need to
                                    # have state in the loop that this
                                    # link has already been saved
                                    dicturl = True

                    if dicturl:
                        continue

                    # If it was not link, save as metadata. 
                    add_meta(globaldata, pagenode, pagename,
                             "[[MetaData(%s,%s)]]" % (key, val))

    # Add the page categories as links too
    _, categories = parse_categories(request, text)
    for category in categories:
        name, url, linktype = parse_link(wikiparse, category, "word")
        if name:
            add_link(globaldata, pagename, pagegraph,
                     name, url, "gwikicategory", category)

    return globaldata, pagegraph

def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    globaldata = request.graphdata

    # Expires old locks left by crashes etc.
    # Page locking mechanisms should prevent this code being
    # executed prematurely - thus expiring both read and
    # write locks
    request.lock = WriteLock(request.cfg.data_dir, timeout=10.0)
    request.lock.acquire()
    
    # Page graph file to save detailed data in
    gfn = os.path.join(pagedir,'graphdata.pickle')

    old_data = graph.Graph()

    # load graphdata if present and not trashed
    if os.path.isfile(gfn) and os.path.getsize(gfn):
        pagegraphfile = file(gfn)
        old_data = cPickle.load(pagegraphfile)
        pagegraphfile.close()

    # Get new data from parsing the page
    newdata, pagegraph = parse_text(request, dict(), page, text)

    # Find out which links need to be saved again
    oldedges = set()
    for edge in old_data.edges.getall():
        e = old_data.edges.get(*edge)
        linktypes = getattr(e, 'linktype', ['_notype'])
        for linktype in linktypes:        
            ed = tuple(((edge), (linktype)))
            oldedges.add(ed)

    newedges = set()
    for edge in pagegraph.edges.getall():
        e = pagegraph.edges.get(*edge)
        linktypes = getattr(e, 'linktype', ['_notype'])
        for linktype in linktypes:        
            ed = tuple(((edge), linktype))
            newedges.add(ed)

    remove_edges = oldedges.difference(newedges)
    add_edges = newedges.difference(oldedges)

    # Save the edges
    for edge, linktype in remove_edges:
#        print "Removed", edge, linktype
#        print edge, linktype
        shelve_remove_in(globaldata, edge, [linktype])
        shelve_remove_out(globaldata, edge, [linktype])
    for edge, linktype in add_edges:
#        print "Added", edge, linktype
        frm, to = edge
        data = [(x,y) for x,y in enumerate(newdata[frm]['out'][linktype])
                if y == to]

        # Temporary hack: add gwikiurl:s to some edges
        nodeurl = newdata.get(to, '')
        if nodeurl:
            nodeurl = nodeurl.get('meta', {}).get('gwikiURL', set(['']))
            nodeurl = list(nodeurl)[0]

        # Save both the parsed and unparsed versions
        for idx, item in data:
            hit = newdata[frm]['lit'][linktype][idx]
            shelve_add_in(globaldata, edge, linktype, nodeurl)
            shelve_add_out(globaldata, edge, linktype, hit)

    # Insert metas and other stuff from parsed content
    temp = globaldata.get(pagename, {'time': time(), 'saved': True})
    temp['meta'] = newdata.get(pagename, {}).get('meta', {})
    temp['acl'] = newdata.get(pagename, {}).get('acl', '')
    temp['include'] = newdata.get(pagename, {}).get('include', set())
    temp['mtime'] = time()
    temp['saved'] = True
    globaldata[pagename] = temp

    # Save graph as pickle, close
    pagegraphfile = file(gfn, 'wb')
    cPickle.dump(pagegraph, pagegraphfile)
    pagegraphfile.close()

    request.lock.release()
