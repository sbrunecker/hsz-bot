class Course:
    def __init__(self, id, url, password=None):
        self.id = str(id)
        self.url = url
        self.password = password