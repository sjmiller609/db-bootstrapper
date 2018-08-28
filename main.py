"""
Bootstrap database and Kubernetes secrets for Astronomer EE install.
"""

import os
import sys

import click
import sqlalchemy
from kubernetes import client, config
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists


def create_db_client(conn):
    """Create SQLAlchemy engine for PostgreSQL connection."""
    return create_engine(conn, isolation_level='AUTOCOMMIT')


def get_new_db(engine, db_name):
    """Add database name to SQLAlchemy engine."""
    conn = engine.url
    conn.database = db_name
    return conn


def ensure_db(conn):
    """
    Create the PostgreSQL database if it does not exist.
    Attempt to convert db names with dashes to underscores, unless they exist already
    """
    db_name = conn.database

    # if db_name passed in already exists, always use it
    if database_exists(conn):
        click.echo("Database exists, skipping...")
        return conn

    # convert any `-` to `_`, and recheck if it exists
    conn.database = db_name.replace('-', '_')
    if database_exists(conn):
        click.echo("Database exists, skipping...")
        return conn

    # database didn't exist with `-` or `_`, so create it with `_`
    click.echo("Database does not exist, creating...")
    create_database(conn)
    click.echo("Successfully created database")

    return conn


def create_kube_client(in_cluster):
    """
    Load and store authentication and cluster information from kube-config
    file; if running inside a pod, use Kubernetes service account. Use that to
    instantiate Kubernetes client.
    """
    if in_cluster:
        click.echo("Using in cluster kubernetes configuration")
        config.load_incluster_config()
    else:
        click.echo("Using kubectl kubernetes configuration")
        config.load_kube_config()
    return client.CoreV1Api()


def create_conn_secret(kube, namespace, secret_name, connection):
    """Create the Kubernetes secret for PostgreSQL."""
    metadata = client.V1ObjectMeta(name=secret_name,
                                   labels={'component': secret_name})

    body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data={'connection': connection})

    try:
        kube.create_namespaced_secret(namespace, body)
        click.echo("Successfully created secret")
    except Exception as e:
        print(e)
        click.echo("Error creating secret")


def patch_conn_secret(kube, namespace, secret_name, connection):
    """Patch the existing Kubernetes secret for PostgreSQL."""
    metadata = client.V1ObjectMeta(labels={'component': secret_name})

    body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data={'connection': connection})

    try:
        kube.patch_namespaced_secret(secret_name, namespace, body)
        click.echo("Successfully patched secret")
    except Exception as e:
        print(e)
        click.echo("Error patching secret")


def ensure_conn_secret(kube, namespace, secret_name, conn):
    """Create/update Kubernetes secret for PostgreSQL."""
    # Search for Secret
    kwargs = dict(label_selector=f'component={secret_name}', limit=1)

    try:
        secrets = kube.list_namespaced_secret(namespace, **kwargs)
        if len(secrets.items) != 1:
            click.echo("Secret does not exist, creating...")
            create_conn_secret(kube, namespace, secret_name, str(conn))
        else:
            click.echo("Secret exists, patching...")
            patch_conn_secret(kube, namespace, secret_name, str(conn))

    except Exception as e:
        click.echo(e)


@click.command()
@click.option('--bootstrap-db', envvar='BOOTSTRAP_DB', required=True)
@click.option('--db-name', envvar='DB_NAME', required=True)
@click.option('--secret-name', envvar='SECRET_NAME', required=True)
@click.option('--namespace', envvar='NAMESPACE', required=True)
@click.option('--in-cluster', envvar='IN_CLUSTER', type=bool, default=False)
def main(bootstrap_db, db_name, secret_name, namespace, in_cluster):
    """Entrypoint."""
    db_client = create_db_client(bootstrap_db)
    kube_client = create_kube_client(in_cluster)

    # ensure the database exists
    conn = get_new_db(db_client, db_name)
    conn = ensure_db(conn)

    # ensure the k8 secret exists for the conn
    ensure_conn_secret(kube_client, namespace, secret_name, conn)



if __name__ == '__main__':
    main()
