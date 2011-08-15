# -*- coding: utf-8 -*-"
"""
    MetaFormEdit action to MoinMoin
     - Editing page metadata usig the pages as forms of sort

    @copyright: 2008 by Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re
import StringIO

from copy import copy

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page

from graphingwiki import actionname, SEPARATOR
from graphingwiki.util import encode, format_wikitext, form_unescape
from graphingwiki.util import form_writer as wr

from graphingwiki.editing import get_properties

from savegraphdata import parse_text

value_re = re.compile(
    '(<dt>.+?</dt>\s*<dd>\s*)<input class="metavalue" type="text" ' +
    'name="(.+?)" value="\s*(.*?)\s*">')

# Override Page.py to change the parser. This method has the advantage
# that it works regardless of any processing instructions written on
# page, including the use of other parsers
class FormPage(Page):

    def __init__(self, request, page_name, **keywords):
        # Cannot use super as the Moin classes are old-style
        apply(Page.__init__, (self, request, page_name), keywords)

    # It's important not to cache this, as the wiki thinks we are
    # using the default parser
    def send_page_content(self, request, body, format="wiki_form", 
                          format_args='', do_cache=0, **kw):
        kw['format'] = "wiki_form"
        kw['format_args'] = format_args
        kw['do_cache'] = 0
        apply(Page.send_page_content, (self, request, body), kw)

def execute(pagename, request):
    _ = request.getText

    formpage = '../' * pagename.count('/') + pagename

    form = request.values.to_dict(flat=False)

    frm = wr(
        u'<form method="POST" enctype="multipart/form-data" action="%s">\n',
             actionname(request))+\
          wr(u'<input type="hidden" name="action" value="MetaEdit">\n')+\
          wr(u'<input type="hidden" name="gwikiseparator" value="%s">\n', 
             SEPARATOR)
    
    btn = '<div class="saveform"><p class="savemessage">' + \
          wr('<input type=submit name=saveform value="%s">',
             _(form.get('saveBtnText', ['Save Changes'])[0])) + \
             wr('<input type=submit name=cancel value="%s">',
                _('Cancel')) +'</p></div>'

    # Template to use for any new pages
    template = form.get('template', [''])[0]
    if template:
        frm += '<input type="hidden" name="template" value="%s">' % template
    # Where to after saving page
    backto = form.get('backto', [''])[0]
    if backto:
        frm += '<input type="hidden" name="backto" value="%s">' % backto

    old_header = request.cfg.page_header2
    old_footer = request.cfg.page_footer1
    # The post-header and pre-footer texts seem to be implemented in themes.
    # Using post-header instead of page msg to avoid breaking header forms.
    request.cfg.page_header2 += frm + btn
    request.cfg.page_footer1 += btn + '</form>'

    old_page = request.page
    request.page = FormPage(request, pagename)

    error = ''
    newpage = False
    # If the page does not exist but we'd know how to construct it, 
    # replace the Page content with template and pretend it exists
    if template and not request.page.exists():
        template_page = wikiutil.unquoteWikiname(template)
        if request.user.may.read(template_page):
            editor = PageEditor(request, template_page)
            editor.user = request.user
            text = editor.get_raw_body()
            editor.page_name = pagename
            request.page.set_raw_body(editor._expand_variables(text))
            request.page.exists = lambda **kw: True
            request.page.lastEditInfo = lambda: {}
            newpage = True
        else:
            error = '<div class="saveform"><p class="savemessage">' + \
                    _("Cannot read template") + '</p></div>'

    elif not template and not request.page.exists():
        error = '<div class="saveform"><p class="savemessage">' + \
                _("No template specified, cannot edit") + '</p></div>'


    if error:
        request.cfg.page_header2 = request.cfg.page_header2 + error
        request.cfg.page_footer1 = request.cfg.page_footer1

    # Extra spaces from formatter need to be removed, that's why the
    # page is not sent as it is
    out = StringIO.StringIO()
    request.redirect(out)
    request.sent_headers = True
    request.page.send_page()
    request.redirect()

    graphdata = request.graphdata
    vals_on_keys = graphdata.get_vals_on_keys()

    # If we're making a new page based on a template, make sure that
    # the values from the evaluated template are included in the form editor
    if newpage:
        data = parse_text(request, request.page, request.page.get_raw_body())
        for page in data:
            pagemeta = graphdata.get_meta(page)
            for key in pagemeta:
                for val in pagemeta[key]:
                    vals_on_keys.setdefault(key, set()).add(val)

    # Form types
    def form_selection(request, pagekey, curval, values, description=''):
        msg = wr('<select name="%s">', pagekey)
        msg += wr('<option value=""> </option>')
        
        for keyval, showval in values:
            msg += wr('<option value="%s"%s>%s</option>',
                      keyval, curval == keyval and ' selected' or '',
                      showval)

        msg += '</select>'

        return msg

    def form_checkbox(request, pagekey, curval, values, description=''):
        msg = ''

        for keyval, showval in values:
            msg += wr(
                '<input type="checkbox" name="%s" value="%s"%s>',
                pagekey, keyval, curval == keyval and ' checked' or '') + \
                format_wikitext(request, showval)

        return msg

    def form_radio(request, pagekey, curval, values, description=''):
        msg = ''

        for keyval, showval in values:
            msg += wr(
                '<input type="radio" name="%s" value="%s"%s>',
                pagekey, keyval, curval == keyval and ' checked' or '') + \
                format_wikitext(request, showval)

        return msg

    def form_textbox(request, pagekey, curval, values, description=''):
        return wr('<input type="text" name="%s" value="%s">',
                  pagekey, curval)

    def form_textarea(request, pagekey, curval, values, description=''):
        return wr('<textarea rows=20 cols=70 name="%s">%s</textarea>',
                  pagekey, curval)

    def form_file(request, pagekey, curval, values, description=''):
        if curval:
            return wr(
                '<input class="file" type="text" name="%s" value="%s" readonly>'
                , pagekey, curval)
        else:
            return wr(
                '<input class="file" type="file" name="%s" value="" readonly>',
                  pagekey)

    formtypes = {'selection': form_selection,
                 'checkbox': form_checkbox,
                 'textbox': form_textbox,
                 'textarea': form_textarea,
                 'radio': form_radio,
                 'file': form_file} 

    def repl_subfun(mo):
        dt, pagekey, val = mo.groups()

        pagekey = form_unescape(pagekey)
        msg = dt
        key = pagekey.split(SEPARATOR)[1]

        properties = get_properties(request, key)

        if properties.get('hidden'):
            return ""

        values = list()

        # Placeholder key key
        if key in vals_on_keys:
            for keyval in sorted(vals_on_keys[key]):
                keyval = keyval.strip()
                if len(keyval) > 30:
                    showval = keyval[:27] + '...'
                else:
                    showval = keyval

                values.append((keyval, showval))

        formtype = properties.get('hint')
        constraint = properties.get('constraint')
        desc = properties.get('description')
        hidden = False

        if formtype == "hidden":
            hidden = True

        if not formtype in formtypes:
            formtype = "selection"

        if (not formtype == "radio" and
            not (formtype == "checkbox" and constraint == "existing")):
            cssclass = "metaformedit-cloneable"
        else:
            cssclass = "metaformedit-notcloneable"
       
        if desc:
            msg = msg.replace('</dt>', ' %s</dt>' % \
                                  request.formatter.icon('info'))
            msg = msg.replace('<dt>', wr(
                    '<dt class="mt-tooltip" title="%s" rel="%s">', key, desc))

        msg = msg.replace('<dd>', '<dd class="%s">'% cssclass)

        msg += formtypes[formtype](request, pagekey, val, values)


        if (not constraint == 'existing' and 
            not formtype in ['textbox', 'textarea', 'file']):
            msg += wr('<input class="metavalue" type="text" ' + \
                          'name="%s" value="">', pagekey)

        if hidden:
            msg = request.formatter.div(1, css_class='comment') + msg + \
                request.formatter.div(0)
        return msg

    data = out.getvalue()
    data = value_re.sub(repl_subfun, data)
    request.write(data)
    request.page = old_page
    request.cfg.page_header2 = old_header
    request.cfg.page_footer1 = old_footer
