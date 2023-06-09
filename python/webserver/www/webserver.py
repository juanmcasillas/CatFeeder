#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
'''
http://joelinoff.com/blog/?p=1658
Simple web server that demonstrates how browser/server interactions
work for GET and POST requests. Use it as a starting point to create a
custom web server for handling specific requests but don't try to use
it for any production work.

You start by creating a simple index.html file in web directory
somewhere like you home directory: ~/www.

You then add an HTML file: ~/www/index.html. It can be very
simple. Something like this will do nicely:

   <!DOCTYPE html>
   <html>
     <head>
       <meta charset="utf-8">
       <title>WebServer Test</title>
     </head>
     <body>
       <p>Hello, world!</p>
     </body>
   </html>

At this point you have a basic web infrastructure with a single file
so you start the server and point to the ~/www root directory:

   $ webserver.py -r ~/www

This will start the web server listening on your localhost on port
8080. You can change both the host name and the port using the --host
and --port options. See the on-line help for more information (-h,
--help).

If you do not specify a root directory, it will use the directory that
you started the server from.

Now go to your browser and enter http://0.0.0.0:8080 on the command
line and you will see your page.

Try entering http://0.0.0.0:8080/info to see some server information.

You can also use http://127.0.0.1.

By default the server allows you to see directory listings if there is
no index.html or index.htm file. You can disable this by specifying
the --no-dirlist option.

If you want to see a directory listing of a directory that contains a
index.html or index.htm directory, type three trailing backslashes in
the URL like this: http://foo/bar/spam///. This will not work if the
--no-dirlist option is specified.

The default logging level is "info". You can change it using the
"--level" option.

The example below shows how to use a number of the switches to run a
server for host foobar on port 8080 with no directory listing
capability and very little output serving files from ~/www:

  $ hostname
  foobar
  $ webserver --host foobar --port 8080 --level warning --no-dirlist --rootdir ~/www

To daemonize a process, specify the -d or --daemonize option with a
process directory. That directory will contain the log (stdout), err
(stderr) and pid (process id) files for the daemon process. Here is an
example:

  $ hostname
  foobar
  $ webserver --host foobar --port 8080 --level warning --no-dirlist --rootdir ~/www --daemonize ~/www/logs
  $ ls ~/www/logs
  webserver-foobar-8080.err webserver-foobar-8080.log webserver-foobar-8080.pid
'''

# LICENSE
#   Copyright (c) 2015 Joe Linoff
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.

# VERSIONS
#   1.0  initial release
#   1.1  replace req with self in request handler, add favicon
#   1.2  added directory listings, added --no-dirlist, fixed plain text displays, logging level control, daemonize
VERSION = '1.2'

import argparse
import BaseHTTPServer
from SocketServer import ThreadingMixIn, ForkingMixIn
import threading
import cgi
import logging
import os
import sys
import re
import platform
import datetime

class Handler_Base:
    def __init__(self):
        pass

    def Path(self):
        return '/'

    def ContentType(self):
        return 'text/html'

    def Dispatch(self, opts, request, args={}):
        pass


