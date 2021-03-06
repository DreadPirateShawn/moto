from __future__ import unicode_literals

import boto.rds
import boto.vpc
from boto.exception import BotoServerError
import sure  # noqa

from moto import mock_ec2, mock_rds
from tests.helpers import disable_on_py3


@disable_on_py3()
@mock_rds
def test_create_database():
    conn = boto.rds.connect_to_region("us-west-2")

    database = conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2',
        security_groups=["my_sg"])

    database.status.should.equal('available')
    database.id.should.equal("db-master-1")
    database.allocated_storage.should.equal(10)
    database.instance_class.should.equal("db.m1.small")
    database.master_username.should.equal("root")
    database.endpoint.should.equal(('db-master-1.aaaaaaaaaa.us-west-2.rds.amazonaws.com', 3306))
    database.security_groups[0].name.should.equal('my_sg')


@disable_on_py3()
@mock_rds
def test_get_databases():
    conn = boto.rds.connect_to_region("us-west-2")

    list(conn.get_all_dbinstances()).should.have.length_of(0)

    conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')
    conn.create_dbinstance("db-master-2", 10, 'db.m1.small', 'root', 'hunter2')

    list(conn.get_all_dbinstances()).should.have.length_of(2)

    databases = conn.get_all_dbinstances("db-master-1")
    list(databases).should.have.length_of(1)

    databases[0].id.should.equal("db-master-1")


@mock_rds
def test_describe_non_existant_database():
    conn = boto.rds.connect_to_region("us-west-2")
    conn.get_all_dbinstances.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds
def test_delete_database():
    conn = boto.rds.connect_to_region("us-west-2")
    list(conn.get_all_dbinstances()).should.have.length_of(0)

    conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')
    list(conn.get_all_dbinstances()).should.have.length_of(1)

    conn.delete_dbinstance("db-master-1")
    list(conn.get_all_dbinstances()).should.have.length_of(0)


@mock_rds
def test_delete_non_existant_database():
    conn = boto.rds.connect_to_region("us-west-2")
    conn.delete_dbinstance.when.called_with("not-a-db").should.throw(BotoServerError)


@mock_rds
def test_create_database_security_group():
    conn = boto.rds.connect_to_region("us-west-2")

    security_group = conn.create_dbsecurity_group('db_sg', 'DB Security Group')
    security_group.name.should.equal('db_sg')
    security_group.description.should.equal("DB Security Group")
    list(security_group.ip_ranges).should.equal([])


@mock_rds
def test_get_security_groups():
    conn = boto.rds.connect_to_region("us-west-2")

    list(conn.get_all_dbsecurity_groups()).should.have.length_of(0)

    conn.create_dbsecurity_group('db_sg1', 'DB Security Group')
    conn.create_dbsecurity_group('db_sg2', 'DB Security Group')

    list(conn.get_all_dbsecurity_groups()).should.have.length_of(2)

    databases = conn.get_all_dbsecurity_groups("db_sg1")
    list(databases).should.have.length_of(1)

    databases[0].name.should.equal("db_sg1")


@mock_rds
def test_get_non_existant_security_group():
    conn = boto.rds.connect_to_region("us-west-2")
    conn.get_all_dbsecurity_groups.when.called_with("not-a-sg").should.throw(BotoServerError)


@mock_rds
def test_delete_database_security_group():
    conn = boto.rds.connect_to_region("us-west-2")
    conn.create_dbsecurity_group('db_sg', 'DB Security Group')

    list(conn.get_all_dbsecurity_groups()).should.have.length_of(1)

    conn.delete_dbsecurity_group("db_sg")
    list(conn.get_all_dbsecurity_groups()).should.have.length_of(0)


@mock_rds
def test_delete_non_existant_security_group():
    conn = boto.rds.connect_to_region("us-west-2")
    conn.delete_dbsecurity_group.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds
