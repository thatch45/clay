'''
The simple interface to pin images to hypervisors, this interface is required
by many components.
'''
import os

class Pin(object):
    '''
    Interface to the clay pinning system
    '''
    def __init__(self, opts):
        '''
        Create a pin object, pass in the opts dict
        '''
        self.opts = opts
        self.instance = self.__gen_instance()

    def __gen_instance(self):
        '''
        Figures out what the instance directory should be and returns it.
        '''
        pri = os.path.join(self.opts['instances'], self.opts['name'])
        sec = os.path.join(self.opts['instances'], self.opts['fqdn'])
        if os.path.isdir(pri):
            return pri
        if os.path.isdir(sec):
            return sec
        return pri

    def check_pins(self):
        '''
        Check the instances dir to see if this image has been previously
        pinned.
        '''
        pinfile = os.path.join(self.instance, 'pin')
        if os.path.isfile(pinfile):
            return open(pinfile, 'r').read().strip()
        return ''

    def set_pin_data(self, pin_data):
        '''
        Create the pin file.
        '''
        pinfile = os.path.join(self.instance, 'pin')
        open(pinfile, 'w+').write(pin_data)
