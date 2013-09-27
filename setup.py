#!/usr/bin/env python

from distutils.core import setup

setup(name='smartforge',
      version='0.1',
      description='SmartForge',
      author='FELD Boris',
      author_email='lothiraldan@gmail.com',
      packages=['smartforge', 'smartforge.bin', 'smartforge.services', 'smartforge.ui'],
      package_data={
        'smartforge.ui': ['smartforge/ui/templates/*', 'smartforge/ui/static/*']
      }
     )
