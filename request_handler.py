from users_stack import Queue, ChatsPool
import json

class RequestHandler:
	def __init__ (self, request):
		self.commands = {
		"/start" : self.start,
		"/next"  : self.next,
		"/stop"  : self.stop
		}

		# all except text and location. actions, which contains field 'file_id'
		self.actions = {
		'photo': 'sendPhoto',
		'audio': 'sendAudio',
		'document': 'sendDocument',
		'sticker': 'sendSticker',
		'video': 'sendVideo'}

		self.request = request

		self.pending = Queue()
		self.pool = ChatsPool()

	def handle(self, response_data):
		# TODO: make multithreading!!! we got len(...) at the same time and we have to use len(...) threads
		for k in range(len(response_data['result'])):
			message = response_data['result'][k]['message']
			chat_id = message['chat']['id']

			# is it command?
			try:
				text = message['text']
				if text in self.commands.keys():
					self.commands[text](chat_id) # execute command
					return
			except KeyError as e:
				pass
				# it is not text

			# is chat_id in pool?
			receiver_chat_id = self.pool.find(chat_id)
			if receiver_chat_id != None:
				keys = message.keys()
				for action in self.actions:
					if action in keys:
						# if in message more than one file
						if isinstance(message[action], list):
							file = message[action][0]
							print(message)
							self.request(self.actions[action], {'chat_id':receiver_chat_id, action:file['file_id']})
						else: # if only one file is sending
							self.request(self.actions[action], {'chat_id':receiver_chat_id, action:message[action]['file_id']})

				if 'text' in keys:
					self.request('sendMessage', {'chat_id':receiver_chat_id, 'text':message['text']})
				if 'location' in keys:
					print(message)
					self.request('sendLocation', {'chat_id':receiver_chat_id, 'latitude':message['location']['latitude'], 'longitude':message['location']['longitude']})

				return

			# add chat_id to pending
			self.pending.push(chat_id)

	def start(self, chat_id):
		self.pending.push(chat_id)
		self.request("sendChatAction", {"chat_id":chat_id, 'action': "find_location"})
		
		if len(self.pending) > 1:
			A = self.pending.pop()
			B = self.pending.pop()
			self.pool.create(A, B)
			self.request("sendMessage", {"chat_id":A, 'text': "Bot: Say hello!"})
			self.request("sendMessage", {"chat_id":B, 'text': "Bot: Say hello!"})

	def next(self, chat_id):
		self.stop(chat_id)
		self.start(chat_id)

	def stop(self, chat_id):
		receiver_chat_id = self.pool.close(chat_id)
		self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Conversation was stopped by you!"})
		self.request("sendMessage", {"chat_id":receiver_chat_id, 'text': "Bot: Conversation was stopped by your companion!"})