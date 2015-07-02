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
        self.pending_users = self.manager.list()
        self.pending_responses = self.manager.Queue()
        self.chats = self.manager.dict()

        self.commands = {
            '/start' : self.start,
            '/stop'  : self.stop,
            '/status': self.status,
            '/test'  : self.test
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

            print("[added]:\t Size: ", self.pending_responses.qsize())
    
    def chat_find(self, A):
        return None if A not in self.chats else self.chats[A]

    def chat_create(self, A, B):
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
        if chat_id not in self.pending_users:
            self.pending_users.append(chat_id)
            self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Looking for a partner..."})
        else:
            self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Don't repeat yourself. Bot is looking for partner for you."})

        if len(self.pending_users) > 1:
            A = self.pending_users.pop(0)
            B = self.pending_users.pop(0)
            self.chat_create(A, B)
            self.request("sendMessage", {"chat_id":A, 'text': "Bot: Say hello!"})
            self.request("sendMessage", {"chat_id":B, 'text': "Bot: Say hello!"})

    def test(self, chat_id):
        if chat_id not in self.chats and chat_id not in self.pending_users:
            self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: You are in chat with yourself (test mode)"})
            self.chat_create(chat_id, chat_id)
            self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Say hello!"})
        else:
            self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Stop previous chat before entering in test mode"})

    def stop(self, chat_id):
        self.pending_users.remove(chat_id)
        receiver_chat_id = self.chat_close(chat_id)
        self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Conversation was stopped."})
        self.request("sendMessage", {"chat_id":receiver_chat_id, 'text': "Bot: Conversation was stopped by your partner!"})

    def status(self, chat_id):
        text = "{0} users is looking for a company.".format( len(self.pending_users) + len(self.chats) )
        self.request('sendMessage', {'chat_id': chat_id, 'text':text})

    def resend(self, response, chat_id):
        k = response.keys()
        if 'reply_to_message' in k:
            # it is a reply
            forward_m_id = response['reply_to_message']['message_id']
        else:
            if 'forward_from' in k:
                forward_m_id = response['message_id']
                if 'text' in k:
                    response['text'] = 'message forwarded...'
            else:
                forward_m_id = ''

        print(response)

        if 'text' in k:
            self.request('sendMessage',{'chat_id':chat_id, 'text':response['text'], 'reply_to_message_id': forward_m_id})
        if 'photo' in k:
            if isinstance(response['photo'], list):
                response['photo'] = response['photo'][0]
            a = self.request('sendPhoto',{'chat_id':chat_id, 'photo':response['photo']['file_id'], 'reply_to_message_id': forward_m_id})
        if 'audio' in k:
            self.request('sendAudio',{'chat_id':chat_id, 'audio':response['audio']['file_id'], 'reply_to_message_id': forward_m_id})
        if 'document' in k:
            self.request('sendDocument',{'chat_id':chat_id, 'document':response['document']['file_id'], 'reply_to_message_id':forward_m_id})
        if 'video' in k:
            self.request('sendVideo',{'chat_id':chat_id, 'video':response['video']['file_id'], 'reply_to_message_id': forward_m_id})
        if 'sticker' in k:
            self.request('sendSticker',{'chat_id':chat_id, 'sticker':response['sticker']['file_id'], 'reply_to_message_id': forward_m_id})
        if 'location' in k:
            self.request('sendLocation',{'chat_id':chat_id, 'latitude':response['location']['latitude'], 'longitude':response['location']['longitude'], 'reply_to_message_id': forward_m_id})

    def eval_request(self):
        while True:
            if self.pending_responses.qsize() > 0:
                response = self.pending_responses.get()['message']
                print("[removed]:\t Size: ", self.pending_responses.qsize())

                if 'text' in response.keys():
                    # is it command?
                    text = response['text']
                    if text in self.commands.keys():
                        self.commands[text](response['chat']['id'])
                        continue
                # is h.sender_chat_id in chats?
                receiver_chat_id = self.chat_find(response['chat']['id'])
                if receiver_chat_id != None:
                    self.resend(response, receiver_chat_id)


if __name__ == '__main__':
    T = Tetatet()

    polls = Process(target=T.long_poll)
    req = Process(target=T.eval_request)
    
    polls.start()
    req.start()

    polls.join()
    req.join()