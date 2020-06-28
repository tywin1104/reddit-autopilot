import copy
import json
import requests
from requests.auth import HTTPBasicAuth
import urllib.parse


class DbOperationException(Exception):
    pass


class CouchdbService:
    @staticmethod
    def _selector(body):
        return {
            "selector": body
        }

    def __init__(self, url, user, password):
        self._url = url
        self._user = user
        self._password = password

    def _call_api(self, path, verb='GET', data={}):
        api_base_url = self._url
        headers = {
            'content-type': 'application/json'
        }
        response = requests.request(
            verb,
            auth=HTTPBasicAuth(self._user, self._password),
            headers=headers,
            url=urllib.parse.urljoin(api_base_url, path),
            data=json.dumps(data)
        )
        return response

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

    def _create_db(self, db_name):
        r = self._call_api(f'/{self._db_name}', verb='PUT')
        self._check_error(
            r,
            err_msg=f'Failed to initially create db: {self._db_name}',
        )

    def _setup(self):
        r = self._call_api(f'/{self._db_name}')
        if r.status_code == requests.codes.not_found:
            self._create_db(self._db_name)

    def create_doc(self, id, doc):
        r = self._call_api(f'/{self._db_name}/{id}', verb='PUT', data=doc)
        self._check_error(
            r,
            err_msg=f'Failed to create db cocument for {self._db_name}',
        )

    def db(self, name):
        newobj = copy.copy(self)
        newobj._db_name = name
        newobj._setup()
        return newobj

    def get_docs(self, filter):
        selector = CouchdbService._selector(filter)
        r = self._call_api(f'/{self._db_name}/_find', verb='POST', data=selector)
        self._check_error(
            r,
            err_msg=f'Failed to get documents for db {self._db_name}',
        )
        return r.json()['docs']

    def get_doc_by_id(self, id):
        docs = self.get_docs({
            '_id': id
        })

        if len(docs) == 0:
            return None

        return docs[0]

    def update_doc(self, new_doc):
        id = new_doc['_id']
        existing_record = self.get_doc_by_id(id)

        if not existing_record:
            raise DbOperationException("Document for update does not exist")

        rev = existing_record['_rev']

        new_doc['_rev'] = rev

        r = self._call_api(f'/{self._db_name}/{id}?rev={rev}', verb='PUT', data=new_doc)
        self._check_error(
            r,
            err_msg=f'Failed to update doc for db {self._db_name} with id {id} & rev {rev}',
        )

    def upsert_doc(self, id, doc):
        existing_record = self.get_doc_by_id(id)

        if not existing_record:
            self.create_doc(id, doc)
        else:
            if "_id" not in doc:
                doc['_id'] = id
            self.update_doc(doc)
