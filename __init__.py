import random
from tempfile import mkstemp
import time
import os

from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.user import User
from MoinMoin.action.AttachFile import getAttachDir

from graphingwiki.editing import getmetas
from graphingwiki.editing import edit_meta
from graphingwiki.editing import getkeys
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input
from graphingwiki.patterns import GraphData
from graphingwiki.patterns import getgraphdata
from graphingwiki.patterns import encode

statuscategory = u'CategoryStatus'
coursecategory = u'CategoryCourse'
coursepointcategory = u'CategoryCoursepoint'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
historycategory = u'CategoryHistory'
answercategory = u'CategoryAnswer'
tipcategory = u'CategoryTip'
timetrackcategory = u'CategoryTimetrack'
usercategory = u'CategoryUser'

class RaippaUser:
    def __init__(self, request, name=None):
        getgraphdata(request)
        self.request = request

        if name:
            self.id = encode(name)
            self.name = unicode() 
        else:
            self.id = encode(self.request.user.name)
            self.name = self.request.user.aliasname

        self.categories = list()
        if self.id in request.graphdata:
            meta = getmetas(request, self.request.graphdata, encode(self.id), ["WikiCategory", "name"], checkAccess=False)
            for name, type in meta["name"]:
                self.name = name
                break
            for category, type in meta["WikiCategory"]:
                self.categories.append(category)
        if not self.categories:
            self.categories.append(usercategory)
 
        self.statuspage = encode("%s/status" % self.id)
        if self.statuspage in request.graphdata:
            self.statusdict = self.request.graphdata.getpage(self.statuspage).get('lit', {})
        else:
            self.statusdict = dict()

        self.currentcourse = removelink(self.statusdict.get("current", [""])[0])
        self.currentcoursepoint = removelink(self.statusdict.get(self.currentcourse, [""])[0])
        self.currenttask = removelink(self.statusdict.get(self.currentcoursepoint, [""])[0])

    def getcourselist(self):
        courselist = list()
        metakeys = getkeys(self.request.graphdata, self.statuspage)
        for key in metakeys:
            categorymetas = getmetas(self.request, self.request.graphdata, key, ["WikiCategory"])
            for category, type in categorymetas["WikiCategory"]:
                if category == coursecategory:
                    courselist.append(key)
                    break
        return courselist

    def gettimetrack(self, course):
        page = self.request.graphdata.getpage(self.id)
        linking_in = page.get('in', {}) 
        pagelist = linking_in.get("user", [])
        timetracklist = dict()
        for page in pagelist:
            metas = getmetas(self.request, self.request.graphdata, page, ["course", "WikiCategory", "hours", "description", "date"], checkAccess=False)
            if metas["course"]:
                if course == metas["course"][0][0]:
                    for category, type in metas["WikiCategory"]:
                        if category == timetrackcategory:
                            if metas["date"] and metas["hours"]:
                                date = metas["date"][0][0]
                                hours = metas["hours"][0][0]
                                if metas["description"]:
                                    description = metas["description"][0][0]
                                else:
                                    description = unicode()
                    
                                timetracklist[description] = [date, hours]
                            break
        return timetracklist

    def canDo(self, pagename, course):
        page = FlowPage(self.request, pagename)
        may = False
        if "[[end]]" in self.statusdict.get(page.pagename, []):
            return False
        elif coursepointcategory in page.categories:
            metas = getmetas(self.request, self.request.graphdata, encode(pagename), ["deadline"], checkAccess=False)
            if metas["deadline"]:
                deadline = time.strptime(metas["deadline"][0][0], "%Y-%m-%d")
                currentdate = time.gmtime()
                if (deadline[0] < currentdate[0]) or \
                   (deadline[0] <= currentdate[0] and deadline[1] < currentdate[1]) or \
                   (deadline[0] <= currentdate[0] and deadline[1] <= currentdate[1] and deadline[2] < currentdate[2]):
                    return False
            prerequisites = page.getprerequisite()
            for prequisite in prerequisites:
                 if not self.hasDone(prequisite, course):
                     return False
            course = FlowPage(self.request, course)
            flow = course.getflow()
            prelist = list()
            for point, nextlist in flow.iteritems():
                if page.pagename in nextlist:
                    prelist.append(point)
                    if point == "start":
                        may = True
                        continue
                    statuslist = self.statusdict.get(point, [])
                    if "[[end]]" in statuslist:
                        may = True
        return may

    def hasDone(self, pagename, course=None):
        page = FlowPage(self.request, pagename)
        if coursepointcategory in page.categories:
            flow = page.getflow()
            taskpoint = encode(flow.pop()[0])
        elif taskpointcategory in page.categories:
            taskpoint = encode(pagename)
        taskpoint = self.request.graphdata.getpage(taskpoint)
        linking_in = taskpoint.get('in', {})
        pagelist = linking_in.get("task", [])
        for page in pagelist:
            metas = getmetas(self.request, self.request.graphdata, encode(page), ["WikiCategory", "user", "overallvalue"], checkAccess=False)
            if metas["user"] and metas["overallvalue"]:
                for category, type in metas["WikiCategory"]:
                    if category == historycategory and metas["user"][0][0] == self.id:
                        return True
        return False

    def updatestatus(self, newstatusdict=None):
        if newstatusdict:
            for key in newstatusdict:
                self.statusdict[key] = newstatusdict[key]
        else:
            statuspage = self.request.graphdata.getpage(self.statuspage)
            self.statusdict = statuspage.get('lit', {})

        self.currentcourse = removelink(self.statusdict.get("current", [""])[0])
        self.currentcoursepoint = removelink(self.statusdict.get(self.currentcourse, [""])[0])
        self.currenttask = removelink(self.statusdict.get(self.currentcoursepoint, [""])[0])

    def editstatus(self, flowpoint, task, debug=None):
        #print debug, flowpoint, task
        flowpoint = encode(flowpoint)
        task = encode(task)

        metakeys = getkeys(self.request.graphdata, self.statuspage)

        oldmetas = dict()
        newmetas = dict()

        newmetas[self.currentcourse] = [addlink(flowpoint)]
        if metakeys.has_key(self.currentcourse):
            oldmetas[self.currentcourse] = [addlink(self.currentcoursepoint)]
        else:
            oldmetas[u''] = [u'']


        if flowpoint != u'end' and task != u'end':
            newmetas[flowpoint] = [addlink(task)]
            if metakeys.has_key(flowpoint):
                meta = getmetas(self.request, self.request.graphdata, self.statuspage, [flowpoint], checkAccess=False)
                oldtask = encode(meta[flowpoint][0][0])
                oldmetas[flowpoint] = [addlink(oldtask)]
            else:
                oldmetas[u''] = [u'']
        else:
            newmetas[self.currentcoursepoint] = [addlink(task)]
            if metakeys.has_key(self.currentcoursepoint):
                meta = getmetas(self.request, self.request.graphdata, self.statuspage, [self.currentcoursepoint], checkAccess=False)
                oldtask = encode(meta[self.currentcoursepoint][0][0])
                oldmetas[self.currentcoursepoint] = [addlink(oldtask)]
            else:
                oldmetas[u''] = [u'']
        msg = edit_meta(self.request, self.statuspage, oldmetas, newmetas, True, [statuscategory])
        self.updatestatus(newmetas)


