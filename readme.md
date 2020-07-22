

# Reddit Autopilot - Autopilot Your Reddit Posts



A **smart** service for making routine posts to target subreddits with the content pre-configured within the app. A great companion for your online marketing compaign in Reddit platform.

Configure, Run, and Autopilot!

---


### Features

1. **Ease of setting up tasks with human-readble JSON documents**
   * Each task JSON document represents one custom post that is going to be posted to various target subreddits in the future. Populate multiple task documents at once, run the app and let it autopilot. 
2. **Smart spamming prevention mechanism for subreddits**
   * Never spamming a subreddit by keeping track of last submission timestamp for individual subreddits and adheres to configured minimum & maximum reposting delay for each subreddit.
3. **Smooth handling of Reddit API Ratelimiting**
   * Strict ratelimiting will be imposed for new Reddit accounts with low Karmas. The app will pause accordingly to the ratelimiting requirement and not making Reddit API unhappy by flooding requests. 
4. **Support automatic scheduled reply**
   * The app supports setting up auto reply to the newly submitted posts. Reply could be setup in individual tasks with flexible Markdown format.
5. **Fleixble post types**
   * Currently the app supports link posts and crosspost posts. Three modes of operation are available to be configured for individual tasks:
        * Crosspost with direct link post as fallback
        * Crosspost only
        * Direct link post only
6. **Post Flair Supported**
   * Configurable use of flairs when making post to subreddits. Enable post automation even for subreddits with mandatory post_flair constraints
  
---

## Get Started

> Requirements to start the app locally:
Python (version 3.7+), 
Apache CouchDB (See https://couchdb.apache.org/ for setup instructions)
Reddit Developer API Credentials (https://ssl.reddit.com/prefs/apps/)

  
  After obtaining required dependencies and cloned the repo, follow the steps to get started
 
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

Start adding a few task JSONs to the CouchDB `tasks` collections and run the app `python main.py` to start processing all uncompleted tasks! (See below for the format of task json documents)

If some of your tasks are configured with auto reply, you would need to start a separate terminal session and run `huey_consumer.py my_app.huey -k process -w 4` This process needs to be keep alive while handling all configured auto replies for your tasks.


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
            "name": "subreddit1",
            "posted": false
        },
        {
            "name": "subreddit2",
            "posted": false,
        },
        {
            "name": "subreddit3",
            "posted": false,
            "flair_id": "acfg4c2c-b45c-12ea-a9ob-0e8bd1d23233"
        }
    ]
}
```
**Note**: 
`link` -> URL for the link to be posted
`crosspost_source_link` -> A reddit post that serves as the source of crosspost.
`reply_content` -> Markdown format for the reply content
These three fields above determins the mode of opeartions to post for this task.


> when both `crosspost_source_link` and `link` are set, the app will attempt to crosspost from the source and if fails, will direct post the link as fallback.
If only `crosspost_source_link` or `link` is specified, the app will only attempt the desired opeartion. 

`subreddits` -> 
  - Define as many target subreddits you want here
  - for some subreddits the post flair is mandatory, in this case, you could supply the `flair_id` and the app will apply the specified flair when making post to this subreddit for this task

---

## FAQ

- **How should I generate and populate tasks to CouchDB**
Reddit Autopilot sits in the consumer side of the stack and it consumers CouchDB task collections and behave accordingly according to the setup. Users are free to choose any approach in terms of generating and populating task documents to the DB whether it is from an UI application or through custom scripts as different use cases may choose different strageties.
`Fauxton` is recommended if doing so manually
https://couchdb.apache.org/fauxton-visual-guide/ 

- **How much does it cost??**
Unlike other similar premium services like Later for Reddit / Delay for Reddit, Reddit Autopilot is open-sources and **completely free**. However, this service focuses more on the post scheduling part and does not provide same feature sets as other similar services. 
Moreover, **there are no daily post limits** imposed. Reddit API rate limiting is the only constraint here. However, keep in mind that it is a bad idea to spam on subreddits and you could be banned from subreddits or even the reddit platform from doing so. 

- **How does Reddit Autopilot post on my behalf?**
Reddit Autopilot uses the Reddit API via OAuth2. All the sensitive reddit credentials are configured locally.

## License

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)
