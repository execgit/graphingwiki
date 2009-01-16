import time
import datetime 

from MoinMoin.Page import Page
from MoinMoin import wikiutil

from graphingwiki.editing import get_metas

from raippa import RaippaUser
from raippa import Question
from raippa import raippacategories, removelink, getcourseusers, getflow

def _enter_page(request, pagename):
    request.http_headers()
    request.theme.send_title(pagename)
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter
    request.write(request.page.formatter.startContent("content"))

def _exit_page(request, pagename):
    request.write(request.page.formatter.endContent())
    request.theme.send_footer(pagename)

def draw_taskstats(request, task, course=None, user=None):
    currentuser = RaippaUser(request, request.user.name)
    isteacher = currentuser.isTeacher()

    metas = get_metas(request, task, ["title", "description"], display=True, checkAccess=False)
    if metas["title"]:
        title = metas["title"].pop()
    else:
        title = unicode()
        reporterror(request, "%s doesn't have title meta." % task)

    html = unicode()
    if isteacher:
        html += u'''
Page: <a href="%s/%s">%s</a> <a href="%s/%s?action=EditTask">[edit]</a>
''' % (request.getBaseURL(), task, task, request.getBaseURL(), task)

    html += u'<h1>%s</h1>' % title

    if not user: 
        courseusers = getcourseusers(request, course)
    else:
        courseusers = list()

    taskflow = getflow(request, task)
    for taskpoint, questionpage in taskflow:
        question = Question(request, questionpage)
        html += "\n%s " % question.question

        if isteacher:
            html += u'<a href="%s/%s?action=EditQuestion">[edit]</a>' % (request.getBaseURL(), questionpage)

        if user:
            history = question.gethistory(user.user, course)
            if history:
                if history[0] not in ["False", "pending", "picked", "recap"]:
                    html += u'''
<ul><li>Passed with %d tries, in time %s</li></ul>
''' % (Page(request, history[3]).get_real_rev(), history[4])
            else:
                html += u'<ul><li>No answers for this question</li></ul>'

        else:
            histories = question.gethistories(coursefilter=course, taskfilter=taskpoint)
            users = list()
            has_passed = int()
            average_tries = float()
            average_time = float()
           
            for history in histories:
                h_users = history[0]
                for h_user in h_users:
                    if h_user not in users:
                        users.append(h_user)
               
                if history[1] not in ["False", "pending", "picked", "recap"]:
                    has_passed += 1

                average_tries += Page(request, history[5]).get_real_rev()
                if history[6]:
                    t = time.strptime(history[6], "%H:%M:%S")
                    average_time += datetime.timedelta(hours=t[3], minutes=t[4], seconds=t[5]).seconds

            if len(users) > 0:
                average_tries = average_tries/len(histories)
                average_time = int("%.f" % (average_time/average_tries))
                iso_time = time.strftime("%H:%M:%S", time.gmtime(average_time)) 
                html += u'<ul>\n'
                if len(users) == has_passed:
                    html += u'''
<li>%d of %d students have tried and passed.</li>\n''' % (has_passed, len(courseusers))
                else:
                    html += u'''
<li>%d of %d students have tried, %d of them have passed.</li>\n''' % (len(users), len(courseusers), has_passed)

                html += u'''
<li>Average of %.2f tries and %s time used per try.</li>
</ul>
''' % (average_tries, iso_time)
            else:
                html += u'<ul><li>No answers for this question</li></ul>'

    return html

def execute(pagename, request):
#    for key, values in request.form.iteritems():
#        request.write("%s: %s<br>\n" % (key, ", ".join(values)))

    coursepage = request.form.get("course", [None])[0]
    username = request.form.get("user", [None])[0]
    taskpage = request.form.get("task", [None])[0]
    html = unicode()

    currentuser = RaippaUser(request, request.user.name)
    if username != currentuser.user and not currentuser.isTeacher():
        return u'You are not allowed to view users (%s) statistics.' % username
        
    getcourses = wikiutil.importPlugin(request.cfg, "macro", 'RaippaStats', 'getcourses')

    if username:
        user = RaippaUser(request, username)
        courses = getcourses(request, user)
    else:
        courses = getcourses(request)

    if coursepage and coursepage not in courses.keys():
        return u'%s not in courselist.' % coursepage
    elif coursepage:
        if not Page(request, coursepage).exists():
            message = u'%s does not exist.' % coursepage
            Page(request, pagename).send_page(msg=message)
            return None

        metas = get_metas(request, coursepage, ["gwikicategory"], display=True, checkAccess=False)
        if raippacategories["coursecategory"] not in metas["gwikicategory"]:
            message = u'%s is not coursepage.' % coursepage
            Page(request, pagename).send_page(msg=message)
            return None

    if request.form.has_key("compress"):
        compress = True
    else:
        compress = False

    draw_stats = wikiutil.importPlugin(request.cfg, "macro", 'RaippaStats', 'draw_coursestats')
    draw_courselist = wikiutil.importPlugin(request.cfg, "macro", 'RaippaStats', 'draw_courselist')

    if username:
        if taskpage:
            if coursepage:
                html += draw_courselist(request, courses, user, coursepage, show_compress=False)
                html += draw_taskstats(request, taskpage, coursepage, user)
            else:
                html += draw_taskstats(request, taskpage, user=user)
        else:
            if coursepage:
                html += draw_courselist(request, courses, user, coursepage, compress)
                html += draw_stats(request, coursepage, user, compress)
            else:
                html += draw_courselist(request, courses, user, compress)
    else:
        if taskpage:
            if coursepage:
                html += draw_courselist(request, courses,selected=coursepage, show_compress=False)
                html += draw_taskstats(request, taskpage, coursepage)
            else:
                html += draw_taskstats(request, taskpage)
        else:
            if coursepage:
                html += draw_courselist(request, courses, selected=coursepage, compress=compress)
                html += draw_stats(request, coursepage, compress=compress)
            else:
                html += draw_courselist(request, courses, compress=compress)

    _enter_page(request, pagename)
    request.write(html)
    _exit_page(request, pagename)
