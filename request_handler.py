from users_stack import Queue, ChatsPool

class RequestHandler:
	def __init__ (self, request):
		self.commands = {
		"/start" : self.start,
		"/next"  : self.next,
		"/stop"  : self.stop
		}

		self.request = request

		self.pending = Queue()
		self.pool = ChatsPool()

	def handle(self, response_data):
		message = response_data['result'][0]['message']
		chat_id = message['chat']['id']

		print(message)

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
			self.request("forwardMessage", {"chat_id":receiver_chat_id, "from_chat_id": chat_id, "message_id":message['message_id']})
			print("request sended")
			return

		# add chat_id to pending
		self.pending.push(chat_id)

	def start(self, chat_id):
		self.pending.push(chat_id)
		self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Waiting a company for you!"})
		
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
		self.pool.close(chat_id)
		self.request("sendMessage", {"chat_id":chat_id, 'text': "Bot: Bye!"})