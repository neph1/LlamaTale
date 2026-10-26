"""
Setup script for distutils

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import re
from setuptools import setup

with open("tale/__init__.py") as version_file:
    # extract the VERSION definition from the tale package without importing it
    version_line = next(line for line in version_file if line.startswith("__version__"))
    tale_version = re.match(r"__version__\s?=\s?['\"](.+)['\"]", version_line).group(1)

print("version=" + tale_version)

setup(
    name='tale',
    version=tale_version,
    url='http://tale.readthedocs.io/',
    author='Irmen de Jong',
    author_email='irmen@razorvine.net',
    license="LGPL3",
    description='Interactive Fiction, MUD & mudlib framework',
    long_description="""Tale is a framework for creating interactive fiction (text adventures), or MUDs (multi-user dungeons).

It's still being developed and new features are implement along the way,
but the current version is quite capable of running an interactive fiction story world.
Also the basics for a multi-user (MUD) server are working nicely.

An example test/demo story is included in the ``stories`` directory of the distribution archive.
This will require you to extract the source archive manually.

You can also run the tiny embedded test story like this, after you've installed the framework::

    $ python -m tale.demo.story

The source code repository is on Github: https://github.com/irmen/Tale
""",
    packages=['tale', 'tale.cmds', 'tale.items', 'tale.tio', 'tale.demo', 'tale.demo.zones', 'tale.web'],
    package_data={
        'tale': ['soul_adverbs.txt'],
        'tale.web': ['*']
    },
    include_package_data=True,
    keywords="mud, mudlib, interactive fiction, text adventure",
    scripts=["scripts/tale-run.cmd", "scripts/tale-run"],
    platforms="any",
    zip_safe=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Communications :: Chat",
        "Topic :: Games/Entertainment",
        "Topic :: Games/Entertainment :: Role-Playing",
        "Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)"
    ],
    install_requires=["appdirs", "colorama>=0.3.6", "smartypants>=1.8.6", "serpent>=1.23"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    options={"install": {"optimize": 0}},
    test_suite="tests"
)
