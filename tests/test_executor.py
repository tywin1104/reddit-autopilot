from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock, patch
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
            SubredditTask(name="subreddit1", flair_id="fake-flair-id", processed=False),
            SubredditTask(name="subreddit2", processed=False),
            SubredditTask(name="subreddit3", processed=False)
        ]
    )


@pytest.fixture
def task_obj_no_crosspost():
    return Task(
        id="2",
        link="https://fake-link.com",
        reply_content="sample reply",
        completed=False,
        subreddits=[
            SubredditTask(name="subreddit1", flair_id="fake-flair-id", processed=False),
            SubredditTask(name="subreddit2", processed=False),
            SubredditTask(name="subreddit3", processed=False)
        ],
        title="fake-title-provided"
    )


@pytest.fixture
def task_obj_only_crosspost():
    return Task(
        id="3",
        crosspost_source_link="https://reddit.com/fake-post",
        completed=False,
        subreddits=[
            SubredditTask(name="subreddit1", flair_id="fake-flair-id", processed=False),
            SubredditTask(name="subreddit2", processed=False),
            SubredditTask(name="subreddit3", processed=False)
        ]
    )


@pytest.fixture
def mock_reddit():
    return Mock(spec=RedditService)


@pytest.fixture
def mock_db():
    return Mock()


@pytest.fixture
def mock_executor(mock_reddit, mock_db):
    return Executor(mock_reddit, mock_db, min_reposting_delay=12, max_reposting_delay=24)


def test_crosspost(mock_reddit, mock_executor, task_obj):
    mock_reddit.crosspost.return_value = "fake-link"
    post_url = mock_executor._crosspost(task_obj, task_obj.subreddits[0])
    mock_reddit.crosspost.assert_called_with(
        task_obj.subreddits[0].name, task_obj.crosspost_source_link,
        flair_id=task_obj.subreddits[0].flair_id, nsfw=task_obj.nsfw
    )
    assert(post_url == "fake-link")


def test_should_post_first_time(mock_executor):
    record = []
    result = mock_executor._should_post(record, datetime.now())
    assert(result)


@pytest.mark.parametrize('delta_hours, expected', [(3, False), (25, True)])
def test_should_post_not_first_time(mock_executor, delta_hours, expected):
    record = {
        "_id": "subreddit1",
        "lastPostedTimestamp": 1593526695.604652
    }
    result = mock_executor._should_post(record, datetime.fromtimestamp(record['lastPostedTimestamp']) + timedelta(hours=delta_hours))
    assert(result == expected)


@pytest.mark.parametrize('is_on_frontpage, expected', [(True, False), (False, True)])
def test_should_post_with_frontpage_check(mock_reddit, mock_executor, is_on_frontpage, expected):
    record = {
        "_id": "subreddit1",
        "lastPostedTimestamp": 1593526695.604652
    }
    mock_reddit.is_on_frontpage.return_value = is_on_frontpage
    result = mock_executor._should_post(record, datetime.fromtimestamp(record['lastPostedTimestamp']) + timedelta(hours=16))
    mock_reddit.is_on_frontpage.assert_called_with(
        "subreddit1", "hot", threshold=mock_executor._subreddit_frontpage_shreshold
    )
    assert(result == expected)


def test_get_title_from_crosspost(mock_executor, mock_reddit, task_obj):
    mock_reddit.get_post_title.return_value = "fake-title"
    result = mock_executor._get_title(task_obj)
    assert(result == "fake-title")


def test_get_title_from_task(mock_executor, task_obj_no_crosspost):
    result = mock_executor._get_title(task_obj_no_crosspost)
    assert(result == task_obj_no_crosspost.title)


def test_get_operations_both(mock_executor, task_obj):
    result = mock_executor._get_operations(task_obj)
    assert([mock_executor._crosspost, mock_executor._post_direct] == result)


def test_get_operations_direct_post_only(mock_executor, task_obj_no_crosspost):
    result = mock_executor._get_operations(task_obj_no_crosspost)
    assert([mock_executor._post_direct] == result)


def test_get_operations_crosspost_only(mock_executor, task_obj_only_crosspost):
    result = mock_executor._get_operations(task_obj_only_crosspost)
    assert([mock_executor._crosspost] == result)

