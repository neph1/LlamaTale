"""
This __main__.py file is used to make it very easy to launch stories as a zip file.
If you zip up the story's directory as "story.zip", you can then simply:

    $ python story.zip

to launch the game. (as long as you have Tale installed)
"""

from __future__ import print_function
import os
import sys

if sys.version_info < (3, 5):
    raise SystemExit("You have to use Python 3.5 or newer to run this. (current version: %s %s)" %
                     (sys.executable, ".".join(str(v) for v in sys.version_info[:3])))

tale_error = None
try:
    import tale
    tale._check_required_libraries()
    import tale.main
    from packaging.version import Version
    if Version(tale.__version__) < Version("{required_tale_version}"):
        print("Tale version installed:", tale.__version__, file=sys.stderr)
        print("Tale version required : {required_tale_version}", file=sys.stderr)
        tale_error = "installed Tale library version too old"
except ImportError as x:
    tale_error = str(x)

if tale_error:
    print("Error loading Tale: ", tale_error, file=sys.stderr)
    print("To run this game you have to install a recent enough Tale library.\n"
          "Running the command 'pip install --upgrade tale' usually fixes this.\n", file=sys.stderr)
    print("Enter to exit: ", file=sys.stderr)
    input()
    raise SystemExit


# insert path to this game and any necessary command line options (edit these if needed)
gamelocation = sys.path[0] or os.path.dirname(__file__)
args = ["--game", gamelocation, "--mode", "{gamemode}"] + sys.argv[1:]

# start the game
tale.main.run_from_cmdline(args)
