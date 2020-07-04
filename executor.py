from datetime import datetime, timedelta
import logging
import time
import traceback
import praw
from utils import sleep_with_progess


class Executor:

    @staticmethod
    def _is_crosspost_forbidden_error(error):
        reddit_api_crosspost_forbidden_errors = ["NO_CROSSPOSTS", "OVER18_SUBREDDIT_CROSSPOST"]
        return error.error_type in reddit_api_crosspost_forbidden_errors

    @staticmethod
    def _update_task(task, subreddit, post_url, timestamp):
        # Update task document
        # update corresponding subreddit block in the task document
        subreddit_item = next(item for item in task['subreddits'] if item["name"] == subreddit)
        subreddit_item['posted'] = True
        subreddit_item['link'] = post_url
        subreddit_item['timestamp'] = timestamp

        # If this is the last subreddit for this task
        # also mark the whole task as complete
        done = True
        for item in task['subreddits']:
            if not item['posted']:
                done = False
        if done:
            task['completed'] = True

        # Update last_updated_timestamp & last_posted_timestamp
        task['last_posted_timestamp'] = timestamp
        task['last_updated_timestamp'] = timestamp
        return task

    @staticmethod
    def _within_last_hours(timestamp, hours):
        now = datetime.now()
        return now-timedelta(hours=hours) <= timestamp

    def __init__(
        self, reddit, db,
        running_window=(8, 22),
        min_reposting_dalay=12,
        max_reposting_delay=24,
        subreddit_frontpage_shreshold=10,
        run_interval_seconds=3600
    ):
        self._reddit = reddit
        self._db = db
        # only allow postes to be made during running_window
        self._running_window = running_window
        self._min_reposting_dalay = min_reposting_dalay
        self._max_reposting_delay = max_reposting_delay
        self._subreddit_frontpage_shreshold = subreddit_frontpage_shreshold
        self._run_interval_seconds = run_interval_seconds

    def _crosspost(self, task, subreddit, flair_id):
        '''
        Crosspost existing reddit submission to other subs
        '''
        existing_submission_link = task['link']
        _, post_url = self._reddit.crosspost(subreddit, existing_submission_link, flair_id=flair_id)
        logging.info(f'{post_url} crossposted successfully')

        return post_url

    def _is_in_running_window(self):
        hour = datetime.now().hour
        start, end = self._running_window
        return start <= hour <= end

    def _post_direct(self, task, subreddit, flair_id):
        '''
        Post a new link submission to subreddit
        (also reply to the new post with video source)
        '''
        gif_link = task['gif_link']
        if "***REMOVED***" not in gif_link:
            raise ValueError("Direct post invalid gif link")

        # use the same title as used in existing_submission
        existing_submission_link = task['link']
        title = self._reddit.get_post_title(existing_submission_link)

        submission, post_url = self._reddit.post(subreddit, title, gif_link, flair_id=flair_id)
        logging.info(f'{post_url} posted successfully')

        # Reply the post with video source
        # if task.get('video_link', None):
        #     self._reddit.reply(submission, task['video_link'])

        return post_url

    def _process_task(self, task):
        logging.info(f'Start processing task [{task["_id"]}]')
        subreddits = task.get('subreddits', [])
        for _, subreddit_block in enumerate(subreddits):
            posted = False

            # Wait for some time to prevent reddit spamming detection
            subreddit = subreddit_block['name']
            logging.info(f'Starting: Task [{task["_id"]}] subreddit [{subreddit}]')

            if subreddit_block['posted']:
                logging.info('Already posted. Skip')

            if not subreddit_block['posted'] and self._should_post(task, subreddit):
                # Only some subreddit_block will have flair_id set
                flair_id = subreddit_block.get('flair_id', None)
                try:
                    post_url = self._crosspost(task, subreddit, flair_id)
                    posted = True
                except praw.exceptions.RedditAPIException as api_exception:
                    # Try crosspost first, if fails due to subreddit rules, submit direct post
                    if Executor._is_crosspost_forbidden_error(api_exception):
                        logging.warning(f'Crosspost not allowed on subreddit [{subreddit}], will make a direct post')
                        try:
                            post_url = self._post_direct(task, subreddit, flair_id)
                            posted = True
                        except praw.exceptions.RedditAPIException as api_exception:
                            logging.error(f'Failed to process task [{task["_id"]}] on subreddit [{subreddit}] due to RedditAPI error: {api_exception}')
                        except Exception as e:
                            logging.error(f'Failed to process task [{task["_id"]}] on subreddit [{subreddit}]: {e}')
                            traceback.print_exc()
                    else:
                        logging.error(
                            f'Failed to process task [{task["_id"]}] on subreddit [{subreddit}] due to RedditAPI error: {api_exception}'
                        )
                except Exception as e:
                    logging.error(f'Failed to process task [{task["_id"]}] on subreddit [{subreddit}]: {e}')
                    traceback.print_exc()
                finally:
                    if posted:
                        # Either crosspost or direct post is made, update db records
                        self._update_records(task, subreddit, post_url)
                        sleep_with_progess(60)
                    continue

    def _process_tasks(self):
        uncompleted_tasks = self._db.task.get_uncompleted()
        logging.info(f'Found total {len(uncompleted_tasks)} uncompleted tasks')
        for task in uncompleted_tasks:
            self._process_task(task)

    def _should_post(self, task, subreddit):
        record = self._db.subreddit_record.get(subreddit)
        # first time posting on that subreddit, should allow
        if not record:
            logging.info(
                '[Admission Control] ALLOWED: ' +
                f'First time posting on [{subreddit}]'
            )
            return True

        last_posted_time = datetime.fromtimestamp(record['lastPostedTimestamp'])

        # Do not repost to the same subreddit within the min thereshold period
        # this is in place to prevent spamming the subreddits
        min_delay = self._min_reposting_dalay

        if Executor._within_last_hours(last_posted_time, min_delay):
            logging.info(
                '[Admission Control] DENIED: ' +
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'does not satisfy min reposting delay {min_delay} hours'
            )
            return False

        # If a post has not been made to a subreddit more than max threshold
        # allow to post it
        max_delay = self._max_reposting_delay
        if not Executor._within_last_hours(last_posted_time, max_delay):
            logging.info(
                '[Admission Control] ALLOWED: ' +
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'exceeds max reposting delay {max_delay} hours. '
            )
            return True

        # If any earlier submission is on the frontpage of that subreddit
        # delay new submission and check next round
        is_new = self._reddit.is_on_frontpage(subreddit, "new", threshold=self._subreddit_frontpage_shreshold)
        is_hot = self._reddit.is_on_frontpage(subreddit, "hot", threshold=self._subreddit_frontpage_shreshold)
        if is_new:
            msg = "new listings"
        if is_hot:
            msg = "hot listings"

        if is_new or is_hot:
            logging.info(
                '[Admission Control] DENIED: ' +
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'satisfy min reposting delay {min_delay} hours. ' +
                f'However, found earlier submission within top [{self._subreddit_frontpage_shreshold}] of ' +
                f'[{msg}]'
            )
            return False

        logging.info(
            '[Admission Control] ALLOWED: ' +
            f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
            f'satisfies min reposing period of {min_delay} hours. ' +
            'No earlier submission found in hot nor new listings.'
        )

        return True

    def _update_records(self, task, subreddit, submission_url):
        timestamp = time.time()
        new_task = Executor._update_task(task, subreddit, submission_url, timestamp)

        # Update task in db
        self._db.task.update(new_task)

        # Update subreddit_last_posted record db
        self._db.subreddit_record.upsert(subreddit, {
            "_id": subreddit,
            "lastPostedTimestamp": timestamp
        })

    def run(self):
        while True:
            if self._is_in_running_window():
                logging.info("In running window. Starting processing tasks")
                self._process_tasks()
            else:
                logging.info("Out of running window. Sleep.")

            # Run the cycle at time intervals
            logging.info(f'This run cycle is over. Sleep {self._run_interval_seconds // 60} minutes')
            sleep_with_progess(self._run_interval_seconds)