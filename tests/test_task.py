import pytest
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
def task_dict():
    return {
        "_id": "1",
        "link": "https://fake-link.com",
        "crosspost_source_link": "https://reddit.com/fake-post",
        "reply_content": "sample reply",
        "completed": False,
        "subreddits": [
            {"name": "subreddit1", "flair_id": "fake-flair-id", "posted": False},
            {"name": "subreddit2", "posted": False},
            {"name": "subreddit3", "posted": False}
        ]
    }


def test_from_dict(task_dict):
    result_obj = Task.from_dict(task_dict)

    assert(result_obj.id == "1")
    assert(not result_obj.title)
    assert(len(result_obj.subreddits) == 3)
    assert(isinstance(result_obj.subreddits[0], SubredditTask))
    assert(result_obj.subreddits[0].name == "subreddit1" and result_obj.subreddits[0].flair_id == "fake-flair-id")
    assert(not result_obj.subreddits[1].flair_id and not result_obj.subreddits[1].error)


def test_to_dict(task_obj):
    result_dict = Task.to_dict(task_obj)

    assert(result_dict['_id'] == "1")
    assert(result_dict['link'] == "https://fake-link.com")
    assert(not result_dict['title'])

    assert(len(result_dict['subreddits']) == 3)
    assert(isinstance(result_dict['subreddits'][0], dict))

    assert(result_dict['subreddits'][0]['name'] == "subreddit1" and result_dict['subreddits'][0]['flair_id'] == "fake-flair-id")
    assert(not result_dict['subreddits'][1]['posted'] and not result_dict['subreddits'][1]['error'])


def test_task_update_on_success(task_obj):
    task = task_obj
    task.update_on_success(task.subreddits[0], "2020-08-01 18:32 UTC", "https://fake-post.com")

    assert(task.subreddits[0].posted)
    assert(task.subreddits[0].timestamp == "2020-08-01 18:32 UTC")
    assert(task.subreddits[0].link == "https://fake-post.com")
    assert(not task.subreddits[0].error)

    task.update_on_success(task.subreddits[1], "2020-08-01 18:42 UTC", "https://fake-post2.com")

    assert(task.subreddits[1].posted)
    assert(task.subreddits[1].timestamp == "2020-08-01 18:42 UTC")
    assert(task.subreddits[1].link == "https://fake-post2.com")
    assert(not task.subreddits[0].error)


def test_task_update_on_error(task_obj):
    task = task_obj
    task.update_on_error(task.subreddits[1], "2020-08-01 18:33 UTC", Exception("Some error"))

    assert(not task.subreddits[1].posted and not task.subreddits[1].link)
    assert(task.subreddits[1].timestamp == "2020-08-01 18:33 UTC")
    assert(task.subreddits[1].error == "Some error")
