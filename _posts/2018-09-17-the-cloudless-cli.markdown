---
layout: post
title:  "Using The Cloudless Command Line"
date:   2018-09-17 10:00:00 -0400
categories: cloudless command line
---
Up until now, the Cloudless has provided only a python API to interact with
networks and services, but the current release now has a command line interface
to make it easier to get started.  This post is a walkthrough of how to set up
and use the command line interface.

As a warning, some of these steps don't fall into the free tiers of the
respective cloud providers, so you might get charged.  If you're diligent about
cleaning up when you done it should be on the order of a dollar or less, but it
could add up if you leave this running.

## Installation

Cloudless is in the python package index, so you can install it just like you
would any other package.  For example, using pip:

```shell
$ pip install cloudless --user
```

Once you install this package, you should have the `cldls` executable in your
path.  Test this by running:

```shell
$ cldls --help
```

If you have an issue with this, there is likely something wrong with your python
setup, so check out
[https://packaging.python.org/tutorials/installing-packages/](https://packaging.python.org/tutorials/installing-packages/)
for more help.

## Credentials and Profiles

First, just like the python API, you need to up your credentials so that
Cloudless can authenticate with the cloud provider.  This setup is slightly
different whether you're using Google Compute Engine or Amazon Web Services
since they handle access differently.

We will install our credentials in a named "profile" which allows us to easily
switch between different cloud providers.  You can set your profile either by
passing the `--profile` option to all commands or setting the
`CLOUDLESS_PROFILE` environment variable.  If you don't set either of these you
are using the "default" profile.

### Google Compute Engine (GCE) Credentials

Behind the scenes, Cloudless uses the [Apache
Libcloud](https://libcloud.apache.org/) project for GCE.  This is a python
library that has bindings to many different cloud providers.  This means that
their documentation is helpful for understanding how to set up your credentials.
The guide for finding the credentials Cloudless uses can be found here:
[https://libcloud.readthedocs.io/en/latest/compute/drivers/gce.html#service-account](https://libcloud.readthedocs.io/en/latest/compute/drivers/gce.html#service-account).

Cloudless currently uses a "Service Account", so you will need three things:

- A service account "key", which is a JSON file you can download from the
  console at
  [https://console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts).  Save this somewhere you remember.
- A project ID, which will look something like "project-220098".
- A service account user ID, which will look something like
  "service-account@project-220098.iam.gserviceaccount.com".

Once you think you have that information, run the init command:

```shell
$ cldls --profile gce init --provider gce
```

This will prompt you for the information and save it in
`~/.cloudless/config.yml`.  When you're done it should look something like this:

```shell
$ cat ~/.cloudless/config.yml
gce:
  credentials: {key: /home/sverch/.gce/project-220098-166248430d42.json, project: project-220098,
    user_id: 'service-account@project-220098.iam.gserviceaccount.com'}
  provider: gce
```

### Amazon Web Services (AWS) Credentials

For interacting with AWS, Cloudless uses the
[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
library.

To set up your credentials for AWS, follow the instructions here:
[https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html).
That link shows how to set up the AWS command line tool, and once that is set up
Cloudless should work.  Currently, which AWS profile Cloudless uses is only
configurable via the `AWS_PROFILE` environment variable.  If you don't know what
that means, you are using the "default" aws profile and everything should just
work.

Once you have that set up, run:

```shell
$ cldls --profile aws init --provider aws
```

Because the AWS client uses the credentials saved in the `~/.aws/` directory,
you don't have to pass anything else to Cloudless.

## Your First Network

Now that you have your credentials set up, it's time to get started!  First, to
verify everything is connected properly, run:

```shell
$ cldls network list
```

These examples assume you either are using the "default" profile or have set the
`CLOUDLESS_PROFILE` environment variables.  This command will list all networks
in the profile.  If everything is set up properly and you haven't created
networks without Cloudless you should see nothing, or an empty list.

Now, let's create a network.  To create a network named "dev", run:

```shell
$ cldls network create dev example-blueprints/network/blueprint.yml
Created network: dev
```

The blueprint file has some basic configuration for our network.  Now we can see
what we created:

```shell
$ cldls network get dev
Name: dev
Id: vpc-0c00ce4d55a177bec
Network: 10.0.0.0/16
Region: us-east-1
```

Success!  We now have a new network with a `10.0.0.0/16` network block (not all
cloud providers need a network block for the top level network, so if you see
"null" here that's okay).

## Creating A Service

Now that we have a network, we want to actually run something in it.  Here we'll
create a simple service running the default nginx configuration.  Again, the
blueprint file contains some configuration for the service, such as the resource
requirements for each instance, how much redundancy you need, the base image to
start with (Ubuntu in this case), and the startup script that installs nginx:

```shell
$ cldls service create dev public example-blueprints/aws-nginx/blueprint.yml
...
Waiting for instance creation for service public.  0 of 3 running
...
Success!  3 of 3 instance running.
Created service: public in network: dev
```

Great!  We now have three instances running in the "dev" network.  Let's get
details about our service:

```shell
$ cldls service get dev public
name: public
has_access_to:
- default-all-outgoing-allowed
is_accessible_from: []
network:
  name: dev
  id: vpc-00c0ce4d42a166bec
  block: 10.0.0.0/16
  region: us-east-1
  subnetworks:
  - name: public
    id: subnet-039a58e389a587408
    block: 10.0.0.0/24
    region: us-east-1
    availability_zone: us-east-1a
    instances:
    - id: i-05b07de532f613dd9
      public_ip: 34.228.236.82
      private_ip: 10.0.0.235
      state: running
      availability_zone: us-east-1a
  - name: public
    id: subnet-0bb6ed2f9853c2716
    block: 10.0.1.0/24
    region: us-east-1
    availability_zone: us-east-1b
    instances:
    - id: i-059d06940243444ac
      public_ip: 34.239.226.191
      private_ip: 10.0.1.201
      state: running
      availability_zone: us-east-1b
  - name: public
    id: subnet-032b434b6b00a1551
    block: 10.0.2.0/24
    region: us-east-1
    availability_zone: us-east-1c
    instances:
    - id: i-0d5b345cdb764a274
      public_ip: 54.175.1.164
      private_ip: 10.0.2.148
      state: running
      availability_zone: us-east-1c
```

There we have it, three instances running across availability zones.  By default
nothing can access this service, but it's up and running!

## Making It Public

Now that we have our service, we want to expose it on the internet.  To do that,
we can use the `paths` subcommand:

```shell
$ cldls paths allow_network_block dev public 0.0.0.0/0 80
Added path from 0.0.0.0/0 to public in network dev for port 80
```

This command allows `0.0.0.0/0` (all ip addresses) to access our service on port
`80`.  Now let's see our paths:

```shell
$ cldls paths list
external:0.0.0.0/0 -(80)-> dev:public
```

There we have it!  We should also see our path in the `is_accessible_from`
attribute of the service command output.

Now, let's check if our site is running using the `public_ip` of one of our
instances:

```shell
$ curl http://$(cldls service get dev public | grep public_ip | awk -F: '{print $2}' | head -n 1)
curl: (3) Bad URL
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
    body {
        width: 35em;
        margin: 0 auto;
        font-family: Tahoma, Verdana, Arial, sans-serif;
    }
</style>
</head>
<body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, the nginx web server is successfully installed and
working. Further configuration is required.</p>

<p>For online documentation and support please refer to
<a href="http://nginx.org/">nginx.org</a>.<br/>
Commercial support is available at
<a href="http://nginx.com/">nginx.com</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>
```

Success!  We now have a simple site up and running, and all the steps here work
on any cloud provider (except the credential setup of course).

## Cleaning Up

You don't want to get charged for leaving these things running, so you can clean
up the resources you created by running:

```shell
cldls service destroy dev public
cldls network destroy
```

<hr>

Thanks for trying Cloudless!  Check out the
[Documentation](https://docs.getcloudless.com/) for more info, and star the
[Github Repo](https://github.com/getcloudless/cloudless) if you like this
project.  You can also [subscribe for updates](/#subscribe-for-updates) or email
[info@getcloudless.com](info@getcloudless.com).