class Info_Handler(Handler_Base):
    def __init__(self):
        Handler_Base.__init__(self)

    def Path(self):
        return ('/info')

    def Dispatch(self, opts, request, args={}):

        '''
        Display some useful server information.

        http://127.0.0.1:8080/info
        '''

        request.send_response(200)  # OK
        request.send_header('Content-type', self.ContentType())
        request.end_headers()


        request.wfile.write('<html>')
        request.wfile.write('  <head>')
        request.wfile.write('    <title>Server Info</title>')
        request.wfile.write('  </head>')
        request.wfile.write('  <body>')
        request.wfile.write('    <table>')
        request.wfile.write('      <tbody>')
        request.wfile.write('        <tr>')
        request.wfile.write('          <td>client_address</td>')
        request.wfile.write('          <td>%r</td>' % (repr(request.client_address)))
        request.wfile.write('        </tr>')
        request.wfile.write('        <tr>')
        request.wfile.write('          <td>command</td>')
        request.wfile.write('          <td>%r</td>' % (repr(request.command)))
        request.wfile.write('        </tr>')
        request.wfile.write('        <tr>')
        request.wfile.write('          <td>headers</td>')
        request.wfile.write('          <td>%r</td>' % (repr(request.headers)))
        request.wfile.write('        </tr>')
        request.wfile.write('        <tr>')
        request.wfile.write('          <td>path</td>')
        request.wfile.write('          <td>%r</td>' % (repr(request.path)))
        request.wfile.write('        </tr>')
        request.wfile.write('        <tr>')
        request.wfile.write('          <td>server_version</td>')
        request.wfile.write('          <td>%r</td>' % (repr(request.server_version)))
        request.wfile.write('        </tr>')
        request.wfile.write('        <tr>')
        request.wfile.write('          <td>sys_version</td>')
        request.wfile.write('          <td>%r</td>' % (repr(request.sys_version)))
        request.wfile.write('        </tr>')
        request.wfile.write('      </tbody>')
        request.wfile.write('    </table>')
        request.wfile.write('  </body>')
        request.wfile.write('</html>')

def dinamic_handlers(external_handlers=None):

    r = {}
    r['/info'] = Info_Handler()

    if external_handlers:
        for k in external_handlers.keys():
            r[k] = external_handlers[k]

    return r



