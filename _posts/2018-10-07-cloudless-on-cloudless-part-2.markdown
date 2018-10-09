---
layout: post
title:  "Deploying getcloudless.com on Cloudless (Part 2)"
date:   2018-10-07 00:30:00 -0400
categories: cloudless production
---
This is part two of deploying
[https://getcloudless.com](https://getcloudless.com) using Cloudless. In [part
one]({% post_url 2018-10-03-cloudless-on-cloudless %}), we set up a very basic
Vault server without TLS/SSL (no encryption in transit) or high availability
(only a single node).

Whil that's is not the most secure or resilient deployment, for the bare minimum
setup that we're trying to go for, it's enough. It's not enough to just say that
though, so I'll give a short justification as to why _for this particular case_
I'm not going to worry about these right now.

Remember, our architecture is a single Vault server with web servers that will
pull secrets from the Vault server on startup.

## Resilience

When thinking about resilience of this basic set up, I can think through what
might fail at a high level, and what would happen in that case.

- Anything about the web servers: The [DataDog](https://www.datadoghq.com/)
  agent will stop reporting from the server, and I can trigger an alert if any
  servers stop responding. If I'm tearing down a server on purpose, I'll know
  I caused the alert, so the spurious alert isn't a big deal. I'll also get
  notifications from [uptime monitoring](https://uptime.com/) to tell me that
  clients have started recieving errors, and I can respond to correct the issue.
- The Vault server: The web servers will only pull secrets on startup, so the
  Vault server going down won't take down the site (but will prevent me from
  spinning up new servers). If I combine this with monitoring on the web servers
  that checks that the Vault server is still responding, I can ensure I get
  notified if something is wrong so I know I can still scale up if I need to.

Since this is a simple site, and since I'll have redundant web servers, I'm
considering that good enough for now. Some future optimizations would of course
be to make Vault HA, to put the web servers behind a load balancer with health
checks, and have automation to change DNS entries if one of the user facing
servers stops responding.

## Security

For security, we have a place to store our secrets, so we don't have to commit
them into version control or pass them around out of band, but we still have a
problem. How do we make sure the web servers, and only the web servers, can
access the secrets?

Well, it comes down to choosing something that is true about the authorized
clients but not true about anyone else. Some of our options are:

- *Where they are*: This gives full access to any client that can reach the
  resource, and protection is done using private networks and firewall rules.
- *What they have*: This requires the client to present something that shows
  they should be allowed to do the requested operation, like an API token.
- *What they can do*: This requires the client to do something that only an
  authorized client can do, like add a DNS entry to prove they own a domain.
- *Who they are*: This requires clients to prove their identity, or on some kind
  of inherent property of the client, like tags on the instance the request is
  coming from.

For now, I'm just going to do *where they are* and control access using firewall
rules. This is the least secure, but for now it's good enough. Since the web
servers have to access the secrets to function anyway, I'm going to assume that
once the web servers are compromised everything I care about is compromised
anyway (and make sure that the Vault server doesn't have any extra permissions
or access that the web servers don't).

Once Cloudless supports [portable instance
permissions](https://github.com/getcloudless/cloudless/issues/48), we can allow
the Vault server to ask our cloud provider "is this instance really tagged as a
web server", which will add a layer of *who they are* on top of what we're doing
now. We would also need to set up TLS on the Vault server for this to matter at
all.

## Deployment

Because the current security model for this deployment is all about protecting
access using firewall rules, I'm going to just save the root key on the Vault
server so that nothing has to be stored in version control or out of band. This
is not really the way you're supposed to use Vault, but for what we're trying to
do now it'll work, and once
[https://github.com/getcloudless/cloudless/issues/48](https://github.com/getcloudless/cloudless/issues/48)
is done, or we have some kind of real inventory server, we can do something
smarter.

So first, let's add a small change to the
[example-vault](https://github.com/getcloudless/example-vault) blueprint to make
it possible to add some SSH keys. At some point, we might be able to do
something smarter (like store these in Vault so we can centrally manage user
accounts), but as we're bootstrapping adding
them as arguments to the startup script is good enough. The pull request is up
[here](), and note it comes with a regression test.

Now, just like before, let's copy the [example-apache](https://github.com/getcloudless/example-apache) blueprint to create [example-static-site](https://github.com/getcloudless/example-static-site).

The first difference from our Vault setup is that this blueprint will depend on
the Vault blueprint. Until [issue]() is done, we have to clone that blueprint as
a submodule:

```
git submodule add https://github.com/getcloudless/example-vault
```

Now, in the test setup, we can add:

```
TODO
```

This will tell the test framework to create a Vault server before creating our
static web server. It also unseals the Vault server and passes the root key and
private IP address back to the test framework. These will be passed to the web
server startup script because of these lines in `blueprint.yml`:

```
TODO
```

They will be passed as template variables to jinja2, which will template out the
startup script. Just to get started, let's add this to our startup script:

```
TODO
```

I don't know if this is what we'll ultimately want, but it will save the Vault
root token in the test user's home directory, which is the perfect place for us
to pick up.

TODO: Going to need mock echo servers...


