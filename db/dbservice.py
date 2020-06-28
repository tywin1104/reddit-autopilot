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

Task should be in the shape of

{
    "_id": "123",
    "gif_link": "https://gfycat.com/faintsnivelinggroundhog-tippy-taps-cute-aww",
    "video_link": "https://videos.com/videos?1212891",
    "completed": false,
    "last_posted_timestamp": 1291298130,
    "total_karmas": 123,
    "last_updated_timestamp": 1291298130,
    "subreddits": [
        {
            "name": "subreddit1",
            "posted": True,
            "link": "https://www.reddit.com/r/TheoryOfReddit/comments/b45qro/best_times_to_post_on_reddit/",
            "timestamp": 1291298127
        },
        {
            "name": "subreddit2",
            "posted": true
        },
        {
            "name": "subreddit3",
            "posted": false,
        },
        {
            "name": "subreddit4",
            "posted": false,
            "link": "https://www.reddit.com/r/TheoryOfReddit/comments/b45qro/best_times_to_post_on_reddit/",
            "timestamp": 1291298130
        }
    ],
    "titles": [
        "this is a fake title 1",
        "this is a fake title 2",
        "this is a fake title 3",
        "this is a fake title 4",
        "this is a fake title 5"
    ]
}
'''


class TaskDbService:
    def __init__(self, db):
        self.db = db

    def create(self, id, task):
        return self.db.create_doc(id, task)

    def get(self, id):
        return self.get_doc_by_id(id)

    def get_uncompleted(self):
        return self.db.get_docs({
            "completed": False
        })

    def update(self, new_task):
        self.db.update_doc(new_task)


'''
SubredditLastPosted db service deals with SubredditLastPosted related db operations
record should be in the shape of
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

