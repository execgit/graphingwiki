from graphingwiki.editing import getmetas
from graphingwiki.editing import edit_meta
from graphingwiki.editing import getkeys
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input
from graphingwiki.patterns import GraphData
from graphingwiki.patterns import getgraphdata
from graphingwiki.patterns import encode

from raippa import RaippaUser
from raippa import FlowPage
from raippa import Question
from raippa import addlink, removelink

taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
statuscategory = u'CategoryStatus'

def redirect(request, pagename, tip=None):
    if tip == "generic":
        url = u'%s/%s?action=tip' % (request.getBaseURL(), pagename)
    elif tip:
        url = u'%s/%s?action=tip&%s' % (request.getBaseURL(), pagename, tip)
    else:
        url = u'%s/%s' % (request.getBaseURL(), pagename)
    request.http_redirect(url)

def execute(pagename, request):
    if not hasattr(request, 'graphdata'):
        getgraphdata(request)
    request.raippauser = RaippaUser(request)

    if request.form.has_key("selectcourse"):
        coursename = request.form.get("course", [u''])[0]
        if coursename:
            currentpage = FlowPage(request, pagename, request.raippauser)
            metakeys = getkeys(request.graphdata, request.raippauser.statuspage)
            if metakeys.has_key("current"):
                edit_meta(request, request.raippauser.statuspage, {"current": [addlink(request.raippauser.currentcourse)]}, {"current": [addlink(coursename)]})
            else:
                edit_meta(request, request.raippauser.statuspage, {"": [""]}, {"current": [addlink(coursename)]})
            redirect(request, coursename)
        else:
            request.write(u'Missing course name.')
    elif request.form.has_key(u'start'):
        userselection = request.form.get("userselection", [None])[0]
        currentpage = FlowPage(request, pagename, request.raippauser)
        fp, task = currentpage.setnextpage(userselection)
        if fp == "end" and task == "end":
            redirect(request, pagename)
        else:
            #statusdata = {request.raippauser.currentcourse: [addlink(fp)]}
            #input = order_meta_input(request, request.raippauser.statuspage, statusdata, "repl")
            #process_edit(request, input, True, {request.raippauser.statuspage:[statuscategory]})
            redirect(request, task)
    elif request.form.has_key(u'next'):
        currentpage = FlowPage(request, pagename, request.raippauser)
        if request.raippauser.hasDone(pagename):
            nextflowpoint, nexttask = currentpage.setnextpage()
            if nextflowpoint == "end" and nexttask == "end":
                redirect(request, request.raippauser.currentcourse)
            else:
                redirect(request, nexttask)
    elif request.form.has_key(u'send'):
        currentpage = FlowPage(request, pagename, request.raippauser)
        if taskcategory in currentpage.categories and (currentpage.type == u'exam' or currentpage.type == u'questionary'):
            useranswers = dict()
            taskflow = currentpage.getflow()
            for key in request.form:
                if key.startswith('answer'):
                    useranswers[int(key[6:])] = request.form[key]
            if len(useranswers) != len(taskflow) and currentpage.type == u'questionary':
                redirect(request, currentpage.pagename, "noanswer")
            else:
                #let's mark user to the first taskpoint
                taskpage = FlowPage(request, taskflow[0][0], request.raippauser)
                nextflowpoint, nexttask = taskpage.setnextpage()
                for index, page_tuple in enumerate(taskflow):
                    if useranswers.get(index, None):
                        questionpage = Question(request, page_tuple[1])
                        if questionpage.answertype == "file":
                            questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, page_tuple[0], "pending", {}, file=True)
                        else:
                            overallvalue, successdict, tips = questionpage.checkanswers(useranswers[index])
                            questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, page_tuple[0], overallvalue, successdict)
                    if len(taskflow) > 1 and nextflowpoint != "end" and nexttask != "end" and nextflowpoint == request.raippauser.currentcoursepoint:
                        taskpage = FlowPage(request, page_tuple[0], request.raippauser)
                        nextflowpoint, nexttask = taskpage.setnextpage()
                if nextflowpoint == "end" and nexttask == "end":
                    redirect(request, request.raippauser.currentcourse)
                else:
                    redirect(request, nexttask)
        elif taskpointcategory in currentpage.categories:
            if request.form.has_key(u'answer') or request.form.has_key(u'file'):
                useranswers = request.form[u'answer']
                questionpage = currentpage.getquestionpage()
                if questionpage:
                    questionpage = Question(request, questionpage)
                    if questionpage.answertype == "file":
                        questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, request.raippauser.currenttask, "pending", {}, file=True)
                        redirect(request, currentpage.pagename)
                    else:
                        overallvalue, successdict, tips = questionpage.checkanswers(useranswers)
                        questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, request.raippauser.currenttask, overallvalue, successdict)
                        if overallvalue:
                            nextflowpoint, nexttask = currentpage.setnextpage()
                            if nextflowpoint == "end" and nexttask == "end":
                                redirect(request, request.raippauser.currentcourse)
                            else:
                                redirect(request, nexttask)
                        else:
                            try:
                                metas = getmetas(request, request.graphdata, currentpage.pagename, ["recap"], checkAccess=False)
                                failurepage = metas["recap"][0][0]
                                failurekey = request.raippauser.currentcoursepoint + "/recap"
                                statusdata = {request.raippauser.currentcourse:[addlink(failurekey)],
                                              failurekey:[addlink(failurepage)]}
                                input = order_meta_input(request, request.raippauser.statuspage, statusdata, "repl")
                                process_edit(request, input, True, {request.raippauser.statuspage:[statuscategory]})
                                redirect(request, failurepage, "recap")
                            except:
                                if len(tips) > 0:
                                    redirect(request, currentpage.pagename, tips[0])
                                else:
                                    redirect(request, currentpage.pagename, "generic")
                else:
                    request.write(u'Cannot find questionpage.')
            else:
                redirect(request, currentpage.pagename, "noanswer")
        else:
            request.write(u'Invalid input. 1')
    else:
        request.write(u'Invalid input. 2')
