"""
Main startup class

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import argparse
import sys
import traceback
from typing import Sequence

from . import __version__
from .tio import DEFAULT_SCREEN_DELAY
from .story import GameMode
from .driver import Driver

stored_args = None

def run_from_cmdline(cmdline: Sequence[str]) -> None:
    """Run Tale from the commandline."""
    parser = argparse.ArgumentParser(description="""
        Tale framework %s game driver. Use this to launch a game and specify some settings.
        Sometimes the game will provide its own startup script that invokes this automatically.
        If it doesn't, refer to the options to see how to launch it manually instead.
        """ % __version__)
    parser.add_argument('-g', '--game', type=str, help='path to the game directory', required=True)
    parser.add_argument('-d', '--delay', type=int, help='screen output delay for IF mode (milliseconds, 0=no delay)',
                        default=DEFAULT_SCREEN_DELAY)
    parser.add_argument('-m', '--mode', type=str, help='game mode, default=if', default="if", choices=["if", "mud"])
    parser.add_argument('-i', '--gui', help='gui interface', action='store_true')
    parser.add_argument('-w', '--web', help='web browser interface', action='store_true')
    parser.add_argument('-r', '--restricted', help='restricted mud mode; do not allow new players', action='store_true')
    parser.add_argument('-z', '--wizard', help='force wizard mode on if story character (for debug purposes)', action='store_true')
    parser.add_argument('-c', '--character', help='load a v2 character card as player (skips character builder)')
    args = parser.parse_args(cmdline)
    vargs = vars(args)
    global stored_args
    stored_args = vargs
    run_game(vargs)

def run_game(vargs) -> None:
    """Run the game."""
    try:
        # select the correct driver type, configure it, and start the story.
        game_mode = GameMode(vargs.get('mode', 'if'))
        if game_mode == GameMode.IF:
            from .driver_if import IFDriver
            driver = IFDriver(
                screen_delay=vargs.get('delay', DEFAULT_SCREEN_DELAY),
                gui=vargs.get('gui', False),
                web=vargs.get('web', False),
                wizard_override=vargs.get('wizard', False),
                character_to_load=vargs.get('character')
            )   # type: Driver
        elif game_mode == GameMode.MUD:
            from .driver_mud import MudDriver
            driver = MudDriver(vargs.get('restricted', False))
        else:
            raise ValueError("invalid game mode")
        driver.start(vargs.get('game', '.'))
    except:
        if vargs.get('gui', False):
            tb = traceback.format_exc()
            from .tio import tkinter_io
            tkinter_io.show_error_dialog("Exception during start", "An error occurred while starting up the game:\n\n" + tb)
        raise

def restart_game(game: str) -> None:
    """Restart the game."""
    del sys.modules["story"]
    args = dict()
    args['game'] = game
    args['delay'] = DEFAULT_SCREEN_DELAY
    args['mode'] = "if"
    args['gui'] = False
    args['web'] = False
    args['restricted'] = False
    args['wizard'] = True
    run_game(args)

if __name__ == "__main__":
    run_from_cmdline(sys.argv[1:])
