import time
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from graphingwiki.editing import get_metas, get_keys, set_metas 
from raippa import page_exists, addlink, randompage
from raippa import raippacategories as rc
from raippa.flow import Flow

class DeadLinkException(Exception):
    pass

class TooManyKeysException(Exception):
    pass

class TooManyLinksException(Exception):
    pass

class TooManyValuesException(Exception):
    pass

class MissingMetaException(Exception):
    pass

class PageDoesNotExistException(Exception):
    pass

class SaveException(Exception):
    pass

class Answer:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename

    def question(self):
        pagedata = self.request.graphdata.getpage(self.pagename)
        pages = pagedata.get('in', dict()).get('answer', list())

        questions = list()

        for page in pages:
            keys = ["gwikicategory"]
            metas = get_metas(self.request, page, keys, display=True, checkAccess=False)
            #TODO: replace with CategoryQuestionOptions
            if page.endswith('/flow'):
                questions.append(page[:-5])

        if len(questions) == 1:
            return Question(self.request, questions[0])
        elif len(questions) > 1:
            raise TooManyValuesException(u'Too many pages linking in to %s.' % self.pagename)
        else:
            return None

    def answer(self):
        metas = get_metas(self.request, self.pagename, ['answer'], display=True, checkAccess=False)
        answers = metas.get('answer', list())

        answer = None

        if len(answers) == 1:
            answer = answers[0]
            #TODO: if page, get content
        elif len(answers) > 1:
            raise TooManyValuesException(u'Page %s has too many "answer" -metas.' % self.pagename)
        else:
            raise MissingMetaException(u'''Page %s doesn't have "answer" -meta.''' % self.pagename)

        return answer

    def value(self):
        metas = get_metas(self.request, self.pagename, ['value'], display=True, checkAccess=False)
        values = metas.get('value', list())

        value = None

        if len(values) == 1:
            value = values[0]
        elif len(values) > 1:
            raise TooManyValuesException(u'Page %s has too many "value" -metas.' % self.pagename)
        else:
            raise MissingMetaException(u'''Page %s doesn't have "value" -meta.''' % self.pagename)

        return value

    def tips(self):
        metas = get_metas(self.request, self.pagename, ['tip'], display=True, checkAccess=False)
        tips = metas.get('tip', list())

        return tips

    def comment(self):
        metas = get_metas(self.request, self.pagename, ['comment'], display=True, checkAccess=False)
        comments = metas.get('comment', list())
        if len(comments) == 1:
            return comments[0]
        elif len(comments) > 1:
            raise TooManyValuesException(u'Page %s has too many "comment" -metas.' % self.pagename)
        else:
            return None


