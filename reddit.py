import praw


class Subreddit:
    def __init__(self, name, low_volume=False):
        self.name = name
        self.low_volume = low_volume


class RedditService:
    def __init__(self, subreddits):
        self._reddit = praw.Reddit()
        self._reddit.validate_on_submit = True
        self._low_volume_subreddits = [s.name for s in subreddits if s.low_volume]
        self._username = self._reddit.user.me().name

    def is_low_volume(self, subreddit):
        '''
        Check if the specified subreddit is of low_volume
        low_volume is manually defined during class construction
        Will set different threshold for low_volume subreddits
        then others (eg. min interval between new submissions)
        '''
        return subreddit in self._low_volume_subreddits

    def is_on_frontpage(self, subreddit, category, threshold=10):
        '''
        Check if there exists any submissions on the front page
        of the subreddit for the current authenticated user.
        This checks any submission listed within top {threshold}
        in either hot / new categories.
        '''
        if category not in ['hot', 'new']:
            raise ValueError("On-frontpage check only supports hot or new listings")

        func = getattr(self._reddit.subreddit(subreddit), category)
        for submission in func(limit=threshold):
            if self._username == submission.author:
                return True

        return False

    def post(self, subreddit, title, link, flair_id=None):
        '''
        Post a link to the target subreddit with specified title
        :returns: the full url for the submission if successful
        '''
        reddit_base_url = "https://www.reddit.com"

        submission = self._reddit.subreddit(subreddit).submit(
            title,
            url=link,
            nsfw=True,
            flair_id=flair_id
        )

        return (submission, reddit_base_url + submission.permalink)
