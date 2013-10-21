

        # NUSH 0.2 CORE NAMESPACE
        # This is Free Software (GPL)


import os
import cgi
import json
import shutil
from time import sleep
from threading import Thread

import cherrypy
import pipes

from subprocess import Popen, PIPE

superspace = {'SUPERPIN': 0}


# INTERNAL: DOMAINS MANAGER
class DomainsManager:

    def __init__(self): self.domains = {}

    def register(self, domain, seen=True):

        self.domains[domain.domain] = domain
        if seen: shell.execute('toastr.success("NEW DOMAIN: {0}")'.format(domain.domain))

    def read_post(self):

        try: return cherrypy.request.body.read().decode()
        except: return None

    def handle(self, *args, **kargs):

        args = list(args)
        data = self.read_post()

        domain = self.domains[args.pop(0)]
        method = args.pop(0)

        if data: return getattr(domain, method)(data, *args, **kargs)
        else: return getattr(domain, method)(*args, **kargs)

    handle.exposed = True


# INTERNAL: EMPTY DOMAIN FOR HANDLERS
class OrphanHandlers: domain = 'handlers'


# INTERNAL: BUILT IN DOMAIN HANDLERS
class CoreBuiltIns:

    domain = 'builtin'

    def issue_pin(self): return superpin()

    def superspace(self, data=None):

        if data: superspace.update(json.loads(data))
        return json.dumps(superspace)

    def editor(self, path):

        highlighting = {
            'py':   'python',
            'htm':  'html',
            'html': 'html',
            'css':  'css',
            'js':   'javascript',
            'json': 'json'
            }

        ext = path.split('.')[-1]
        try: lang = highlighting[ext]
        except: lang = ''

        appdir = ROOTDIR + '/static/apps/editor'
        with open(appdir + '/editor.html') as f: editor = f.read()

        return editor.replace(
            '$$ title $$', path.split('/')[-1]
            ).replace(
            '$$ appdir $$', appdir
            ).replace(
            '$$ filepath $$', path
            ).replace(
            '$$ lang $$', lang
            )

    def load_file(self, path, timestamp): return open(path)

    def radio_send(self, data):
        
        data = json.loads(data)
        radio.send(data['channels'], data['message'])


# HELPERS
# =======

def superpin():

    '''Function that increments and then returns the superpin as an id string.'''

    superspace['SUPERPIN'] += 1
    return 'pin' + str(superspace['SUPERPIN'])


def feed(color, title, message, body=''):

    '''Generate a new feed package with an optional body.'''

    if body: body = '<div class=padded_feed>{0}</div>'.format(body)

    feed = '''
        <span class="{0}">{1}</span> <span class=grey>#</span>
        <span style="float: right" onclick="this.parentNode.parentNode.removeChild(this.parentNode); editor.focus()">
        <span style="padding-right: 4px" class="dull kill_button hint--left hint--bounce"
            data-hint="Delete This Feed">x</span></span>
        {2}{3}'''.format(color, title, message, body)

    return json.dumps({'feed': feed, 'jscript': 'create_feed(pkg.feed)'})


def escape_html(html): return '<xmp>{0}</xmp>'.format(html)


def path_resolve(path):

    '''This function patches the way paths are printed, so they look consistant.'''

    if not path: return path
    path = path_expand(path)
    if path != '/' and path.endswith('/'): path = path[:-1]
    return path[1:] if path.startswith('//') else path


def path_expand(path):

    '''Expand paths, including bookmarks, to absolute paths.'''

    cwd = os.getcwd()
    dad = os.path.dirname(cwd)
    starts = path.startswith
    normalise = os.path.normpath

    if   starts('/'):   return path
    elif starts('./'):  return normalise(cwd + path[1:])
    elif starts('../'): return normalise(dad + path[2:])
    elif starts('~/'):  return os.path.expanduser("~") + path[1:]
    elif starts('|'):

        try:

            if not '/' in path: return BOOKMARKS[path[1:]]

            name = path[1:path.find('/')]
            tail = path[path.find('/'):]
            return BOOKMARKS[name] + tail

        except KeyError: return path

    else: return cwd + '/' + path


def dir2html(path):

    '''Render a directory's contents as HTML, as used by the view and goto command.'''

    dirs, files = '', ''
    items = os.listdir(path)
    items.sort()

    for item in items:

        ends = item.endswith
        full_path = '{0}/{1}'.format(path, item)

        if os.path.isdir(full_path):

            dirs += '''<directory>{0}</directory><br>'''.format(item)
            continue

        elif ends('.py'): tag = 'python_file'
        elif ends('.zip'): tag = 'archive_file'
        elif item.startswith('.'): tag = 'hidden_file'
        elif item.startswith('README') or item.startswith('LICENSE'): tag = 'readme_file'
        elif ends('.png') or ends('.jpg') or ends('.jpeg') or ends('.mp4'): tag = 'media_file'
        elif ends('.html') or ends('.md') or ends('.css') or ends('.js') or ends('.json'): tag = 'web_file'
        else: tag = 'file'

        files += '''<{0}>{1}</{0}><br>'''.format(tag, item)

    return dirs + files if dirs or files else '<span class=dull>(this directory is empty)</span>'

def bosh(line):

    '''Get the output of a system command as a string.'''

    stdout, stderr = Popen([line], shell=True, stdout=PIPE, stderr=PIPE).communicate()
    output = stdout if stdout else stderr
    return(output.decode())

def read(path):
    
    '''Get the contents of a file from a path.'''
    
    return open(path_resolve(path)).read()


# GLOBAL NAMESPACE
# ================

def init():

    global issue_pin, domains, handlers

    issue_pin = superpin
    domains = DomainsManager()
    server.nush = domains.handle
    handlers = OrphanHandlers()
    domains.register(handlers, False)
    domains.register(CoreBuiltIns(), False)


# the current user's home directory
HOME = os.path.expanduser("~")

# get a path to this application's root directory
ROOTDIR = os.path.dirname(os.path.abspath(__file__))

# load the bookmarks.json file into a dict
BOOKMARKS = json.loads(open(ROOTDIR+'/static/apps/shell/bookmarks.json').read())

# this code is executed inside the interpreter when it's created
namespace = '''
import os
nush.init()
from nush import issue_pin
from nush import handlers, domains, radio
from nush import superspace, path_resolve
nush.interpreter.extensions.append('core')
'''
