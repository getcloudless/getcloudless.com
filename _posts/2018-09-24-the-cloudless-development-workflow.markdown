---
layout: post
title:  "The Cloudless Development Workflow"
date:   2018-09-24 23:00:00 -0400
categories: cloudless development modules
---
From the [first blog post about the Cloudless command line]({% post_url
2018-09-17-the-cloudless-cli %}), you can see that cloudless is a tool that
makes it easier to manage and configure groups of servers in a cross cloud way.

You can also see some of the design philosophies of Cloudless, including
simplicity (no agents or infrastructure setup needed, just API calls), and
immutability (the blueprint file describes the full expected state of your
instance).

However, there's a problem.  There's a reason that
_just-ssh-into-the-instance-and-change-some-things_ based workflows have stuck
around so long even though we all know by now how damaging they are.  It's
because they are _easy_.  It's much easier to just log into an instance and look
at the logs than it is to hire a team of 20 Site Reliability Engineers to build
a destributed log aggregation tool and ensure it has five nines of uptime 365
days a year.

So this workflow aims to change that.  It tries to capture the simplicity of the
"just log in and fix it" mindset, while encouraging habits that will result in
more deterministic and more flexible infrastructure down the line.

## The Base Image

First, anyone below the level of abstraction of a managed platform as a service
has to deal with building a base image for a virtual machine.  Sure, you can do
everything on the instance after you've created it in production, but this slows
down deploys and is more error prone because you are finding more bugs at deploy
time rather than build time.

The current version of Cloudless in pypi now has tools to help with this.  To
follow along with these examples you should clone
[https://github.com/getcloudless/cloudless](https://github.com/getcloudless/cloudless)
at version `v0.0.4`.  These examples also assume you have your provider set up
properly, which you can find help for in the [blog post about the Cloudless
command line]({% post_url 2018-09-17-the-cloudless-cli %}), and in the
[documentation](https://docs.getcloudless.com/).

To build an image, install cloudless and run this from the root of the Cloudless
repository (so you have these example configurations on your machine):

```shell
$ cldls image-build run examples/base-image/gce_image_build_configuration.yml
```

That's it!  Note that these example image build configuration files are prefixed
by the backend provider.  This is because they use stock Ubuntu 16.04 images,
which have different names in the different providers.

Now, to list the image you just created, run:

```shell
$ cldls image list
Listing all images.
Image Name: cloudless-example-base-image-v0
Image Id: ami-0465dffd3ba77d840
Image Created At: 2018-09-23T18:31:06.000Z
```

Ok, we have our image build command, and a subcommand to manage the images we've
built, but what about the workflow to develop a new image?  Well, to deploy an
instance that you want to iterate on, run:

```shell
$ cldls image-build deploy examples/base-image/gce_image_build_configuration.yml
...
To log in, run:
ssh -i examples/apache/id_rsa_image_build cloudless_image_build@35.237.12.140
```

Now you have a single instance and the ssh login credentials if you need to
diagnose issues.  To run the actual configuration scripts, run:

```shell
$ cldls image-build configure examples/base-image/gce_image_build_configuration.yml
```

This calls the configure script described in the image build configuration with
arguments specifying the same SSH login info that the deploy command just
printed.  Now you can iterate on this script, and when you're done, run:

```shell
$ cldls image-build check examples/base-image/gce_image_build_configuration.yml
```

This can do things like validate that your server got configured as expected.

And there you have it!  The full build will do all the previous steps in order
and then save the image.  Running the full build is the only way to save the
image because it ensures as much as possible that the configure and check
scripts are the source of truth for what's on the image.

## Testing Your Service

Now that you have an image, you can test your completely cloud provider
independent service.  This will deploy the service, and check that it exposes a
default apache web page on port 80:

```shell
$ cldls service-test run examples/apache/service_test_configuration.yml
```

Or you can just deploy it using Cloudless:

```shell
$ cldls network create example-network examples/network/blueprint.yml
...
$ cldls service create example-network example-apache examples/apache/blueprint.yml
...
$ cldls paths allow_external example-network example-apache 0.0.0.0/0 80
...
$ cldls service get example-network example-apache
...
```

Now you have an Apache server running your new base image that was fully tested
by the Cloudless test framework!

There are more commands to the test framework that are very similar to the
commands in the image build framework for debugging and development, so refer to
the [Cloudless documentation](https://docs.getcloudless.com/#service-tester) to
learn more.

And that's it!  Now you have a full end to end workflow for building new
Services using Cloudless.

<hr>

Thanks for trying Cloudless!  Check out the
[Documentation](https://docs.getcloudless.com/) for more info, and star the
[Github Repo](https://github.com/getcloudless/cloudless) if you like this
project.  You can also [subscribe for updates](/#subscribe-for-updates) or email
[info@getcloudless.com](info@getcloudless.com).
