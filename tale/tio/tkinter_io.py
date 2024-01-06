"""
GUI input/output using Tkinter.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import collections
import re
import sys
import textwrap
import threading
import tkinter
import tkinter.font
import tkinter.messagebox
from typing import Sequence, Tuple, Any, Optional

from . import iobase
from .. import vfs
from .. import __version__ as tale_version
from .. import mud_context
from ..util import format_traceback

__all__ = ["TkinterIo"]


# note: mypy doesn't deal with tkinter very well (complains about tkinter.font not existing and lots of other things)
# so this module doesn't contain any tkinter type hints because they're a royal pain or require lots of @no_type_check  decorations.


class TkinterIo(iobase.IoAdapterBase):
    """
    Tkinter-GUI based Input/Output adapter.
    """
    def __init__(self, config, player_connection) -> None:
        super().__init__(player_connection)
        self.gui = TaleGUI(self, config)
        self.textwrapper = textwrap.TextWrapper()

    def singleplayer_mainloop(self, player_connection) -> None:
        """Main event loop for this I/O adapter for single player mode"""
        self.gui.mainloop(player_connection)

    def pause(self, unpause: bool=False) -> None:
        self.gui.pause(unpause)

    def clear_screen(self) -> None:
        """Clear the screen"""
        self.gui.clear_screen()

    def critical_error(self, message: str="A critical error occurred! See below and/or in the error log.") -> None:
        """called when the driver encountered a critical error and the session needs to shut down"""
        super().critical_error(message)
        tb = "".join(format_traceback())
        self.output("<monospaced>" + tb + "</>")
        self.output("<rev><it>Please report this problem.</>\n")

    def destroy(self) -> None:
        self.gui.destroy()

    def gui_terminated(self) -> None:
        self.gui = None     # type: ignore

    def abort_all_input(self, player) -> None:
        """abort any blocking input, if at all possible"""
        player.store_input_line("")

    def render_output(self, paragraphs: Sequence[Tuple[str, bool]], **params: Any) -> str:
        """
        Render (format) the given paragraphs to a text representation.
        It doesn't output anything to the screen yet; it just returns the text string.
        Any style-tags are still embedded in the text.
        This tkinter-implementation expects no extra parameters.
        """
        if not paragraphs:
            return ""
        output = []
        for txt, formatted in paragraphs:
            if formatted:
                # formatted output, munge whitespace (like the console text output does)
                txt = self.textwrapper._munge_whitespace(txt) + "\n"
            else:
                # unformatted paragraph, just leave the text as-is (don't textwrap it)
                txt = "<monospaced>" + txt + "</monospaced>\n"
            assert txt.endswith("\n")
            output.append(txt)
        return self.smartquotes("".join(output))

    def output(self, *lines: str) -> None:
        """Write some text to the screen. Needs to take care of style tags that are embedded."""
        super().output(*lines)
        for line in lines:
            self.gui.write_line(line)

    def output_no_newline(self, text: str, new_paragraph = True) -> None:
        """Like output, but just writes a single line, without end-of-line."""
        super().output_no_newline(text, new_paragraph)
        self.gui.write_line(text)


class TaleWindow(tkinter.Toplevel):
    """The actual gui-window, containing the output text and the input command bar."""

    def __init__(self, gui, parent, title, text, modal=False):
        super().__init__(parent)
        self.gui = gui
        self.configure(borderwidth=5)
        self.geometry("=%dx%d+%d+%d" % (800, 600, parent.winfo_rootx() + 10, parent.winfo_rooty() + 10))
        self.bg = '#f8f8f0'
        self.fg = '#080808'
        self.fontsize_monospace = 11
        self.fontsize_normal = 11
        if sys.platform == "darwin":
            self.fontsize_monospace += 3
            self.fontsize_normal += 5
        self.font = self.findfont(['Georgia', 'DejaVu Serif', 'Droid Serif', 'Times New Roman', 'Times', 'Serif'],
                                  self.fontsize_normal)
        self.boldFont = self.findfont(['Georgia', 'DejaVu Serif', 'Droid Serif', 'Times New Roman', 'Times', 'Serif'],
                                      self.fontsize_normal, weight=tkinter.font.BOLD)
        self.italicFont = self.findfont(['Georgia', 'DejaVu Serif', 'Droid Serif', 'Times New Roman', 'Times', 'Serif'],
                                        self.fontsize_normal, slant="italic")
        self.underlinedFont = self.findfont(['Georgia', 'DejaVu Serif', 'Droid Serif', 'Times New Roman', 'Times', 'Serif'],
                                            self.fontsize_normal, underlined=True)
        self.createwidgets()
        self.title(title)
        self.protocol("WM_DELETE_WINDOW", self.quit_button_clicked)
        self.parent = parent
        self.textView.focus_set()
        # key bindings for this dialog
        # self.bind('<Return>',self.Ok) #dismiss dialog
        # self.bind('<Escape>',self.Ok) #dismiss dialog
        self.textView.insert(0.0, text)
        self.textView.config(state=tkinter.DISABLED)
        try:
            img = tkinter.PhotoImage(data=vfs.internal_resources["tio/quill_pen_paper.gif"].data)
        except tkinter.TclError:
            pass  # older versions of Tkinter can't create an image from data bytes, don't bother then
        else:
            self.wm_iconphoto(self, img)
            if sys.platform == "win32":
                # tell windows to use a new toolbar icon
                import ctypes
                myappid = 'net.Razorvine.Tale.story'  # arbitrary string
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.history = collections.deque(maxlen=100)
        self.history.append("")
        self.history_idx = 0
        if modal:
            self.transient(parent)
            self.grab_set()
            self.wait_window()
        self.update_lock = threading.Lock()

    def createwidgets(self):
        frameText = tkinter.Frame(self, relief=tkinter.SUNKEN, height=700)
        frameCommands = tkinter.Frame(self, relief=tkinter.SUNKEN)
        self.scrollbarView = tkinter.Scrollbar(frameText, orient=tkinter.VERTICAL, takefocus=tkinter.FALSE, highlightthickness=0)
        self.textView = tkinter.Text(frameText, wrap=tkinter.WORD, highlightthickness=0,
                                     fg=self.fg, bg=self.bg, font=self.font, padx=8, pady=8)
        self.scrollbarView.config(command=self.textView.yview)
        self.textView.config(yscrollcommand=self.scrollbarView.set)
        self.commandPrompt = tkinter.Label(frameCommands, text="> ")
        fixedFont = self.findfont(["Consolas", "Lucida Console", "DejaVu Sans Mono"], self.fontsize_monospace)
        if not fixedFont:
            fixedFont = tkinter.font.nametofont('TkFixedFont').copy()
            fixedFont["size"] = self.fontsize_monospace
        self.commandEntry = tkinter.Entry(frameCommands, takefocus=tkinter.TRUE, font=fixedFont)
        self.commandEntry.bind('<Return>', self.user_cmd)
        self.commandEntry.bind('<Extended-Return>', self.user_cmd)
        self.commandEntry.bind('<KP_Enter>', self.user_cmd)
        self.commandEntry.bind('<F1>', self.f1_pressed)
        self.commandEntry.bind('<Up>', self.up_pressed)
        self.commandEntry.bind('<Down>', self.down_pressed)
        self.scrollbarView.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        self.textView.pack(side=tkinter.LEFT, expand=tkinter.TRUE, fill=tkinter.BOTH)
        # configure the text tags
        self.textView.tag_configure('userinput', font=fixedFont, foreground='maroon',
                                    spacing1=10, spacing3=4, lmargin1=20, lmargin2=20, rmargin=20)
        self.textView.tag_configure('dim', foreground='brown')
        self.textView.tag_configure('bright', foreground='dark green', font=self.boldFont)
        self.textView.tag_configure('ul', font=self.underlinedFont)
        self.textView.tag_configure('it', font=self.italicFont)
        self.textView.tag_configure('rev', foreground=self.bg, background=self.fg)
        self.textView.tag_configure('living', font=self.boldFont)
        self.textView.tag_configure('player', font=self.boldFont)
        self.textView.tag_configure('item', font=self.boldFont)
        self.textView.tag_configure('exit', font=self.boldFont)
        self.textView.tag_configure('location', foreground='navy', font=self.boldFont)
        self.textView.tag_configure('monospaced', font=fixedFont)
        # pack
        self.commandPrompt.pack(side=tkinter.LEFT)
        self.commandEntry.pack(side=tkinter.LEFT, expand=tkinter.TRUE, fill=tkinter.X, ipady=1)
        frameText.pack(side=tkinter.TOP, expand=tkinter.TRUE, fill=tkinter.BOTH)
        frameCommands.pack(side=tkinter.BOTTOM, fill=tkinter.X)
        self.commandEntry.focus_set()

    def findfont(self, families, size, weight=tkinter.font.NORMAL, slant=tkinter.font.ROMAN, underlined=False):
        fontfamilies = tkinter.font.families()
        for family in families:
            if family in fontfamilies:
                return tkinter.font.Font(family=family, size=size, weight=weight, slant=slant, underline=underlined)
        return None

    def f1_pressed(self, e):
        self.commandEntry.delete(0, tkinter.END)
        self.commandEntry.insert(0, "help")
        self.commandEntry.event_generate("<Return>")

    def up_pressed(self, e):
        self.history_idx = max(0, self.history_idx - 1)
        if self.history_idx < len(self.history):
            self.commandEntry.delete(0, tkinter.END)
            self.commandEntry.insert(0, self.history[self.history_idx])

    def down_pressed(self, e):
        self.history_idx = min(len(self.history) - 1, self.history_idx + 1)
        if self.history_idx < len(self.history):
            self.commandEntry.delete(0, tkinter.END)
            self.commandEntry.insert(0, self.history[self.history_idx])

    def user_cmd(self, e):
        cmd = self.commandEntry.get().strip()
        if cmd:
            self.write_line("", self.gui.io.do_styles)
            self.write_line("<userinput>%s</>" % cmd, True)
        self.gui.register_cmd(cmd)
        self.commandEntry.delete(0, tkinter.END)
        if cmd:
            if cmd != self.history[-1]:
                self.history.append(cmd)
            self.history_idx = len(self.history)

    def clear_text(self):
        with self.update_lock:
            self.textView.config(state=tkinter.NORMAL)
            self.textView.delete(1.0, tkinter.END)
            self.textView.config(state=tkinter.DISABLED)

    def write_line(self, line, do_styles):
        with self.update_lock:
            if do_styles:
                words = re.split(r"(<\S+?>)", line)
                self.textView.config(state=tkinter.NORMAL)
                tag = None
                for word in words:
                    match = re.match(r"<(\S+?)>$", word)
                    if match:
                        tag = match.group(1)
                        if tag == "monospaced":
                            self.textView.mark_set("begin_monospaced", tkinter.INSERT)
                            self.textView.mark_gravity("begin_monospaced", tkinter.LEFT)
                        elif tag == "/monospaced":
                            self.textView.tag_add("monospaced", "begin_monospaced", tkinter.INSERT)
                            tag = None
                        elif tag == "/":
                            tag = None
                        elif tag == "clear":
                            self.gui.clear_screen()
                        elif tag not in iobase.ALL_STYLE_TAGS and tag != "userinput":
                            self.textView.insert(tkinter.END, word, None)
                        continue
                    self.textView.insert(tkinter.END, word, tag)        # @todo this can't deal yet with combined styles
                self.textView.insert(tkinter.END, "\n")
                self.textView.config(state=tkinter.DISABLED)
            else:
                line2 = iobase.strip_text_styles(line)
                self.textView.config(state=tkinter.NORMAL)
                self.textView.insert(tkinter.END, line2 + "\n")
                self.textView.config(state=tkinter.DISABLED)
            self.textView.yview(tkinter.END)

    def quit_button_clicked(self, event=None):
        quit = tkinter.messagebox.askokcancel("Quit Confirmation",
                                              "Quitting like this will abort your game.\nYou will lose your progress. Are you sure?",
                                              master=self)
        if quit:
            self.gui.destroy(True)
            self.gui.window_closed()

    def disable_input(self):
        self.commandEntry.config(state=tkinter.DISABLED)


class TaleGUI:
    """Helper class to set up the gui and connect events."""

    def __init__(self, io, storyconfig):
        self.io = io
        self.server_config = storyconfig
        self.root = tkinter.Tk()
        window_title = "{name}  {version}  |  Tale IF {taleversion}".format(
            name=self.server_config.name,
            version=self.server_config.version,
            taleversion=tale_version
        )
        self.root.title(window_title)
        self.window = TaleWindow(self, self.root, window_title, "")
        self.root.withdraw()
        self.root.update()
        self.install_tab_completion()

    def install_tab_completion(self):
        def tab_pressed(event):
            begin, _, prefix = event.widget.get().rpartition(" ")
            candidates = self.io.tab_complete(prefix, mud_context.driver)
            if candidates:
                if len(candidates) == 1:
                    # replace text by the only possible candidate
                    event.widget.delete(0, tkinter.END)
                    if begin:
                        event.widget.insert(0, begin + " " + candidates[0] + " ")
                    else:
                        event.widget.insert(0, candidates[0] + " ")
                else:
                    self.write_line("\n<ul>possible words:</> ")
                    self.write_line("<monospaced>" + "   ".join(candidates) + "</>\n")
            return "break"  # stop event propagation
        self.window.commandEntry.bind('<Tab>', tab_pressed)

    def mainloop(self, player_connection):
        while True:
            try:
                self.root.mainloop()   # tkinter main loop
                break
            except KeyboardInterrupt:
                print("* break: close the application via its Gui instead.")
                continue
        self.window = None
        self.root = None
        self.io.gui_terminated()

    def pause(self, unpause: bool=False) -> None:
        if unpause:
            self.write_line("---- session continues ----")
        else:
            self.write_line("---- session paused ----")

    def destroy(self, force: bool=False) -> None:
        def destroy2():
            self.window.destroy()
            self.root.destroy()
            self.window = None
            self.root = None
        if self.window:
            self.window.disable_input()
        if force:
            destroy2()
        elif self.root:
            self.root.after(2000, destroy2)

    def window_closed(self) -> None:
        mud_context.driver._stop_driver()

    def clear_screen(self) -> None:
        if self.root:
            self.root.after_idle(lambda: self.window.clear_text())

    def write_line(self, line: str) -> None:
        if self.root:
            self.root.after_idle(lambda: self.window.write_line(line, self.io.do_styles))

    def register_cmd(self, cmd: str) -> None:
        self.io.player_connection.player.store_input_line(cmd)


def show_error_dialog(title, message):
    """show a modal error dialog"""
    root = tkinter.Tk()
    root.withdraw()
    tkinter.messagebox.showerror(title, message)
    root.destroy()
