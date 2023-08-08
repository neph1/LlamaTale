from typing import Any, Sequence, Tuple, IO, Optional, Set, List, Union

class TextBuffer:
    """
    Buffered output for the text that the player will see on the screen.
    The buffer queues up output text into paragraphs.
    Notice that no actual output formatting is done here, that is performed elsewhere.
    """
    class Paragraph:
        def __init__(self, format: bool=True, line_breaks=True) -> None:
            self.format = format
            self.lines = []  # type: List[str]
            self.line_breaks = line_breaks

        def add(self, line: str) -> None:
            if self.line_breaks:
                self.lines.append(line)
            elif len(self.lines) > 0:
                self.lines[-1] += line 
            else:
                self.lines.append(line)

        def text(self) -> str:
            return "\n".join(self.lines) + "\n"
            
    def __init__(self) -> None:
        self.init()

    def init(self) -> None:
        self.paragraphs = []  # type: List[TextBuffer.Paragraph]
        self.in_paragraph = False

    def p(self) -> None:
        """Paragraph terminator. Start new paragraph on next line."""
        if not self.in_paragraph:
            self.__new_paragraph(False, True)
        self.in_paragraph = False

    def __new_paragraph(self, format: bool, line_breaks: bool) -> Paragraph:
        p = TextBuffer.Paragraph(format, line_breaks)
        self.paragraphs.append(p)
        self.in_paragraph = True
        return p

    def print(self, line: str, end: bool=False, format: bool=True, line_breaks=True) -> None:
        """
        Write a line of text. A single space is inserted between lines, if format=True.
        If end=True, the current paragraph is ended and a new one begins.
        If format=True, the text will be formatted when output, otherwise it is outputted as-is.
        """
        if not line and format and not end:
            return
        if self.in_paragraph:
            p = self.paragraphs[-1]
        else:
            p = self.__new_paragraph(format, line_breaks)
        if p.format != format:
            p = self.__new_paragraph(format, line_breaks)
        if format:
            line = line.strip()
        p.add(line)
        if end:
            self.in_paragraph = False

    def get_paragraphs(self, clear: bool=True) -> Sequence[Tuple[str, bool]]:
        paragraphs = [(p.text(), p.format) for p in self.paragraphs]
        if clear:
            self.init()
        return paragraphs
