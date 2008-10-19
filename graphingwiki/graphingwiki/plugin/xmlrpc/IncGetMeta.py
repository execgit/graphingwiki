"""
    Incremental GetMeta (prototype).

    @copyright: 2008 by Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import os
import struct
import base64
import shelve
import xmlrpclib

from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from graphingwiki.editing import get_metas, metatable_parseargs, decode_page

def diff(previous, current):
    removedPages = list()
    updates = dict()

    for page in set(previous) | set(current):
        currentPage = current.get(page, dict())
        prevPage = previous.get(page, dict())

        # The page has been removed
        if page not in current:
            removedPages.append(page)
            continue

        # Signal that a page has been added to the result set even if
        # it contains no meta
        if page not in previous:
            updates[page] = dict()

        for key in set(currentPage) | set(prevPage):
            currentValues = currentPage.get(key, set())
            prevValues = prevPage.get(key, set())

            added = list(currentValues - prevValues)
            discarded = list(prevValues - currentValues)

            if discarded or added:
                updates.setdefault(page, dict())[key] = discarded, added
            
    return removedPages, updates

def create_new_handle(db):
    number = db.get("", 0)
    db[""] = number + 1
    return base64.b64encode(struct.pack("!Q", number))

def inc_get_metas(request, args, handle=None):
    pages, keys, _ = metatable_parseargs(request, args, get_all_keys=True)

    current = dict()
    for page in pages:
        # metatable_parseargs checks read permissions, no need to do it again
        metas = get_metas(request, page, keys, 
                          checkAccess=False)

        current[page] = dict()
        for key in keys:
            values = set(metas[key])
            current[page][key] = values

    path = os.path.join(request.cfg.data_dir, "getmetas.shelve")
    db = shelve.open(path)

    incremental = True
    try:
        if not handle or handle not in db:
            incremental = False
            handle = create_new_handle(db)
        previous = db.get(handle, dict())
        db[handle] = current
    finally:
        db.close()

    return [incremental, handle, diff(previous, current)]

def execute(xmlrpcobj, query, handle=None):
    request = xmlrpcobj.request
    request.formatter = TextFormatter(request)

    return inc_get_metas(request, query, handle)