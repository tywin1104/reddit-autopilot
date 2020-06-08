from .couchdb import CouchdbService


class DbService:
    def __init__(self, db_options):
        url, user, password = db_options.values()

        self.task = TaskService(
            CouchdbService(url, user, password, "tasks")
        )

        self.subreddit_record =  SubredditLastPostedService(
            CouchdbService(url, user, password, "subreddits")
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
class TaskService:
    def __init__(self, db):
        self.db = db

    def create(self, id, task):
        return self.db.create_doc(id, task)

    def get(self, id):
        return self.db.get_docs(_selector({
            "_id" : id
        }))

    def get_uncompleted(self):
        return self.db.get_docs(_selector({
            "completed": False
        }))

    def update(self, new_task):
        id, rev = new_task.get('_id'), new_task.get('_rev')
        return self.db.update_doc(id, rev, new_task)

'''
SubredditLastPosted db service deals with SubredditLastPosted related db operations
record should be in the shape of
{
    "_id": "subredditname",
    "lastPostedTimestamp": linux-timestamp-num
}
'''
class SubredditLastPostedService:
    def __init__(self, db):
        self.db = db

    def upsert(self, new_record):
        id = new_record['_id']
        existing_records = self.db.get_docs(_selector({
            "_id": id
        }))

        # First time posted in this subreddit
        # Create associated record
        if not existing_records:
            self.db.create_doc(id, new_record)
        else:
            existing_record = existing_records[0]
            self.db.update_doc(
                existing_record['_id'],
                existing_record['_rev'],
                new_record
            )

    def get(self, id):
        return self.db.get_docs(_selector({
            "_id" : id
        }))


def _selector(body):
    return {
        "selector": body
    }