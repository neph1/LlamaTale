import requests
import time
import aiohttp
import asyncio
import json
import tale.parse_utils as parse_utils
from tale.player_utils import TextBuffer

class IoUtil():
    """ Handles connection and data retrieval from backend """

    def synchronous_request(self, url: str, request_body: dict):
        """ Send request to backend and return the result """
        response = requests.post(url, data=json.dumps(request_body))
        text = parse_utils.trim_response(json.loads(response.text)['results'][0]['text'])
        return text

    def stream_request(self, stream_url: str, data_url: str, request_body: dict, player_io: TextBuffer, io) -> str:
        result = asyncio.run(self._do_stream_request(stream_url, request_body))
        if result:
            return self._do_process_result(data_url, player_io, io)
        return ''

    async def _do_stream_request(self, url: str, request_body: dict,) -> bool:
        """ Send request to stream endpoint async to not block the main thread"""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(request_body)) as response:
                if response.status == 200:
                    return True
                else:
                    # Handle errors
                    print("Error occurred:", response.status)

    def _do_process_result(self, url, player_io: TextBuffer, io) -> str:
        """ Process the result from the stream endpoint """
        tries = 0
        old_text = ''
        while tries < 4:
            time.sleep(0.5)
            data = requests.post(url)
            text = json.loads(data.text)['results'][0]['text']

            if len(text) == len(old_text):
                tries += 1
                continue
            new_text = text[len(old_text):]
            player_io.print(new_text, end=False, format=True, line_breaks=False)
            io.write_output()
            old_text = text

        return old_text
