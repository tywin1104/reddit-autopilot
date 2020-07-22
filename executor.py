from datetime import datetime, timedelta
import logging
import time
import traceback
import praw
from tasks import schedule_reply
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
        min_reposting_delay=12,
        max_reposting_delay=24,
        subreddit_frontpage_shreshold=10,
        run_interval_seconds=3600,
        crosspost=True,
        nsfw=False
    ):
        self._reddit = reddit
        self._db = db
        # only allow postes to be made during running_window
        self._running_window = running_window
        self._min_reposting_delay = min_reposting_delay
        self._max_reposting_delay = max_reposting_delay
        self._subreddit_frontpage_shreshold = subreddit_frontpage_shreshold
        self._run_interval_seconds = run_interval_seconds
        self._crosspost_enabled = crosspost
        self._nsfw = nsfw

    def _crosspost(self, task, subreddit, flair_id):
        '''
        Crosspost existing reddit submission to other subs
        '''
        crosspost_source_link = task.get('crosspost_source_link', None)
        if not crosspost_source_link:
            raise ValueError('No crosspost source link found for this task')

        _, post_url = self._reddit.crosspost(subreddit, crosspost_source_link, flair_id=flair_id, nsfw=self._nsfw)
        logging.info(f'{post_url} crossposted successfully')

        return post_url

    def _is_in_running_window(self):
        hour = datetime.now().hour
        start, end = self._running_window
        return start <= hour <= end

    def _post_direct(self, task, subreddit, flair_id):
        '''
        Post a new link submission to subreddit
        Use same title as the crosspost target if it exists
        or use title field specified in the task document
        (could optionally schedule automatic reply to the newly created posts)
        '''
        link = task.get('link', None)
        if not link:
            raise ValueError('No link found within the task document to perform direct post. Skip this subreddit')

        # use the same title as used in existing_submission
        crosspost_source_link = task.get('crosspost_source_link', None)
        if crosspost_source_link:
            if "reddit.com" not in crosspost_source_link:
                raise ValueError(f'Invalid crosspost target: {crosspost_source_link} not a proper reddit submission')

            title = self._reddit.get_post_title(crosspost_source_link)
        else:
            title = task.get('title', None)

        if not title:
            raise ValueError(
                'Invalid task: unable to determine title for new submission.' +
                'Either crosspost target or title field should be nonempty.'
            )

        submission, post_url = self._reddit.post(subreddit, title, link, flair_id=flair_id, nsfw=self._nsfw)
        logging.info(f'{post_url} posted successfully')

        # Schedule async jobs to reply the post
        if task.get('reply_content', None):
            schedule_reply(submission, task['reply_content'])
            logging.info('Reply scheduled')

        return post_url

    def _process_task(self, task):
        logging.info(f'Start processing task [{task["_id"]}]')
        subreddits = task.get('subreddits', [])
        for _, subreddit_block in enumerate(subreddits):
            posted = False

            subreddit = subreddit_block['name']
            logging.info(f'Starting: Task [{task["_id"]}] subreddit [{subreddit}]')

            if subreddit_block['posted']:
                logging.info('Already posted. Skip')

            if not subreddit_block['posted'] and self._should_post(subreddit):
                # If crosspost option is enabled, use crosspost first
                # Otherwise only attempts to make direct post submissions
                operations = [self._crosspost, self._post_direct]
                if not self._crosspost_enabled:
                    operations = [self._post_direct]

                # Only some subreddit_block will have flair_id set
                # as it is not a mandtory requirement of most subreddits
                flair_id = subreddit_block.get('flair_id', None)

                for op_func in operations:
                    try:
                        post_url = op_func(task, subreddit, flair_id)
                        posted = True
                    except praw.exceptions.RedditAPIException as api_exception:
                        if Executor._is_crosspost_forbidden_error(api_exception):
                            logging.warning(f'Crosspost not allowed on subreddit [{subreddit}], will make a direct post')
                            continue
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
                            # short period of sleep to prevent spamming per reddit's policy
                            sleep_with_progess(60)
                        break

    def _process_tasks(self):
        uncompleted_tasks = self._db.task.get_uncompleted()
        logging.info(f'Found total {len(uncompleted_tasks)} uncompleted tasks')
        for task in uncompleted_tasks:
            self._process_task(task)

    def _should_post(self, subreddit):
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
        min_delay = self._min_reposting_delay

        if Executor._within_last_hours(last_posted_time, min_delay):
            logging.info(
                '[Admission Control] DENIED: ' +
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'does not satisfy min reposting delay {min_delay} hours'
            )
            return False

        # If no post has been made to a subreddit more than max threshold period
        # allow to post
        max_delay = self._max_reposting_delay
        if not Executor._within_last_hours(last_posted_time, max_delay):
            logging.info(
                '[Admission Control] ALLOWED: ' +
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'exceeds max reposting delay {max_delay} hours. '
            )
            return True

        # If any earlier submission is on the frontpage of that subreddit
        # delay new submission for this round
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
                logging.info("Out of running window.")

            # Run the cycle at time intervals
            logging.info(f'This run cycle is over. Sleep {self._run_interval_seconds // 60} minutes')
            sleep_with_progess(self._run_interval_seconds)
