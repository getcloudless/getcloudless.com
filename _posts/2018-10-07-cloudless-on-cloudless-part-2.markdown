---
layout: post
title:  "Deploying getcloudless.com on Cloudless (Part 2)"
date:   2018-10-07 00:30:00 -0400
categories: cloudless production
---
This is part two of deploying
[https://getcloudless.com](https://getcloudless.com) using Cloudless. In [part
1.5]({% post_url 2018-10-14-cloudless-on-cloudless-1.5 %}), we set up a simple
Consul server without TLS/SSL (no encryption in transit) or high availability
(only a single node).

Whil that's is not the most secure or resilient deployment, for the bare minimum
setup that we're trying to go for, it's enough. It's not enough to just say that
though, so I'll give a short justification as to why _for this particular case_
I'm not going to worry about these right now.

Remember from [part 1]({% post_url 2018-10-03-cloudless-on-cloudless %}) that
the overall architecture is one Consul server to store our API keys and multiple
client facing web servers that pull the API keys on startup.

## Resilience

When thinking about resilience of this basic set up, I can think through what
might fail at a high level, and what would happen in that case.

- Failure of the web servers: The [DataDog](https://www.datadoghq.com/) agent
  will stop reporting from the server, and I can trigger an alert if any servers
  stop responding. If I'm tearing down a server on purpose, I'll know I caused
  the alert, so the spurious alert isn't a big deal. I'll also get notifications
  from [uptime monitoring](https://uptime.com/) to tell me that
  clients have started recieving errors, and I can respond to correct the issue.
- Failure of the Consul server: The web servers will only pull secrets on
  startup, so the Consul server going down won't take down the site (but will
  prevent me from spinning up new servers). If I combine this with monitoring on
  the web servers that checks that the Consul server is still responding, I can
  ensure I get notified if something is wrong so I know I can still scale up if
  I need to.

Since this is a simple site, and since I'll have redundant web servers, I'm
considering that good enough for now. Some future optimizations would of course
be to deploy multiple Consul servers, to put the web servers behind a load
balancer with health checks, and have automation to change DNS entries if one of
the user facing servers stops responding.

## Security

For security, we have a place to store our secrets, so we don't have to commit
them into version control or pass them around out of band, which is good. We're
not really using a secrets server for this, so what are the implications?

Well, from a security perspective it would be nice to get access logging, TLS
encryption of traffic in transit, and true access controls so that only
authorized clients can retrieve the secrets they need. However, that's future
work and would require spending more time on the Vault setup.

For now, we'll rely on Consul being an internal only service, and assume that
once someone is in the private network (so either on the Consul server or the
web servers), they've already mostly compromised enough to get those API keys
anyway, and don't have that much to gain by stealing them.

If I was protecting finanical or health data, that consideration would be very
different, but for now this is a good place to start.

## Initial Setup

Just like before, our first step is to copy an existing blueprint. Let's start
with the [example-apache](https://github.com/getcloudless/example-apache)
blueprint to create
[example-static-site](https://github.com/getcloudless/example-static-site). The
pull request for the import is
[here](https://github.com/getcloudless/example-static-site/pull/1). All our
changes will be based on that starting point.

## Consul Dependency

The first difference from our Vault/Consul setup is that this blueprint will
depend on the Consul blueprint. Until [support for pulling modules directly from
a remote source](https://github.com/getcloudless/cloudless/issues/39) is done,
we have to clone that blueprint as a submodule:

```
git submodule add https://github.com/getcloudless/example-consul
```

Now, in the test setup, we can add:

```
...

SERVICE_BLUEPRINT = os.path.join(os.path.dirname(__file__), "example-consul/blueprint.yml")

RETRY_DELAY = float(10.0)
RETRY_COUNT = int(6)

class BlueprintTest(BlueprintTestInterface):
    """
    Fixture class that creates the dependent resources.
    """
    def setup_before_tested_service(self, network):
        """
        Create the dependent services needed to test this service.
        """
        # Since this service has no dependencies, do nothing.
        service_name = "consul"
        service = self.client.service.create(network, service_name, SERVICE_BLUEPRINT, count=1)
        return SetupInfo(
            {"service_name": service_name},
            {"consul_ips": [i.private_ip for s in service.subnetworks for i in s.instances]})

    def setup_after_tested_service(self, network, service, setup_info):
        """
        Do any setup that must happen after the service under test has been
        created.
        """
        @retry(wait_fixed=5000, stop_max_attempt_number=24):
        def add_dummy_api_keys(service):
            public_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
            assert public_ips, "No services are running..."
            for public_ip in public_ips:
                consul_client = consul.Consul(public_ip)
                if consul_client.kv.get('dummy_api_key'):
                    continue
                consul_client.kv.put('dummy_api_key', 'dummy_api_key_value')
            return True

        # First set up our real paths, two on http and https from the internet,
        # and one to consul from the web service.
        consul_service_name = setup_info.deployment_info["service_name"]
        consul_service = self.client.service.get(network, consul_service_name)
        internet = CidrBlock("0.0.0.0/0")
        self.client.paths.add(service, consul_service, 8500)
        self.client.paths.add(internet, service, 80)

        # Now let's add some dummy API keys to Consul.
        self.client.paths.add(internet, consul_service, 8500)
        add_dummy_api_keys(consul_service)
        self.client.paths.remove(internet, consul_service, 8500)

...
```

Here's where things start to get interesting. The test framework will call two
functions in our test fixture, one to set up any dependencies that need to be
there before the service under test has been created, and the other to do any
final setup after the service under test has been created.

In this example, our web service depends on Consul, which means we not only need
to deploy a Consul service, but also allow access from the web server to the
consul service on port 8500.

## Blueprint Variables

Now that we've expressed the Consul dependency in the test framework, how do we
actually tell the web servers where our Consul servers live?

For every Cloudless service, there's a "blueprint" configuration file where you
can specify the required resources, the initial base image, and a startup
script. This script can actually take parameters so you can control the behavior
of the service without changing the configuration itself.

In this setup, our startup script block will look like this:

```
initialization:
  - path: "static_site_startup_script.sh"
    vars:
      consul_ips:
        required: true
      cloudless_test_framework_ssh_key:
        required: false
      cloudless_test_framework_ssh_username:
        required: false
```

The SSH information is passed in by the test framework, while the `consul_ips`
will be required by our setup.

They will be passed as template variables to jinja2, which will template out the
startup script. Just to get started, let's add this to our startup script:

```
#! /bin/bash

{% if cloudless_test_framework_ssh_key %}
adduser "{{ cloudless_test_framework_ssh_username }}" --disabled-password --gecos "Cloudless Test User"
echo "{{ cloudless_test_framework_ssh_username }} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
mkdir /home/{{ cloudless_test_framework_ssh_username }}/.ssh/
echo "{{ cloudless_test_framework_ssh_key }}" >> /home/{{ cloudless_test_framework_ssh_username }}/.ssh/authorized_keys
{% endif %}

apt-get update
apt-get install -y python3-pip
pip install python-consul
cat <<EOF > /tmp/fetch_key.py
import consul
consul_client = consul.Consul("{{ consul_ips[0] }}")
dummy_api_key = consul_client.kv.get('dummy_api_key')
print(dummy_api_key[1]["Value"].decode("utf-8").strip()
EOF

python /tmp/fetch_key.py >> /tmp/dummy_key.txt
```

I don't know if this is what we'll ultimately want, but it will install the
Consul client and save the dummy API key so we can at least see whether this
part works.

Variables can be passed in via the API or the command line, but we don't need to
do that yet because the "ServiceInfo" object that we passed back to the test
framework in our test fixture above contains this information, which the test
fixture will pass to the service being tested.

All the work from this section can be found in [this pull
request](https://github.com/getcloudless/example-static-site/pull/2).

## First Run

If you read the first two posts, this is starting to become familiar:

```
$ cldls service-test deploy service_test_configuration.yml 
Service test group with provider: gce
...
INFO:cloudless.providers.gce:Creating subnetwork consul in test-network-hbocrrlcgg with blueprint /home/sverch/projects/example-static-site/example-consul/blueprint.yml
...
INFO:cloudless.providers.gce:Discovering subnetwork test-network-hbocrrlcgg, test-service-kgfotabkoy
Deploy complete!
To log in, run:
ssh -i /home/sverch/projects/example-static-site/.cloudless/id_rsa_test cloudless_service_test@35.237.3.172
```

One difference here is you can see that the consul service was automatically
created. Let's see if the connection worked!

```
ssh -i /home/sverch/projects/example-static-site/.cloudless/id_rsa_test cloudless_service_test@35.237.3.172
$ cat /tmp/dummy_key.txt 
$
```

No luck, but let's see if the python script is there:

```
$ cat /tmp/fetch_key.py 
import consul
consul_client = consul.Consul("10.0.0.2")
dummy_api_key = consul_client.kv.get('dummy_api_key')
print(dummy_api_key[1]["Value"].decode("utf-8").strip()
$ python /tmp/fetch_key.py
  File "/tmp/fetch_key.py", line 5

                                                           ^
SyntaxError: invalid syntax
```

Alright, looks like a simple missing parentheses, let's fix that and try again:

```
$ python /tmp/fetch_key.py 
Traceback (most recent call last):
  File "/tmp/fetch_key.py", line 1, in <module>
    import consul
ImportError: No module named consul
```

Ok, we probably installed Consul as root, so let's install it and try again:

```
$ sudo pip install python-consul
sudo: pip: command not found
$ sudo pip3 install python-consul
...
Successfully installed python-consul-1.1.0
$ python3
Python 3.5.2 (default, Nov 23 2017, 16:37:01) 
[GCC 5.4.0 20160609] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import consul
>>> consul_client = consul.Consul("10.0.0.2")
>>> dummy_api_key = consul_client.kv.get('dummy_api_key')
>>> dummy_api_key
('1', None)
>>> 
```

After playing around a bit, I found that I needed to use `pip3` and `python3` to
run these commands, because that's what I installed. However, it is a bit
strange that the dummy api key didn't get added. Looking at the real return
value of this, I can see that this line in the test fixture is probably the
issue:

```
if consul_client.kv.get('dummy_api_key'):
    continue
```

When what I really need is:

```
if consul_client.kv.get('dummy_api_key')[1]:
    continue
```

I'll fix that in the test fixture and the other issues in the startup script and
move on for now. This is all in [the same pull request as
before](https://github.com/getcloudless/example-static-site/pull/2). The good
news is that Consul is up and we can successfully connect from the web servers!

## Jekyll Setup

Now that we have our server running, let's try to set up some of the other
things we need, starting with the web server itself.

First, let's install nginx:

```
$ sudo apt-get install nginx
```

And from another terminal make sure we can reach it:

```
$ curl --silent 35.237.3.172 | grep "Thank you"
<p><em>Thank you for using nginx.</em></p>
```

Now, let's do all the Jekyll setup:

```
$ sudo apt-get install git
$ git clone https://github.com/getcloudless/getcloudless.com.git
$ sudo apt-get install ruby ruby-dev build-essential
$ sudo gem install bundler
$ cd getcloudless.com/
$ export GEM_HOME=$HOME/gems
$ export PATH=$HOME/gems/bin:$PATH
$ bundle install
...
	ERROR: Failed to build gem native extension.
...
zlib is missing; necessary for building libxml2
...
$ sudo apt-get install zlib1g-dev
$ bundle install
$ sudo chown -R $(whoami) /var/www/html
$ bundle exec jekyll build --destination /var/www/html
```

That's a lot, but it's mostly fighting with ruby dependencies and the normal
installation of Jekyll, which you can find
[here](https://jekyllrb.com/docs/installation/ubuntu/).

But now, we're serving Cloudless!

```
$ curl --silent 35.237.3.172 | grep "<title>"
    <title>Cloudless</title>
```

Before we go any further, let's add this to our regression test:

```
def verify(self, network, service, setup_info):
    """
    Given the network name and the service name of the service under test,
    verify that it's behaving as expected.
    """
    def check_responsive():
        public_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
        assert public_ips
        for public_ip in public_ips:
            response = requests.get("http://%s" % public_ip)
            expected_content = "Cloudless"
            assert response.content, "No content in response"
            assert expected_content in str(response.content), (
                "Unexpected content in response: %s" % response.content)
    call_with_retries(check_responsive, RETRY_COUNT, RETRY_DELAY)
```

And check it:

```
$ cldls service-test check service_test_configuration.yml
...
Check complete!
...
```

Now I'll just add all the above configuration to the startup script, and try to
run the full deploy/test cycle:

```
$ cldls service-test cleanup service_test_configuration.yml
$ cldls service-test deploy service_test_configuration.yml
$ cldls service-test check service_test_configuration.yml
$ cldls service-test cleanup service_test_configuration.yml
```

It takes a while to set up, which would be fixed by [building much of the setup
into a base image]({% post_url 2018-09-24-the-cloudless-development-workflow
%}), but it works!

This part of the setup is all in [this pull
request](https://github.com/getcloudless/example-static-site/pull/3). The next
step is to serve this page over https.

## Getting a Certificate

Fortunately, [sslmate](https://sslmate.com/) comes with a
[sandbox](https://sslmate.com/help/sandbox) to make it easier to test out the
process of getting new certificates, so let's start there.

From the sandbox documentation and and the [automation
documentation](https://sslmate.com/help/cmdline/automation), I create a
`.sslmate` configuration file with `api_key` and `api_endpoint` set to the
sandbox credentials and ran this on my local machine:

```
$ sslmate --batch buy --no-wait --email admin@getcloudless.com getcloudless.com
Generating private key... Done.
Generating CSR... Done.
Placing order...
Order complete.

You will soon receive an email at admin@getcloudless.com from noreply_support@comodoca.com. Follow the instructions in the email to verify your ownership of your domain.

Once you've verified ownership, you will be able to download your certificate with the 'sslmate download' command.

           Private key: getcloudless.com.key
      Bare certificate: (not yet issued - will be getcloudless.com.crt)
     Certificate chain: (not yet issued - will be getcloudless.com.chain.crt)
Certificate with chain: (not yet issued - will be getcloudless.com.chained.crt)
```

I haven't gotten an email, so maybe the sandbox doesn't send an email?

```
$ sslmate download getcloudless.com
The certificate for getcloudless.com has been downloaded.

           Private key: getcloudless.com.key
      Bare certificate: getcloudless.com.crt
     Certificate chain: getcloudless.com.chain.crt
Certificate with chain: getcloudless.com.chained.crt
```

Looks like that's the case! Let's check out the certificates:

```
$ openssl x509 -text -noout -in getcloudless.com.crt  | grep Sandbox
        Issuer: C = US, O = SSLMate, CN = SSLMate 2015 Sandbox Intermediate CA 2
        Subject: OU = SSLMate Sandbox (Untrusted), OU = Domain Control Validated, OU = PositiveSSL, CN = getcloudless.com
```

Great, we got a self signed cert from the sandbox, this should be enough to get
started!

## Installing the Certificate

Because we want our nodes to be able to fully bootstrap without human
intervention, we'll need to set up sslmate on the destination machine.




