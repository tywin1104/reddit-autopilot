import coloredlogs
import logging
from reddit import RedditService
from db import DbService
from db.couchdb import CouchdbService
from executor import Executor


def configure_logging():
    coloredlogs.install(
        level='INFO',
        fmt='%(asctime)s, %(levelname)s %(message)s',
        logger=logging.getLogger()
    )


reddit = RedditService()

couchdb_engine = CouchdbService(
    url="http://127.0.0.1:5984",
    user="***REMOVED***",
    password="412476can"
)
db = DbService(couchdb_engine)

if __name__ == "__main__":
    configure_logging()
    executor = Executor(
        reddit=reddit,
        db=db,
        running_window=(8, 23),
        min_reposting_dalay=12,
        max_reposting_delay=24,
        subreddit_frontpage_shreshold=10,
        run_interval_seconds=3600
    )
    executor.run()
