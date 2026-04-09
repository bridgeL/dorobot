class Msg:
    def __init__(self, content: str = ""):
        self.content = content

    def __str__(self):
        return self.content

    def get_data(self):
        return {"type": "text", "data": self.content}