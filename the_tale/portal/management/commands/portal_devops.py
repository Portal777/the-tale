# coding: utf-8

import subprocess

from optparse import make_option

from django.core.management.base import BaseCommand

from meta_config import meta_config

FABFILE = '/home/tie/repos/mine/devops/the_tale'
SETUP_HOST = "root@the-tale.org"
UPDATE_HOST = "the-tale@the-tale.org"

class Command(BaseCommand):

    help = 'devops commands'

    requires_model_validation = False

    option_list = BaseCommand.option_list + ( make_option('-c', '--command',
                                                          action='store',
                                                          type=str,
                                                          dest='command',
                                                          help='command'),
                                            )


    def handle(self, *args, **options):

        command = options['command']

        if command == 'setup':
            subprocess.call(['fab', '-f', FABFILE, 'setup:host=%s' % SETUP_HOST])

        elif command == 'update':
            subprocess.call(['fab', '-f', FABFILE, 'update:static_data_version=%s,host=%s' % (meta_config.static_data_version, UPDATE_HOST)])
        else:

            print 'unknown command'