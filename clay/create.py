'''
The create.py module is used to provision fresh virtual machines, if needed the
create.py module creates the needed filesystem higherarchy, coppied the files
into place, generates the libvirt xml configuration, and starts the virtual
machine.
'''

# Import clay libs
import clay.data
import clay.utils
# Import func libs
import func.overlord.client as fc
# Import python libs
import shutil
import os
import time
import random
import subprocess
import sys

def find_image(pool, distro):
    '''
    Returns the image to move into the final location.
    '''
    fn_types = ['Qemu',
                'data',
                'x86',
                ]
    images = []
    for fn_ in os.listdir(pool):
        path = os.path.join(pool, fn_)
        f_cmd = 'file ' + path
        f_type = subprocess.Popen(f_cmd,
            shell=True,
            stdout=subprocess.PIPE).communicate()[0]
        f_type = f_type.split(':')[1].split()[0]
        if not fn_types.count(f_type):
            continue
        if os.path.isdir(path):
            continue
        if fn_.split('_')[0] == distro:
            images.append(fn_)
    images.sort() # Need to put a check for images in
    return os.path.join(pool, images[-1])
        

class Create(object):
    '''
    Manages the creation of virtual machines
    '''
    def __init__(self, opts):
        self.opts = opts
        self.instance = self.__gen_instance()
        self.data = clay.data.HVStat()
        self.hyper = self.data.hyper

    def __gen_mac(self, prefix=''):
        '''
        Generates a mac addr with the defined prefix
        '''
        src = ['1','2','3','4','5','6','7','8','9','0','A','B','C','D','E','F']
        mac = prefix
        while len(mac) < 18:
            if len(mac) < 3:
                mac = random.choice(src) + random.choice(src) + ':'
            if mac.endswith(':'):
                mac += random.choice(src) + random.choice(src) + ':'
        return mac[:-1]

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

    def __gen_xml(self, vda, conf, root):
        '''
        Generates the libvirt xml file, right now this only supports kvm
        '''
        external_kernel = '''
                <kernel>%%KERNEL%%</kernel>
                <initrd>%%INITRD%%</initrd>
                <cmdline>root=%%ROOT%% vga=normal</cmdline>
        '''
        data = '''
<domain type='kvm'>
        <name>%%NAME%%</name>
        <vcpu>%%CPU%%</vcpu>
        <memory>%%MEM%%</memory>
        <os>
                <type>hvm</type>
                %%EXTK%%
                <boot dev='hd'/>
        </os>
        <devices>
                <emulator>/usr/bin/kvm</emulator>
                <disk type='file' device='disk'>
                        <source file='%%VDA%%'/>
                        <target dev='vda' bus='virtio'/>
                        <driver name='qemu' cache='writeback' io='native'/>
                </disk>
                %%PIN%%
                <interface type='bridge'>
                        <source bridge='virt_mgmt_br'/>
                        <mac address='%%MGMT_MAC%%'/>
                        <model type='virtio'/>
                </interface>
                <interface type='bridge'>
                        <source bridge='virt_service_br'/>
                        <mac address='%%SVC_MAC%%'/>
                        <model type='virtio'/>
                </interface>
                <interface type='bridge'>
                        <source bridge='virt_storage_br'/>
                        <mac address='%%STOR_MAC%%'/>
                        <model type='virtio'/>
                </interface>
                <graphics type='vnc' listen='0.0.0.0' autoport='yes'/>
        </devices>
        <features>
                <acpi/>
        </features>
</domain>
        '''
        data = data.replace('%%NAME%%', self.opts['name'])
        data = data.replace('%%CPU%%', str(self.opts['cpus']))
        data = data.replace('%%MEM%%', str(self.opts['mem'] * 1024))
        if self.opts['rpp']:
            data = data.replace('%%VDA%%', self.opts['rpp'])
        else:
            data = data.replace('%%VDA%%', vda)
        data = data.replace('%%MGMT_MAC%%', self.opts['macs']['virt_mgmt'])
        data = data.replace('%%SVC_MAC%%', self.opts['macs']['virt_service'])
        data = data.replace('%%STOR_MAC%%', self.opts['macs']['virt_storage'])

        if self.opts['extk']:
            data = data.replace('%%EXTK%%', external_kernel)

            data = data.replace('%%KERNEL%%', self.opts['kernel'])
            data = data.replace('%%INITRD%%', self.opts['initrd'])
            data = data.replace('%%ROOT%%', root)
        else:
            data = data.replace('%%EXTK%%', '')

        if self.opts['pin']:
            letters = clay.utils.gen_letters()
            pin_str = ''
            for ind in range(0, len(self.opts['pin'])):
                disk = self.opts['pin'][ind]
                pin_d = '''
                <disk type='file' device='disk'>
                        <source file='%%PIN_PATH%%'/>
                        <target dev='%%VD%%' bus='virtio'/>
                        <driver name='qemu' type='%%TYPE%%' cache='writeback' io='native'/>
                </disk>
                '''

                pin_d = pin_d.replace('%%PIN_PATH%%', disk['path'])
                pin_d = pin_d.replace('%%TYPE%%', disk['format'])
                pin_d = pin_d.replace('%%VD%%', 'vd' + letters[ind + 1])

                pin_str += pin_d
            data = data.replace('%%PIN%%', pin_str)
        else:
            data = data.replace('%%PIN%%', '')
        open(conf, 'w+').write(data)

    def _start_vm(self, conf, target, hyper=''):
        '''
        Starts a virtual machine
        Arguments:
        conf - string, the location of the libvirt xml configuration file
        '''
        stat = ''
        if hyper:
            stat = 'Starting the virtual machine ' + self.opts['name']\
                 + ' on hypervisor ' + hyper
        else:
            stat = 'Starting the virtual machine ' + self.opts['name']
        print stat
        v_cmd = 'virsh -c qemu:///system create ' + conf
        target.command.run(v_cmd)
        tgt_vinfo = target.virt.info()
        up = False
        for host in tgt_vinfo:
            if tgt_vinfo[host].has_key(self.opts['name']):
                up = True
        if not up:
            err = ''
            if hyper:
                err = 'Virtual machine failed to start on hypervisor ' + hyper
            else:
                err = 'Virtual machine failed to start'
            sys.stderr.write(err + '\n')
            return False
        return True

    def _find_hyper(self):
        '''
        Returns the hypervisor to create the vm on
        Returns - tuple, (string, bool)
        If the bool is True, then the string is the name of the hypervisor that
        houses the active vm, if False, then the hypervisor that is best suited
        for a new virtual machine
        '''
        hyper = ''
        best = (-10000, -1000000, 1000000)
        resources = self.data.resources()
        for host in resources:
            for vm in resources[host]['vms']:
                if self.opts['name'] == vm:
                    # The vm already exists in the cloud
                    return [host, True]
            if self.opts['hyper'] and resources.has_key(self.opts['hyper']):
                return (self.opts['hyper'], False)
            elif not resources.has_key(self.opts['hyper']):
                # hyper specified on the command line does not exist
                return [None, True]
            if resources[host]['cpus'] > best[0]:
                if resources[host]['mem'] > best[1]:
                    if len(resources[host]['vms']) < best[2]:
                        best = (resources[host]['cpus'],
                                resources[host]['mem'],
                                len(resources[host]['vms']))
                        hyper = host
        return [hyper, False]

    def _set_overlay(self, vda, target):
        '''
        Uses guestfish to overlay files into the vm image.
        '''
        over = os.path.join(self.opts['overlay'], self.opts['name'])
        if not os.path.isdir(over):
            return
        tarball = os.path.join(self.instance,
                str(int(time.time())) + str(random.randint(10000,99999)) + '.tgz')
        cwd = os.getcwd()
        os.chdir(over)
        print 'Packaging the virtual machine overlay'
        t_cmd = 'tar czf ' + tarball + ' *'
        subprocess.call(t_cmd, shell=True)
        print 'Applying the virtual machine overlay, this will take a few'\
            + ' moments...'
        g_cmd = ''
        if os.path.isfile('/etc/debian_version'):
            os.environ['LIBGUESTFS_QEMU'] = '/opt/guest-qemu/qemu-wrap'
        if self.opts['distro'] == 'ubuntu':
            g_cmd = 'guestfish -a ' + vda + ' --mount ' + self.opts['root']\
                  + ' tgz-in ' + tarball + ' /'
        else:
            g_cmd = 'guestfish -i -a ' + vda + ' tgz-in ' + tarball + ' /'
        subprocess.call(g_cmd, shell=True)
        os.remove(tarball)

    def _place_image(self, image, vda):
        '''
        Moves the image file from the image pool into the final destination.
        '''
        image_d = image + '.d'
        if not os.path.isdir(image_d):
            print 'No available images in the pool, copying fresh image...'
            shutil.copy(image, vda)
            return
        images = os.listdir(image_d)
        if not images:
            print 'No available images in the pool, copying fresh image...'
            shutil.copy(image, vda)
            return
        shutil.move(os.path.join(image_d, images[0]), vda)

    def _check_pins(self):
        '''
        Check the instances dir to see if this image has been previously
        pinned
        '''
        pinfile = os.path.join(self.instance, 'pin')
        if os.path.isfile(pinfile):
            return open(pinfile, 'r').read().strip()
        return ''

    def _set_pin_data(self, pin_data):
        '''
        Create the pin file
        '''
        pinfile = os.path.join(self.instance, 'pin')
        open(pinfile, 'w+').write(pin_data)

    def _check_existing(self, vda, conf):
        '''
        Check to see if the virtual machine image exists. It is does return
        True, else False
        '''
        if not os.path.isfile(conf):
            return False
        return True

    def create(self):
        '''
        Create a new virtual machine, returns the hypervisor housing the
        virtual machine.
        '''
        h_data = self._find_hyper()
        pin_data = []
        if not os.path.isdir(self.instance):
            os.makedirs(self.instance)
        else:
            pin_data = self._check_pins()
        if pin_data:
            h_data[0] = pin_data
        if h_data[1]:
            return None
        target = fc.Overlord(h_data[0], timeout=2400)
        if not os.path.isdir(self.opts['pool']):
            return False
        vda = os.path.join(self.instance, 'disk0.qcow2')
        conf = os.path.join(self.instance, 'config.xml')
        if self._check_existing(vda, conf):
            self._start_vm(conf, target, h_data[0])
            return True
        print 'VM ' + self.opts['name'] + ' not found in the cloud, \n'\
                + 'Creating a new VM, this will take a few moments...'
        image = find_image(self.opts['pool'], self.opts['distro'])
        root = self.opts['root']
        if self.opts['distro'] == 'arch':
            if not root and self.opts['extk']:
                root = self.detect_root(image)
        elif self.opts['distro'] == 'ubuntu':
            if not root:
                err = 'Ubuntu virtual machines require that the root partition'\
                    + ' be passed.'
                system.stderr.write(err + '\n')
                sys.exit(1)
        self._place_image(image, vda)
        self.__gen_xml(vda, conf, root)
        group = target.command.run("grep group /etc/libvirt/qemu.conf")[h_data[0]][1].split('"')[-2]
        user = target.command.run("grep user /etc/libvirt/qemu.conf")[h_data[0]][1].split('"')[-2]
        if self.opts['pin']:
            # The pin image file needs to be created
            target.clayvm.gen_pin_image(self.opts['pin'], self.opts['name'],
                    group, user)
            self._set_pin_data(h_data[0])
        target.command.run('chown ' + user + ':' + group + ' ' + vda)
        self._set_overlay(vda, target)
        if self.opts['rpp']:
            target.clayvm.set_rpp(vda, self.opts['rpp'])
            target.command.run('chown ' + user + ':' + group + ' ' + self.opts['rpp'])
            self._set_pin_data(h_data[0])
        self._start_vm(conf, target, h_data[0])
        return True

    def detect_root(self, image):
        '''
        Attempt to detect the root 
        Arguments: string - vda - Path to the hard drive image.
        '''
        root_fn = os.path.join(image + '.d', 'root')
        if os.path.isfile(root_fn):
            return open(root_fn, 'r').read()
        g_cmd = 'guestfish -i -a ' + vda + ' inspect-get-roots'
        root = subprocess.call(g_cmd,
                shell=True,
                stdout=subprocess.PIPE).communicate()[0]
        if not os.path.isdir(os.path.dirname(root_fn)):
            err = 'Cannot save detected root, pool dir is not present - is'\
                + ' clayd running?'
            sys.stderr.write(err + '\n')
        else:
            open(root_fn, 'w+').write(root.strip())
        return root.strip()

    def destroy(self):
        '''
        Force quit the named vm
        '''
        host = self.find_host()
        if not host:
            print 'Virtual machine ' + self.opts['name'] + ' not found in'\
                + ' the cloud'
            return
        target = fc.Overlord(host)
        target.virt.destroy(self.opts['name'])
        return target

    def purge(self):
        '''
        Destroy and DELETE the named vm
        '''
        host = self.find_host()
        target = None
        if not host:
            print 'Virtual machine ' + self.opts['name'] + ' not found in'\
                + ' the cloud'
        else:
            target = fc.Overlord(host)
        if not self.opts['force']:
            print 'This action will recursively destroy a virtual machine, you'\
                + ' better be darn sure you know what you are doing!!'
            conf = raw_input('Please enter yes or no [yes/No]: ')
            if not conf.strip() == 'yes':
                return
        if target:
            target.clayvm.purge(self.opts['name'])
        if os.path.isdir(self.instance):
            shutil.rmtree(self.instance)

    def find_host(self):
        '''
        Returns the hostname of the hypervisor housing the named vm
        '''
        h_data = self._find_hyper()
        if h_data[1]:
            return h_data[0]
        else:
            return None

    def get_host_fc(self):
        '''
        Returns a func connection to the host holding the named vm.
        '''
        h_data = self._find_hyper()
        if h_data[1]:
            return fc.Overlord(h_data[0])

