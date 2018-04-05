from flask import Flask
from appkernel import AppKernelEngine, Model, Repository, Service, Parameter, NotEmpty, Regexp, Past
from datetime import datetime
from appkernel.repository import MongoRepository
from test_util import User
import uuid, os, sys
import pytest

try:
    import simplejson as json
except ImportError:
    import json

# crud
# method not allowed
# test some error
# more params on the query than supported by the method
# less params than supported on the query
# test not just date but time too
# todo: has field
# todo: contains element size
# todo: try class based discovery before regular expression matching
# todo: contains roles

flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = 'S0m3S3cr3tC0nt3nt!'
flask_app.testing = True


@pytest.fixture
def app():
    return flask_app


@pytest.fixture
def user_dict():
    return {
        "birth_date": "1980-06-30T00:00:00",
        "description": "some description",
        "name": "some_user",
        "password": "some_pass",
        "roles": [
            "User",
            "Admin",
            "Operator"
        ]
    }


def setup_module(module):
    current_file_path = os.path.dirname(os.path.realpath(__file__))
    print '\nModule: >> {} at {}'.format(module, current_file_path)
    kernel = AppKernelEngine('test_app', app=flask_app, cfg_dir='{}/../'.format(current_file_path), development=True)
    kernel.register(User)


def setup_function(function):
    """ executed before each method call
    """
    print ('\n\nSETUP ==> ')
    User.delete_all()


def test_get_basic(client):
    u = User().update(name='some_user', password='some_pass')
    user_id = u.save()
    rsp = client.get('/users/{}'.format(user_id))
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200, 'the status code is expected to be 200'
    result = rsp.json
    assert result.get('id') == user_id
    assert 'type' in result
    assert result.get('type') == 'User'


def test_get_not_found(client):
    rsp = client.get('/users/1234')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 404, 'the status code is expected to be 404'
    assert rsp.json.get('type') == 'ErrorMessage'


def test_get_invalid_url(client):
    rsp = client.get('/uzerz/1234')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 404, 'the status code is expected to be 404'
    assert rsp.json.get('type') == 'ErrorMessage'


def test_delete_basic(client):
    u = User().update(name='some_user', password='some_pass')
    user_id = u.save()
    rsp = client.delete('/users/{}'.format(user_id))
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200, 'the status code is expected to be 200'
    assert rsp.json.get('result') == 1


def test_delete_invalid_url(client):
    rsp = client.delete('/uzerz/1234')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 404, 'the status code is expected to be 404'
    assert rsp.json.get('type') == 'ErrorMessage'


def test_get_query_between_dates(client):
    u = User().update(name='some_user', password='some_pass')
    u.birth_date = datetime.strptime('1980-06-30', '%Y-%m-%d')
    u.description = 'some description'
    u.roles = ['User', 'Admin', 'Operator']
    user_id = u.save()
    print('\nSaved user -> {}'.format(User.find_by_id(user_id)))
    rsp = client.get('/users/?birth_date=>1980-06-30&birth_date=<1985-08-01&logic=AND')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200, 'the status code is expected to be 200'
    assert rsp.json[0].get('id') == user_id


def test_get_query_between_not_found(client):
    rsp = client.get('/users/?birth_date=>1980&birth_date=<1985&logic=AND')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 404, 'the status code is expected to be 404'
    assert rsp.json.get('type') == 'ErrorMessage'


def test_find_date_range(client):
    base_birth_date = datetime.strptime('1980-01-01', '%Y-%m-%d')
    for m in xrange(1, 13):
        u = User().update(name='multi_user_{}'.format(m)).update(password='some default password'). \
            append_to(roles=['Admin', 'User', 'Operator']).update(description='some description').update(
            birth_date=base_birth_date.replace(month=m))
        u.save()
    assert User.count() == 12
    rsp = client.get('/users/?birth_date=>1980-03-01&birth_date=<1980-05-30&logic=AND')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    response_list = rsp.json
    assert len(response_list) == 3


def create_a_user(name, password, description):
    u = User().update(name=name).update(password=password). \
        append_to(roles=['Admin', 'User', 'Operator']).update(description=description)
    u.save()
    return u


