'''
This module is reserved for data collection, finding out what nodes are
available, who is who and what basic resources are being used.
This should onlu be used for determinining non-granular stats, like how many
vms are on a node, not granulay stats, func should not collect granular stats.
'''

# Import func modules
import func.overlord.client as fc

# Import clay modules
import clay.mfunc

def trim_mgmt(host):
    '''
    There is an issue where the name of the vm to clay/func is not the same
    as the migration host name, this is a hack to trim it.
    '''
    s_host = host.split('.')
    if s_host[1] == 'mgmt':
        return '.'.join([s_host[0]] + s_host[2:])
    return host


class HVStat(object):
    '''
    Detects statistics on virtual machines, used for provisioning, migrating
    etc.
    '''
    def __init__(self):
        live = clay.mfunc.GenLive()
        self.client = live.gen_live_target()
        self.hyper = fc.Overlord(self.__find_hv())

    def __find_hv(self):
        '''
        Query the minions and discover which ones are hypervisors, returns a
        func client string of hypervisors
        '''
        libvirt = set()
        qemu = ''
        types = self.client.virt.virttype()
        for host in types:
            if types[host] == 'QEMU':
                qemu += host + ';'
        if qemu:
            qemu = qemu[:-1]
        subc = fc.Overlord(qemu)
        outs = subc.command.run('lsmod | grep kvm_')
        for out in outs:
            if not outs[out][0]:
                libvirt.add(out)
        
        f_str = ''

        for host in libvirt:
            f_str += host + ';'

        return f_str[:-1]

    def resources(self, vinfo={}):
        '''
        Get what resources are availabe
        Returns:
        dict: {'hostname': {'cpus': <int>,
                            'mem': <int>, 
                            'vms': ['vm1', 'vm2']}}
        '''
        resources = {}
        ninfo = self.hyper.virt.nodeinfo()
        if not vinfo:
            vinfo = self.hyper.virt.info()
        # Populate resources template
        for host in vinfo:
            resources[host] = {'cpus': int(ninfo[host]['cpus']),
                               'mem': int(ninfo[host]['phymemory']),
                               'vms': []}
            for vm in vinfo[host]:
                resources[host]['cpus'] -= vinfo[host][vm]['nrVirtCpu']
                resources[host]['mem'] -= (int(vinfo[host][vm]['maxMem']) / 1024 )
                resources[host]['vms'].append(vm)

        return resources

    def migration_data(self, name, hyper=''):
        '''
        Determines what hosts to migrate a vm from and to, returns a dict.
        If the origin is known it can be passed.
        Returns { 'from': 'hv', 'to': 'hv'}
        '''
        ret = {'from': '', 'to': ''}
        best = (-10000, -1000000, 1000000)
        resources = self.resources()
        for host in resources:
            for vm in resources[host]['vms']:
                if name == vm:
                    ret['from'] = host
            if ret['from'] == host:
                continue
            if hyper and resources.has_key(hyper):
                ret['to'] = trim_mgmt(hyper)
            if resources[host]['cpus'] > best[0]:
                if resources[host]['mem'] > best[1]:
                    if len(resources[host]['vms']) < best[2]:
                        best = (resources[host]['cpus'],
                                resources[host]['mem'],
                                len(resources[host]['vms']))
                        ret['to'] = trim_mgmt(host)
        return ret


class VMStat(object):
    '''
    Returns data about virtual machines.
    '''
    def __init__(self):
        self.hv = HVStat()
        self.hyper = self.hv.hyper
        self.vm_info = self.__load_vms()

    def __load_vms(self):
        '''
        Load up the virtual machine data
        '''
        # TODO:
        # Maybe move this to the clayvm on the client side, would it be faster?
        # (probably menial)
        vm_info = self.hyper.virt.info()
        pops = []
        for host in vm_info:
            if type(vm_info[host]) == type(list()):
                pops.append(host)
                continue
            fc_host = fc.Overlord(host)
            for vm in vm_info[host]:
                vnc = fc_host.virt.get_graphics(vm)
                vm_info[host][vm]['vnc'] = vnc[host]['port']

        for host in pops:
            vm_into.pop(host)

        return vm_info

    def list_resources(self):
        '''
        Returns a formated string of what the vm resources are
        '''
        resources = self.hv.resources(self.vm_info)
        ret = ''
        for host in sorted(resources):
            ret += 'Resources available on ' + host + ' :\n'
            ret += '  Virtual CPUS:       ' + str(resources[host]['cpus'])\
                + '\n'
            ret += '  Memory:             ' + str(resources[host]['mem'])\
                + '\n'
            ret += '  Number of VMs:      ' + str(len(resources[host]['vms']))\
                + '\n'
        return ret

    def list_vm(self, name):
        '''
        Returns a string describing a simgle vm
        '''
        ret = 'Info for vm ' + name + ' :\n'
        for host in self.vm_info:
            for vm in self.vm_info[host]:
                if vm == name:
                    ret += '  Hypervisor hosting vm: ' + host + '\n'
                    ret += '  Virtual CPUS: '\
                        + str(self.vm_info[host][vm]['nrVirtCpu'])+ '\n'
                    ret += '  Memory:       '\
                        + str(int(self.vm_info[host][vm]['maxMem']) / 1024)\
                        + '\n'
                    ret += '  State:        '\
                        + self.vm_info[host][vm]['state'] + '\n'
                    ret += '  VNC Con:      ' + host + ':'\
                        +  self.vm_info[host][vm]['vnc'] + '\n'
        return ret

    def list_vms(self):
        '''
        Returns a formated string with information about available vms
        '''
        ret = ''
        for host in sorted(self.vm_info):
            ret += 'Virtual machines on ' + host + ' :\n'
            for vm in sorted(self.vm_info[host]):
                ret += '  ' + vm + '\n'
                ret += '    Virtual CPUS: '\
                    + str(self.vm_info[host][vm]['nrVirtCpu']) + '\n'
                ret += '    Memory:       '\
                    + str(int(self.vm_info[host][vm]['maxMem']) / 1024)\
                    + '\n'
                ret += '    State:        ' + self.vm_info[host][vm]['state']\
                    + '\n'
                ret += '    VNC Con:      ' + host + ':'\
                    +  self.vm_info[host][vm]['vnc'] + '\n'
            ret += '############\n\n'
        return ret

