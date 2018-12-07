---
layout: post
title:  "Deploying getcloudless.com on Cloudless (Part 3)"
date:   2018-12-07 17:00:00 -0400
categories: cloudless production
---
The past few posts have been about creating and testing the Cloudless modules we
need to deploy our static site, but now we get to see how it all comes together.

This diagram was generated from Cloudless itself, and shows the architecture we
are building:

![Statis Site Architecture Digram with Consul and Single Web
Service](/assets/images/2018-12-07-cloudless-on-cloudless-3-architecture.svg){:class="post-img-centered"}

Note that there's a Consul service that is not internet accessible, but the web
servers can access it on the Consul port (8500).  The web servers are accessible
to the internet on https port 443 and on http port 80, which will redirect to
https on port 443.

Most of the code for this post can be found in [this pull
request](https://github.com/getcloudless/getcloudless.com/pull/1), so check
there if you want to see how this all comes together in the end.

# Creating The Network 

This part is easy.  All we need is a network configuration file, which is empty
because the defaults are fine for us (default is to create a network of size
2^16, or 16 bits).  Then we run our deployment command with the empty file:

```shell
$ cldls network create cloudless network.yml
Created network: cloudless
$ cldls network get cloudless
Name: cloudless
Id: vpc-00000000000000000
Network: 10.0.0.0/16
Region: us-east-1
```

Now we have our network!  Note it doesn't matter whether you're using AWS or
GCE.  This step will be exactly the same.

# Consul Deployment

Now it gets interesting.  Remember in [part 1.5]({% post_url
2018-10-14-cloudless-on-cloudless-1.5 %}) of this series, we created a Consul
module.  Well now we are actually going to use it.  Until
[https://github.com/getcloudless/cloudless/issues/39](https://github.com/getcloudless/cloudless/issues/39)
is done, we can only deploy module code from our local machine, so we have to
check out a git submodule:

```shell
$ git submodule add git@github.com:getcloudless/example-consul.git
```

Now that we have this checked out we can deploy Consul!

```shell
$ cldls service create --count 1 cloudless consul-1 example-consul/blueprint.yml
...
Created service: consul-1 in network: cloudless
```

And now we've deployed the Consul server we will use to store our secrets.
Let's configure it to work with our site.

# Consul Configuration

Now that we have a Consul service running, we need to store the proper
configuration.  For that we need to start by cloning the example static site
module we wrote in [part 2]({% post_url 2018-10-18-cloudless-on-cloudless-part-2
%}):

```shell
$ git submodule add git@github.com:getcloudless/example-static-site.git
```

Remember in [part 2]({% post_url 2018-10-18-cloudless-on-cloudless-part-2 %})
when we wrote an integration test for our static site?  Well, one of the things
that integration test had to do in order to work properly was set up Consul,
which happens to be exactly the code that we need now.

In [this pull
request](https://github.com/getcloudless/example-static-site/pull/11) I factored
that setup out into a separate script, so the integration test now looks
something like:

```python
...
from helpers.setup_consul import setup_consul, check_environment
...
setup_consul(consul_ips, "getcloudless.com", use_sslmate=use_sslmate,
             use_datadog=use_datadog)
...
```

It doesn't seem like much, but this means we can use this script outside the
integration test.  For us, this looks like:

```shell
# Get my IP for whitelisting
MY_IP_ADDRESS=$(curl --silent ipinfo.io/ip)
# Allow my IP to connect
cldls paths allow_network_block cloudless consul-1 $MY_IP_ADDRESS 8500
# Get the IP of the Consul node
CONSUL_IP=$(cldls service get cloudless consul-1 | grep public_ip | awk -F: '{print $2}')
# Run the configuration script
python example-static-site/helpers/setup_consul.py $CONSUL_IP getcloudless.com both
# Disallow my IP
cldls paths revoke_network_block cloudless consul-1 $MY_IP_ADDRESS 8500
```

The configuration script will upload all the necessary secrets to Consul that
the web servers need to deploy.  And the best part is that this code is actually
covered by our tests!

# Web Service Deployment

Up until this point we used the Cloudless command line, but for the web service
deployment, we'll use the Cloudless python API directly.  In the end, this is a
single python script that's less than 70 lines in total.  You can find it
[here](https://github.com/getcloudless/getcloudless.com/blob/master/deployment/deploy_web.py)
if you want to see the whole thing.

First, remember that [this pull
request](https://github.com/getcloudless/example-static-site/pull/11) factored
out the health check into a separate script, so the integration test looks
something like this:

```python
...
from helpers.health import check_health
...
expected_content = "Cloudless"
services = [{"public_ip": i.public_ip, "private_ip": i.private_ip}
            for s in service.subnetworks for i in s.instances]
check_health(services, expected_content, use_datadog, use_sslmate)
...
```

That's it!  Most of the code is hidden in the `check_health` function, which we
can reuse in our full deployment script:

```python
...
from helpers.health import check_health
...
consul_service = client.service.get(network, consul_name)
consul_instances = client.service.get_instances(consul_service)
...
internet = CidrBlock("0.0.0.0/0")
service = client.service.create(network, service_name,
                                blueprint="example-static-site/blueprint.yml",
                                count=count, template_vars=blueprint_vars)
client.paths.add(service, consul_service, 8500)
client.paths.add(internet, service, 80)
client.paths.add(internet, service, 443)
print("Created service: %s!" % service_name)
service_instances = client.service.get_instances(service)
service_ips = [{"public_ip": instance.public_ip, "private_ip": instance.private_ip}
               for instance in service_instances]
check_health(service_ips, "Cloudless", use_datadog=True, use_sslmate=True)
...
```

Here you can see our deployment script doing a little work to set up the
networking, exposing port 80 and port 443, and linking it up to Consul (our
integration test does this in a separate step).  For the most part though, it
looks very similar to our integration test.  Let's see what a deploy looks like:

```shell
$ python deploy_web.py consul-1 web-1
...
Created service: web-1!
Checking url: https://54.174.226.40
...
Checking to see if agent is reporting for host: 10.0.8.116.
INFO:datadog.api:200 GET https://api.datadoghq.com/api/v1/events (88.5127ms)
...
Checking query: nginx.net.connections{*}by{private_ip} to check for nginx metrics.
Checking query: consul.catalog.total_nodes{*}by{private_ip} to check for consul metrics.

Deploy Successful!

Service IPs: [{'public_ip': '54.174.226.40', 'private_ip': '10.0.8.116'}]
Use 'cldls service get cloudless web-1' for more info.
```

Success!  Now our `web-1` service is running, and because it uses the same
health checks as our integration test, we not only know that our service is up
and responding, but we have confidence that our new service is actually
reporting metrics for the services we care about.

# DNS Setup

So now we are at the final step.  We have an automated deploy script to deploy
our service, but what we really want is for
[https://getcloudless.com](https://getcloudless.com) to point to our newly
deployed server.

Do do this we have to create a DNS entry that points `getcloudless.com` at the
public IP of the new server, or `54.174.226.40`.  Since everything else is
automated, it would be unfortunate if this step required a human, so we're going
to use [NS1](https://ns1.com/) to host our DNS because they have great API
support.

In a nutshell, the DNS update script looks like:

```python
from ns1 import NS1
...
API_KEY = os.environ["NSONE_CLOUDLESS_API_KEY"]
...
api = NS1(apiKey=API_KEY)
zone = api.loadZone("getcloudless.com")
record = zone.loadRecord("aws", "A")
answers = [answer["answer"] for answer in record["answers"]]
print("Old IPs for record 'aws.getcloudless.com': %s" % answers)
if remove:
    print("Removing IP: %s" % ip_address)
    answers = [answer for answer in answers
                if answer != ip_address and ip_address not in answer]
else:
    print("Adding IP: %s" % ip_address)
    answers.append([ip_address])
print("New IPs for record 'aws.getcloudless.com': %s" % answers)
record.update(answers=answers)
...
```

This is a simple script that lets us add or remove an IP address from
`aws.getcloudless.com` (I made `getcloudless.com` ALIAS to that, which is an NS1
feature).  It works like this:

```shell
$ python update_dns.py 54.174.226.40
Old IPs for record 'aws.getcloudless.com': []
Adding IP: 54.174.226.40
New IPs for record 'aws.getcloudless.com': [['54.174.226.40']]
```

And there we go!  Now `getcloudless.com` is updated to point to the new server
we just deployed.  If we want to do an update, we can deploy a new web service
and update the DNS to point to that and remove the entry for the old server.

Be warned though, that DNS responses get cached all over the place, so you
should wait a while before tearing down your old server even if you've
technically removed the record.

# And We're Done!

That's it!  [https://getcloudless.com](https://getcloudless.com) is now
officially deployed on Cloudless.  Not only that, we have zero downtime deploys
with a short (and tested!) python script.

Obviously there's a lot of room for improvement, from deploying our web services
behind a load balancer so we don't have to wait for DNS caches to clear, to
securing our internal secrets store using something besides firewall rules, but
this gives us something to build on.  Check back for more updates!

{% include post-footer.html %}
