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
    """Create the PostgreSQL database if it does not exist."""
    if database_exists(conn):
        click.echo("Database exists, skipping...")
    else:
        click.echo("Database does not exist, creating...")
        create_database(conn)
        click.echo("Successfully created database")


def create_kube_client(in_cluster):
    """
    Load and store authentication and cluster information from kube-config
    file; if running inside a pod, use Kubernetes service account. Use that to
    instantiate Kubernetes client.
    """
    if in_cluster:
        print("loading incluster")
        config.load_incluster_config()
    else:
        print("loading outside cluster")
        config.load_kube_config()
    return client.CoreV1Api()


def create_conn_secret(kube, secret_name, connection):
    """Create the Kubernetes secret for PostgreSQL."""
    metadata = client.V1ObjectMeta(name=secret_name,
                                   labels={'component': secret_name})

    body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data={'connection': connection})

    try:
        kube.create_namespaced_secret('default', body)
        click.echo("Successfully created secret")
    except Exception as e:
        print(e)
        click.echo("Error creating secret")


def patch_conn_secret(kube, secret_name, connection):
    """Patch the existing Kubernetes secret for PostgreSQL."""
    metadata = client.V1ObjectMeta(labels={'component': secret_name})

    body = client.V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=metadata,
        string_data={'connection': connection})

    try:
        kube.patch_namespaced_secret(secret_name, 'default', body)
        click.echo("Successfully patched secret")
    except Exception as e:
        print(e)
        click.echo("Error patching secret")


def ensure_conn_secret(kube, secret_name, conn):
    """Create/update Kubernetes secret for PostgreSQL."""
    # Search for Secret
    kwargs = dict(label_selector=f'component={secret_name}', limit=1)

    try:
        secrets = kube.list_namespaced_secret('default', **kwargs)
        if len(secrets.items) != 1:
            click.echo("Secret does not exist, creating...")
            create_conn_secret(kube, secret_name, str(conn))
        else:
            click.echo("Secret exists, patching...")
            patch_conn_secret(kube, secret_name, str(conn))

    except Exception as e:
        click.echo(e)


@click.command()
@click.option('--bootstrap-db', envvar='BOOTSTRAP_DB')
@click.option('--db-name', envvar='DB_NAME')
@click.option('--secret-name', envvar='SECRET_NAME')
@click.option('--in-cluster', envvar='IN_CLUSTER', type=bool, default=False)
def main(bootstrap_db, db_name, secret_name, in_cluster):
    """Entrypoint."""
    if not (bootstrap_db and db_name and secret_name):
        click.echo("Environment not set correctly")
        sys.exit(1)

    db_client = create_db_client(bootstrap_db)
    kube_client = create_kube_client(in_cluster)
    conn = get_new_db(db_client, db_name)

    ensure_conn_secret(kube_client, secret_name, conn)
    ensure_db(conn)


if __name__ == '__main__':
    main()
