"""
The actual mudlib 'world' code

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
from pkg_resources import parse_version
import sys
from typing import Any


__version__ = "4.7"


class _MudContext:
    driver = None       # type: Any
    config = None       # type: Any
    resources = None    # type: Any


# The mud_context is a global container for the following attributes,
# that will be set (by the driver) to the correct initialized instances:
#  - driver   (driver)
#  - config   (story config)
#  - resources  (story's file resources, just a shortcut to driver.resources)
mud_context = _MudContext()


def _check_required_libraries():
    try:
        import appdirs
    except ImportError:
        appdirs = None
    try:
        import colorama
    except ImportError:
        colorama = None
    try:
        import smartypants
    except ImportError:
        smartypants = None
    try:
        import serpent
    except ImportError:
        serpent = None
    all_good = True
    smartypants_version_required = parse_version("1.8.6")
    colorama_version_required = parse_version("0.3.6")
    serpent_version_required = parse_version("1.23")
    # Note: prompt_toolkit is a nice to have, but it is not required. We do install it if other libs are missing though.
    if not appdirs:
        print("The 'appdirs' Python library (any recent version) is required to run Tale.", file=sys.stderr)
        all_good = False
    if not colorama or parse_version(colorama.__version__) < colorama_version_required:
        print("The 'colorama' Python library (version >= {}) is required to run Tale."
              .format(colorama_version_required), file=sys.stderr)
        all_good = False
    if not smartypants or parse_version(smartypants.__version__) < smartypants_version_required:
        print("The 'smartypants' Python library (version >= {}) is required to run Tale."
              .format(smartypants_version_required), file=sys.stderr)
        all_good = False
    if not serpent or parse_version(serpent.__version__) < serpent_version_required:
        print("The 'serpent' Python library (version >= {}) is required to run Tale."
              .format(serpent_version_required), file=sys.stderr)
        all_good = False
    if not all_good:
        print("\nInstall this/these and try again. Try using your package manager (on Linux) or try executing the following command:")
        print('  pip install "appdirs" "prompt-toolkit" "smartypants>={spv}" "colorama>={cv}" "serpent>={sv}"'
              .format(spv=smartypants_version_required, cv=colorama_version_required, sv=serpent_version_required))
        print("(you may have to add the --user option if you have insufficient privileges)")
        choice = input("\nDo you want to attempt to install them (using pip) right now (y/n)? ")
        if choice == 'y':
            import pip
            # we don't use "--user" here because then it won't work when using a virtualenv.
            statuscode = pip.main(["install", "appdirs", "prompt-toolkit", "smartypants>=" + str(smartypants_version_required),
                                   "colorama>=" + str(colorama_version_required), "serpent>=" + str(serpent_version_required)])
            if statuscode:
                print("\n\nInstallation failed.\n")
                raise SystemExit(statuscode)
            else:
                print("\n\nInstallation finished, try to run me again now.\n")
        raise SystemExit
