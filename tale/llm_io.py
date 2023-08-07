import requests
import time
import aiohttp
import asyncio
import threading
import json
import tale.parse_utils as parse_utils
from tale.player_utils import TextBuffer
from .tio.iobase import IoAdapterBase
class IoUtil():

    def synchronous_request(self, url: str, request_body: dict):
        response = requests.post(url, data=json.dumps(request_body))
        text = parse_utils.trim_response(json.loads(response.text)['results'][0]['text'])
        return text

    def stream_request(self, player_io: TextBuffer, url: str, request_body: dict, io: IoAdapterBase) -> str:
        result = asyncio.run(self._do_stream_request(url, request_body))
        if result:
            return self._do_process_result(url, player_io, io)
        return ''

    async def _do_stream_request(self, url: str, request_body: dict,) -> bool:
        sub_endpt = "http://localhost:5001/api/extra/generate/stream"

        async with aiohttp.ClientSession() as session:
            async with session.post(sub_endpt, data=json.dumps(request_body)) as response:
                if response.status == 200:
                    return True
                    
                else:
                    # Handle errors
                    print("Error occurred:", response.status)

    def _do_process_result(self, url, player_io: TextBuffer, io: IoAdapterBase) -> str:
        tries = 0
        old_data = ''
        while tries < 2:
            data = requests.post("http://localhost:5001/api/extra/generate/check")
            text = json.loads(data.text)['results'][0]['text']
            new_text = text[len(old_data):]
            player_io.print(new_text, end=False, format=False, line_breaks=False)
            io.write_output()
            if len(text) == len(old_data):
                tries += 1
            old_data = text
            time.sleep(1)
        return old_data
