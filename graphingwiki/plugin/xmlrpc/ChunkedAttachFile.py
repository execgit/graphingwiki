import xmlrpclib
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from cStringIO import StringIO

from graphingwiki.editing import save_attachfile
from graphingwiki.editing import check_attachfile
from graphingwiki.editing import list_pagecachefiles
from graphingwiki.editing import list_attachments

from graphingwiki.editing import load_pagecachefile
from graphingwiki.editing import delete_pagecachefile
from graphingwiki.editing import load_attachfile
from graphingwiki.editing import delete_attachfile

from MoinMoin.wikiutil import normalize_pagename

CHUNK_SIZE = 1024 * 1024

def runChecked(func, request, pagename, filename, *args, **keys):
    # Checks ACLs and the return value of the called function.
    # If the return value is None, return Fault

    _ = request.getText
    if not request.user.may.read(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to access this page"))

    result = func(request, pagename, filename, *args, **keys)
    if result is None:
        return xmlrpclib.Fault(2, "%s: %s" % (_("Nonexisting attachment"),
                                              filename))

    return result

def info(request, pagename, filename):
    try:
        fpath, exists = check_attachfile(request, pagename, filename)
        if not exists:
            return None

        stream = open(fpath, "rb")
        digest = md5()

        data = stream.read(CHUNK_SIZE)
        while data:
            digest.update(data)
            data = stream.read(CHUNK_SIZE)

        digest = digest.hexdigest()
        size = stream.tell()
        stream.close()
    except:
        return None

    return [digest, size]

def load(request, pagename, filename, start, end):
    try:
        fpath, exists = check_attachfile(request, pagename, filename)
        if not exists:
            return None

        stream = open(fpath, "rb")
        stream.seek(start)
        data = stream.read(max(end-start, 0))
        stream.close()
    except:
        return None

    return xmlrpclib.Binary(data)

def reassembly(request, pagename, filename, chunkSize, digests, overwrite=True):
    _ = request.getText

    # Also check ACLs
    if not request.user.may.write(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to attach a "+
                                    "file to this page"))

    # Check whether the file already exists. If it does, check the hashes.
    fpath, exists = check_attachfile(request, pagename, filename)
    if chunkSize is not None and exists:
        try:
            stream = open(fpath, "rb")
        except:
            pass
        else:
            for digest in digests:
                data = stream.read(chunkSize)
                other = md5(data).hexdigest()
                if other != digest:
                    break
            else:
                data = stream.read(chunkSize)
                if not data:
                    stream.close()
                    return list()
            
            stream.close()

        # Fail if the file doesn't match and we don't want to overwrite.
        if not overwrite:
            return xmlrpclib.Fault(2, _("Attachment not saved, file exists"))

    # If there are missing chunks, just return them. Chunks might also
    # be in attachments for the people that use older versions of
    # opencollab.
    result = list_pagecachefiles(request, pagename)
    result.extend(list_attachments(request, pagename))
    missing = [digest for digest in digests if digest not in result]
    if missing:
        return missing

    # Reassembly the file from the chunks into a temp file.
    buffer = StringIO()
    
    for bite in digests:
        # Try both cache files and attachments (for legacy, see above)
        data = load_pagecachefile(request, pagename, bite)
        if not data:
            data = load_attachfile(request, pagename, bite)
        if not data:
            return xmlrpclib.Fault(2, "%s: %s" % (_("Nonexisting "+
                                                    "attachment or cachefile"),
                                                  filename))
        buffer.write(data)

    # Attach the decoded file.
    success = save_attachfile(request, pagename, buffer.getvalue(), filename, 
                              overwrite, True)

    # FIXME: What should we do when the cleanup fails?
    for bite in digests:
        # Try both cache files and attachments (for legacy, see above)
        in_cache = delete_pagecachefile(request, pagename, bite)
        if not in_cache:
            delete_attachfile(request, pagename, bite, True)

    # On success signal that there were no missing chunks.
    if success:
        return list()
    
    if overwrite == False:
        return xmlrpclib.Fault(2, _("Attachment not saved, file exists"))

    return xmlrpclib.Fault(2, _("Attachment not saved"))

def execute(xmlrpcobj, page, fname, action='info', start=None, end=None):
    request = xmlrpcobj.request
    _ = request.getText

    page = xmlrpcobj._instr(page)
    fname = xmlrpcobj._instr(fname)
    page = normalize_pagename(page, request.cfg)
    # Fault at empty pagenames
    if not page:
        return xmlrpclib.Fault(3, _("No page name entered"))

    if action == 'info':
        success = runChecked(info, request, page, fname)
    elif action == 'load' and None not in (start, end):
        success = runChecked(load, request, page, fname, start, end)
    elif action == 'reassembly' and start is not None:
        chunk, digests = start, end
        success = runChecked(reassembly, request, page, fname, chunk, digests)
    else:
        success = xmlrpclib.Fault(3, _("No method specified or invalid span"))

    return success
