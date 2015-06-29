import requests
from datetime import datetime
import time
import logging
import json
import urllib

from request_handler import RequestHandler

class Tetatet:
    # config
    LONG_POLL_TIME = 60

    def wait(self, t = 60):
        time.sleep(t)
        return

    def request(self, method, parameters={}):
        TELEGRAM_API_ENDPOINT = 'https://api.telegram.org/bot{token}/{method}?{options}'
        HEADERS               = {'Content-type': 'application/json','Accept': 'text/plain'}
        ACCESS_TOKEN          = "123092027:AAFnmwkmT4uTXS809vbfqMwAqFX-qE6Fo9U"

        data        = urllib.parse.urlencode(parameters)
        response    = requests.get(TELEGRAM_API_ENDPOINT.format(token=ACCESS_TOKEN,method=method,options=data),timeout=self.LONG_POLL_TIME,headers=HEADERS)
        print('Request was made to url: {url}'.format(url = response.url), end="\n\n")
        return response

    def start_long_polling(self):
        LAST_REQUEST_ID = 0
        NOW = int(datetime.now().strftime('%s'))
        LAST_POLL_START = NOW

        Handler = RequestHandler(self.request)

        while True:
            NOW = int(datetime.now().strftime('%s'))
            LAST_POLL_START = NOW
            try:
                response = self.request("getUpdates", {"offset":LAST_REQUEST_ID, 'timeout':self.LONG_POLL_TIME})
            except requests.exceptions.Timeout as e:
                print('Request timed out: {error}'.format(error = str(e)))
                continue

            if not response.status_code == requests.codes.ok:
                print('Update check call failed. Server responded with HTTP code: {code}'.format(code = response.status_code))
                self.wait()
                continue

            try:
                response_data = json.loads(response.text.strip())
            except ValueError as e:
                print('Parsing response Json failed with: {err}'.format(err = str(e)), end="\n\n")

                # Wait a little for the dust to settle and
                # retry the update call
                self.wait()
                continue

            if 'ok' not in response_data or not response_data['ok']:
                print('Response from Telegram API was not OK. We got: {resp}'.format(resp = str(response_data)), end="\n\n")
                continue

            # Check that some data was received from the API
            if not response_data['result']:
                print('This poll retreived no data')
                continue

            max_request_id = max([x['update_id'] for x in response_data['result']])
            LAST_REQUEST_ID =  max_request_id + 1 if ((max_request_id + 1) >= LAST_REQUEST_ID) else LAST_REQUEST_ID

            # handle message
            Handler.handle(response_data)
            

if __name__ == '__main__':
    Tetatet().start_long_polling()
