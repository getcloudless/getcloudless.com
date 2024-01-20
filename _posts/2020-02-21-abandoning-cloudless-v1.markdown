---
layout: post
title:  "Cloudless V1 Lessons Learned"
date:   2020-02-21 17:00:00 -0400
categories: cloudless
---
I spent three months working on Cloudless and deployed both [this
site](https://getcloudless.com/cloudless/production/2018/12/07/cloudless-on-cloudless-3.html)
and [my personal site](https://shaunverch.com/).  However, at this point, I've
moved on to other approaches to the same problem.  I [wrote a
post](https://shaunverch.com/compatibility/open-source/2020/02/21/thoughts-on-cloud-compatibility.html)
that describes why I originally wanted to work on this, and what I'll be doing
next.

To make it short, this was a great proof of concept and I learned a lot, but one
of the issues is that the "mapping" to the different cloud providers was baked
into python.  I think this is a mapping problem at its heart, and I think baking
that mapping into your library is a losing battle (and will only work with one
language).  That post has much more on this.

If you want to see what I'm doing now (at least as of this post), take a look at
[this
summary](https://shaunverch.com/butter/open-source/2019/12/13/butter-days-17.html),
or just go to [my personal site](https://shaunverch.com/).

Thanks for reading!
