import requests
from requests.auth import HTTPBasicAuth
import urllib.parse
import json

class CouchdbService:
    def __init__(self, url, user, password, db_name):
        self.url = url
        self.user = user
        self.password = password
        self.db_name = db_name
        self._setup()

    def _setup(self):
        r = self._call_api(f'/{self.db_name}')
        if r.status_code == requests.codes.not_found:
            self._create_db(self.db_name)

    def _check_error(
        self,
        response,
        err_msg="",
        accepted_codes=[
            requests.codes.accepted, requests.codes.created, requests.codes.ok
        ]):
        if response.status_code not in accepted_codes:
            json = response.json()
            message = err_msg + "\n" + json.get('error', "") + " : " + json.get('reason', "")
            raise DbOperationException(message)

    def create_doc(self, id, doc):
        r = self._call_api(f'/{self.db_name}/{id}', verb='PUT', data=doc)
        self._check_error(
            r,
            err_msg=f'Failed to initially create db: {self.db_name}',
        )

    def get_docs(self, selector):
        r = self._call_api(f'/{self.db_name}/_find', verb='POST', data=selector)
        self._check_error(
            r,
            err_msg=f'Failed to get documents for db {self.db_name}',
        )
        return r.json()['docs']

    def update_doc(self, id, rev, new_doc):
        r = self._call_api(f'/{self.db_name}/{id}?rev={rev}', verb='PUT', data=new_doc)
        self._check_error(
            r,
            err_msg=f'Failed to update doc for db {self.db_name} with id {id} & rev {rev}',
        )

    def _create_db(self, db_name):
        r = self._call_api(f'/{self.db_name}', verb='PUT')
        self._check_error(
            r,
            err_msg=f'Failed to initially create db: {self.db_name}',
        )

    def _call_api(self, path, verb='GET', data={}):
        api_base_url = self.url
        headers = {
            'content-type': 'application/json'
        }
        response = requests.request(
            verb,
            auth=HTTPBasicAuth(self.user, self.password),
            headers=headers,
            url=urllib.parse.urljoin(api_base_url, path),
            data=json.dumps(data)
        )
        return response

class DbOperationException(Exception):
    pass
