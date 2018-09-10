---
layout: post
title:  "Welcome to Cloudless!"
date:   2018-09-05 15:30:00 -0400
categories: cloudless introduction
---
Cloudless is a tool designed to make it easy for people to build production
ready infrastructure without having to:

1. Pay a company lots of money to do it for them.
2. Use a black box hosted service that they have no visibility into.
3. Use a opinionated tool optimized for a very specific use case.

These options all have some serious downsides, including vendor lock-in,
inflexibility, dependency, and cost.

However, for many teams the alternative is not acheivable.  There's a long list
of things that need to be done to deploy software safely and securely in
production.  While this is possible for a team to do, it requires a lot of time
from a team of very skilled software engineers who collectively understand
software development, release management, infrastructure reliability, security,
and many other areas.

With this in mind, Cloudless aims to increase what a small number of engineers
can do by doing the things a human shouldn't have to think about in a safe,
secure, flexible, and reliable way so that teams can spend more time focusing on
their real goals.

## How does it work?

The core principle of Cloudless is to focus on what the user is actually trying
to do, and to be very strict about everything else.

It's focused specifically on the layer of provisioning virtual machines,
commonly known as instances, from a cloud provider, which means it's lower in
the stack than things like Serverless or Kubernetes, and could be used to deploy
those services on the instances themselves in a custom deployment.

When it comes to provisioning instances, most users are trying to:

- Run software on a set of instances.
- Restrict communication to and from these instances.

These things may seem silly to even list, but anyone who's had to deploy
infrastructure will immediately notice that this leaves out or is not
prescriptive about a huge amount of setup.  To give some examples:

- Creating a top level environment or network.
- Creating private subnetworks for the instances to run in.
- Ensuring private subnetworks are the right size.
- Ensuring private subnetworks don't overlap existing subnetworks.
- Creating an internet gateway.
- Ensuring the routes are properly set up.
- Ensuring the firewall rules are properly configured.
- Ensuring that the software gets run on the instances.
- Ensuring that there is a scale up mechanism.
- Striping the instances across availability zones.

This is just a high level list of the things must be set up to achieve our
original goals.

Cloudless abstracts away all those details.  To run a group of instances, you
only need to specify some generic initial configuration about the instances,
such as what code they should run at startup and how many resources each
instance should have.  Cloudless will handle everything else.  To control which
groups of instances can communicate with each other, you tell cloudless which
service should have access to which other service, and all the firewalls and
routes will be handled automatically.

## How do I get started?

The best place to start is the [Github
Repository](https://github.com/getcloudless/cloudless).  From there you can find
usage and getting started instructions, or just follow that repository to stay
up to date on development.  Contributions are welcome!

Note that as of this writing Cloudless is still under active development, so if
you have any problems or feature requests, please [file an
issue](https://github.com/getcloudless/cloudless/issues).

For more information, email
[info@getcloudless.com](mailto:info@getcloudless.com).
