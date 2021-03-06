from __future__ import unicode_literals
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError

import boto
from boto.exception import S3ResponseError
from boto.s3.key import Key
from boto.s3.connection import OrdinaryCallingFormat

from freezegun import freeze_time
import requests

import sure  # noqa

from moto import mock_s3bucket_path


def create_connection(key=None, secret=None):
    return boto.connect_s3(key, secret, calling_format=OrdinaryCallingFormat())


class MyModel(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def save(self):
        conn = create_connection('the_key', 'the_secret')
        bucket = conn.get_bucket('mybucket')
        k = Key(bucket)
        k.key = self.name
        k.set_contents_from_string(self.value)


@mock_s3bucket_path
def test_my_model_save():
    # Create Bucket so that test can run
    conn = create_connection('the_key', 'the_secret')
    conn.create_bucket('mybucket')
    ####################################

    model_instance = MyModel('steve', 'is awesome')
    model_instance.save()

    conn.get_bucket('mybucket').get_key('steve').get_contents_as_string().should.equal(b'is awesome')


@mock_s3bucket_path
def test_missing_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    bucket.get_key("the-key").should.equal(None)


@mock_s3bucket_path
def test_missing_key_urllib2():
    conn = create_connection('the_key', 'the_secret')
    conn.create_bucket("foobar")

    urlopen.when.called_with("http://s3.amazonaws.com/foobar/the-key").should.throw(HTTPError)


@mock_s3bucket_path
def test_empty_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("")

    bucket.get_key("the-key").get_contents_as_string().should.equal(b'')


@mock_s3bucket_path
def test_empty_key_set_on_existing_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar")

    bucket.get_key("the-key").get_contents_as_string().should.equal(b'foobar')

    key.set_contents_from_string("")
    bucket.get_key("the-key").get_contents_as_string().should.equal(b'')


@mock_s3bucket_path
def test_large_key_save():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("foobar" * 100000)

    bucket.get_key("the-key").get_contents_as_string().should.equal(b'foobar' * 100000)


@mock_s3bucket_path
def test_copy_key():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    bucket.copy_key('new-key', 'foobar', 'the-key')

    bucket.get_key("the-key").get_contents_as_string().should.equal(b"some value")
    bucket.get_key("new-key").get_contents_as_string().should.equal(b"some value")


@mock_s3bucket_path
def test_set_metadata():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = 'the-key'
    key.set_metadata('md', 'Metadatastring')
    key.set_contents_from_string("Testval")

    bucket.get_key('the-key').get_metadata('md').should.equal('Metadatastring')


@freeze_time("2012-01-01 12:00:00")
@mock_s3bucket_path
def test_last_modified():
    # See https://github.com/boto/boto/issues/466
    conn = create_connection()
    bucket = conn.create_bucket("foobar")
    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    rs = bucket.get_all_keys()
    rs[0].last_modified.should.equal('2012-01-01T12:00:00.000Z')

    bucket.get_key("the-key").last_modified.should.equal('Sun, 01 Jan 2012 12:00:00 GMT')


@mock_s3bucket_path
def test_missing_bucket():
    conn = create_connection('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket').should.throw(S3ResponseError)


@mock_s3bucket_path
def test_bucket_with_dash():
    conn = create_connection('the_key', 'the_secret')
    conn.get_bucket.when.called_with('mybucket-test').should.throw(S3ResponseError)


@mock_s3bucket_path
def test_bucket_deletion():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    key = Key(bucket)
    key.key = "the-key"
    key.set_contents_from_string("some value")

    # Try to delete a bucket that still has keys
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    bucket.delete_key("the-key")
    conn.delete_bucket("foobar")

    # Get non-existing bucket
    conn.get_bucket.when.called_with("foobar").should.throw(S3ResponseError)

    # Delete non-existant bucket
    conn.delete_bucket.when.called_with("foobar").should.throw(S3ResponseError)


@mock_s3bucket_path
def test_get_all_buckets():
    conn = create_connection('the_key', 'the_secret')
    conn.create_bucket("foobar")
    conn.create_bucket("foobar2")
    buckets = conn.get_all_buckets()

    buckets.should.have.length_of(2)


@mock_s3bucket_path
def test_post_to_bucket():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://s3.amazonaws.com/foobar", {
        'key': 'the-key',
        'file': 'nothing'
    })

    bucket.get_key('the-key').get_contents_as_string().should.equal(b'nothing')


@mock_s3bucket_path
def test_post_with_metadata_to_bucket():
    conn = create_connection('the_key', 'the_secret')
    bucket = conn.create_bucket("foobar")

    requests.post("https://s3.amazonaws.com/foobar", {
        'key': 'the-key',
        'file': 'nothing',
        'x-amz-meta-test': 'metadata'
    })

    bucket.get_key('the-key').get_metadata('test').should.equal('metadata')


@mock_s3bucket_path
def test_bucket_method_not_implemented():
    requests.patch.when.called_with("https://s3.amazonaws.com/foobar").should.throw(NotImplementedError)


@mock_s3bucket_path
def test_key_method_not_implemented():
    requests.post.when.called_with("https://s3.amazonaws.com/foobar/foo").should.throw(NotImplementedError)


@mock_s3bucket_path
def test_bucket_name_with_dot():
    conn = create_connection()
    bucket = conn.create_bucket('firstname.lastname')

    k = Key(bucket, 'somekey')
    k.set_contents_from_string('somedata')


@mock_s3bucket_path
def test_key_with_special_characters():
    conn = create_connection()
    bucket = conn.create_bucket('test_bucket_name')

    key = Key(bucket, 'test_list_keys_2/*x+?^@~!y')
    key.set_contents_from_string('value1')

    key_list = bucket.list('test_list_keys_2/', '/')
    keys = [x for x in key_list]
    keys[0].name.should.equal("test_list_keys_2/*x+?^@~!y")


@mock_s3bucket_path
def test_bucket_key_listing_order():
    conn = create_connection()
    bucket = conn.create_bucket('test_bucket')
    prefix = 'toplevel/'

    def store(name):
        k = Key(bucket, prefix + name)
        k.set_contents_from_string('somedata')

    names = ['x/key', 'y.key1', 'y.key2', 'y.key3', 'x/y/key', 'x/y/z/key']

    for name in names:
        store(name)

    delimiter = None
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key',
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3'
    ])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix, delimiter)]
    keys.should.equal([
        'toplevel/y.key1', 'toplevel/y.key2', 'toplevel/y.key3', 'toplevel/x/'
    ])

    # Test delimiter with no prefix
    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix=None, delimiter=delimiter)]
    keys.should.equal(['toplevel'])

    delimiter = None
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal(['toplevel/x/key', 'toplevel/x/y/key', 'toplevel/x/y/z/key'])

    delimiter = '/'
    keys = [x.name for x in bucket.list(prefix + 'x', delimiter)]
    keys.should.equal(['toplevel/x/'])
