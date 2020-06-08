import logging
from reddit import Subreddit, RedditService
from db import DbService
from executor import Executor

def configure_logging():
    logging.basicConfig(
        format='%(asctime)s - %(message)s',
        datefmt='%d-%b-%y %H:%M:%S',
        level=logging.INFO)


with open('subreddits') as f:
    subreddit_names = [line.rstrip() for line in f]

subreddits = []
for sub_name in subreddit_names:
    # use * at start to indicate low_volume
    if sub_name[0] == "*":
        subreddits.append(Subreddit(sub_name[1:], low_volume=True))
    else:
        subreddits.append(Subreddit(sub_name))


reddit = RedditService(subreddits)

db = DbService({
    "url": "",
    "user": "",
    "password": ""
})

if __name__ == "__main__":
    configure_logging()
    executor = Executor(
        reddit=reddit,
        db=db,
        running_window=(8,24),
        min_reposting_dalay=12,
        max_reposing_delay=24,
        subreddit_frontpage_shreshold=10,
        run_period=3600
    )
    executor.run()