def make_request_handler_class(opts, handlers):
    '''
    Factory to make the request handler and add arguments to it.

    It exists to allow the handler to access the opts.path variable
    locally.
    '''
    class MyRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        '''
        Factory generated request handler class that contain
        additional class variables.
        '''
        m_opts =  opts
        m_opts.serverpath = 'http://%s:%s' % (m_opts.host, m_opts.port)
        dinamic_handlers = handlers

        # rootdir
        # no_dirlist

        def do_HEAD(self):
            '''
            Handle a HEAD request.
            '''
            logging.debug('HEADER %s' % (self.path))
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()



        def do_GET(self):
            '''
            Handle a GET request.
            '''

            self.path = re.sub('[/]+','/',self.path) # strip //

            logging.debug('GET %s' % (self.path))

            # Parse out the arguments.
            # The arguments follow a '?' in the URL. Here is an example:
            #   http://example.com?arg1=val1
            args = {}
            idx = self.path.find('?')
            if idx >= 0:
                rpath = self.path[:idx]
                args = cgi.parse_qs(self.path[idx+1:])
            else:
                rpath = self.path

            # Print out logging information about the path and args.
            if 'content-type' in self.headers:
                ctype, _ = cgi.parse_header(self.headers['content-type'])
                logging.debug('TYPE %s' % (ctype))

            logging.debug('PATH %s' % (rpath))
            logging.debug('ARGS %d' % (len(args)))
            if len(args):
                i = 0
                for key in sorted(args):
                    logging.debug('ARG[%d] %s=%s' % (i, key, args[key]))
                    i += 1

            # Check to see whether the file is stored locally,
            # if it is, display it.
            # There is special handling for http://127.0.0.1/info. That URL
            # displays some internal information.

            if rpath in MyRequestHandler.dinamic_handlers.keys():

                #logging.info('Dinamic Dispatcher (GET) %s' % (rpath))
                #self.send_header('Content-type', 'text/html')
                MyRequestHandler.dinamic_handlers[rpath].Dispatch(MyRequestHandler.m_opts,self,args)

            else:
                # Get the file path.
                path = MyRequestHandler.m_opts.rootdir + rpath
                dirpath = None
                logging.debug('FILE %s' % (path))

                # If it is a directory look for index.html
                # or process it directly if there are 3
                # trailing slashed.
                if rpath[-3:] == '///':
                    dirpath = path



                elif os.path.exists(path) and os.path.isdir(path):
                    dirpath = path  # the directory portion
                    index_files = ['/index.html', '/index.htm', ]
                    for index_file in index_files:
                        tmppath = path + index_file
                        if os.path.exists(tmppath):
                            path = tmppath
                            break



                # Allow the user to type "///" at the end to see the
                # directory listing.

                if os.path.exists(path) and os.path.isfile(path):


                    # This is valid file, send it as the response
                    # after determining whether it is a type that
                    # the server recognizes.

                    _, ext = os.path.splitext(path)
                    ext = ext.lower()
                    content_type = {
                        '.css': 'text/css',
                        '.gif': 'image/gif',
                        '.htm': 'text/html',
                        '.kml': 'application/vnd.google-earth.kml+xml',
                        '.kmz': 'application/vnd.google-earth.kmz',
                        '.html': 'text/html',
                        '.jpeg': 'image/jpeg',
                        '.jpg': 'image/jpg',
                        '.js': 'text/javascript',
                        '.png': 'image/png',
                        '.text': 'text/plain',
                        '.txt': 'text/plain',
                        '.ttf':  'application/octet-stream',
                        '.otf':  'application/octet-stream'
                    }

                    # If it is a known extension, set the correct
                    # content type in the response.
                    if ext in content_type:
                        self.send_response(200)  # OK
                        self.send_header('Content-type', content_type[ext])
                        
                       
                        
                        self.send_header('Access-Control-Allow-Origin', MyRequestHandler.m_opts.serverpath)
                        self.end_headers()

                        with open(path,'rb') as ifp:
                            self.wfile.write(ifp.read())
                    else:
                        # Unknown file type or a directory.
                        # Treat it as plain text.
                        self.send_response(200)  # OK
                        self.send_header('Content-type', 'text/plain')
                        self.end_headers()

                        with open(path) as ifp:
                            self.wfile.write(ifp.read())
                else:
                    if dirpath is None or self.m_opts.no_dirlist == True:
                        # Invalid file path, respond with a server access error
                        
                        #tplmgr = templater.Templater()
                        #g = templater.D()
                        g = {}
        
                        g['response'] = [500]
                        g['title'] = ["Server Access Error (500)" ]
                        g['desc'] = ["""<p>Server access error.</p>
                                    <p>%r</p>
                                    <p><a href='%s'>Back</a></p>""" % (repr(self.path),(rpath))]

                        MyRequestHandler.dinamic_handlers["/genericpage"].Dispatch(MyRequestHandler.m_opts,self,g)                                    
                        #fdata = tplmgr.Generate("genericpage", [ { 'tag': 'GENERIC', 'obj': g } ])
                        #self.wfile.write(fdata.encode('utf-8'))
                        
                        #self.wfile.write('<html>')
                        #self.wfile.write('  <head>')
                        #self.wfile.write('    <title>Server Access Error</title>')
                        #self.wfile.write('  </head>')
                        #self.wfile.write('  <body>')
                        #self.wfile.write('    <p>Server access error.</p>')
                        #self.wfile.write('    <p>%r</p>' % (repr(self.path)))
                        #self.wfile.write('    <p><a href="%s">Back</a></p>' % (rpath))
                        #self.wfile.write('  </body>')
                        #self.wfile.write('</html>')
                    else:
                        MyRequestHandler.m_opts.dirpath = dirpath
                        MyRequestHandler.m_opts.rpath = rpath
                        MyRequestHandler.dinamic_handlers["/listdir"].Dispatch(MyRequestHandler.m_opts,self)     
                        # List the directory contents. Allow simple navigation.
                        # logging.debug('DIR %s' % (dirpath))

                        #self.send_response(200)  # OK
                        #self.send_header('Content-type', 'text/html')
                        #self.end_headers()

                        #self.wfile.write('<html>')
                        #self.wfile.write('  <head>')
                        #self.wfile.write('    <title>%s</title>' % (dirpath))
                        #self.wfile.write('  </head>')
                        #self.wfile.write('  <body>')
                        #self.wfile.write('    <a href="%s">Home</a><br>' % ('/'));

                        # Make the directory path navigable.
                        #dirstr = ''
                        #href = None
                        #for seg in rpath.split('/'):
                        #    if href is None:
                        #        href = seg
                        #    else:
                        #        href = href + '/' + seg
                        #        dirstr += '/'
                        #    dirstr += '<a href="%s">%s</a>' % (href, seg)
                        #self.wfile.write('    <p>Directory: %s</p>' % (dirstr))

                        # Write out the simple directory list (name and size).
                        #self.wfile.write('    <table border="0">')
                        #self.wfile.write('      <tbody>')
                        #fnames = ['..']
                        #fnames.extend(sorted(os.listdir(dirpath), key=str.lower))
                        #for fname in fnames:
                        #    self.wfile.write('          <td align="left">')
                        #    self.wfile.write('        <tr>')
                        #    path = rpath + '/' + fname
                        #    fpath = os.path.join(dirpath, fname)
                        #    stat = os.stat(fpath)
                        #    ctime = stat.st_ctime
                        #    ctime = datetime.datetime.fromtimestamp(ctime).strftime('%m/%d/%Y %H:%M:%S')
                            
                        #    if os.path.isdir(path):
                        #        self.wfile.write('            <a href="%s%s">%s/</a>' % ( MyRequestHandler.m_opts.serverpath, path, fname))
                        #    else:
                        #        self.wfile.write('            <a href="%s%s">%s</a>' % ( MyRequestHandler.m_opts.serverpath,path, fname))
                        #    self.wfile.write('          <td>&nbsp;&nbsp;</td>')
                        #    self.wfile.write('          <td align="right">%3.2f Kb&nbsp;&nbsp;</td><td>%s</td>' % ((os.path.getsize(fpath) / 1024.0), ctime))
                        #    self.wfile.write('          </td>')
                        #    self.wfile.write('        </tr>')
                        #self.wfile.write('      </tbody>')
                        #self.wfile.write('    </table>')
                        #self.wfile.write('  </body>')
                        #self.wfile.write('</html>')

        def do_POST(self):
            '''
            Handle POST requests. TODO (not used)
            '''
            logging.debug('POST %s' % (self.path))

            # CITATION: http://stackoverflow.com/questions/4233218/python-basehttprequesthandler-post-variables
            ctype, pdict = cgi.parse_header(self.headers['content-type'])
            if ctype == 'multipart/form-data':
                postvars = cgi.parse_multipart(self.rfile, pdict)
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers['content-length'])
                postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
    
            else:
                postvars = {}

            # Get the "Back" link.
            back = self.path if self.path.find('?') < 0 else self.path[:self.path.find('?')]

            # Print out logging information about the path and args.
            logging.debug('TYPE %s' % (ctype))
            logging.debug('PATH %s' % (self.path))
            logging.debug('ARGS %d' % (len(postvars)))
            if len(postvars):
                i = 0
                for key in sorted(postvars):
                    logging.debug('ARG[%d] %s=%s' % (i, key, postvars[key]))
                    i += 1

            #
            # here, call the dispatcher also (GET  & POST is the same.)
            #

            if self.path in MyRequestHandler.dinamic_handlers.keys():
                #logging.info('Dinamic Dispatcher (POST) %s' % (self.path))
                MyRequestHandler.dinamic_handlers[self.path].Dispatch(MyRequestHandler.m_opts,self,postvars)

            else:

                # Tell the browser everything is okay and that there is
                # HTML to display.
                self.send_response(200)  # OK
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                # Display the POST variables.
                self.wfile.write('<html>')
                self.wfile.write('  <head>')
                self.wfile.write('    <title>Server POST Response</title>')
                self.wfile.write('  </head>')
                self.wfile.write('  <body>')
                self.wfile.write('    <p>POST variables (%d).</p>' % (len(postvars)))

                if len(postvars):
                    # Write out the POST variables in 3 columns.
                    self.wfile.write('    <table>')
                    self.wfile.write('      <tbody>')
                    i = 0
                    for key in sorted(postvars):
                        i += 1
                        val = postvars[key]
                        self.wfile.write('        <tr>')
                        self.wfile.write('          <td align="right">%d</td>' % (i))
                        self.wfile.write('          <td align="right">%s</td>' % key)
                        self.wfile.write('          <td align="left">%s</td>' % val)
                        self.wfile.write('        </tr>')
                    self.wfile.write('      </tbody>')
                    self.wfile.write('    </table>')

                self.wfile.write('    <p><a href="%s">Back</a></p>' % (back))
                self.wfile.write('  </body>')
                self.wfile.write('</html>')

    return MyRequestHandler

