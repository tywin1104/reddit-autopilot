from datetime import datetime, timedelta
import logging
import time
import praw
from .jobs import schedule_reply
from .task import Task
from .utils import sleep_with_progess


class Executor:

    @staticmethod
    def _is_crosspost_forbidden_error(error):
        reddit_api_crosspost_forbidden_errors = ["NO_CROSSPOSTS", "OVER18_SUBREDDIT_CROSSPOST"]
        return error.error_type in reddit_api_crosspost_forbidden_errors

    @staticmethod
    def _within_last_hours(last_posted_timestamp, hours, timestamp):
        now = timestamp
        return now-timedelta(hours=hours) <= last_posted_timestamp

    def __init__(
        self, reddit, db,
        running_window=(8, 22),
        min_reposting_delay=12,
        max_reposting_delay=24,
        subreddit_frontpage_shreshold=10,
        run_interval_seconds=3600,
    ):
        self._reddit = reddit
        self._db = db
        # only allow postes to be made during running_window
        self._running_window = running_window
        self._min_reposting_delay = min_reposting_delay
        self._max_reposting_delay = max_reposting_delay
        self._subreddit_frontpage_shreshold = subreddit_frontpage_shreshold
        self._run_interval_seconds = run_interval_seconds

    def _get_operations(self, task):
        '''
        Get desired operation modes from the given task
        This allows individual task to define the desired post types
        '''
        link, crosspost_link = task.link, task.crosspost_source_link
        operations = []
        if crosspost_link:
            operations.append(self._crosspost)
        if link:
            operations.append(self._post_direct)
        if not operations:
            raise ValueError('Invalid task document. Neither crosspost target nor direct link found')

        return operations

    def _is_in_running_window(self, timestamp):
        hour = timestamp.hour
        start, end = self._running_window
        return start <= hour <= end

    def _get_title(self, task):
        '''
        Get title from a given task. Use same title of the crosspost_source if exists
        '''
        crosspost_source_link = task.crosspost_source_link
        if crosspost_source_link:
            if "reddit.com" not in crosspost_source_link:
                raise ValueError(f'Invalid crosspost target: {crosspost_source_link} not a proper reddit submission')

            return self._reddit.get_post_title(crosspost_source_link)
        return task.title

    def _crosspost(self, task, subreddit):
        '''
        Crosspost existing reddit submission to other subs
        '''
        crosspost_source_link = task.crosspost_source_link
        if not crosspost_source_link:
            raise ValueError('No crosspost source link found for this task')

        post_url = self._reddit.crosspost(subreddit.name, crosspost_source_link, flair_id=subreddit.flair_id, nsfw=task.nsfw)
        logging.info(f'{post_url} crossposted successfully')

        return post_url

    def _post_direct(self, task, subreddit):
        '''
        Post a new link submission to subreddit
        Use same title as the crosspost target if it exists
        or use title field specified in the task document
        (could optionally schedule automatic reply to the newly created posts)
        '''
        link = task.link
        if not link:
            raise ValueError('No link found within the task document to perform direct post. Skip this subreddit')

        title = self._get_title(task)

        if not title:
            raise ValueError(
                'Invalid task: unable to determine title for new submission. ' +
                'Either crosspost target or title field should be nonempty.'
            )

        submission, post_url = self._reddit.post(subreddit.name, title, link, flair_id=subreddit.flair_id, nsfw=task.nsfw)
        logging.info(f'{post_url} posted successfully')

        # Schedule async jobs to reply the post
        if task.reply_content:
            schedule_reply(submission, task.reply_content, self._reddit)
            logging.info('Reply scheduled')

        return post_url

    def _process_subreddit_in_task(self, task, subreddit, operations):
        '''
        Process one subreddit within a given task
        Return if new post is made from the processing of this subreddit
        '''
        for op_func in operations:
            try:
                post_url = op_func(task, subreddit)
                self._update_documents_on_success(task, subreddit, post_url)
                return True
            except praw.exceptions.RedditAPIException as api_exception:
                if Executor._is_crosspost_forbidden_error(api_exception):
                    logging.warning(f'Crosspost not allowed on subreddit [{subreddit.name}], will make a direct post')
                    continue
                else:
                    raise
            except Exception as e:
                logging.error(f'Failed to process task [{task.id}] on subreddit [{subreddit.name}]: {e}')
                self._update_documents_on_error(task, subreddit, e)
        return False

    def _process_task(self, task):
        logging.info(f'Start processing task [{task.id}]')
        subreddits = task.subreddits
        # Get the mode of opeartions from the task document
        # This allows flexible mode defined per task
        operations = self._get_operations(task)
        for subreddit in subreddits:
            subreddit_name = subreddit.name
            logging.info(f'Starting: Task [{task.id}] subreddit [{subreddit_name}]')

            if subreddit.processed:
                logging.info('Already processed. Skip')
            else:
                record = self._db.subreddit_record.get(subreddit_name)
                if self._should_post(record, datetime.now()):
                    posted = self._process_subreddit_in_task(task, subreddit, operations)
                    if posted:
                        # sleep for a short period after each successful post
                        sleep_with_progess(60)

    def _process_tasks(self):
        uncompleted_tasks = self._db.task.get_uncompleted()
        logging.info(f'Found total {len(uncompleted_tasks)} uncompleted tasks')
        for task_dict in uncompleted_tasks:
            # documents fetched from db are in dict shape
            # use marshalled Task object as argument
            task = Task.from_dict(task_dict)
            self._process_task(task)

    def _should_post(self, record, timestamp):
        # first time posting on that subreddit, should allow
        if not record:
            logging.info(
                '[Admission Control] ALLOWED: ' +
                'First time posting'
            )
            return True

        subreddit_name = record['_id']
        last_posted_time = datetime.fromtimestamp(record['lastPostedTimestamp'])

        # Do not repost to the same subreddit within the min thereshold period
        # this is in place to prevent spamming the subreddits
        min_delay = self._min_reposting_delay

        if Executor._within_last_hours(last_posted_time, min_delay, timestamp):
            logging.info(
                '[Admission Control] DENIED: ' +
                f'Most recent post on [{subreddit_name}] at [{last_posted_time}] ' +
                f'does not satisfy min reposting delay {min_delay} hours'
            )
            return False

        # If no post has been made to a subreddit more than max threshold period
        # allow to post
        max_delay = self._max_reposting_delay
        if not Executor._within_last_hours(last_posted_time, max_delay, timestamp):
            logging.info(
                '[Admission Control] ALLOWED: ' +
                f'Most recent post on [{subreddit_name}] at [{last_posted_time}] ' +
                f'exceeds max reposting delay {max_delay} hours. '
            )
            return True

        # If any earlier submission is on the frontpage of that subreddit
        # delay new submission for this round
        is_new = self._reddit.is_on_frontpage(subreddit_name, "new", threshold=self._subreddit_frontpage_shreshold)
        is_hot = self._reddit.is_on_frontpage(subreddit_name, "hot", threshold=self._subreddit_frontpage_shreshold)
        if is_new:
            msg = "new listings"
        if is_hot:
            msg = "hot listings"

        if is_new or is_hot:
            logging.info(
                '[Admission Control] DENIED: ' +
                f'Most recent post on [{subreddit_name}] at [{last_posted_time}] ' +
                f'satisfy min reposting delay {min_delay} hours. ' +
                f'However, found earlier submission within top [{self._subreddit_frontpage_shreshold}] of ' +
                f'[{msg}]'
            )
            return False

        logging.info(
            '[Admission Control] ALLOWED: ' +
            f'Most recent post on [{subreddit_name}] at [{last_posted_time}] ' +
            f'satisfies min reposing period of {min_delay} hours. ' +
            'No earlier submission found in hot nor new listings.'
        )

        return True

    def _update_documents_on_success(self, task, subreddit, submission_url):
        timestamp = time.time()
        task.update_on_success(subreddit, timestamp, submission_url)

        # Update task in db
        self._db.task.update(Task.to_dict(task))

        # Update subreddit_last_posted record
        self._db.subreddit_record.upsert(subreddit.name, {
            "_id": subreddit.name,
            "lastPostedTimestamp": timestamp
        })

    def _update_documents_on_error(self, task, subreddit, error):
        timestamp = time.time()
        task.update_on_error(subreddit, timestamp, error)

        # Update task in db
        self._db.task.update(Task.to_dict(task))

    def run(self):
        while True:
            if self._is_in_running_window(datetime.now()):
                logging.info("In running window. Starting processing tasks")
                self._process_tasks()
            else:
                logging.info("Out of running window.")

            # Run the cycle at time intervals
            logging.info(f'This run cycle is over. Sleep {self._run_interval_seconds // 60} minutes')
            sleep_with_progess(self._run_interval_seconds)
