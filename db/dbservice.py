class DbService:
    def __init__(self, db_engine):
        self._db_engine = db_engine

        self.task = TaskDbService(
            self._db_engine.db("tasks")
        )

        self.subreddit_record = SubredditLastPostedDbService(
            self._db_engine.db("subreddits")
        )


'''
Task db service deals with task related db operations
Task document should be in the shape of

{
    "_id": "123",
    "link": "https://link"
    "crosspost_source_link": "https://www.reddit.com/r/example/comments/hvcqse/example/",
    "reply_content": "content to reply to the newly made posts. Markdown format",
    "completed": false,
    "subreddits": [
        {
            "name": "subreddit2",
            "posted": false
        },
        {
            "name": "subreddit3",
            "posted": false,
        }
    ]
}
'''


class TaskDbService:
    def __init__(self, db):
        self.db = db

    def create(self, id, task):
        return self.db.create_doc(id, task)

    def get(self, id):
        return self.db.get_doc_by_id(id)

    def get_uncompleted(self):
        return self.db.get_docs({
            "completed": False
        })

    def update(self, new_task):
        self.db.update_doc(new_task)


'''
SubredditLastPosted db service keep track of posts being made to various subreddits
record document should be in the shape of
{
    "_id": "subredditname",
    "lastPostedTimestamp": linux-timestamp-num
}
'''


class SubredditLastPostedDbService:
    def __init__(self, db):
        self.db = db

    def get(self, id):
        return self.db.get_doc_by_id(id)

    def upsert(self, id, new_record):
        self.db.upsert_doc(id, new_record)
