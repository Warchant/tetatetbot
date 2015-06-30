import requests
from datetime import datetime
import time
import logging
import json
import urllib
import multiprocessing as mp

from data_structures import Pending, ChatsPool
from response import Response

class Tetatet:
    # config
    LONG_POLL_TIME = 60

    PENDING = Pending()
    CHATS   = ChatsPool()

    def __init__(self):
        self.COMMANDS = {
            '/start' : self.start,
            '/next' : self.next,
            '/stop' : self.stop,
            '/status' : self.status
        }    

    def wait(self, t = 60):
        time.sleep(t)
        return

    def request(self, method, parameters={}):
        TELEGRAM_API_ENDPOINT = 'https://api.telegram.org/bot{token}/{method}?{options}'
        HEADERS               = {'Content-type': 'application/json','Accept': 'text/plain'}
        ACCESS_TOKEN          = "123092027:AAFnmwkmT4uTXS809vbfqMwAqFX-qE6Fo9U"

        data        = urllib.parse.urlencode(parameters)
        response    = requests.get(TELEGRAM_API_ENDPOINT.format(token=ACCESS_TOKEN,method=method,options=data),timeout=self.LONG_POLL_TIME,headers=HEADERS)
        #print('Request was made to url: {url}'.format(url = response.url))
        return response

    def start_long_polling(self):
        LAST_REQUEST_ID = 0
        NOW = int(datetime.now().strftime('%s'))
        LAST_POLL_START = NOW

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

            max_request_id  = max([x['update_id'] for x in response_data['result']])
            LAST_REQUEST_ID =  max_request_id + 1 if ((max_request_id + 1) >= LAST_REQUEST_ID) else LAST_REQUEST_ID

            # handle message
            pool = mp.Pool(processes = 4)
            message_workers = pool.map_async(self.response_handler, response_data['result'])
            message_workers.get()
        return

    def start(self, chat_id):
    	
        self.PENDING.push(chat_id)
        self.request("sendChatAction", {"chat_id":chat_id, 'action': "typing"})
        if len(self.PENDING) > 1:
            A = self.PENDING.pop()
            B = self.PENDING.pop()
            self.CHATS.create(A, B)
            self.request("sendMessage", {"chat_id":A, 'text': "Bot: Say hello!"})
            self.request("sendMessage", {"chat_id":B, 'text': "Bot: Say hello!"})

    def next(self, chat_id):
        self.stop(chat_id)
        self.start(chat_id)

    def stop(self, chat_id):
        receiver_chat_id = self.CHATS.close(chat_id)
        self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Conversation was stopped by you!"})
        self.request("sendMessage", {"chat_id":receiver_chat_id, 'text': "Bot: Conversation was stopped by your companion!"})

    def status(self, chat_id):
        text = "There are {0} users online.".format(len(self.PENDING) + len(self.CHATS))
        self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: " + text})
    
    def resend(self, handle, chat_id):
        if handle.response.m_type == 'text':
            self.request('sendMessage',{'chat_id':chat_id, 'text':handle.response['text']})
        if handle.response.m_type == 'photo':
            self.request('sendPhoto',{'chat_id':chat_id, 'photo':handle.response['photo']['file_id']})
        if handle.response.m_type == 'audio':
            self.request('sendAudio',{'chat_id':chat_id, 'audio':handle.response['audio']['file_id']})
        if handle.response.m_type == 'document':
            self.request('sendDocument',{'chat_id':chat_id, 'document':handle.response['document']['file_id']})
        if handle.response.m_type == 'video':
            self.request('sendVideo',{'chat_id':chat_id, 'video':handle.response['video']['file_id']})
        if handle.response.m_type == 'location':
            self.request('sendLocation',{'chat_id':chat_id, 'latitude':handle.response['location']['latitude'], 'longitude':handle.response['location']['longitude']})


    def response_handler(self, response):
        try:
            print(len(self.CHATS))
            print(len(self.PENDING), "\n\n")

            handle = Response(response)
            if handle.m_type == 'text':
                text = handle.response['text']
                if text in self.COMMANDS.keys(): # if it is a command
                    self.COMMANDS[text](handle.sender_chat_id)
                    return

            # if this chat_id in pool
            receiver_chat_id = self.CHATS.find(handle.sender_chat_id)
            if receiver_chat_id != None:
                self.resend(handle, receiver_chat_id)
                return

            # if this chat_id not in pool
            self.PENDING.push(handle.sender_chat_id)
            return

        except Exception as e:
            print("response_handler(response) error: \n{0}".format(str(e)))
           

if __name__ == '__main__':
    Tetatet().start_long_polling()
