# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - create account action

    @copyright: 2007 MoinMoin:JohannesBerg
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin import user, wikiutil, util
from MoinMoin.Page import Page
from MoinMoin.widget import html
from MoinMoin.security.textcha import TextCha
from MoinMoin.auth import MoinAuth

from graphingwiki.editing import set_metas

from raippa import raippacategories as rc

_debug = False

def _create_user(request):
    _ = request.getText
    form = request.form

    if request.request_method != 'POST':
        return

    if not TextCha(request).check_answer_from_form():
        return _('TextCha: Wrong answer! Go back and try again...')

    userdata = {'gwikicategory': [rc['student']]}

    # Create user profile
    theuser = user.User(request, auth_method="new-user")

    # Require non-empty name
    try:
        name = int(form['name'][0])
        theuser.name = form['name'][0]
        userdata['number'] = [theuser.name]
    except KeyError:
        return _("Empty student number. Please enter your student number.")
    except ValueError:
        return _("Invalid student number. Student number may contain only numeric characters.")

    # Don't allow creating users with invalid names
    if not user.isValidName(request, theuser.name):
        return _("""Invalid student number {{{'%s'}}}.
Student number may contain only numeric characters.
""", wiki=True) % wikiutil.escape(theuser.name)

    # Name required to be unique. Check if name belong to another user.
    if user.getUserId(request, theuser.name):
        return _("Account for this student number already exists.")

    # Require non-empty name
    try:
        theuser.aliasname = form['aliasname'][0]
        userdata['name'] = [theuser.aliasname]
    except KeyError:
        return _("Empty name. Please enter your name.")

    # try to get the password and pw repeat
    password = form.get('password1', [''])[0]
    password2 = form.get('password2', [''])[0]

    # Check if password is given and matches with password repeat
    if password != password2:
        return _("Passwords don't match!")
    if not password:
        return _("Please specify a password!")

    pw_checker = request.cfg.password_checker
    if pw_checker:
        pw_error = pw_checker(request, theuser.name, password)
        if pw_error:
            return _("Password not acceptable: %s") % pw_error

    # Encode password
    if password and not password.startswith('{SHA}'):
        try:
            theuser.enc_password = user.encodePassword(password)
        except UnicodeError, err:
            # Should never happen
            return "Can't encode password: %s" % str(err)

    # try to get the email, for new users it is required
    email = wikiutil.clean_input(form.get('email', [''])[0])
    theuser.email = email.strip()
    userdata['email'] = [theuser.email]

    if not theuser.email and 'email' not in request.cfg.user_form_remove:
        return _("Please provide your email address. If you lose your"
                 " login information, you can get it by email.")

    # Email should be unique - see also MoinMoin/script/accounts/moin_usercheck.py
    if theuser.email and request.cfg.user_email_unique:
        if user.get_by_email_address(request, theuser.email):
            return _("This email already belongs to somebody else.")

    # save data
    theuser.save()

    usermetas = {theuser.name: userdata}

    success, msg = set_metas(request, dict(), dict(), usermetas)
    result = _("Account created! Use your student number to login.")

    if not success:
        result += _("Failed to create student page.")

    if _debug:
        result = result + util.dumpFormData(form)
    return result


def _create_form(request):
    _ = request.getText
    url = request.page.url(request)
    ret = html.FORM(action=url)
    ret.append(html.INPUT(type='hidden', name='action', value='newaccount'))
    lang_attr = request.theme.ui_lang_attr()
    ret.append(html.Raw('<div class="userpref"%s>' % lang_attr))
    tbl = html.TABLE(border="0")
    ret.append(tbl)
    ret.append(html.Raw('</div>'))

    row = html.TR()
    tbl.append(row)
    row.append(html.TD().append(html.STRONG().append(
                                  html.Text(_("Student number")))))
    cell = html.TD()
    row.append(cell)
    cell.append(html.INPUT(type="text", size="36", name="name"))
#    cell.append(html.Text(' ' + _("(Use student number)")))

    row = html.TR()
    tbl.append(row)
    row.append(html.TD().append(html.STRONG().append(
                                  html.Text(_("Password")))))
    row.append(html.TD().append(html.INPUT(type="password", size="36",
                                           name="password1")))

    row = html.TR()
    tbl.append(row)
    row.append(html.TD().append(html.STRONG().append(
                                  html.Text(_("Password repeat")))))
    row.append(html.TD().append(html.INPUT(type="password", size="36",
                                           name="password2")))

    row = html.TR()
    tbl.append(row)
    row.append(html.TD().append(html.STRONG().append(html.Text(_("Name")))))
    row.append(html.TD().append(html.INPUT(type="text", size="36",
                                           name="aliasname")))

    row = html.TR()
    tbl.append(row)
    row.append(html.TD().append(html.STRONG().append(html.Text(_("Email")))))
    row.append(html.TD().append(html.INPUT(type="text", size="36",
                                           name="email")))

    textcha = TextCha(request)
    if textcha.is_enabled():
        row = html.TR()
        tbl.append(row)
        row.append(html.TD().append(html.STRONG().append(
                                      html.Text(_('TextCha (required)')))))
        td = html.TD()
        if textcha:
            td.append(textcha.render())
        row.append(td)

    row = html.TR()
    tbl.append(row)
    row.append(html.TD())
    td = html.TD()
    row.append(td)
    td.append(html.INPUT(type="submit", name="create",
                         value=_('Create Account')))

    return unicode(ret)

def execute(pagename, request):
    found = False
    for auth in request.cfg.auth:
        if isinstance(auth, MoinAuth):
            found = True
            break

    if not found:
        # we will not have linked, so forbid access
        request.makeForbidden403()
        return

    page = Page(request, pagename)
    _ = request.getText
    form = request.form

    submitted = form.has_key('create')

    if submitted: # user pressed create button
        request.theme.add_msg(_create_user(request), "dialog")
        return page.send_page()
    else: # show create form
        request.emit_http_headers()
        request.theme.send_title(_("Create Account"), pagename=pagename)

        request.write(request.formatter.startContent("content"))

        # THIS IS A BIG HACK. IT NEEDS TO BE CLEANED UP
        request.write(_create_form(request))

        request.write(request.formatter.endContent())

        request.theme.send_footer(pagename)
        request.theme.send_closing_html()
