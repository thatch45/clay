'''
Utilities such as logging and deamonizing
'''

# Import python modules
import sys
import os
import multiprocessing

# Import Func modules
import func.overlord.client as fc

def daemonize():
    '''
    Daemonize a process
    '''
    try: 
        pid = os.fork() 
        if pid > 0:
            # exit first parent
            sys.exit(0) 
    except OSError, e: 
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1)

    # decouple from parent environment
    os.chdir("/") 
    os.setsid() 
    os.umask(022) 

    # do second fork
    try: 
        pid = os.fork() 
        if pid > 0:
            # print "Daemon PID %d" % pid 
            sys.exit(0) 
    except OSError, e: 
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror) 
        sys.exit(1) 

    dev_null = file('/dev/null','rw') 
    os.dup2(dev_null.fileno(), sys.stdin.fileno()) 
    os.dup2(dev_null.fileno(), sys.stdout.fileno()) 
    os.dup2(dev_null.fileno(), sys.stderr.fileno()) 

def check_root():
    '''
    Most of the clay scripts need to run as root, this function will simple
    verify that root is the user before the application discovers it.
    '''
    if os.getuid():
        print 'Sorry, clay has to run as root, it needs to opperate in a' \
                + ' privileged environment to do what it does.' \
                + ' http://xkcd.com/838/'
        sys.exit(1)

def gen_letters():
    '''
    Generate the letters used to farm out all of the virtual pin drives
    '''
    lets = map(chr, range(97, 123))
    alets = map(chr, range(97, 123))
    blets = map(chr, range(97, 123))
    for alet in alets:
        for blet in blets:
            lets.append(alet + blet)
    return lets

