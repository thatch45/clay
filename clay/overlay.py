'''
Prepare files which are generated before deployment for the overlay.
'''

import subprocess
import os
import shutil
import sys

class Overlay(object):
    '''
    Manage the creation of a basic virtual machine overlay
    '''
    def __init__(self, opts):
        self.opts = opts
        self.over = os.path.join(self.opts['overlay'], self.opts['name'])

    def gen_puppet(self):
        '''
        Generate and place the puppet certificates.
        '''
        tmp_priv = os.path.join(self.over, 'priv')
        privkeyd = os.path.join(self.over, 'var/lib/puppet/ssl/private_keys/')
        privkey = os.path.join(privkeyd, self.opts['fqdn'] + '.pem')
        if os.path.isfile(privkey):
            return
        if not os.path.exists(privkeyd):
            os.makedirs(privkeyd)
        ca_cmd = 'puppetca --generate ' + self.opts['fqdn'] + ' --privatekeydir=' + self.over
        subprocess.call(ca_cmd, shell=True)
        if os.path.isfile(os.path.join(self.over, self.opts['fqdn'] + '.pem')):
            shutil.move(os.path.join(self.over, self.opts['fqdn'] + '.pem'), privkeyd)
        else:
            err = 'Failed to find puppet key, was it generated properly?'
            sys.stderr.write(err + '\n')

    def set_env(self):
        '''
        Sets the environment for puppet to use in the puppet rc script
        '''
        conf_d = os.path.join(self.over, 'etc/conf.d')
        conf_f = os.path.join(conf_d, 'puppet')
        if not os.path.exists(conf_d):
            os.makedirs(conf_d)
        puppet_d = os.path.join(self.over, 'etc/puppet')
        puppet_f = os.path.join(puppet_d, 'puppet.conf')
        if not os.path.exists(puppet_d):
            os.makedirs(puppet_d)
        if not os.path.exists(conf_f):
            line = 'PUPPETD_ARGS="--environment=' + self.opts['env'] + '"\n'
            open(conf_f, 'w+').write(line)
        if not os.path.exists(puppet_f):
            lines = [
                     '[main]\n',
                     '    logdir = /var/log/puppet\n',
                     '    rundir = /var/run/puppet\n',
                     '    ssldir = $vardir/ssl\n',
                     '    factpath=$vardir/lib/facter\n',
                     '    pluginsync=true\n',
                     '[agent]\n',
                     '    environment = ' + self.opts['env'] + '\n',
                     '    classfile = $vardir/classes.txt\n',
                     '    localconfig = $vardir/localconfig\n',
                     '    report = true\n',
                    ]
            open(puppet_f, 'w+').writelines(lines)


    def gen_ssh(self):
        '''
        Generates initial ssh keys for the host
        '''
        keydir = os.path.join(self.over, 'etc/ssh')
        if not os.path.exists(keydir):
            os.makedirs(keydir)
        keys = [os.path.join(keydir, 'ssh_host_key'),
                os.path.join(keydir, 'ssh_host_rsa_key'),
                os.path.join(keydir, 'ssh_host_dsa_key')
               ]
        cmds = ['ssh-keygen -f ' + keydir + '/ssh_host_key -t rsa1 -C ' + self.opts['name']  + ' -N ""',
                'ssh-keygen -f ' + keydir + '/ssh_host_rsa_key -t rsa -C ' + self.opts['name'] + ' -N ""',
                'ssh-keygen -f ' + keydir + '/ssh_host_dsa_key -t dsa -C ' + self.opts['name'] + ' -N ""'
               ]
        for cmdi in range(0, len(cmds)):
            if os.path.exists(keys[cmdi]):
                continue
            subprocess.call(cmds[cmdi], shell=True)

    def gen_dhcp(self):
        '''
        Generate all the DHCP configs for dnsmasq
        '''
        fn_ = os.path.join(self.opts['dhcp_dir'],
                self.opts['name'] + '.conf')
        if os.path.exists(fn_):
            return False
        configs = []
        for mac in self.opts['macs']:
            configs.append("dhcp-host=net:%s,%s,%s,2h"%(mac,
                self.opts['macs'][mac],
                self.opts['name']))
        configs.append("")
        configs = os.linesep.join(configs)

        open(fn_, 'w+').writelines(configs)
        
        return True

    def setup_rc_local(self):
        '''
        Prepares the Ubuntu rc.local file to run puppet
        '''
        rc = os.path.join(self.over, 'etc/rc.local')
        if not os.path.isdir(os.path.dirname(rc)):
            os.makedirs(os.path.dirname(rc))
        lines = [
                'sed -i s/START=no/START=yes/ /etc/default/puppet\n',
                'service puppet stop\n',
                'sleep 20\n',
                'service puppet start\n',
                ]
        open(rc, 'w+').writelines(lines)
        os.chmod(rc, 493)

    def setup_overlay(self):
        '''
        Run the sequence that sets up the overlay
        '''
        # Run distro dependent overlay here
        if self.opts['distro'] == 'ubuntu':
            self.setup_rc_local()
        elif self.opts['distro'] == 'arch':
            pass
        self.gen_puppet()
        self.gen_ssh()
        if self.opts['env']:
            self.set_env()
        if self.gen_dhcp():
            print 'Fresh dnsmasq config generated, restarting...'
            r_cmd = 'service dnsmasq restart'
            subprocess.call(r_cmd, shell=True)

    def purge_overlay(self):
        '''
        Delete the old overlay files for a vm
        '''
        if not self.opts['force']:
            print 'This action will recursively destroy the virtual machine'\
                    + ' overlay and certificates, you better be darn sure you'\
                    + ' know what you are doing!!'
            conf = raw_input('Please enter yes or no [yes/No]: ')
            if not conf.strip() == 'yes':
                return
        dhcp = os.path.join(self.opts['dhcp_dir'],
                self.opts['name'] + '.conf')
        func = os.path.join(self.opts['func_certs'],
                self.opts['fqdn'] + '.cert')
        if os.path.isdir(self.over):
            shutil.rmtree(self.over)
        if os.path.isfile(dhcp):
            os.remove(dhcp)
        if os.path.isfile(func):
            os.remove(func)
        ca_cmd = 'puppetca --clean ' + self.opts['fqdn']
        subprocess.call(ca_cmd, shell=True)
