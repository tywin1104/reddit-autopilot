from huey import SqliteHuey

huey = SqliteHuey('testing')


@huey.task(retries=10, retry_delay=300)
def schedule_reply(submission, reply_content, reddit):
    '''
    schedule_reply will add task to reply a given submission via comment
    the scheduled task will run outside of main processing window to avoid
    excessive reddit API ratelimiting. Tasks run with retries & delays in between
    '''
    reddit.reply(submission, reply_content)
