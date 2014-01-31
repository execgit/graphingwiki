# -*- coding: utf-8 -*-"
"""
    ClarifiedTopology macro plugin to MoinMoin/Graphingwiki
     - Shows the Topology information generated by Clarified
       Analyser as an image

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
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
import math
import csv

from MoinMoin.action import cache
from MoinMoin.action import AttachFile
from MoinMoin.macro.Include import _sysmsg

from graphingwiki.plugin.action.ShowGraph import GraphShower
from graphingwiki.plugin.action.metasparkline import write_surface, draw_line
from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.util import form_escape, make_tooltip, \
    cache_key, cache_exists, latest_edit, encode_page, decode_page
from graphingwiki import cairo, cairo_found

Dependencies = ['metadata']

def draw_topology(request, args, key):
    args = [x.strip() for x in args.split(',')]

    topology, flowfile, color = '', '', ''
    rotate, width = '', ''
    graph = GraphShower(request.page.page_name, request)

    # take flow file specification from arguments as flow=k.csv,
    # otherwise assume that the argument specifies the topology
    for arg in args:
        if '=' in arg:
            key, val = [x.strip() for x in arg.split('=', 1)]
            if key == 'color':
                color = val
            if key == 'flow':
                flowfile = val
            if key == 'rotate':
                rotate = True
            if key == 'width':
                try:
                    width = float(val)
                except ValueError:
                    pass
        else:
            topology = arg

    _ = request.getText

    # Get all containers
    args = 'CategoryContainer, %s=/.+/' % (topology)

    #request.write(args)

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, styles = metatable_parseargs(request, args,
                                                     get_all_keys=True)

    if not pagelist:
        return False, "", \
            _sysmsg % ('error', "%s: %s" % 
                       (_("No such topology or empty topology"), 
                        form_escape(topology)))

    coords = dict()
    images = dict()
    aliases = dict()
    areas = dict()
    colors = dict()

    # Make a context to calculate font sizes with
    # There must be a better way to do this, I just don't know it!
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)

    allcoords = list()
    for page in pagelist:
        data = get_metas(request, page, 
                         [topology, 'gwikishapefile', 'tia-name', color],
                         checkAccess=False, formatLinks=True)

        crds = [x.split(',') for x in data.get(topology, list)]

        if not crds:
            continue
        crds = [x.strip() for x in crds[0]]
        if not len(crds) == 2:
            continue

        try:
            start_x, start_y = int(crds[0]), int(crds[1])
        except ValueError:
            continue

        coords[page] = start_x, start_y
        allcoords.append((start_x, start_y))

        img = data.get('gwikishapefile', list())
        if color:
            clr = data.get(color, list())
            if clr:
                colors[page] = clr[0]

        alias = data.get('tia-name', list())
        # Newer versions of analyzer do not use aliases anymore
        if not alias:
            alias = [page]

        aliases[page] = alias[0]

        if img:
            # Get attachment name, name of the page it's on, strip
            # link artifacts, find filesys name
            img = img[0].split(':')[1]
            pname = '/'.join(img.split('/')[:-1])
            img = img.split('/')[-1]
            img = img.split('|')[0]
            img = img.rstrip('}').rstrip(']]')
            imgname = AttachFile.getFilename(request, pname, img)
            try:
                images[page] = cairo.ImageSurface.create_from_png(imgname)
                end_x = start_x + images[page].get_width()
                end_y = start_y + images[page].get_height()
            except cairo.Error:
                end_x = start_x
                end_y = start_y
                pass

        text_len = ctx.text_extents(aliases[page])[4]
        text_end = start_x + text_len
        if text_end > end_x:
            end_x = text_end

        # If there was no image or a problem with loading the image
        if not page in images:
            # Lack of image -> black 10x10 rectangle is drawn
            end_x, end_y = start_x + 10, start_y + 10

        allcoords.append((end_x, end_y))

    if flowfile:
        flowcoords = list()
        flowname = AttachFile.getFilename(request, topology, flowfile)
        try:
            flows = csv.reader(file(flowname, 'r').readlines(), delimiter=';')
        except IOError:
            return False, "", \
                _sysmsg % ('error', "%s: %s" % 
                           (_("No such flowfile as attachment on topology page"), 
                            form_escape(flowfile)))

        flows.next()
        for line in flows:
            if not line:
                continue
            try:
                flowcoords.append((line[0], line[6]))
            except IndexError:
                # Pasted broken lines?
                pass

    max_x = max([x[0] for x in allcoords])
    min_x = min([x[0] for x in allcoords])
    max_y = max([x[1] for x in allcoords])
    min_y = min([x[1] for x in allcoords])

    # Make room for text under pictures
    if rotate:
        surface_y = max_y - min_y
        surface_x = max_x - min_x + 25
    else:
        surface_y = max_y - min_y + 25
        surface_x = max_x - min_x

    try:
        # Get background image, if any
        toponame = AttachFile.getFilename(request, topology, 'shapefile.png')
        background = cairo.ImageSurface.create_from_png(toponame)

        h = background.get_height()
        w = background.get_width()
        diff_x = w - surface_x
        diff_y = h - surface_y

        if diff_x > 0:
            surface_x = w
        else:
            diff_x = 0

        if diff_y > 0:
            surface_y = h
        else:
            diff_y = 0

    except cairo.Error:
        background = None
        diff_x = 0
        diff_y = 0
        pass

    # Setup Cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 int(surface_x), int(surface_y))


    # request.write(repr([surface_x, surface_y]))
    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)

    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(0, 0, surface_x, surface_y)
    ctx.fill()

    if background:
        # Center background if not large. Again, I'm just guessing
        # where the background image should be, and trying to mimic
        # analyzer.
        h = background.get_height()
        w = background.get_width()
        start_x, start_y = 0, 0
        if w < surface_x:
            start_x = start_x - min_x - w/2
        if h < surface_y:
            start_y = start_y - min_y - h/2
        ctx.set_source_surface(background, start_x, start_y)
        ctx.rectangle(start_x, start_y, w, h)
        ctx.fill()

    midcoords = dict()
    for page in pagelist:
        if not coords.has_key(page):
            continue

        x, y = coords[page]
#         request.write('<br>' + repr(get_metas(request, page, ['tia-name'])) + '<br>')
#         request.write(repr(coords[page]) + '<br>')
#         request.write(str(x-min_x) + '<br>')
#         request.write(str(y-min_y) + '<br>')

        # FIXME need more data to align different backgrounds
        # correctly, this is just guessing
        start_x = x - min_x + (diff_x / 2)
        start_y = y - min_y + (diff_y / 3)

        w, h = 10, 10
        if not images.has_key(page):
            ctx.set_source_rgb(0, 0, 0)
        else:
            h = images[page].get_height()
            w = images[page].get_width()
            if colors.has_key(page):
                clr = graph.hashcolor(colors[page])
                r, g, b = [int(''.join(x), 16) / 255.0 for x in 
                           zip(clr[1::2], clr[2::2])]
                ctx.set_source_rgb(r, g, b)
            else:
                ctx.set_source_rgb(1, 1, 1)

        midcoords[page] = (start_x + w / 2, start_y + h / 2)
        ctx.rectangle(start_x, start_y, w, h)
        ctx.fill()

        if images.has_key(page):
            ctx.set_source_surface(images[page], start_x, start_y)
            ctx.rectangle(start_x, start_y, w, h)
            ctx.fill()

        text = make_tooltip(request, page)

        areas["%s,%s,%s,%s" % (start_x, start_y, start_x + w, start_y + h)] = \
            [page, text, 'rect']


        if page in aliases:
            ctx.set_source_rgb(0, 0, 0)
            if rotate:
                ctx.move_to(start_x + w + 10, start_y + h)
            else:
                ctx.move_to(start_x, start_y + h + 10)

            ## FIXME, should parse links more nicely, now just removes
            ## square brackets
            text = aliases[page].lstrip('[').rstrip(']')

            if rotate:
                ctx.rotate(-90.0*math.pi/180.0)

            ctx.show_text(text)

            if rotate:
                ctx.rotate(90.0*math.pi/180.0)

    if flowfile:
        ctx.set_line_width(1)
        ctx.set_source_rgb(0, 0, 0)
        for start, end in flowcoords:
            if (not midcoords.has_key(start) or
                not midcoords.has_key(end)):
                continue
            sx, sy = midcoords[start]
            ex, ey = midcoords[end]
            ctx.move_to(sx, sy)
            ctx.line_to(ex, ey)
            #request.write("%s %s<br>" % (start, end))
            #request.write("%s %s %s %s<br>" % (sx, sy, ex, ey))
            ctx.stroke()

    s2 = surface

    if width:
        # For scaling
        new_surface_y = width
        factor = surface_y/new_surface_y
        new_surface_x = surface_x / factor

        # Recalculate image map data
        newareas = dict()
        for coords, data in areas.iteritems():
            corners = [float(x) for x in coords.split(',')]
            corners = tuple(x / factor for x in corners)
            newareas['%s,%s,%s,%s' % corners] = data
        areas = newareas
    else:
        new_surface_y = surface_y
        new_surface_x = surface_x

    if rotate:
        temp = new_surface_x
        new_surface_x = new_surface_y
        new_surface_y = temp
        temp = surface_x
        surface_x = surface_y
        surface_y = temp
        transl = -surface_x

    s2 = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 int(new_surface_x), int(new_surface_y))

    ctx = cairo.Context(s2)

    if rotate:
        ctx.rotate(90.0*math.pi/180.0)

        # Recalculate image map data
        newareas = dict()
        for coords, data in areas.iteritems():
            corners = coords.split(',')
            corners = [float(x) for x in coords.split(',')]
            corners = tuple([new_surface_x - corners[1], corners[0], 
                             new_surface_x - corners[3], corners[2]])
            newareas['%s,%s,%s,%s' % corners] = data
        areas = newareas

    if width:
        ctx.scale(new_surface_x/surface_x, new_surface_y/surface_y)

    if rotate:
        ctx.translate(0, -surface_x)
        
    ctx.set_source_surface(surface, 0, 0)
    ctx.paint()

    data = write_surface(s2)

    map = ''
    for coords in areas:
        name, text, shape = areas[coords]
        pagelink = request.script_root + u'/' + name

        tooltip = "%s\n%s" % (name, text)

        map += u'<area href="%s" shape="%s" coords="%s" title="%s">\n' % \
            (form_escape(pagelink), shape, coords, tooltip)

    return True, data, map

def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    if not args:
        args = request.page.page_name

    key = cache_key(request, (macro.name, args, latest_edit(request)))

    map_text = 'usemap="#%s" ' % (key)

    if not cache_exists(request, key):
        succ, data, mappi = draw_topology(request, args, key)
        if not succ:
            return mappi

        mappi = encode_page(mappi)
        cache.put(request, key, data, content_type='image/png')
        cache.put(request, key + '-map', mappi, content_type='text/html')
    else:
        mappifile = cache._get_datafile(request, key + '-map')
        mappi = mappifile.read()
        mappifile.close()

    div = u'<div class="ClarifiedTopology">\n' + \
        u'<img %ssrc="%s" alt="%s">\n</div>\n' % \
        (map_text, cache.url(request, key), _('topology'))

    map = u'<map id="%s" name="%s">\n' % (key, key)
    map += decode_page(mappi)
    map += u'</map>\n'
    
    return div + map
