import functools
import logging
import re
import praw
from utils import sleep_with_progess


def _handle_ratelimit(function):
    """
    A decorator that handles reddit API ratelimiting
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except praw.exceptions.RedditAPIException as e:
            # Ratelimit api error
            if e.error_type.strip() == "RATELIMIT":
                match = re.search(r'[0-9]+', e.message, flags=0)
                if match:
                    mins = int(match.group())
                    logging.warning(f'Reddit API ratelimit reached: wait {mins} minutes')
                    sleep_secs = 60 * (mins + 1) + 10
                    sleep_with_progess(sleep_secs)

                    return function(*args, **kwargs)
            else:
                raise
    return wrapper


class RedditService:
    def __init__(self):
        self._reddit = praw.Reddit("crosspost")
        self._reddit.validate_on_submit = True
        self._username = self._reddit.user.me().name

    @_handle_ratelimit
    def crosspost(self, subreddit, existing_submission_link, flair_id=None, nsfw=False):
        '''
        Crosspost a submission to target subreddit
        :returns: the full url for the submission if successful
        '''
        reddit_base_url = "https://www.reddit.com"

        existing_submission = self._reddit.submission(url=existing_submission_link)
        crosspost_submission = existing_submission.crosspost(
            subreddit=subreddit,
            send_replies=True,
            nsfw=nsfw,
            flair_id=flair_id
        )

        return (crosspost_submission, reddit_base_url + crosspost_submission.permalink)

    def get_post_title(self, post_url):
        submission = self._reddit.submission(url=post_url)
        return submission.title

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

    @_handle_ratelimit
    def post(self, subreddit, title, link, flair_id=None, nsfw=False):
        '''
        Post a link to the target subreddit with specified title
        :returns: the full url for the submission if successful
        '''
        reddit_base_url = "https://www.reddit.com"

        submission = self._reddit.subreddit(subreddit).submit(
            title,
            url=link,
            nsfw=nsfw,
            flair_id=flair_id
        )

        return (submission, reddit_base_url + submission.permalink)

    def reply(self, submission, reply_content):
        submission.reply(reply_content)
        logging.info("commented successfully")
