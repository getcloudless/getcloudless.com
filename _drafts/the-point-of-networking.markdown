---
layout: post
title:  "The Point Of Networking"
date:   2018-11-13 13:23:46 -0500
categories: networking user-experience
---
Core Principle: The Point of Networking Is To Control What Can Talk To What
- That's it.  That's ultimately what the user cares about.  Anything else is secondary.  Therefore Butter will handle all that.  If you need to create a network to deploy an instance, Butter will create it transparently.  As a user, you don't care that it's in a network, you just care that it's isolated from other networks.  So that will be the default.  Each service can only talk to itself and no one else.  And then users can add paths between services.
