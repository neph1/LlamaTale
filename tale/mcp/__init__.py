"""
In-process MCP (Model Context Protocol) server package for LlamaTale.

The server runs inside the driver process (started with the ``--mcp`` flag) and
exposes the live :class:`~tale.story_manager.StoryManager` as MCP tools, so an
agent can build and modify stories/worlds against a running story.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
