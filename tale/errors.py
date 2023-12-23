"""
Exception classes

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import inspect
from typing import Generator, Tuple, Any, Optional, Sequence


class TaleError(Exception):
    """base class for tale related errors"""
    pass


class TaleFlowControlException(Exception):
    """base class for flow-control exceptions"""
    pass


class StoryConfigError(TaleError):
    """There was a problem with the story configuration"""
    pass


class SecurityViolation(TaleError):
    """Some security constraint was violated"""
    pass


class ParseError(TaleError):
    """Problem with parsing the user input. Should be shown to the user as a nice error message."""
    pass


class ActionRefused(TaleFlowControlException):
    """The action that was tried was refused by the situation or target object"""
    pass


class SessionExit(TaleFlowControlException):
    """Player session ends."""
    pass


class RetrySoulVerb(TaleFlowControlException):
    """Retry a command as soul verb instead."""
    pass


class RetryParse(TaleFlowControlException):
    """Retry the command as a different one"""
    def __init__(self, command: str) -> None:
        self.command = command


class LocationIntegrityError(TaleError):
    """When the driver notices an integrity problem with locations, exits, etc."""
    def __init__(self, msg: str, direction: str, exit: Any, location: Any) -> None:
        super().__init__(msg)
        self.direction = direction
        self.exit = exit
        self.location = location


class AsyncDialog(TaleFlowControlException):
    """Command execution needs to continue with the async dialog generator given as argument."""
    # @todo replace by proper generator and yield from ?
    def __init__(self, dialog: Generator[Tuple[str, Any], str, None]) -> None:
        if not inspect.isgenerator(dialog):
            raise TypeError("async dialogs only work with generators")
        self.dialog = dialog


class NonSoulVerb(TaleFlowControlException):
    """
    The soul's parser encountered a verb that cannot be handled by the soul itself.
    However the command string has been parsed and the calling code could try
    to handle the verb by itself instead.
    """
    def __init__(self, parseresult) -> None:
        super().__init__(parseresult.verb)
        self.parsed = parseresult


class UnknownVerbException(ParseError):
    """
    The soul doesn't recognise the verb that the user typed.
    The engine can and should search for other places that define this verb first.
    If nothing recognises it, this error should be shown to the user in a nice way.
    """
    def __init__(self, verb: str, words: Sequence[str], qualifier: str) -> None:
        super().__init__(verb)
        self.verb = verb
        self.words = words
        self.qualifier = qualifier


class StoryCompleted(TaleFlowControlException):
    """
    This is raised as soon as the (IF) story has been completed by the player!
    Can be successful, or failed ending. You'll have to print the correct message yourself.
    Do not use this in a Mud story.
    """
    pass

class LlmResponseException(TaleFlowControlException):
    """
    Used when LLM response parsing fails. User should retry again.
    """
    pass
