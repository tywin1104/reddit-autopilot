from config import huey
from reddit import RedditService


@huey.task(retries=10, retry_delay=300)
def schedule_reply(submission, video_link):
    '''
    schedule_reply will add task to reply a given submission via comment
    the scheduled task will run outside of main processing window to avoid
    excessive reddit API ratelimiting. Tasks run with retries & delays in between
    '''
    reddit = RedditService()
    reddit.reply(submission, video_link)