class FlowPage:
    def __init__(self, request, pagename, user=None):
        if not hasattr(request, 'graphdata'):
            getgraphdata(request)
        self.request = request

        self.pagename = encode(pagename)
        if user:
            self.user = user
        
        metas = getmetas(request, self.request.graphdata, self.pagename, ["WikiCategory", "type", "next", "start"], checkAccess=False)
        self.categories = list()
        for category, type in metas[u'WikiCategory']:
            self.categories.append(category)
            
        self.startlist = list()
        for start, type in metas["start"]:
            self.startlist.append(start)
            
        self.nextlist = list()
        for next, type in metas["next"]:
            self.nextlist.append(next)

        if metas[u'type']:
            self.type = metas[u'type'][0][0]
        else:
            self.type = None

    def setnextpage(self, userselection=None):
        if coursecategory in self.categories:
            if userselection in self.startlist:
                courseflowpoint = FlowPage(self.request, userselection, self.user)
                nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                return nextcoursepoint, nexttask
            elif userselection and self.user.canDo(userselection, self.pagename):
                courseflowpoint = FlowPage(self.request, userselection, self.user)
                nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                return nextcoursepoint, nexttask
            elif self.user.currenttask and self.user.currenttask != "end":
                return self.user.currentcoursepoint, self.user.currenttask
            elif self.user.currentcoursepoint and self.user.currentcoursepoint != "end":
                courseflowpoint = FlowPage(self.request, self.user.currentcoursepoint, self.user)
                nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                return nextcoursepoint, nexttask
            else:
                courseflowpoint = FlowPage(self.request, self.startlist[0], self.user)
                nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                return nextcoursepoint, nexttask
        elif coursepointcategory in self.categories:
            recapkey = self.pagename+"/recap"
            if self.user.statusdict.has_key(recapkey):
                recaptask = removelink(self.user.statusdict[recapkey][0])
                return recapkey, recaptask
            else:
                temp = removelink(self.user.statusdict.get(self.pagename, [""])[0])
                if temp:
                    if temp == "end":
                        if not "end" in self.nextlist:
                            metas = getmetas(self.request, self.request.graphdata, self.pagename, ["split"], checkAccess=False)
                            #let's go to coursepage if coursepoint has many selectable next pages
                            if len(self.nextlist) > 1:
                                for split, type in metas["split"]:
                                    if split == u'select':
                                        return "end", "end"

                            #else, let se system decide where to go
                            next = random.choice(self.nextlist)
                            for key in self.user.statusdict:
                                if key in self.nextlist:
                                    next = key
                                    break
                            courseflowpoint = FlowPage(self.request, next, self.user)
                            nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                            return nextcoursepoint, nexttask
                        else:
                            return "end", "end"
                    else:
                        self.user.editstatus(self.pagename, temp, 2)
                        return self.pagename, temp
                else:
                    metas = getmetas(self.request, self.request.graphdata, self.pagename, ["task"], checkAccess=False)
                    self.user.editstatus(self.pagename, metas["task"][0][0], 3)
                    return self.pagename, metas["task"][0][0]
        elif taskcategory in self.categories:
            metas = getmetas(self.request, self.request.graphdata, self.pagename, ["start"], checkAccess=False)
            if metas["start"]:
                start = random.choice(metas["start"])[0]
                self.user.editstatus(self.user.currentcoursepoint, start, 4)
                return self.user.currentcoursepoint, start
            else:
                return False, False
        elif taskpointcategory in self.categories:
            metas = getmetas(self.request, self.request.graphdata, self.pagename, ["next"], checkAccess=False)
            if metas["next"]:
                nextpage = random.choice(metas["next"])[0]
                if nextpage != "end":
                    self.user.editstatus(self.user.currentcoursepoint, nextpage, 5)
                    return self.user.currentcoursepoint, nextpage
                else:
                    if self.user.currentcoursepoint.endswith("/recap"):
                        returncp = "/".join(self.user.currentcoursepoint.split("/")[:-1])
                        returntask = removelink(self.user.statusdict[returncp][0])
                        statusdata = {self.user.currentcoursepoint: [" "],
                                      self.user.currentcourse: [addlink(returncp)]}
                        input = order_meta_input(self.request, self.user.statuspage, statusdata, "repl")
                        process_edit(self.request, input, True, {self.user.statuspage:[statuscategory]})
                        return returncp, returntask
                    else:
                        self.user.editstatus(self.user.currentcoursepoint, "end", 6)
                        courseflowpoint  = FlowPage(self.request, self.user.currentcoursepoint, self.user)
                        nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                        return nextcoursepoint, nexttask
                return False, False
        else:
            self.request.write(u'%s has no category.' % self.pagename)
            return False, False

    def getprerequisite(self):
        if not coursepointcategory in self.categories:
            return []
        else:
            meta = getmetas(self.request, self.request.graphdata, self.pagename, ["prerequisite"], checkAccess=False)
            prerequisites = list()
            for prerequisite, type in meta["prerequisite"]:
                prerequisites.append(prerequisite)
            return prerequisites

    def getquestionpage(self):
        meta = getmetas(self.request, self.request.graphdata, self.pagename, [u'question'], checkAccess=False)
        if meta[u'question']:
            return encode(meta[u'question'][0][0])
        else:
            return None

    def getflow(self):
        if coursecategory in self.categories:
            flow = dict()
            def subflow(page):
                meta = getmetas(self.request, self.request.graphdata, page, ["next"], checkAccess=False)
                for next, type in meta["next"]:
                    next = encode(next)
                    if page not in flow.keys():
                        flow[page] = list()
                    if next not in flow[page]:
                        flow[page].append(next)
                    if next != "end":
                        subflow(next)
                    
            meta = getmetas(self.request, self.request.graphdata, self.pagename, ["start"], checkAccess=False)
            for start, type in meta["start"]:
                start = encode(start)
                if "start" not in flow.keys():
                    flow["start"] = []
                if start not in flow["start"]:
                    flow["start"].append(start)
                subflow(start)
        elif taskcategory in self.categories:
            #if self.type == "exam" or self.type == "questionary":
            meta = getmetas(self.request, self.request.graphdata, self.pagename, ["start"], checkAccess=False)
            taskpoint = encode(meta["start"][0][0])
            flow = list()
            while taskpoint != "end":
                meta = getmetas(self.request, self.request.graphdata, taskpoint, ["question", "next"], checkAccess=False)
                taskpage = encode(meta["question"][0][0])
                flow.append((taskpoint, taskpage))
                if meta["next"]:
                    taskpoint = encode(meta["next"][0][0])
                else:
                    taskpoint = "end"
        else:
            return False
        return flow

