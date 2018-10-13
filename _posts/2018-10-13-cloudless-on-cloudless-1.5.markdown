---
layout: post
title:  "Deploying getcloudless.com on Cloudless (Part 1.5)"
date:   2018-10-3 16:30:00 -0400
categories: cloudless production
---
In the last post we set up a [Vault server]({% post_url
2018-10-03-cloudless-on-cloudless %}). I was planning on using this to store the
monitoring and HTTPS certificate API keys. However, since that doesn't have
proper authentication set up and has no TLS, I thought it would be misleading to
use that in this deployment since I'm not really using it as a secret server.

So this post is about doing something similar to what we did in that post,
except instead we will deploy [Consul](https://www.consul.io/).
