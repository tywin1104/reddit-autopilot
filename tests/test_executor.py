from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock
from src.db import DbService
from src.reddit import RedditService
from src.executor import Executor
from src.task import Task, SubredditTask


@pytest.fixture
def task_obj():
    return Task(
        id="1",
        link="https://fake-link.com",
        crosspost_source_link="https://reddit.com/fake-post",
        reply_content="sample reply",
        completed=False,
        subreddits=[
            SubredditTask(name="subreddit1", flair_id="fake-flair-id", posted=False),
            SubredditTask(name="subreddit2", posted=False),
            SubredditTask(name="subreddit3", posted=False)
        ]
    )


@pytest.fixture
def mock_reddit():
    return Mock(spec=RedditService)


@pytest.fixture
def mock_db():
    return Mock()


def test_crosspost(mock_reddit, mock_db, task_obj):
    executor = Executor(mock_reddit, mock_db, min_reposting_delay=12, max_reposting_delay=24)
    mock_reddit.crosspost.return_value = "fake-link"
    post_url = executor._crosspost(task_obj, task_obj.subreddits[0])
    mock_reddit.crosspost.assert_called_with(
        task_obj.subreddits[0].name, task_obj.crosspost_source_link,
        flair_id=task_obj.subreddits[0].flair_id, nsfw=task_obj.nsfw
    )
    assert(post_url == "fake-link")


def test_should_post_first_time(mock_reddit, mock_db):
    executor = Executor(mock_reddit, mock_db, min_reposting_delay=12, max_reposting_delay=24)
    record = []
    result = executor._should_post(record, datetime.now())
    assert(result)


def test_should_post_exceed_max_reposting_limit(mock_reddit, mock_db):
    executor = Executor(mock_reddit, mock_db, min_reposting_delay=12, max_reposting_delay=24)
    record = {
        "name": "subreddit1",
        "lastPostedTimestamp": 1593526695.604652
    }
    result = executor._should_post(record, datetime.fromtimestamp(record['lastPostedTimestamp']) + timedelta(hours=25))
    assert(result)


def test_should_post_below_min_reposting_limit(mock_reddit, mock_db):
    executor = Executor(mock_reddit, mock_db, min_reposting_delay=12, max_reposting_delay=24)
    record = {
        "name": "subreddit1",
        "lastPostedTimestamp": 1593526695.604652
    }
    result = executor._should_post(record, datetime.fromtimestamp(record['lastPostedTimestamp']) + timedelta(hours=3))
    assert(not result)


def test_should_post_within_limits_not_on_feeds(mock_reddit, mock_db):
    executor = Executor(mock_reddit, mock_db, min_reposting_delay=12, max_reposting_delay=24)
    record = {
        "name": "subreddit1",
        "lastPostedTimestamp": 1593526695.604652
    }
    mock_reddit.is_on_frontpage.return_value = False
    mock_reddit.is_on_frontpage.return_value = False
    result = executor._should_post(record, datetime.fromtimestamp(record['lastPostedTimestamp']) + timedelta(hours=16))
    mock_reddit.is_on_frontpage.assert_called_with(
        "subreddit1", "hot", threshold=executor._subreddit_frontpage_shreshold
    )
    assert(result)


def test_should_post_within_limits_on_feeds(mock_reddit, mock_db):
    executor = Executor(mock_reddit, mock_db, min_reposting_delay=12, max_reposting_delay=24)
    record = {
        "name": "subreddit1",
        "lastPostedTimestamp": 1593526695.604652
    }
    mock_reddit.is_on_frontpage.return_value = True
    result = executor._should_post(record, datetime.fromtimestamp(record['lastPostedTimestamp']) + timedelta(hours=16))
    assert(not result)