def test_security_group_authorize():
    conn = boto.rds.connect_to_region("us-west-2")
    security_group = conn.create_dbsecurity_group('db_sg', 'DB Security Group')
    list(security_group.ip_ranges).should.equal([])

    security_group.authorize(cidr_ip='10.3.2.45/32')
    security_group = conn.get_all_dbsecurity_groups()[0]
    list(security_group.ip_ranges).should.have.length_of(1)
    security_group.ip_ranges[0].cidr_ip.should.equal('10.3.2.45/32')


@disable_on_py3()
@mock_rds
def test_add_security_group_to_database():
    conn = boto.rds.connect_to_region("us-west-2")

    database = conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')
    security_group = conn.create_dbsecurity_group('db_sg', 'DB Security Group')
    database.modify(security_groups=[security_group])

    database = conn.get_all_dbinstances()[0]
    list(database.security_groups).should.have.length_of(1)

    database.security_groups[0].name.should.equal("db_sg")


@mock_ec2
@mock_rds
def test_add_database_subnet_group():
    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet1 = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")
    subnet2 = vpc_conn.create_subnet(vpc.id, "10.2.0.0/24")

    subnet_ids = [subnet1.id, subnet2.id]
    conn = boto.rds.connect_to_region("us-west-2")
    subnet_group = conn.create_db_subnet_group("db_subnet", "my db subnet", subnet_ids)
    subnet_group.name.should.equal('db_subnet')
    subnet_group.description.should.equal("my db subnet")
    list(subnet_group.subnet_ids).should.equal(subnet_ids)


@mock_ec2
@mock_rds
def test_describe_database_subnet_group():
    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")

    conn = boto.rds.connect_to_region("us-west-2")
    conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
    conn.create_db_subnet_group("db_subnet2", "my db subnet", [subnet.id])

    list(conn.get_all_db_subnet_groups()).should.have.length_of(2)
    list(conn.get_all_db_subnet_groups("db_subnet1")).should.have.length_of(1)

    conn.get_all_db_subnet_groups.when.called_with("not-a-subnet").should.throw(BotoServerError)


@mock_ec2
@mock_rds
def test_delete_database_subnet_group():
    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")

    conn = boto.rds.connect_to_region("us-west-2")
    conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
    list(conn.get_all_db_subnet_groups()).should.have.length_of(1)

    conn.delete_db_subnet_group("db_subnet1")
    list(conn.get_all_db_subnet_groups()).should.have.length_of(0)

    conn.delete_db_subnet_group.when.called_with("db_subnet1").should.throw(BotoServerError)


@disable_on_py3()
@mock_ec2
@mock_rds
def test_create_database_in_subnet_group():
    vpc_conn = boto.vpc.connect_to_region("us-west-2")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")

    conn = boto.rds.connect_to_region("us-west-2")
    conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])

    database = conn.create_dbinstance("db-master-1", 10, 'db.m1.small',
        'root', 'hunter2', db_subnet_group_name="db_subnet1")

    database = conn.get_all_dbinstances("db-master-1")[0]
    database.subnet_group.name.should.equal("db_subnet1")


@disable_on_py3()
@mock_rds
def test_create_database_replica():
    conn = boto.rds.connect_to_region("us-west-2")

    primary = conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')

    replica = conn.create_dbinstance_read_replica("replica", "db-master-1", "db.m1.small")
    replica.id.should.equal("replica")
    replica.instance_class.should.equal("db.m1.small")
    status_info = replica.status_infos[0]
    status_info.normal.should.equal(True)
    status_info.status_type.should.equal('read replication')
    status_info.status.should.equal('replicating')

    primary = conn.get_all_dbinstances("db-master-1")[0]
    primary.read_replica_dbinstance_identifiers[0].should.equal("replica")

    conn.delete_dbinstance("replica")

    primary = conn.get_all_dbinstances("db-master-1")[0]
    list(primary.read_replica_dbinstance_identifiers).should.have.length_of(0)
