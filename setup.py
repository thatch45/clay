#!/usr/bin/python2

from distutils.core import setup

setup(name='clay',
      version='0.7',
      description='Frontend to manage complex operations made by func',
      author='Thomas S Hatch',
      author_email='thatch@beyondoblivion.com',
      url='http://beyondoblivion.com',
      packages=['clay'],
      scripts=['scripts/clay-vm',
                'scripts/clayd'],
    data_files=[('/etc/clay',
                    ['conf/clay.conf',
                    ]),
                ('/etc/rc.d/',
                    ['init/clayd',
                    ]),
                 ],

     )
