import logging
import praw
import yaml
from src.reddit import RedditService
from src.db import DbService
from src.db.couchdb import CouchdbService
from src.executor import Executor
import coloredlogs


def configure_logging():
    coloredlogs.install(
        level='INFO',
        fmt='%(asctime)s, %(levelname)s %(message)s',
        logger=logging.getLogger()
    )


with open("configs.yaml", 'r') as stream:
    config = yaml.safe_load(stream)


reddit = RedditService(praw.Reddit())

couchdb_engine = CouchdbService(
    url=config['couchdb']['host'],
    user=config['couchdb']['username'],
    password=config['couchdb']['password']
)
db = DbService(couchdb_engine)

if __name__ == "__main__":
    configure_logging()

    app_config = config['app']
    executor = Executor(
        reddit=reddit,
        db=db,
        running_window=(app_config['running_window_start_hour'], app_config['running_window_end_hour']),
        min_reposting_delay=app_config['min_reposting_delay'],
        max_reposting_delay=app_config['max_reposting_delay'],
        subreddit_frontpage_shreshold=app_config['subreddit_frontpage_shreshold'],
        run_interval_seconds=app_config['run_interval_seconds'],
        nsfw=app_config['nsfw']
    )
    executor.run()
