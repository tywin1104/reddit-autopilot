import logging
import yaml
from reddit import RedditService
from db import DbService
from db.couchdb import CouchdbService
from executor import Executor
import coloredlogs


def configure_logging():
    coloredlogs.install(
        level='INFO',
        fmt='%(asctime)s, %(levelname)s %(message)s',
        logger=logging.getLogger()
    )


with open("configs.yaml", 'r') as stream:
    config = yaml.safe_load(stream)


reddit = RedditService()

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
        min_reposting_dalay=app_config['min_reposting_dalay'],
        max_reposting_delay=app_config['max_reposting_dalay'],
        subreddit_frontpage_shreshold=app_config['subreddit_frontpage_shreshold'],
        run_interval_seconds=app_config['run_interval_seconds'],
        crosspost=app_config['crosspost'],
        nsfw=app_config['nsfw']
    )
    executor.run()