class Question:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename
        self.optionspage = pagename+'/options'

    def title(self):
        raw_content = Page(self.request, self.pagename).get_raw_body()
        title = unicode()

        for line in raw_content.split("\n"):
            if line.startswith("== ") and line.endswith(" =="):
                title = line[3:-3]

        return title

    def answers(self):
        answers = list()

        if not page_exists(self.request, self.optionspage):
            return answers

        metas = get_metas(self.request, self.optionspage, ['answer'], display=True, checkAccess=False)
        answerpages = metas.get('answer', list())

        for answerpage in answerpages:
            if not page_exists(self.request, answerpage):
                raise DeadLinkException(u"Page %s linked in %s doesn't exist." % (answerpage, self.optionspage))

            answers.append(answerpage)
            
        return answers

    def check_answers(self, user_answers, user, save_history=False):
        success_dict = {"right":list(), "wrong":list()}
        save_dict = dict() 
        overallvalue = str()

        questiontype = self.options().get('answertype', None)
        if not questiontype:
            raise MissingMetaException(u"Question %s doesn't have answertype option." % self.pagename)

        if questiontype in ['checkbox', 'radio', 'text']:
            answerpages = self.answers()
            save_dict = {"right":list(), "wrong":list()}
            overallvalue = "success"

            for answerpage in answerpages:
                answer = Answer(self.request, answerpage)

                if answer.value() == "right":
                    if answer.answer() not in user_answers:
                        success_dict["wrong"].append(answerpage)
                        if questiontype != 'text':
                            overallvalue = "failure"
                    else:
                        user_answers.remove(answer.answer())
                        success_dict["right"].append(answerpage)
                        save_dict["right"].append(answer.answer())
                else:
                    if answer.answer() in user_answers:
                        success_dict["wrong"].append(answerpage)
                        save_dict["wrong"].append(answer.answer())
                        overallvalue = "failure"

            if len(answerpages) > 0 and len(user_answers) > 0:
                overallvalue = "failure"
                for user_answer in user_answers:
                    save_dict["wrong"].append(user_answer)

        elif questiontype == 'file':
            for filename, content in user_answers:
                overallvalue = "pending"
                save_dict[filename] = content
        else:
            raise ValueError, "Incorrect answertype." 

        if save_history:
            #TODO: check if save was successfull
            success, msg = user.save_answers(self, overallvalue, save_dict)
            if not success:
                raise SaveException, msg

        return overallvalue, success_dict 

    def save_question(self, answers_data, options):
        save_data = dict()
        save_data[self.optionspage] = dict()
        remove = dict()
        remove[self.pagename] = list()
        remove[self.optionspage] = list()
        pages_to_delete = list()
        old_answers = list()

        if len(answers_data) > 0:
            remove[self.optionspage].append("answer")
            old_answers = self.answers()
            new_answers = list()
            answerpages = list()

            for anspage in old_answers:
                remove[anspage] = ["value", "answer", "comment", "tip"]

            for ans in answers_data:
                try:
                    old_page = ans.get("old_page", [u""])[0]
                    anspage = old_answers.pop(old_answers.index(old_page))

                except:
                    anspage = self.pagename +"/" +randompage(self.request, "answer")

                save_data[anspage] ={
                        "answer" : ans.get("answer", [u""]),
                        "value" : ans.get("value", [u""]),
                        "tip" : ans.get("tip", [u""]),
                        "comment" : ans.get("comment", [u""]),
                        "gwikicategory" : [rc['answer']]
                    }
                new_answers.append(addlink(anspage))

            save_data[self.optionspage]["answer"] = new_answers

        if options:
            remove[self.optionspage].extend(["redo", "answertype"])
            save_data[self.optionspage]["redo"] =  options.get("redo", [u"True"])
            save_data[self.optionspage]["answertype"] = options.get("answertype", [u""])
            save_data[self.optionspage]["question"] =  [self.pagename]
            save_data[self.optionspage]["gwikicategory"] =  [rc['questionoptions']]

        success, msg =  set_metas(self.request, remove, dict(), save_data)

        if success:
            for page in old_answers:
                rm_success, rm_msg = PageEditor(self.request,page).deletePage()

        return success, msg

    def options(self):
        options = dict()

        if not page_exists(self.request, self.optionspage):
            return options

        optionkeys = ['answertype', 'redo']
        metas = get_metas(self.request, self.optionspage, optionkeys, display=True, checkAccess=False)

        for key in optionkeys:
            values = metas.get(key, list())
            if len(values) == 1:
                options[key] = values[0]
            elif len(values) > 1:
                raise TooManyValuesException(u'Question %s has too many %s options.' % (self.pagename, key))          
            elif len(values) < 1:
                raise MissingMetaException(u"Question %s doesn't have %s option." % (self.pagename, key))

        return options

    def histories(self):
        histories = list()

        page = self.request.graphdata.getpage(self.pagename)
        pagelist = page.get('in', dict()).get("question", list())

        for historypage in pagelist:
            keys = ["gwikicategory"]
            metas = get_metas(self.request, historypage, keys, display=True, checkAccess=False)

            categories = metas.get("gwikicategory", list())

            if rc['history'] in categories:
                histories.append(historypage)

        return histories

    def task(self):
        pagedict = self.request.graphdata.getpage(self.pagename).get('in', dict())

        tasks = list()

        for key, pages in pagedict.iteritems():
            if key not in ['_notype', 'question']:
                for page in pages:
                    keys = ["gwikicategory"]
                    metas = get_metas(self.request, page, keys, display=True, checkAccess=False)
                    if rc['taskflow'] in metas.get('gwikicategory', list()):
                        #TODO: getparent or link
                        tasks.append(page[:-5])

        if len(tasks) == 1:
            return Task(self.request, tasks[0])
        elif len(tasks) > 1:
            raise TooManyLinksException(u"Question %s linked in: %s" % (self.pagename, ", ".join(tasks)))

        return None


