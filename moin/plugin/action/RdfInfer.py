from codecs import getencoder
from urllib import quote
import os

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.formatter.text_html import Formatter 
from MoinMoin.Page import Page

from euler import run_called as run_inference

def execute(pagename, request):
    _ = request.getText
    request.http_headers()

    # This action generate data using the user language
    request.setContentLanguage(request.lang)

    wikiutil.send_title(request, _('Inference'), pagename=pagename)

    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    formatter = Formatter(request)
    request.write(formatter.startContent("content"))

    infer = ''
    if request.form.has_key('infer'):
        infer = ''.join(request.form['infer'])

    request.write(u'<form method="GET" action="%s">\n' % pagename)
    request.write(u'<input type=hidden name=action value="%s">' %
                  ''.join(request.form['action']))

    request.write(u'<textarea name="infer" rows=10 cols=80>%s</textarea>' %
                  infer)
    request.write(u'<input type=submit value="Submit!">\n</form>\n')

    if infer:
        if request.cfg.interwikiname:
            wikiname = quote(request.cfg.interwikiname)
        else:
            wikiname = quote(request.cfg.sitename)

        pageobj = Page(request, pagename)
        pagedir = pageobj.getPagePath()

        # Encoder from unicode to charset selected in config
        encoder = getencoder(config.charset)
        def _e(str):
            return encoder(str, 'replace')[0]

        n3file = os.path.join(pagedir, '../', 'rdfdata.shelve')
        pagename = _e(pagename)

        rdfdump = wikiutil.importPlugin(request.cfg, 'action',
                                        'N3Dump', 'rdfdump')

        n3data = rdfdump(n3file, wikiname, request.getBaseURL() + '/')

#         request.write(formatter.preformatted(1))
#         request.write(n3data + infer)
#         request.write(formatter.preformatted(0))

        data = run_inference(n3data + infer)
        request.write(formatter.preformatted(1))
        request.write(data)
        request.write(formatter.preformatted(0))
        
#     args = [x for x in request.form if x != 'action']
#     if args:
#         request.write(formatter.preformatted(1))
#         for arg in args:
#             request.write(arg)
#             for val in request.form[arg]:
#                 request.write(" " + val)
#             request.write("\n")
#         request.write(formatter.preformatted(0))

    # End content
    request.write(formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)