class ForkThreadedHTTPServer(ForkingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""
    
class ThreadThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

class  NormalHTTPServer(BaseHTTPServer.HTTPServer):
    """Handle requests in a separate thread."""

class Opts:
    def __init__(self):
        pass

def httpd(lopts=None, dhandlers=None):
    '''
    HTTP server
    '''

    if not lopts:
        opts = Opts()
        opts.host = 'localhost'
        opts.port = 8088
        opts.rootdir = '.'
        opts.no_dirlist = False
        opts.level = 'debug'
    else:
        opts = lopts

    RequestHandlerClass = make_request_handler_class(opts, dinamic_handlers(dhandlers))
    #server = BaseHTTPServer.HTTPServer((opts.host, opts.port), RequestHandlerClass)
    
    
    #if platform.system().lower() == 'windows':
    #    logging.info("Running on Windows platform. Switching to Threaded WWW server")
    #    server = ThreadThreadedHTTPServer((opts.host, opts.port), RequestHandlerClass)    
    #    #server = NormalHTTPServer((opts.host, opts.port), RequestHandlerClass)
    #else:
    #    logging.info("Running on Linux/Mac platform. Switching to Forked WWW server")
    #    server = ForkThreadedHTTPServer((opts.host, opts.port), RequestHandlerClass)   
    # to support global environment variables (HW)
    server = ThreadThreadedHTTPServer((opts.host, opts.port), RequestHandlerClass)    
    logging.info('Server starting %s:%s (level=%s)' % (opts.host, opts.port, opts.level))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print "Exception: ", exc_value
         



    server.server_close()
    logging.info('Server stopping %s:%s' % (opts.host, opts.port))


def get_logging_level(opts):
    '''
    Get the logging levels specified on the command line.
    The level can only be set once.
    '''
    if opts.level == 'notset':
        return logging.NOTSET
    elif opts.level == 'debug':
        return logging.DEBUG
    elif opts.level == 'info':
        return logging.INFO
    elif opts.level == 'warning':
        return logging.WARNING
    elif opts.level == 'error':
        return logging.ERROR
    elif opts.level == 'critical':
        return logging.CRITICAL


def daemonize(opts):
    '''
    Daemonize this process.

    CITATION: http://stackoverflow.com/questions/115974/what-would-be-the-simplest-way-to-daemonize-a-python-script-in-linux
    '''
    if os.path.exists(opts.daemonize) is False:
        err('directory does not exist: ' + opts.daemonize)

    if os.path.isdir(opts.daemonize) is False:
        err('not a directory: ' + opts.daemonize)

    bname = 'webserver-%s-%d' % (opts.host, opts.port)
    outfile = os.path.abspath(os.path.join(opts.daemonize, bname + '.log'))
    errfile = os.path.abspath(os.path.join(opts.daemonize, bname + '.err'))
    pidfile = os.path.abspath(os.path.join(opts.daemonize, bname + '.pid'))

    if os.path.exists(pidfile):
        err('pid file exists, cannot continue: ' + pidfile)
    if os.path.exists(outfile):
        os.unlink(outfile)
    if os.path.exists(errfile):
        os.unlink(errfile)

    if os.fork():
        sys.exit(0)  # exit the parent

    os.umask(0)
    os.setsid()
    if os.fork():
        sys.exit(0)  # exit the parent

    print('daemon pid %d' % (os.getpid()))

    sys.stdout.flush()
    sys.stderr.flush()

    stdin = file('/dev/null', 'r')
    stdout = file(outfile, 'a+')
    stderr = file(errfile, 'a+', 0)

    os.dup2(stdin.fileno(), sys.stdin.fileno())
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())

    with open(pidfile, 'w') as ofp:
        ofp.write('%i' % (os.getpid()))




if __name__ == '__main__':
    #main()  # this allows library functionality

    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.DEBUG)
    httpd()

