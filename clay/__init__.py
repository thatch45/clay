'''
Functions and classes for running batch jobs in clay
'''
# Import python modules
import optparse
import os
import sys
import random
import time
import yaml
import subprocess

# Import clay modules
import clay.create
import clay.data
import clay.overlay
import clay.utils
import clay.daemon
import clay.migrate

class ClayVM(object):
    '''
    Manages virtual machine opperations
    '''
    def __init__(self):
        '''
        '''
        self.opts = self.__parse()

    def __parse(self):
        '''
        Parse the command line arguments, returns a dict of the args
        '''
        parser = optparse.OptionParser()

        parser.add_option('-C',
                '--create',
                dest='create',
                default=False,
                action='store_true',
                help='Set the creation flag')

        parser.add_option('-D',
                '--destroy',
                dest='destroy',
                default=False,
                action='store_true',
                help='Force quit the named vm')

        parser.add_option('-P',
                '--purge',
                dest='purge',
                default=False,
                action='store_true',
                help='Recursively destroy and delete the named vm')

        parser.add_option('-Q',
                '--query',
                dest='query',
                default=False,
                action='store_true',
                help='Set the query flag')

        parser.add_option('-M',
                '--migrate',
                dest='migrate',
                default=False,
                action='store_true',
                help='Set the migrate flag')

        parser.add_option('-R',
                '--reset',
                dest='reset',
                default=False,
                action="store_true",
                help='Hard reset a vm')

        parser.add_option('-n',
                '--name',
                dest='name',
                default='',
                help='The name of the vm to manipulate')

        parser.add_option('-c',
                '--cpus',
                dest='cpus',
                type=int,
                default=1,
                help='The number of cpus to give the vm - only read for new'\
                        + 'virtual machines; default = 1')

        parser.add_option('-m',
                '--mem',
                '--memory',
                dest='mem',
                type=int,
                default=1024,
                help='The amount of ram to give the vm in mebibytes - only read'\
                        + ' for new virtual machines; default = 1024')

        parser.add_option('-d',
                '--distro',
                dest='distro',
                default='arch',
                help='The name of the operating system to use, clay will detect'\
                        + ' and use the latest available image; default = arch')

        parser.add_option('-e',
                '--env',
                '--environment',
                dest='env',
                default='',
                help='The puppet environment for this virtual machine to'\
                    + ' attatch to. By default this will be determined by'
                    + ' the hostname')

        parser.add_option('-r',
                '--root',
                dest='root',
                default='',
                help='The root directory on a new vm - if not specified clay will'\
                        + ' try to detect it.')

        parser.add_option('-p',
                '--pin',
                dest='pin',
                default='',
                help='This option will create a set of local "pinned" virtual'\
                    + ' machine images which will be made available to this'\
                    + ' vm. The pinned vm image will be created on the'\
                    + ' hypervisor. The pin option is a collection of options'\
                    + ' delimited by commas. The option to pass is: '\
                    + ' <image_path>::<size in GB>,<format(raw/qcow2)>,<fs(ext4/xfs)>'\
                    + ':<size in GB>,<format(raw/qcow2)>,<fs(ext4/xfs)>, etc.')

        parser.add_option('-a',
                '--avail',
                dest='avail',
                default=False,
                action='store_true',
                help='This flag is for the Query command, this will cause'\
                    + ' the available resources on the hypervisors to be'\
                    + ' displayed')

        parser.add_option('-f',
                '--force',
                dest='force',
                default=False,
                action='store_true',
                help='Bypass any "are you sure" questions, use with caution!')

        parser.add_option('--clear-node',
                dest='clear_node',
                default='',
                help='Specify which hypervisor to migrate all of the virtual'\
                    + ' machines off of.')

        parser.add_option('--hyper',
                '--hypervisor',
                dest='hyper',
                default='',
                help='The explicit name of the hypervisor to use, bypass node'\
                    + ' detection by clay')

        parser.add_option('--root-pin-path',
                '--rpp',
                dest='rpp',
                default='',
                help='This option will create a pinned vm, unlike the pin'\
                    + ' option this will pin the root image to the specified'\
                    + ' path.')

        parser.add_option('--config',
                dest='config',
                default='/etc/clay/clay.conf',
                help='The location of the clay-vm configuration file;'\
                        + 'default=/etc/clay/clay-vm.conf')

        # TODO
        # These cli opts probably don't need to be here and *could* be restricted
        # to the config file

        parser.add_option('--pool',
                dest='pool',
                default='',
                help='The directory on shared storage that holds pool data, pool'\
                        + ' data is defined as any virtual machine data which'\
                        + ' will need to be coppied and/or reused, this includes'\
                        + ' but is not limited to virtual machine base images')

        parser.add_option('--overlay',
                dest='overlay',
                default='',
                help='The base directory for virtual machine overlays, overlays'\
                        + ' should begin in a directory of the vm name in this'\
                        + ' directory')

        parser.add_option('--boot',
                dest='boot',
                default='',
                help='The directory on shared storage that holds boot data, boot'\
                        + ' data is defined as any virtual machine data which'\
                        + ' will be used to boot vms')

        parser.add_option('--instances',
                dest='instances',
                default='',
                help='The directory on shared storage that holds virtual machine'\
                        + ' instances, this is the libvirt config and the virtual'\
                        + ' machine image(s)')

        parser.add_option('--dhcp-dir',
                dest='dhcp_dir',
                default='',
                help='The directory on which contains the dnsmasq config files'\
                        + ' for virtial machines.')

        parser.add_option('--func-certs',
                dest='func_certs',
                default='',
                help='The location where certmaster saves signed certificates'\
                        + ' for func.')

        parser.add_option('--external-kernel',
                dest='extk',
                default=False,
                action='store_true',
                help='Create the new vm with an externel kernel to boot from,'\
                        + ' do not boot from the kernel inside the vm.')

        options, args = parser.parse_args()

        opts = {}

        opts['pool'] = '/srv/vm/images/pool'
        opts['overlay'] = '/srv/vm/overlay'
        opts['boot'] = '/srv/vm/boot'
        opts['instances'] = '/srv/vm/instances'
        opts['dhcp_dir'] = '/etc/dnsmasq.d/vm'
        opts['func_certs'] = '/var/lib/certmaster/certmaster/certs/'

        if os.path.isfile(options.config):
            opts.update(yaml.load(open(options.config, 'r')))

        # Load up the optparse options
        opts['create'] = options.create
        opts['destroy'] = options.destroy
        opts['purge'] = options.purge
        opts['query'] = options.query
        opts['migrate'] = options.migrate
        opts['reset'] = options.reset
        opts['name'] = options.name
        opts['distro'] = options.distro
        opts['root'] = options.root
        opts['hyper'] = options.hyper
        opts['cpus'] = options.cpus
        opts['mem'] = options.mem
        opts['avail'] = options.avail
        opts['force'] = options.force
        opts['clear_node'] = options.clear_node

        if options.pin:
            path = os.path.join(options.pin.split('::')[0], opts['name'])
            if not options.pin.split('::')[0].startswith('/'):
                err = 'Pin path must begin with / - Exiting'
                sys.stderr.write(err + '\n')
                sys.exit(1)
            disks = []
            letters = clay.utils.gen_letters()
            for disk in options.pin.split('::')[1].split(':'):
                comps = disk.split(',')
                disks.append({'path': os.path.join(path,
                              'vd' + letters[len(disks) + 1] + '.' + comps[1]),
                              'size': comps[0],
                              'format': comps[1],
                              'filesystem': comps[2]})
            opts['pin'] = disks
        else:
            opts['pin'] = ''
        if options.rpp:
            if not options.rpp.startswith('/'):
                err = 'Root pin path must begin with / - Exiting'
                sys.stderr.write(err + '\n')
                sys.exit(1)
            opts['rpp'] = os.path.join(options.rpp, opts['name'], 'disk.0')
        else:
            opts['rpp'] = ''
        if options.pool:
            opts['pool'] = options.pool
        if options.overlay:
            opts['overlay'] = options.overlay
        if options.boot:
            opts['boot'] = options.boot
        if options.instances:
            opts['instances'] = options.instances
        if options.dhcp_dir:
            opts['dhcp_dir'] = options.dhcp_dir
        if options.func_certs:
            opts['func_certs'] = options.func_certs
        opts['extk'] = options.extk
        # 
        # Load up generated options - All configs should be loaded by this
        # point!
        #
        opts['macs'] = self.__generate_macs(opts['dhcp_dir'], opts['name'])
        opts['kernel'] = os.path.join(opts['boot'], opts['distro'] + '_vmlinuz')
        opts['initrd'] = os.path.join(opts['boot'], opts['distro'] + '_initrd.img')
        domain = self.__domain()
        if opts['name'].endswith(domain):
            opts['fqdn'] = opts['name']
        else:
            opts['fqdn'] = opts['name'] + '.' + domain

        if options.env:
            opts['env'] = options.env
        else:
            if opts['fqdn'].count('_'):
                opts['env'] = opts['fqdn'].split('_')[1].split('.')[0]
            else:
                opts['env'] = opts['fqdn'].split('.')[1]
            valid_env = [
                         'prod',
                         'int',
                         'dev',
                         'grease'
                         ]
            if not valid_env.count(opts['env']) and opts['create']:
                err = 'A valid environment could not be determined by the'\
                    + ' hostname, please fix the hostname and execute again'\
                    + ' or declare the environment with the -e flag.'
                sys.stderr.write(err + '\n')
                sys.exit(2)

        return opts

    def __domain(self):
        '''
        Returns the fqdn for the deployment, derived from the master's resolv.conf.
        '''
        return subprocess.Popen('dnsdomainname',
                shell=True,
                stdout=subprocess.PIPE).communicate()[0].strip()

    def __generate_macs(self, dhcp_dir, name):
        '''
        Generate mac addrs to use for a new vm
        '''
        macs = {}
        dns = os.path.join(dhcp_dir, name + '.conf')
        if os.path.isfile(dns):
            for line in open(dns, 'r').readlines():
                com = line.split(',')
                macs[com[0].split(':')[1]] = com[1]
            return macs

        octets = [
            0x00, 
            [0x11, 0x33, 0x44],
                0x3e,
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff)
            ]

        servicemac = [octets[0], octets[1][0], octets[2], octets[3], octets[4], octets[5]]
        storagemac = [octets[0], octets[1][1], octets[2], octets[3], octets[4], octets[5]]
        mgmtmac =    [octets[0], octets[1][2], octets[2], octets[3], octets[4], octets[5]]

        macs = {
            'virt_service': ':'.join(map(lambda x: "%02x" % x, servicemac)),
            'virt_storage': ':'.join(map(lambda x: "%02x" % x, storagemac)),
            'virt_mgmt'   : ':'.join(map(lambda x: "%02x" % x, mgmtmac))
        }
        return macs

    def _verify_env(self):
        '''
        There are a few things that will break vm management in the environment,
        they should be checked.
        '''
        exit = False
        kern = True
        init = True
        if self.opts['extk'] and self.opts['distro']:
            if not os.path.isfile(self.opts['kernel']):
                kern = False
                exit = True
                print 'ERROR: The needed kernel "' + self.opts['kernel'] + '" is unavailable.'
            if not os.path.isfile(self.opts['initrd']):
                init = False
                exit = True
                print 'ERROR: The needed ramdisk "' + self.opts['initrd'] + '" is unavailable.'
        if exit:
            sys.exit(1)

    def clay_vm(self):
        '''
        The main function for clayvm
        '''
        self._verify_env()
        if self.opts['create']:
            overlay = clay.overlay.Overlay(self.opts)
            overlay.setup_overlay()
            create = clay.create.Create(self.opts)
            create.create()
        elif self.opts['query']:
            if self.opts['name']:
                data = clay.data.VMStat()
                print data.list_vm(self.opts['name'])
            elif self.opts['avail']:
                data = clay.data.VMStat()
                print data.list_resources()
            else:
                data = clay.data.VMStat()
                print data.list_vms()
        elif self.opts['destroy']:
            if not self.opts['name']:
                print 'Destroy requires the name of a virtual machine'
                sys.exit(1)
            create = clay.create.Create(self.opts)
            create.destroy()
        elif self.opts['purge']:
            if not self.opts['name']:
                print 'Purge requires the name of a virtual machine'
                sys.exit(1)
            create = clay.create.Create(self.opts)
            overlay = clay.overlay.Overlay(self.opts)
            create.purge()
            overlay.purge_overlay()
        elif self.opts['migrate']:
            migrate = clay.migrate.Migrate(self.opts)
            migrate.run_logic()
        elif self.opts['reset']:
            if not self.opts['name']:
                print 'Reset requires the name of a virtual machine'
                sys.exit(1)
            create = clay.create.Create(self.opts)
            create.destroy()
            time.sleep(2)
            create.create()


class ClayD(object):
    '''
    The clay daemon
    '''
    def __init__(self, conf='/etc/clay/clay.conf'):
        self.cli = self.__parse_cli()
        self.opts = self.__parse(conf)

    def __parse_cli(self):
        '''
        Parse the command line options passed to the clay daemon
        '''
        parser = optparse.OptionParser()
        parser.add_option('-f',
                '--foreground',
                default=False,
                action='store_true',
                dest='foreground',
                help='Run the clay daemon in the foreground')

        options, args = parser.parse_args()

        return {'foreground': options.foreground}

    def __parse(self, conf):
        '''
        Parse the clay deamon configuration file
        '''
        opts = {}

        opts['pool'] = '/srv/vm/images/pool'
        opts['pool_size'] = '5'
        opts['keep_old'] = '2'
        opts['interval'] = '5'
        opts['image_source'] = ''
        opts['distros'] = 'arch'
        opts['format'] = 'raw'

        if os.path.isfile(conf):
            opts.update(yaml.load(open(conf, 'r')))

        return opts

    def clay_daemon(self):
        '''
        Starts the clay daemon
        '''
        clayd = clay.daemon.Daemon(self.opts)
        if not self.cli['foreground']:
            clay.utils.daemonize()
        clayd.watch_pool()
