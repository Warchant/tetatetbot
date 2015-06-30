class Response(object):
    possible_message_types = ['text', 'photo','audio','video','document','sticker','location']
    response = None
    message_type = None
    action = None


    def __init__(self, response):
        if not response['message']:
            print('No message payload in the response? WTF?')
            return
        self.response = response['message']
        self.message_type = self._get_message_type()
        self.sender_chat_id = self.response['chat']['id']

    def _get_message_type(self):
        # Search for the message type
        type_search = [message_type for message_type in self.possible_message_types if message_type in self.response]
        # check that we only got 1 result back from the search
        if len(type_search) > 1:
            print('More than 1 message type found: ({res}). Selecting only the first entry'.format(res = ', '.join(type_search)))
        return type_search[0]
