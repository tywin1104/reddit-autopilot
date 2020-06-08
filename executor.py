import time
from datetime import datetime, timedelta
import logging
import traceback


class Executor:
    def __init__(
        self, reddit, db,
        running_window=(8,22),
        min_reposting_dalay=12,
        max_reposing_delay=24,
        subreddit_frontpage_shreshold=10,
        run_period=120
    ):
        self.reddit = reddit
        self.db = db
        # only allow postes to be made during running_window
        self.running_window = running_window
        self.min_reposting_dalay = min_reposting_dalay
        self.max_reposting_relay = max_reposing_delay
        self.subreddit_frontpage_shreshold = subreddit_frontpage_shreshold
        self.run_period = run_period

    def run(self):
        while True:
            if self.is_in_running_window():
                logging.info("In running window. Starting processing tasks")
                self.process_tasks()
            else:
                logging.info("Out of running window")

            logging.info("Collecting stats for existing submissions")
            self.collect_stats()

            # Run the cycle at time intervals
            logging.info(f'This run cycle is over. Sleep {self.run_period // 60} minutes')
            time.sleep(self.run_period)

    def is_in_running_window(self):
        hour = datetime.now().hour
        start, end = self.running_window
        return start <= hour <= end

    def collect_stats(self):
        pass

    def process_tasks(self):
        uncompleted_tasks = self.db.task.get_uncompleted()
        logging.info(f'Found total {len(uncompleted_tasks)} uncompleted tasks')
        for task in uncompleted_tasks:
            try:
                self.process_task(task)
            except Exception as e:
                logging.error(f'Failed to process task {task["_id"]} : {e}')
                traceback.print_exc()

        logging.info(f'All tasks are processed for this round. Sleeping until next round')

    def process_task(self, task):
        logging.info(f'Start processing task {task["_id"]}')
        subreddits = task.get('subreddits', [])
        posted = False
        for index, subreddit_block in enumerate(subreddits):
            # Wait for some time to prevent reddit spamming detection
            subreddit = subreddit_block['name']
            if posted:
                time.sleep(60)
                logging.info("Post complete. Sleeping for a while...")
                posted = False

            if not subreddit_block['posted'] and self.should_post(task, subreddit):
                self.post(task, index, subreddit)
                posted = True
            logging.info(f'{task["_id"]} processed successfully')


    def post(self, task, index, subreddit):
        if not task['titles']:
            raise Exception("No available titles specified for this task")

        title = task['titles'][index % len(task['titles'])]

        # Make post to subreddit
        post_url = self.reddit.post(subreddit, title, task['gif_link'])
        logging.info(f'Posted {post_url} successfully')

        timestamp = time.time()
        new_task = self.update_task(task, subreddit, post_url, timestamp)
        # Update task in db
        self.db.task.update(new_task)

        # Update subreddit_last_posted record db
        self.db.subreddit_record.upsert({
            "_id": subreddit,
            "lastPostedTimestamp": timestamp
        })

    def update_task(self, task, subreddit, post_url, timestamp):
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

    def should_post(self, task, subreddit):
        now = datetime.now()
        records = self.db.subreddit_record.get(subreddit)
        # first time posting on that subreddit, should allow
        if not records:
            logging.info(f'First time posting on [{subreddit}]')
            return True

        record = records[0]
        last_posted_time = datetime.fromtimestamp(record['lastPostedTimestamp'])

        # Do not repost to the same subreddit within the min thereshold period
        # this is in place to prevent spamming the subreddits
        min_delay = self.min_reposing_delay
        if self.reddit.is_low_volume(subreddit):
            min_delay *= 2

        if now - timedelta(self.min_delay) <= last_posted_time:
            logging.info(
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'does not satisfy min reposting delay {self.min_reposting_dalay} hours. ' +
                f'Will not schedule this post at this time'
            )
            return False

        # If a post has not been made to a subreddit more than max threshold
        # allow to post it
        max_delay = self.max_reposing_delay
        if self.reddit.is_low_volume(subreddit):
            max_delay *= 2
        if now - timedelta(max_delay) <= last_posted_time:
            logging.info(
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'exceeds max reposting delay {self.max_reposting_dalay} hours. ' +
                f'Will submit this post now'
            )
            return True

        # If any earlier submission is on the frontpage of that subreddit
        # delay new submission and check next round
        is_new = self.reddit.is_on_frontpage(subreddit, "new", threshold=self.subreddit_frontpage_shreshold)
        is_hot = self.reddit.is_on_frontpage(subreddit, "hot", threshold=self.subreddit_frontpage_shreshold)
        if is_new:
            msg = "new listings"
        if is_hot:
            msg = "hot listings"

        if is_new or is_hot:
            logging.info(
                f'Most recent post on [{subreddit}] at [{last_posted_time}] ' +
                f'within allowed reposting time window. ' +
                f'However, found earlier submission within top [{self.subreddit_frontpage_shreshold}] of ' +
                f'{msg}'
            )
            return False

        return True