'''
Frontend for running vm migration
'''
# import clay libs
import clay.data
import clay.create
import clay.pin

# import func libs
import func.overlord.client as fc

class Migrate(object):
    '''
    Used to manage virtual machine live migration
    '''
    def __init__(self, opts):
        self.opts = opts
        self.pin = clay.pin.Pin(opts)
        self.data = clay.data.HVStat()

    def run_logic(self):
        '''
        Read the opts structure and determine how to execute
        '''
        if self.opts['clear_node']:
            self.clear_node()
        else:
            self.migrate()

    def migrate(self, name=''):
        '''
        Migrate a virtual machine to the specified destoination.
        '''
        if not name and self.opts['name']:
            name = self.opts['name']
        else:
            raise ValueError('Attemting to migrate without a vm name')
        
        m_data = self.data.migration_data(name, self.opts['hyper'])

        src = fc.Overlord(m_data['from'], timeout=7200)
        tgt = fc.Overlord(m_data['to'])

        # retrive the information about blocks on the vm
        blocks = src.clayvm.get_blocks_data(name)[m_data['from']]
        # Prepare the target hyper to have the correct block devices
        tgt.clayvm.set_migrate_seed(
                clay.create.find_image(self.opts['pool'], self.opts['distro']),
                blocks)

        # execute migration
        print 'Migrating ' + name + ' from ' + m_data['from'] + ' to '\
              + m_data['to'] + '. Be advised that some migrations can take on'\
              + ' the order of hours to complete, and clay will block,'\
              + ' waiting for completion.'
        m_cmd = 'virsh migrate --live --copy-storage-inc ' + name\
              + ' qemu://' + m_data['to'] + '/system'
        print 'Migration command:\n' + m_cmd
        m_ret = src.command.run(m_cmd)
        tgt_vinfo = tgt.virt.info()
        up = False
        for host in tgt_vinfo:
            if tgt_vinfo[host].has_key(self.opts['name']):
                up = True
        if not up:
            # Failed to migrate
            print 'Problems occured in the migration of ' + self.opts['name']\
                + ' Please inspect the systems manually.'
            print m_ret
            return False
        # The migration stated, make sure it finished
        src_vinfo = src.virt.info()
        for host in src_vinfo:
            if src_info[host].has_key(self.opts['name']):
                # Migration is still in progress
                print 'The migration is still in progress or has stalled,'\
                    + ' please manually verify the migration status and clean'\
                    + ' up old files off of the source hypervisor if they'\
                    + ' apply'
                print m_ret
                return False

        # Clean up the vm disks left behind after the migration is complete
        for block in blocks:
            if block['local']:
                rm_cmd = 'rm -rf ' + os.path.dirname(block['path'])
                src.command.run(rm_cmd)
                self.pin.set_pin_data(m_data['to'])

        print 'Migration complete'

        return True

        print 'Finished migrating ' + name

    def clear_node(self):
        '''
        This method will migrate all of the non-pinned virtual machines off a
        node.
        '''
        if not self.opts['clear_node']:
            raise ValueError('Please specify the node to clear with'\
                + ' --clear-node=<nodename>')
        print 'Retriving initial migration information'
        resources = self.data.resources()
        if not resources.has_key(self.opts['clean_node']):
            raise ValueError('Specified node to migrate all vms off of is'\
                + ' not present')
        for vm_ in resources[self.opts['clean_node']]['vms']:
            self.migrate(vm_)