def create_50_users():
    for i in xrange(1, 51):
        u = User().update(name='multi_user_{}'.format(i)).update(password='some default password'). \
            append_to(roles=['Admin', 'User', 'Operator']).update(description='some description').update(sequence=i)
        u.save()
    assert User.count() == 50


def create_john_jane_and_max():
    john = create_a_user('John', 'a password', 'John is a random guy')
    jane = create_a_user('Jane', 'a password', 'Jane is a random girl')
    max = create_a_user('Max', 'a password', 'Jane is a random girl')


def test_find_range_in_user_sequence(client):
    create_50_users()
    rsp = client.get('/users/?sequence=>20&sequence=<25&logic=OR')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    response_object = rsp.json
    assert len(response_object) == 5


def test_find_less_than(client):
    create_50_users()
    rsp = client.get('/users/?sequence=<5')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    response_object = rsp.json
    assert len(response_object) == 5


def test_find_greater_than(client):
    create_50_users()
    rsp = client.get('/users/?sequence=>45')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    response_object = rsp.json
    assert len(response_object) == 5


def test_sort_by(client):
    create_50_users()
    rsp = client.get('/users/?sequence=>45&sort_by=sequence')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    prev_user_seq = None
    for uzer in rsp.json:
        if prev_user_seq:
            assert uzer.get('sequence') == prev_user_seq + 1
        prev_user_seq = uzer.get('sequence')
        assert prev_user_seq is not None


def test_sort_by(client):
    create_50_users()
    rsp = client.get('/users/?sequence=>45&sort_by=sequence&sort_order=DESC')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200
    prev_user_seq = None
    for uzer in rsp.json:
        if prev_user_seq:
            assert uzer.get('sequence') == prev_user_seq - 1
        prev_user_seq = uzer.get('sequence')
        assert prev_user_seq is not None


def test_pagination(client):
    create_50_users()
    for page in range(1, 6):
        print('\n== Page: ({}) ===='.format(page))
        rsp = client.get('/users/?page={}&page_size=5'.format(page))
        print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
        assert rsp.status_code == 200
        result_set = rsp.json
        assert len(result_set) == 5
        assert result_set[4].get('sequence') == page * 5, 'the sequence number should be a multiple of 5'


def test_pagination_with_sort(client):
    create_50_users()
    for page in range(1, 6):
        print('\n== Page: ({}) ===='.format(page))
        rsp = client.get('/users/?page={}&page_size=5&sort_by=sequence&sort_order=DESC'.format(page))
        print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
        assert rsp.status_code == 200
        result_set = rsp.json
        assert len(result_set) == 5
        assert result_set[0].get('sequence') == 55 - (page * 5)


def test_find_contains(client):
    john = create_a_user('John Doe', 'a password', 'John is a random guy')
    jane = create_a_user('Jane Doe', 'a password', 'Jane is a random girl')
    rsp = client.get('/users/?name=~Jane')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    rsp_object = rsp.json
    assert len(rsp_object) == 1
    assert rsp_object[0].get('name') == 'Jane Doe'

    rsp = client.get('/users/?name=~John')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    rsp_object = rsp.json
    assert len(rsp_object) == 1
    assert rsp_object[0].get('name') == 'John Doe'

    rsp = client.get('/users/?name=~Doe')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    rsp_object = rsp.json
    assert len(rsp_object) == 2


def test_find_exact_or(client):
    create_john_jane_and_max()
    rsp = client.get('/users/?name=Jane&name=John&logic=OR')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200
    assert len(rsp.json) == 2


def test_find_contains_or(client):
    create_john_jane_and_max()
    rsp = client.get('/users/?name=~Jane&name=~John&logic=OR')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200
    assert len(rsp.json) == 2


def test_search_for_nonexistent_field(client):
    john = create_a_user('John Doe', 'a password', 'John is a random guy')
    rsp = client.get('/users/?xxxx=Jane')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 404, 'the status code is expected to be 404'


