import copy


class Task:
    def __init__(
        self, id,
        link="", crosspost_source_link="", reply_content="",
        completed=False,
        subreddits=[],
        last_updated_timestamp="", title="", nsfw=False
        ):
        self.id = id
        self.link, self.crosspost_source_link, self.reply_content = link, crosspost_source_link, reply_content
        self.completed = completed
        self.subreddits = subreddits
        self.last_updated_timestamp = last_updated_timestamp
        self.title = title
        self.nsfw = nsfw

    @classmethod
    def from_dict(cls, dict):
        subreddits_data = dict.get('subreddits', [])
        subreddits = list(map(SubredditTask.from_dict, subreddits_data))
        return cls(
            id=dict.get('_id', ""),
            link=dict.get('link', ""),
            crosspost_source_link=dict.get('crosspost_source_link', ""),
            reply_content=dict.get('reply_content', ""),
            completed=dict.get('completed', False),
            subreddits=subreddits,
            last_updated_timestamp=dict.get('last_updated_timestamp', ""),
            title=dict.get('title', ""),
            nsfw=dict.get('nsfw', False)
        )

    @classmethod
    def to_dict(cls, obj):
        return_dict = copy.deepcopy(obj.__dict__)
        return_dict["_id"] = return_dict.pop("id")
        return_dict['subreddits'] = list(map(SubredditTask.to_dict, obj.subreddits))
        # if isinstance(obj, cls):
            # obj.__dict__["_id"] = obj.__dict__["id"]
        # obj.__dict__['subreddits'] = list(map(SubredditTask.to_dict, obj.subreddits))

        # return obj.__dict__
        return return_dict

    def update_on_success(self, subreddit, timestamp, post_url):
        subreddit.link = post_url
        subreddit.processed = True
        subreddit.timestamp = timestamp

        # Check completeness of the whole task
        completed = True
        for item in self.subreddits:
            if not item.processed:
                completed = False
        self.completed = completed

        self.last_updated_timestamp = timestamp

    def update_on_error(self, subreddit, timestamp, error):
        subreddit.processed = True
        subreddit.timestamp = timestamp
        subreddit.error = str(error)

        # Check completeness of the whole task
        completed = True
        for item in self.subreddits:
            if not item.processed:
                completed = False
        self.completed = completed

        self.last_updated_timestamp = timestamp

    def __repr__(self):
        return str(self.__dict__)


class SubredditTask:
    def __init__(self, name, link="", timestamp="", processed=False, flair_id="", error=None):
        self.name, self.processed, self.link, self.timestamp = name, processed, link, timestamp
        self.flair_id = flair_id
        self.error = error

    @classmethod
    def from_dict(cls, dict):
        return cls(
            name=dict.get('name', ""),
            processed=dict.get('processed', False),
            timestamp=dict.get('timestamp', ""),
            link=dict.get('link', ""),
            flair_id=dict.get('flair_id', ""),
            error=dict.get('error', "")
        )

    @classmethod
    def to_dict(_, obj):
        return obj.__dict__

    def __repr__(self):
        return str(self.__dict__)