class Task:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename
        self.optionspage = pagename+'/options'
        self.flowpage = pagename+'/flow'
        if page_exists(request, self.flowpage):
            self.flow = Flow(request, self.flowpage)
        else:
            self.flow = None

    def options(self):
        options = dict()

        if not page_exists(self.request, self.optionspage):
            return options

        optionkeys = ['deadline', 'type', 'prerequisite']
        metas = get_metas(self.request, self.optionspage, optionkeys, display=True, checkAccess=False)
        for key in optionkeys:
            values = metas.get(key, list())

            if key == 'prerequisite':
                if len(values) > 0:
                    options[key] = values

            elif key == 'deadline':
                if len(values) == 1:
                    options[key] = values[0]
                elif len(values) > 1:
                    raise TooManyValuesException(u'Task %s has too many deadlines.' % self.pagename)
            else:
                if len(values) == 1:
                    options[key] = values[0]
                elif len(values) > 1:
                    raise TooManyValuesException(u'Task %s has too many %s options.' % (self.pagename, key))
                elif len(values) < 1:
                    raise MissingMetaException(u"Task %s doesn't have %s option." % (self.pagename, key))

        return options

    def questionlist(self):
        if not self.flow:
            return list()

        questionlist = list()
        next = 'first'

        while next != None:
            nextlist = self.flow.next_from_point(next)
            if len(nextlist) > 1:
                raise TooManyKeysException(u"Flow %s has too many metas with key %s." % (self.flowpage, next))
            elif len(nextlist) < 1:
                next = None
            else:
                next = nextlist[0]

                if next and next in questionlist:
                    raise TooManyValuesException("Flow %s has key %s linked in multiple times." % self.flowpage)       
                elif not page_exists(self.request, next):
                    raise DeadLinkException(u"Page %s linked in %s doesn't exist." % (next, self.flowpage))

                questionlist.append(next)

        return questionlist

    def title(self):
        raw_content = Page(self.request, self.pagename).get_raw_body()
        title = unicode()

        for line in raw_content.split("\n"):
            if line.startswith("== ") and line.endswith(" =="):
                title = line[3:-3]

        return title

    def save_flow(self, flow, options):
        save_data = dict()
        save_data[self.optionspage] = dict()
        save_data[self.flowpage] = dict()
        remove = dict()
        remove[self.pagename] = list()
        remove[self.optionspage] = list()
        remove[self.flowpage] = list()

        #TODO: create copy of questions that already exists in other tasks
        if flow:
            remove[self.flowpage] = self.questionlist()
            remove[self.flowpage].extend(["first"])
            for key,val in flow.iteritems():
                if len(val) > 1:
                    raise TooManyValuesException("Trying to save too many values to flow node.")
                save_data[self.flowpage][key] = [addlink(val[0])]

            remove[self.flowpage].extend(["task"])
            save_data[self.flowpage]["task"] = [addlink(self.pagename)]
            save_data[self.flowpage]["gwikicategory"] = [rc['taskflow']]

        if options:
            remove[self.optionspage].extend(["type", "deadline", "task"])
            save_data[self.optionspage]["type"] = options.get("type", [u""])
            save_data[self.optionspage]["deadline"] = options.get("deadline", [u""])

        save_data[self.optionspage]["task"] =  [addlink(self.pagename)]
        save_data[self.optionspage]["gwikicategory"] =  [rc['taskoptions']]

        success, msg =  set_metas(self.request, remove, dict(), save_data)

        return success, msg



class Course:

    def __init__(self, request, config):
        self.request = request
        self.config = config

        if not Page(request, config).exists():
            self.graphpage = None
            self.flowpage = None
            self.flow = None
        else:
            keys = ['graph', 'flow'] 
            metas = get_metas(self.request, self.config, keys, display=True, checkAccess=False)

            graphs = metas.get('graph', list())
            if len(graphs) == 1:
                self.graphpage = graphs[0]
            elif len(graphs) < 1:
                self.graphpage = None
            else:
                raise TooManyValuesException("Page %s has too many graph values" % self.config)

            flows = metas.get('flow', list())
            if len(flows) == 1:
                self.flowpage = flows[0]
                self.flow = Flow(request, flows[0])
            elif len(flows) < 1:
                self.flowpage = None
                self.flow = None
            else:
                raise TooManyValuesException("Page %s has too many flow values" % self.config)