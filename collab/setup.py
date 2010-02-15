# -*- coding: utf-8 -*-
from distutils.core import setup

setup(name='collab', version='$Rev$',
      author='Marko Laakso, Jani Kenttälä',
      author_email='contact@clarifiednetworks.com',
      description='Collab Backend',
      scripts=[ 'scripts/collab-archive',
        'scripts/collab-account-collablist',
        'scripts/collab-account-create',
        'scripts/collab-account-password',
        'scripts/collab-htaccess',
        'scripts/collab-htpasswd'])
