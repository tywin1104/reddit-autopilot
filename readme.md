

# Reddit Autopilot - Autopilot Your Reddit Posts



A **smart** service for making routine posts to target subreddits with pre-configured content. A great companion for your online marketing campaign in the Reddit platform.

Configure, Run, and Autopilot!

---


### Features

1. **Ease of setting up tasks with human-readable JSON documents**
   * Each task JSON document represents one custom post that is going to be posted to various target subreddits in the future. Populate multiple task documents at once, run the app and let it autopilot. 
2. **Smart spamming prevention mechanism for subreddits**
   * Never spamming a subreddit by keeping track of last submission timestamp for individual subreddits and adheres to the configured minimum & maximum reposting delay for each subreddit.
3. **Smooth handling of Reddit API Rate-limiting**
   * Strict rate-limiting will be imposed for new Reddit accounts with low Karmas. The app will pause accordingly to the rate-limiting requirement and not making Reddit API unhappy by flooding requests. 
4. **Support automatic reply**
   * The app supports setting up auto-replies to the newly submitted posts. The reply could be set up in individual tasks with flexible Markdown format.
5. **Fleixble post types**
   * Currently, the app supports link posts and crosspost posts. Three modes of operation are available to be configured for individual tasks:
        * Crosspost with direct link post as fallback
        * Crosspost only
        * Direct link post only
6. **Post Flair Supported**
   * Configurable use of flairs when making posts to subreddits. Enable post automation even for subreddits with mandatory post_flair constraints
  
---

## Get Started

> Requirements to start the app locally:

> Python (version 3.7+), 

> Apache CouchDB (See https://couchdb.apache.org/ for setup instructions)

> Reddit Developer API Credentials (https://ssl.reddit.com/prefs/apps/)

  
  After obtaining the required dependencies and cloned the repo, follow the steps to get started
 
 Install required python dependencies, we use pipenv to manage Python dependencies:
 See https://pipenv-fork.readthedocs.io/en/latest/ for instructions on installing pipenv
 ```
 pipenv --python 3
 pipenv shell
 pipenv install
 ```
 
 Fill in configuration files `configs.yaml`. See comments for detailed explanation on each configurable items.
 
 Create a file named `praw.ini` in the root of the cloned directory and supply credentials for your Reddit Developer APIs
 ```
[DEFAULT]
client_id=<reddit app client id>
client_secret=<reddit app client secret>
password=<your reddit password>
username=<your reddit username>
user_agent=<platform>:<app ID>:<version string> (by u/<Reddit username>
 ```
 Read more at https://github.com/reddit-archive/reddit/wiki/API

Start adding a few task JSONs to the CouchDB `tasks` collections and run the app `python main.py` to start processing all uncompleted tasks! (See below for the format of task JSON documents)

If some of your tasks are configured with auto-reply, you would need to start a separate terminal session and run

```
huey_consumer.py src.jobs.huey 
```

This process needs to be kept alive while handling all configured auto-replies for your tasks.


---

### Task JSON Document Details

In general, the task JSON document should have the below format:
```
{
    "_id": "1", 
    "link": "https://the-link-url-to-post"
    "crosspost_source_link": "https://www.reddit.com/r/example/comments/hvcqse/example/",
    "reply_content": "content to reply to the newly made posts. Markdown format",
    "completed": false,
    "subreddits": [
        {
            "name": "subreddit1"
        },
        {
            "name": "subreddit2",
        },
        {
            "name": "subreddit3",
            "flair_id": "acfg4c2c-b45c-12ea-a9ob-0e8bd1d23233"
        }
    ],
    "nsfw": false,
    "title": "title"
}
```

`link` -> URL for the link to be posted

`crosspost_source_link` -> A reddit post that serves as the source for crossposting.


`reply_content` -> Markdown format for the reply content (Optional)

`title` -> Title string if intend to post directly

`nsfw` -> NSFW option (Default option is false)

These three fields above determins the mode of opeartions to post for this task.


> when both `crosspost_source_link` and `link` are set, the app will attempt to crosspost from the source and if fails, will direct post the link as a fallback plan.
If only one of `crosspost_source_link` or `link` is specified, the app will only attempt the desired single opeartion. 

**!!** Title (for direct post) must be supplied if crosspost_source_link is not specified

`subreddits`
  - Define as many target subreddits you want here
  - For some subreddits the post flair is mandatory, in this case, you could supply the `flair_id` and the app will apply the specified flair when making posts to this subreddit for this task

---

## FAQ

 **How should I generate and populate tasks to CouchDB**

Reddit Autopilot sits on the consumer side of the stack and it consumers CouchDB task documents and behave according to the setup. Users are free to choose any approach in terms of generating and populating task documents to the DB whether it is from a UI application or through custom scripts as the best way to handle this is highly dependent on different use cases.
`Fauxton` is recommended if doing so manually
https://couchdb.apache.org/fauxton-visual-guide/ 

 **How much does it cost?**

Unlike other similar premium services like Later for Reddit / Delay for Reddit, Reddit Autopilot is open-sourced and **completely free**. However, this service focuses on continueous routine posting rather than explicit scheduling of posts and thus does not provide same feature sets as other similar services. 
Moreover, **there are no daily post limits** imposed. Reddit API rate limiting is the only constraint here. However, keep in mind that it is a bad idea to spam on subreddits and you could be banned from subreddits or even the Reddit platform from doing so. 

 **How does Reddit Autopilot post on my behalf?**

Reddit Autopilot uses the Reddit API via OAuth2. All the sensitive Reddit credentials are configured locally.


 **Feature Request**

For feature requests or bug reports, please open an git issue for this repo.

## License

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)