class Question:         
    def __init__(self, request, pagename):
        self.pagename = encode(pagename)
        if not hasattr(request, 'graphdata'):
            getgraphdata(request)
        self.request = request

        metas = getmetas(request, self.request.graphdata, self.pagename, ["question", "answertype", "note", "type"], checkAccess=False)                  
        self.question = unicode()
        self.answertype = unicode()
        self.note = unicode()
        self.types = list()

        if metas["question"]:
            self.question = metas["question"][0][0]

        if metas["answertype"]:
            self.answertype = metas["answertype"][0][0]

        notepage = encode(self.pagename+"/note")
        if notepage in request.graphdata:
            self.note = Page(self.request, notepage).get_raw_body()
        elif metas["note"]:
            self.note = metas["note"][0][0]

        for type, metatype in metas["type"]:
            self.types.append(type)

    def gethistories(self):
        histories = list()
        page = self.request.graphdata.getpage(self.pagename)
        linking_in = page.get('in', {})
        pagelist = linking_in.get("question", [])
        for page in pagelist:
            metas = getmetas(self.request, self.request.graphdata, page, ["WikiCategory", "user", "overallvalue", "false", "true", "course", "task"])
            for category, type in metas["WikiCategory"]:
                if category == historycategory:
                    if metas["user"] and metas["overallvalue"] and metas["course"]:
                        user = metas["user"][0][0]
                        overallvalue = metas["overallvalue"][0][0]
                        course = metas["course"][0][0]
                        if metas["task"]:
                            task = metas["task"][0][0]
                        else:
                            task = unicode()
                        useranswers = dict()
                        for true in metas["true"]:
                            useranswers[true[0]] = "true"
                        for false in metas["false"]:
                            useranswers[false[0]] = "false"
                        histories.append([user, overallvalue, useranswers, course, task, page])
                    break
        return histories

    def getanswers(self):
        questionpage = self.request.graphdata.getpage(self.pagename)
        linking_in_question = questionpage.get('in', {})
        pagelist = linking_in_question.get("question", [])
        answerdict = dict()
        for page in pagelist:
            metas = getmetas(self.request, self.request.graphdata, page, ["WikiCategory", "true", "false", "option"], checkAccess=False)
            for category, type in metas["WikiCategory"]:
                if category == answercategory:
                    tip = None
                    options = list()
                    if metas["true"]:
                        value = u'true'
                        for answer, type in metas["true"]:
                            if type == "link" and answer.startswith("mailto:"):
                                answer = answer[7:]
                            break
                    elif metas["false"]:
                        value = u'false'
                        for answer, type in metas["false"]:
                            if type == "link" and answer.startswith("mailto:"):
                                answer = answer[7:]
                            break
                        answerpage = self.request.graphdata.getpage(page)
                        try:
                            linking_in_answer = answerpage.get('in', {})
                            tiplist = linking_in_answer["answer"]
                            for tippage in tiplist:
                                meta = getmetas(self.request, self.request.graphdata, tippage, ["WikiCategory"], checkAccess=False)
                                for category, type in meta["WikiCategory"]:
                                    if category == tipcategory:
                                        tip = tippage.split("/")[1]
                                        break
                        except:
                            pass
                    if metas["option"]:
                        for option, type in metas["option"]:
                            options.append(option)
                    answerdict[answer] = [value, tip, options, page]
                    break
        return answerdict

    def checkanswers(self, useranswers):
        successdict = dict()
        tips = list()
        truelist = list()
        overallvalue = True
        answerdict = self.getanswers()

        for answer in answerdict:
            if answerdict[answer][0] == "true":
                truelist.append(answer)

        #TODO: regexp, casesensitivity
        for answer in useranswers:
            if answer in truelist:
                truelist.remove(answer)
                successdict[answer] = "true"
            else:
                successdict[answer] = "false"
                if answerdict.get(answer, [u'', u''])[1]:
                    tips.append(answerdict[answer][1])
                else:
                    tips.append("generic")

        #make sure that all the correct answers are selected
        if self.answertype == "checkbox" and len(truelist) > 0:
            overallvalue = False

        if "false" in successdict.values():
            overallvalue = False

        return overallvalue, successdict, tips

    def writehistory(self, user, course, task, overallvalue, successdict, file=False):
        historypage = None
        histories = self.gethistories()
        for historyuser, ovalue, answers, historycourse, historytask, page in histories:
            if historyuser == user and historycourse == course:
                historypage = page
                oldkeys = getkeys(self.request.graphdata, historypage).keys()
                metas = getmetas(self.request, self.request.graphdata, historypage, oldkeys) 
                oldmetas = dict()
                for metakey in oldkeys:
                    oldmetas[metakey] = list()
                    for meta, type in metas[metakey]:
                        oldmetas[metakey].append(meta)
                break
        if not historypage:
            historypage = randompage(self.request, "History")
            oldmetas = {}

        historydata = {u'user':[addlink(user)],
                       u'course':[addlink(course)],
                       u'task':[addlink(task)],
                       u'question':[addlink(self.pagename)],
                       u'overallvalue':[unicode(overallvalue)],
                       u'time':[time.strftime("%Y-%m-%d %H:%M:%S")]}

        if file:
            filename = unicode()
            if self.request.form.has_key('answer__filename__'):
                filename = self.request.form['answer__filename__']
            filecontent = self.request.form["answer"][0]
            if not isinstance(filecontent, str):
                temp = filecontent.read()
                filecontent = temp
            
            if filename.endswith(".py"):
                filecontent = "#FORMAT python\n"+filecontent
            else:
                filecontent = "#FORMAT plain\n"+filecontent

            filepage = PageEditor(self.request, historypage+"/file")
            try:
                filepage.saveText(filecontent, filepage.get_real_rev())
            except:
                pass

            historydata[u'file'] = [addlink(historypage+"/file")]

        for useranswer, value in successdict.iteritems():
            if not historydata.has_key(value):
                historydata[value] = list()
            historydata[value].append(useranswer)
        if not historydata.has_key("true"):
            historydata["true"] = [u'']
        if not historydata.has_key("false"):
            historydata["false"] = [u'']

        edit_meta(self.request, historypage, oldmetas, historydata, True, [historycategory])

    def getaverage(self, coursename, taskpoint):
        histories = self.gethistories()
        userlist = list()
        answercount = int()
        average = 0
        alltimeuserlist = list()
        alltimeanswercount = len(histories)
        alltimeaverage = 0

        for answer in histories:
            user = answer[0]
            if answer[3] == coursename and answer[4] == taskpoint:
                userlist.append(user)
                answercount += 1
            alltimeuserlist.append(user)

        usercount = len(set(userlist))
        if answercount > 0 and usercount > 0:
            average = answercount / usercount

        alltimeusercount = len(set(alltimeuserlist))
        if alltimeanswercount > 0 and alltimeusercount > 0:
            alltimeaverage = alltimeanswercount / alltimeusercount

        return average, alltimeaverage


def addlink(pagename):
    if not pagename.startswith("[[") and not pagename.endswith("]]"):
        pagename = '[['+pagename+']]'
    return pagename

def removelink(pagename):
    if pagename.startswith("[[") and pagename.endswith("]]"):
        pagename = pagename[2:-2]
    return encode(pagename)

def randompage(request, type):
    getgraphdata(request)

    while True:
        pagename = encode("%s/%i" % (type, random.randint(10000,99999)))
        if pagename not in request.graphdata:
            return pagename