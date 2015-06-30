from datetime import datetime
import time
import logging
import json
import urllib
import requests
from multiprocessing import Queue, Pool, Process, Manager

from response import Response

class Tetatet:
    # config
    LONG_POLL_TIME = 60
    pending_responses = None
    pending_users = None
    chats   = None

    manager = Manager()

    def __init__(self):
        self.manager = Manager()
        self.pending_users = self.manager.Queue()
        self.pending_responses = self.manager.Queue()
        self.chats = self.manager.dict()

        self.commands = {
            '/start' : self.start,
            '/stop'  : self.stop,
            '/next'  : self.next,
            '/status': self.status
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
        
        return response

    def long_poll(self):
        NOW = int(datetime.now().strftime('%s'))
        LAST_REQUEST_ID = 0
        LAST_POLL_START = NOW
        
        while True:
            NOW = int(datetime.now().strftime('%s'))
            LAST_POLL_START = NOW
            try:
                response = self.request("getUpdates", {"offset": LAST_REQUEST_ID, 'timeout': self.LONG_POLL_TIME})
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
            LAST_REQUEST_ID = max_request_id + 1 if ((max_request_id + 1) >= LAST_REQUEST_ID) else LAST_REQUEST_ID

            for response in response_data['result']:
                self.pending_responses.put(response)

            print("[added]: ", self.pending_responses.qsize())
    
    def chat_find(self, A):
        return None if A not in self.chats else self.chats[A]

    def chat_create(self, A, B):
        if A != B:
            if A not in self.chats:
                self.chats[A] = B
            if B not in self.chats:
                self.chats[B] = A
            print("Chat {0}<->{1} started".format(A,B))

    def chat_close(self, item):
        try:
            A = self.chats.pop(item)
            B = self.chats.pop(A)
            print("Chat {0}<->{1} closed".format(A,B))
            return A
        except KeyError as e:
            print("ChatsPool::close(), error: {0}".format(str(e)))

    def start(self, chat_id):
        self.pending_users.put(chat_id)
        self.request("sendChatAction", {"chat_id":chat_id, 'action': "typing"})

        if self.pending_users.qsize() > 1:
            A = self.pending_users.get()
            B = self.pending_users.get()
            if A == B:
                return
            self.chat_create(A, B)
            self.request("sendMessage", {"chat_id":A, 'text': "Bot: Say hello!"})
            self.request("sendMessage", {"chat_id":B, 'text': "Bot: Say hello!"})

    def stop(self, chat_id):
        receiver_chat_id = self.chat_close(chat_id)
        self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Conversation was stopped by you!"})
        self.request("sendMessage", {"chat_id":receiver_chat_id, 'text': "Bot: Conversation was stopped by your companion!"})

    def next(self, chat_id):
        self.stop(chat_id)
        self.start(chat_id)

    def status(self, chat_id):
        text = "{0} users is looking for a company.".format( self.pending_users.qsize() + len(self.chats) )
        self.request('sendMessage', {'chat_id': chat_id, 'text':text})

    def resend(self, handle, chat_id):
        if handle.message_type == 'text':
            self.request('sendMessage',{'chat_id':chat_id, 'text':handle.response['text']})
        if handle.message_type == 'photo':
            print(handle.response)
            self.request('sendPhoto',{'chat_id':chat_id, 'photo':handle.response['photo']['file_id']})
        if handle.message_type == 'audio':
            self.request('sendAudio',{'chat_id':chat_id, 'audio':handle.response['audio']['file_id']})
        if handle.message_type == 'document':
            self.request('sendDocument',{'chat_id':chat_id, 'document':handle.response['document']['file_id']})
        if handle.message_type == 'video':
            self.request('sendVideo',{'chat_id':chat_id, 'video':handle.response['video']['file_id']})
        if handle.message_type == 'sticker':
            self.request('sendSticker',{'chat_id':chat_id, 'sticker':handle.response['sticker']['file_id']})
        if handle.message_type == 'location':
            self.request('sendLocation',{'chat_id':chat_id, 'latitude':handle.response['location']['latitude'], 'longitude':handle.response['location']['longitude']})

    def eval_request(self):
        while True:
            if self.pending_responses.qsize() > 0:
                response = self.pending_responses.get()
                print("[removed]: ", self.pending_responses.qsize())
                h = Response(response)
                if h.message_type == 'text':
                    # is it command?
                    text = h.response['text']
                    if text in self.commands.keys():
                        self.commands[text](h.sender_chat_id)
                        continue

                # is h.sender_chat_id in chats?
                receiver_chat_id = self.chat_find(h.sender_chat_id)
                if receiver_chat_id != None:
                    self.resend(h, receiver_chat_id)


if __name__ == '__main__':
    T = Tetatet()
    polls = Process(target=T.long_poll)
    req = Process(target=T.eval_request)
    
    polls.start()
    req.start()

    polls.join()
    req.join()