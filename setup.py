import os
from babel.messages import frontend as babel
from distutils import cmd
from distutils.command.install_data import install_data as _install_data
from distutils.command.build import build as _build
from setuptools import setup
from copy import copy

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

message_extractors = {'tune': [
        ('**.py', 'python', None)]
        }


    
# Link tune.py to tune
if not os.path.exists("tune/tune"):
    os.symlink(os.path.abspath("tune/tune.py"), "tune/tune")

langs = [l[:-3] for l in os.listdir('po') if l.endswith('.po')
                                          and l != "messages.po"]

mofiles = [('share/locale/%s/LC_MESSAGES' % lang, ['build/mo/%s/tune.mo' % lang]) for lang in langs]

class BuildPofiles(cmd.Command):
    def initialize_options(self): pass
    def finalize_options(self): pass
    def run(self):
        # Create mo files:
        if not os.path.exists("build/mo/"):
            os.mkdir("build/mo/")
        for lang in langs:
            pofile = os.path.join("po", "%s.po" % lang)
            modir = os.path.join("build", "mo", lang)
            mofile = os.path.join(modir, "tune.mo")
            if not os.path.exists(modir):
                os.mkdir(modir)
            print "generating", mofile
            os.system("msgfmt --statistics %s -o %s" % (pofile, mofile))

class build(_build):
    sub_commands = _build.sub_commands + [('build_pofiles', None)]
    def run(self):
        _build.run(self)


setup(
    name = "mpd-tune",
    version = "0.1",
    author = "Rafal Macyszyn",
    author_email = "chommik12@gmail.com",
    description = ("Easily find and tune a song in MPD playlist"),
    
    cmdclass = {'build': build,
                'compile_catalog': babel.compile_catalog,
                'extract_messages': babel.extract_messages,
                'init_catalog': babel.init_catalog,
                'update_catalog': babel.update_catalog,
                'build_pofiles': BuildPofiles},
    
    data_files = mofiles,
      
    license = "ISC",
    url = "http://github.com/chommik/mpd-tune",
    packages = ['tune'],
    package_dir = {"tune": "tune/"},
    scripts = ["tune/tune"],
    
    long_description=read('README'),
)