'''
Executes hypeervisor side clay calls
'''

# Import python modules
import os
import subprocess
import copy
import shutil

# Import func module(s)
import func_module

class ClayVM(func_module.FuncModule):
    '''
    Contains all of the hypervisor side clay commands
    '''
    version = "0.0.1"
    api_version = "0.0.2"
    description = "Contains all of the hypervisor side clay commands"

    def hyper_data(self):
        '''
        Returns information about the hypervisor
        '''
        h_data = {}
        if os.path.exists('/etc/arch-release'):
            h_data['distro'] = 'Arch'
        elif os.path.exists('/etc/ubuntu-release'):
            h_data['distro'] = 'Ubuntu'
        
        if os.path.exists('/usr/bin/guestfish'):
            h_data['guestfish'] = True
        else:
            h_data['guestfish'] = False

        if os.path.isfile('/etc/libvirt/qemu.conf'):
            for line in open('/etc/libvirt/qemu.conf').readlines():
                if line.startswith('user'):
                    h_data['user'] = line.split('=')[1].strip().strip('"')
                    if h_data.has_key('group'):
                        break
                    continue
                if line.startswith('group'):
                    h_data['group'] = line.split('=')[1].strip().strip('"')
                    if h_data.has_key('user'):
                        break
                    continue
            if not h_data.has_key('user'):
                h_data['user'] = 'root'
            if not h_data.has_key('group'):
                h_data['group'] = 'root'

        return h_data

    def start_vm(self):
        '''
        Execute the libvirt call to start the virtual machine.
        '''
        pass

    def apply_overlay(self):
        '''
        If guestfish is available apply the overlay image
        '''
        pass

    def get_block_paths(self, name):
        '''
        Returns a list of block devices for the named virtual machine
        '''
        # be advised, changes in libvirt could make this function not operate
        # properly, and updates may need to be applied in the future
        q_cmd = 'virsh dumpxml ' + name + ' | grep file= | cut -d"\'" -f2'
        files = subprocess.Popen(q_cmd,
                shell=True,
                stdout=subprocess.PIPE).communicate()[0].split()
        return files

    def get_blocks_data(self, name):
        '''
        Returns a structure containing information about the block devices used
        on a named vm.
        '''
        blocks = []
        mfs = self.get_mfs_mounts()
        files = self.get_block_paths(name)
        for fn_ in files:
            block = {}
            block['path'] = fn_
            block['local'] = True
            
            for mnt in mfs:
                if fn_.startswith(mnt):
                    block['local'] = False
            
            q_cmd = "qemu-img info " + fn_  + " | grep virtual | "\
                  + "awk '{print $3}'"
            block['size'] = subprocess.Popen(q_cmd,
                    shell=True,
                    stdout=subprocess.PIPE).communicate()[0].strip()

            q_cmd = "qemu-img info " + fn_  + " | grep format | "\
                  + "awk '{print $3}'"
            block['format'] = subprocess.Popen(q_cmd,
                    shell=True,
                    stdout=subprocess.PIPE).communicate()[0].strip()

            fn_base = os.path.basename(fn_)
            if fn_base.startswith('disk') or fn_base.startswith('vda'):
                block['dev'] = 'vda'
            else:
                block['dev'] = fn_base.split('.')[0]
            blocks.append(block)
        return blocks

    def check_fit(self, vda, path):
        '''
        Returns a bool, true if there is enough space on the device to add the
        image, and false otherwise, pass the image which is being coppied into
        place and the path where the image is being coppied to.
        '''
        if os.path.isfile(path):
            path = os.path.dirname(path)
        a_cmd = "df --block-size M " + path + " | grep -v Filesystem | awk '{print $4}'"
        n_cmd = "ls -l --block-size M " + vda + " | grep -v Filesystem | awk '{print $4}'"
        avail = int(subprocess.Popen(a_cmd,
                shell=True,
                stdout=subprocess.PIPE).communicate()[0].strip()[:-1])
        need = int(subprocess.Popen(n_cmd,
                shell=True,
                stdout=subprocess.PIPE).communicate()[0].strip()[:-1])
        need = int(need + (need/2))
        if avail > need:
            return True
        else:
            return False

    def set_migrate_seed(self, seed_vda, blocks):
        '''
        Look at the block devices used by the virtual machine that we need to
        migrate onto this node. Prepare the blocks for the migration.
        '''
        user, group = self.get_user_group()
        for block in blocks:
            if os.path.exists(block['path']):
                continue
            dirname = os.path.dirname(block['path'])
            if not os.path.isdir(os.path.dirname(block['path'])):
                os.makedirs(dirname)
                tdir = copy.deepcopy(dirname)
                while not tdir == '/':
                    os.chmod(tdir, 493)
                    tdir = os.path.dirname(tdir)
            if block['dev'] == 'vda':
                q_cmd = "qemu-img info " + seed_vda  + " | grep virtual | "\
                      + "awk '{print $3}'"
                seed_size = subprocess.Popen(q_cmd,
                        shell=True,
                        stdout=subprocess.PIPE).communicate()[0].strip()
                if seed_size != block['size']:
                    return False
                shutil.copy(seed_vda, block['path'])
            else:
                q_cmd = 'qemu-img create -f ' + block['format']\
                      + ' ' + block['path'] + ' ' + block['size']
                subprocess.call(q_cmd, shell=True)
            ch_cmd = 'chown ' + user + ':' + group + ' ' + block['path']
            subprocess.call(ch_cmd, shell=True)
            return True

    def get_mfs_mounts(self):
        '''
        Returns a list of the directories locally mounted via MooseFS
        '''
        cmd = "mount | grep fuse.mfs | awk '{print $3}'"
        return subprocess.Popen(cmd,
                shell=True,
                stdout=subprocess.PIPE).communicate()[0].split()

    def get_user_group(self):
        '''
        Returns the user and group that the disk images should be owned by
        '''
        g_cmd = 'grep group /etc/libvirt/qemu.conf'
        u_cmd = 'grep user /etc/libvirt/qemu.conf'
        group = subprocess.Popen(g_cmd,
                shell=True,
                stdout=subprocess.PIPE).communicate()[0].split('"')[1]
        user = subprocess.Popen(u_cmd,
                shell=True,
                stdout=subprocess.PIPE).communicate()[0].split('"')[1]
        return (user, group)

    def purge(self, name):
        '''
        Purge the vm from the hypervisor, this ensures that all disk images are
        removed.
        '''
        files = self.get_block_paths(name)
        d_cmd = 'virsh destroy ' + name
        subprocess.call(d_cmd, shell=True)
        for fn_ in files:
            if os.path.isfile(fn_):
                os.remove(fn_)
            try:
                os.rmdir(os.path.dirname(fn_))
            except OSError:
                pass

    def gen_pin_image(self, pins, name, group, user):
        '''
        Generate the "pinned" vm image
        '''
        for pin in pins:
            dirname = os.path.dirname(pin['path'])
            if os.path.exists(pin['path']):
                continue
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
                tdir = copy.deepcopy(dirname)
                while not tdir == '/':
                    os.chmod(tdir, 493)
                    tdir = os.path.dirname(tdir)

            i_cmd = 'qemu-img create ' + pin['path'] + ' ' + pin['size'] + 'G'
            f_cmd = 'yes | mkfs.' + pin['filesystem'] + ' ' + pin['path']
            ch_cmd = 'chown ' + user + ':' + group + ' ' + pin['path']
            subprocess.call(i_cmd, shell=True)
            subprocess.call(f_cmd, shell=True)
            if pin['filesystem'].startswith('ext'):
                t_cmd = 'tune2fs -c 0 -i 0 ' + pin['filesystem']
                subprocess.call(t_cmd, shell=True)
            if pin['format'] == 'qcow2':
                q_cmd = 'qemu-img convert -O qcow2 ' + pin['path'] + ' '\
                      + pin['path'] + '.tmp'
                subprocess.call(q_cmd, shell=True)
                shutil.move(pin['path'] + '.tmp', pin['path'])
            subprocess.call(ch_cmd, shell=True)
        return True

    def set_rpp(self, vda, rpp):
        '''
        Move the image file into place on the pinned hypervisor
        '''
        if os.path.exists(rpp):
            return False
        dirname = os.path.dirname(rpp)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
            tdir = copy.deepcopy(dirname)
            while not tdir == '/':
                os.chmod(tdir, 493)
                tdir = os.path.dirname(tdir)

        shutil.move(vda, rpp)
