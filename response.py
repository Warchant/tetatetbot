class Response(object):

    possible_m_types = ['text', 'photo','audio','video','document','sticker','location']
    response = None
    m_type = None

    def __init__(self, response):

        if not response['message']:
            raise ValueError('No message payload in the response? WTF?')

        self.response = response['message']
        self.m_type = self._get_m_type()

        self.sender_chat_id = self.response['chat']['id']

    def _get_m_type(self):
        # Search for the message type
        type_search = [m_type for m_type in self.possible_m_types if m_type in self.response]

        # check that we only got 1 result back from the search
        if len(type_search) > 1:
            print('More than 1 message type found: ({res}). Selecting only the first entry'.format(res = ', '.join(type_search)))

        return type_search[0]