def test_find_by_exact_match(client):
    john = create_a_user('John', 'a_password', 'John is a random guy')
    rsp = client.get('/users/?name=John')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200
    assert rsp.json[0].get('name') == 'John'


def test_find_boolean(client):
    john = create_a_user('John Doe', 'a password', 'John is a random guy')
    john.locked = True
    john.save()

    jane = create_a_user('Jane Doe', 'a password', 'Jane is a random girl')
    jane.locked = False
    jane.save()

    max = create_a_user('Max Mustermann', 'a password', 'Max is yet another random guy')

    rsp = client.get('/users/?locked=false')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.json[0].get('name') == 'Jane Doe'

    rsp = client.get('/users/?locked=true')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.json[0].get('name') == 'John Doe'

    rsp = client.get('/users/?locked=true&locked=false&logic=OR')
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert len(rsp.json) == 2


def test_post_user(client, user_dict):
    user_json = json.dumps(user_dict)
    print '\nSending: {}'.format(user_json)
    rsp = client.post('/users/', data=user_json)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 201, 'the status code is expected to be 200'
    document_id = rsp.json.get('result')
    user = User.find_by_id(document_id)
    print '\nLoaded user: {}'.format(user)
    assert user is not None
    assert len(user.roles) == 3


def test_post_incomplete_user(client, user_dict):
    del user_dict['name']
    user_json = json.dumps(user_dict)
    print '\nSending request: {}'.format(user_json)
    rsp = client.post('/users/', data=user_json)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 400, 'the status code is expected to be 400'
    assert rsp.json.get('type') == 'ErrorMessage'


def test_post_update_with_id(client, user_dict):
    user_json = json.dumps(user_dict)
    print '\nSending: {}'.format(user_json)
    rsp = client.post('/users/', data=user_json)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 201, 'the status code is expected to be 200'
    document_id = rsp.json.get('result')
    user_dict['id'] = document_id
    user_dict['name'] = 'changed name'
    user_json = json.dumps(user_dict)
    print '\nSending: {}'.format(user_json)
    rsp = client.post('/users/', data=user_json)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    user = User.find_by_id(rsp.json.get('result'))
    assert user.name == 'changed name'


def test_patch_user(client, user_dict):
    user_json = json.dumps(user_dict)
    print '\nSending: {}'.format(user_json)
    rsp = client.post('/users/', data=user_json)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 201, 'the status code is expected to be 200'
    document_id = rsp.json.get('result')
    user_url = '/users/{}'.format(document_id)
    rsp = client.patch(user_url, data=json.dumps({'description': 'patched description'}))
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    rsp = client.get(user_url)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200, 'the status code is expected to be 200'
    result_user = rsp.json
    assert result_user.get('description') == 'patched description'


def test_patch_nonexistent_field(client):
    john = create_a_user('John Doe', 'some pass', 'a silly description')
    user_url = '/users/{}'.format(john.id)
    rsp = client.patch(user_url, data=json.dumps({'locked': True}))
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    rsp = client.get(user_url)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 200, 'the status code is expected to be 200'
    assert rsp.json.get('locked')


def test_put_user(client, user_dict):
    user_json = json.dumps(user_dict)
    print '\nSending: {}'.format(user_json)
    rsp = client.post('/users/', data=user_json)
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    assert rsp.status_code == 201, 'the status code is expected to be 200'
    document_id = rsp.json.get('result')

    replacement_user = user_dict.copy()
    del replacement_user['birth_date']
    del replacement_user['description']
    replacement_user.update(id=document_id)
    replacement_user.update(name='changed user')
    replacement_user.update(locked=True)
    replacement_user.update(roles=[])
    replacement_user_json = json.dumps(replacement_user)
    print '\nSending: {}'.format(replacement_user_json)
    rsp = client.put('/users/', data=replacement_user_json)
    assert rsp.status_code >= 200
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    rsp = client.get('/users/'.format(document_id))
    print '\nResponse: {} -> {}'.format(rsp.status, rsp.data)
    returned_user = rsp.json
    assert returned_user[0].get('locked') == True
    assert returned_user[0].get('name') == 'changed user'
    assert len(returned_user[0].get('roles')) == 0
