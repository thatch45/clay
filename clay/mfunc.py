'''
The mfunc module is intended to be used for enabling threading
(multiprocessing) support in clay for func
'''
# Import Python Modules
import os
import multiprocessing
import socket
import time
# Import func module(s)
import func.overlord.client as fc

class GenLive(object):
    '''
    Quickly returns a list of live servers
    '''
    def __init__(self, port=51234):
        self.port = port
        self.minions = self.__list_minions()

    def __list_minions(self):
        '''
        Returns a list of available func minions
        '''
        every = fc.Overlord('*')
        minions = set(every.list_minions())
        rm = set(['127.0.0.1'])
        return minions.difference(rm)

    def _check_port(self, minion):
        '''
        Check the port passed to the object, return the port status in a
        string
        '''
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            soc.connect((minion, self.port))
            soc.shutdown(2)
            return True
        except:
            return False

    def find_avail(self):
        '''
        Itterates over the minons and finds those that are up
        '''
        good = set()
        for minion in self.minions:
            if self._check_port(minion):
                good.add(minion)
        return good

    def gen_live_target(self):
        '''
        Returns a func client containing all live targets.
        '''
        good = self.find_avail()
        g_str = ''
        for minion in good:
            g_str += minion + ';'

        g_str = g_str[:-1]

        return fc.Overlord(g_str)


class MPFunc(object):
    '''
    Executes func in paralell with the multiprocessing module
    Takes a set of minions, preferably returned by the GenLive object
    '''
    def __init__(self, minions, module, method, args):
        '''
        Constructing an mpfunc object involves 4 arguments:
        minions: A set() structure containing the minions th manipulate
        mode: a string, the func module to call
        method: a string, the method to call
        args: I don't know yet
        '''
        self.minions = minions
        self.cmd = cmd
        self.args = args

    def process_procs(self):
        '''
        Starts the process bomb
        '''
        rets = {}
        returns = {}
        rms = set()
        for minion in self.minions:
            proc = multiprocessing.Process(target=(lambda : self.run_cmd(minion)))
            rets[minion] = {}
            rets[minion]['proc'] = proc
            rets[minion]['return'] = proc.start()
        while rets:
            for minion in rets:
                time.sleep(0.05)
                if not rets[minion]['proc'].is_alive():
                    returns[minion] = rets[minion]['return']
                    rms.add(minion)
            for rm in rms:
                rets.pop(minion)
        return returns

    def run_cmd(self, minion):
        '''
        Calls func with the passed minion and the object level command.
        '''
        target = fc.Overlord(minion)
        return target.run(self.module, self.method, self.args)


class CheckPort(multiprocessing.Process):
    '''
    Checks if a given port on a given host is open.
    '''
    def __init__(self, host, port, tmpdir):
        super(CheckPort, self).__init__()
        self.host = host
        self.port = int(port)
        self.tmpdir = tmpdir

    def _check_port(self):
        '''
        Check the port passed to the object, return the port status in a
        string
        '''
        p_stat = ''
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            soc.connect((self.host, self.port))
            soc.shutdown(2)
            p_stat = 'open'
        except:
            p_stat = 'closed'
        open(os.path.join(self.tmpdir, self.host), 'w+').write(p_stat)

    def run(self):
        '''
        Starts the process to check the port status
        '''
        self._check_port()
