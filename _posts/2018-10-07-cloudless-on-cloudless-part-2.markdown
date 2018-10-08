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


