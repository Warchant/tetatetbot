# users, which not in ChatsPool (single users)
class Pending:
	def __init__(self):
		self.q = set()

	def __len__(self):
		return len(self.q)

	def pop(self):
		return self.q.pop() if len(self) > 0 else None

	def push(self, item):
		self.q.add(item)

# pairs of chat_ids
class ChatsPool:
	chats = {}

	def __len__(self):
		return len(self.chats)

	def create(self, A, B):
		print(A,B)
		if A not in self.chats:
			self.chats[A] = B
		else:
			self.close(A)
		if B not in self.chats:
			self.chats[B] = A
		else:
			self.close(B)
		print("Chat {0}<->{1} started".format(A,B))

	def close(self, item):
		try:
			A = self.chats.pop(item)
			B = self.chats.pop(A)
			print("Chat {0}<->{1} closed".format(A,B))
			return A
		except KeyError as e:
			print("ChatsPool::close(), error: {0}".format(str(e)))

	def find(self, item):
		return None if item not in self.chats else self.chats[item]