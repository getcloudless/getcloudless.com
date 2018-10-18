---
layout: post
title:  "Deploying getcloudless.com on Cloudless (Part 2)"
date:   2018-10-18 00:30:00 -0400
categories: cloudless production
---
This is part two of deploying
[https://getcloudless.com](https://getcloudless.com) using Cloudless. In this
post we will set up the web servers with https and monitoring that can pull a
Jekyll based site from github.

In [part 1.5]({% post_url 2018-10-14-cloudless-on-cloudless-1.5 %}), we set up a
simple Consul server without TLS/SSL (no encryption in transit) or high
availability (only a single node). While that's is not the most secure or
resilient deployment, for the bare minimum setup that we're trying to go for,
it's enough. It's not enough to just say that though, so I'll give a short
justification as to why _for this particular case_ I'm not going to worry about
these right now.

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

```shell
git submodule add https://github.com/getcloudless/example-consul
```

Now, in the test setup, we can add:

```python
SERVICE_BLUEPRINT = os.path.join(os.path.dirname(__file__), "example-consul/blueprint.yml")
...
def setup_before_tested_service(self, network):
    """
    Create the dependent services needed to test this service.
    """
    service_name = "consul"
    service = self.client.service.create(network, service_name, SERVICE_BLUEPRINT, count=1)
    return SetupInfo(
        {"service_name": service_name},
        {"consul_ips": [i.private_ip for s in service.subnetworks for i in s.instances]})
```

And:

```python
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

```yaml
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

```shell
#! /bin/bash

{% raw %}
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
{% endraw %}
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

```shell
sverch@local:$ cldls service-test deploy service_test_configuration.yml
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
created. Let's see if the web server was able to pull the dummy key from Consul:

```shell
sverch@local:$ ssh -i /home/sverch/projects/example-static-site/.cloudless/id_rsa_test cloudless_service_test@35.237.3.172
sverch@remote:$ cat /tmp/dummy_key.txt
sverch@remote:$
```

No luck, but let's see if the python script is there:

```shell
sverch@remote:$ cat /tmp/fetch_key.py
import consul
consul_client = consul.Consul("10.0.0.2")
dummy_api_key = consul_client.kv.get('dummy_api_key')
print(dummy_api_key[1]["Value"].decode("utf-8").strip()
sverch@remote:$ python /tmp/fetch_key.py
  File "/tmp/fetch_key.py", line 5

                                                           ^
SyntaxError: invalid syntax
```

Alright, looks like a simple missing parentheses. After fixing that and a few
issues involving using `pip` instead of `pip3` everything worked, and running
the check command shows success:

```shell
cldls service-test check service_test_configuration.yml
...
INFO:cloudless.util:Verify successful!
...
```

I copied those fixes back into the test fixture and startup script, so now we
have a working Consul setup. This is all in [the same pull request as
before](https://github.com/getcloudless/example-static-site/pull/2). Now it's
time to actually start configuring our web servers!

## Nginx/Jekyll Setup

I'm going to go through these steps pretty quickly, because this is more about
Cloudless than about how to set up Jekyll or nginx, and they have great docs on
this already.

First, let's install nginx:

```shell
sverch@remote:$ sudo apt-get install nginx
```

And from another terminal make sure we can reach it from the public IP:

```shell
sverch@local:$ curl --silent 35.237.3.172 | grep "Thank you"
<p><em>Thank you for using nginx.</em></p>
```

Now, let's do all the Jekyll setup:

```shell
sverch@remote:$ sudo apt-get install git
sverch@remote:$ git clone https://github.com/getcloudless/getcloudless.com.git
sverch@remote:$ sudo apt-get install ruby ruby-dev build-essential
sverch@remote:$ sudo gem install bundler
sverch@remote:$ cd getcloudless.com/
sverch@remote:$ export GEM_HOME=$HOME/gems
sverch@remote:$ export PATH=$HOME/gems/bin:$PATH
sverch@remote:$ bundle install
...
	ERROR: Failed to build gem native extension.
...
zlib is missing; necessary for building libxml2
...
sverch@remote:$ sudo apt-get install zlib1g-dev
sverch@remote:$ bundle install
sverch@remote:$ sudo chown -R $(whoami) /var/www/html
sverch@remote:$ bundle exec jekyll build --destination /var/www/html
```

That's a lot, but it's mostly fighting with ruby dependencies and stepping
through the normal installation of Jekyll, which you can find
[here](https://jekyllrb.com/docs/installation/ubuntu/).

But now, we're serving Cloudless!

```shell
sverch@local:$ curl --silent 35.237.3.172 | grep "<title>"
    <title>Cloudless</title>
```

Before we go any further, let's add this to our regression test:

```shell
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

```shell
sverch@local:$ cldls service-test check service_test_configuration.yml
...
Check complete!
...
```

Now I'll just add all the above configuration to the startup script, and try to
run the full deploy/test cycle:

```shell
sverch@local:$ cldls service-test cleanup service_test_configuration.yml
sverch@local:$ cldls service-test run service_test_configuration.yml
...
INFO:cloudless.util:All tests passed!
Full test run complete!
```

It takes a while to deploy, which would be fixed by [building much of the setup
into a base image]({% post_url 2018-09-24-the-cloudless-development-workflow
%}), but it works!

This part of the setup is all in [this pull
request](https://github.com/getcloudless/example-static-site/pull/3). The next
step is to serve this page over https.

## Getting a Certificate

Fortunately, [sslmate](https://sslmate.com/) comes with a
[sandbox](https://sslmate.com/help/sandbox) to make it easier to test out the
process of getting new certificates, so let's start there. You can install
sslmate using [these instructions](https://sslmate.com/help/cmdline/install).

From the sandbox documentation and and the [automation
documentation](https://sslmate.com/help/cmdline/automation), I created a
`.sslmate` configuration file with `api_key` and `api_endpoint` set to the
sandbox credentials and ran this on my local machine:

```shell
sverch@local:$ sslmate --batch buy --no-wait --email admin@getcloudless.com getcloudless.com
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

I never got an email, but the certificates are authorized, which is probably
just a feature of the sandbox:

```shell
sverch@local:$ sslmate download getcloudless.com
The certificate for getcloudless.com has been downloaded.

           Private key: getcloudless.com.key
      Bare certificate: getcloudless.com.crt
     Certificate chain: getcloudless.com.chain.crt
Certificate with chain: getcloudless.com.chained.crt
```

All right! Let's check out the certificates:

```shell
sverch@local:$ openssl x509 -text -noout -in getcloudless.com.crt  | grep Sandbox
        Issuer: C = US, O = SSLMate, CN = SSLMate 2015 Sandbox Intermediate CA 2
        Subject: OU = SSLMate Sandbox (Untrusted), OU = Domain Control Validated, OU = PositiveSSL, CN = getcloudless.com
```

Great, we got a self signed cert from the sandbox, this should be enough to get
started!

## Installing the Certificate

Because we want our nodes to be able to fully bootstrap without human
intervention, we'll need to set up sslmate on the destination machine so it can
pull down its own certificates.

From the documentation about [how to automate
sslmate](https://sslmate.com/help/cmdline/automation), I see:

```shell
if sslmate download --all
then
	service apache2 restart
fi
```

That looks like exactly what I want, and I can just replace apache with nginx.
The next challenge here will be actually getting the credentials for sslmate
onto the box! Well, once again, let's use the test framework to do add them to
Consul automatically:

```python
use_sslmate = 'SSLMATE_API_KEY' in os.environ

@retry(wait_fixed=5000, stop_max_attempt_number=24)
def add_api_keys(service):
    public_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
    assert public_ips, "No services are running..."
    for public_ip in public_ips:
        consul_client = consul.Consul(public_ip)
        if use_sslmate:
            consul_client.kv.put('SSLMATE_API_KEY', os.environ['SSLMATE_API_KEY'])
            consul_client.kv.put('SSLMATE_API_ENDPOINT', os.environ['SSLMATE_API_ENDPOINT'])
            consul_client.kv.put('getcloudless.com.key',
                                 open(os.environ['SSLMATE_PRIVATE_KEY_PATH']).read())
    return True

# Now let's add any necessary API keys to Consul.
my_ip = requests.get("http://ipinfo.io/ip")
test_machine = CidrBlock(my_ip.content.decode("utf-8").strip())
self.client.paths.add(test_machine, service, 8500)
add_api_keys(service)
self.client.paths.remove(test_machine, service, 8500)
```

So now we have a test framework that will only test the service with sslmate if
we actually have the `SSLMATE_API_KEY` environment variable set. We also make
this optional in the blueprint configuration:

```yaml
initialization:
  - path: "static_site_startup_script.sh"
    vars:
      jekyll_site_domain:
        required: true
      jekyll_site_github_url:
        required: true
      consul_ips:
        required: true
      use_sslmate:
        required: false
      cloudless_test_framework_ssh_key:
        required: false
      cloudless_test_framework_ssh_username:
        required: false
```

We also have a few more variables because they are needed for the Jekyll and
sslmate setup.

You may wonder what should be passed in as a blueprint variable, what should be
pulled from Consul, what should be in the blueprint startup script, and what
should be in the image itself. The real answer is it varies, but one of the
ideas behind Cloudless is that what something is should be declarative and in
version control, but where it is, how many there are, and what it's being used
for should not be.

In this example, the boilerplate configuration and package installation is more
of the declarative part, while which site is being served, the API keys, and
whether we are using SSL are not. In theory, all this could and probably should
be pulled from a configuration store like Consul, but this shows an example of
how these could be passed through the blueprint itself.

I won't show all the nginx configuration here (you can find it in the [github
project](https://github.com/getcloudless/example-static-site)), but the meat of
the sslmate setup looks like:

```shell
{% raw %}
{% if use_sslmate %}
# Install sslmate certificate download script
cat <<EOF > /opt/sslmate_download.sh
cd /etc/sslmate/
if sslmate download {{ jekyll_site_domain }}
then
    service nginx restart
fi
EOF
chmod a+x /opt/sslmate_download.sh

# Configure sslmate
cat <<EOF >| /etc/sslmate.conf
api_key $(python3 /tmp/fetch_key.py SSLMATE_API_KEY)
api_endpoint $(python3 /tmp/fetch_key.py SSLMATE_API_ENDPOINT)
EOF

# Fetch ssl private key first so sslmate can check that it's correct
python3 /tmp/fetch_key.py "{{ jekyll_site_domain }}.key" >> "/etc/sslmate/{{ jekyll_site_domain }}.key"

# Download ssl certificates
/opt/sslmate_download.sh

# Install certificate download as a cron job
# (https://stackoverflow.com/a/16068840)
(crontab -l ; echo "0 1 * * * /opt/sslmate_download.sh") | crontab -
{% endif %}
{% endraw %}
```

And that's it! All this can be added back to our startup script and we can
update our integration test to use `https` instead of `http` if ssl is being
used. To avoid making this any longer, just check the [pull request]() with all
these changes if you're interested.

## DataDog Setup

We're almost there! The last bit of setup we need is DataDog. Since we already
have all the other machinery, this isn't so bad. We just check if the
`DATADOG_API_KEY` environment variable is set, upload it to Consul if it is, and
download it when we configure datadog. I'm not going to include that
configuration here, but you can [see it in the github
repo](https://github.com/getcloudless/example-static-site) if you're interested.
These were the [datadog installation
docs](https://docs.datadoghq.com/agent/basic_agent_usage/ubuntu/?tab=agentv6#manual-install)
that I referenced.

The thing I really want to show is the test for this:

```python
# Don't check datadog if we have no API key
if 'DATADOG_API_KEY' not in os.environ:
    return

options = {
    'api_key': os.environ['DATADOG_API_KEY'],
    'app_key': os.environ['DATADOG_APP_KEY']
}

initialize(**options)

def is_agent_reporting():
    end_time = time.time()
    # Just go ten minutes back
    start_time = end_time - 6000
    events = api.Event.query(
        start=start_time,
        end=end_time,
        priority="normal"
    )
    def check_event_match(event):
        for tag in event['tags']:
            if re.match(".*%s.*%s.*" % (network.name, service.name), tag):
                return True
        if 'is_aggregate' in event and event['is_aggregate']:
            for child in event['children']:
                child_event = api.Event.get(child['id'])
                if check_event_match(child_event['event']):
                    return True
        return False
    for event in events['events']:
        if check_event_match(event):
            return True
    assert False, "Could not find this service in datadog events!  %s" % events
call_with_retries(is_agent_reporting, RETRY_COUNT, RETRY_DELAY)

def is_agent_sending_nginx_metrics():
    now = int(time.time())
    query = 'nginx.net.connections{*}by{host}'
    series = api.Metric.query(start=now - 600, end=now, query=query)
    for datapoint in series['series']:
        if re.match(".*%s.*%s.*" % (network.name, service.name), datapoint['expression']):
            return
        # Delete this because we don't care about it here and it muddies the error message
        del datapoint['pointlist']
    assert False, "No nginx stats in datadog metrics for this service!  %s" % series
call_with_retries(is_agent_sending_nginx_metrics, RETRY_COUNT, RETRY_DELAY)
```

This is some pretty messy python code, but it shows how you can use the datadog
python library to create an integration test to make sure this thing hooks up
correctly with Datadog.

I did some minor debugging and ran the final test run, so now we're done!  The
pull request for this part is
[here](https://github.com/getcloudless/example-static-site/pull/7).

## Coming Up Next

This was a lot for one post, so there will be one more post to actually run the
real deployment of [getcloudless.com](https://getcloudless.com). But now we have
all the building blocks we need to do that!

Also, remember these are just examples. At your real job you would probably
[build a base image]({% post_url 2018-09-24-the-cloudless-development-workflow
%}) that has a lot of these things preinstalled, and instead of jank bash
scripts to get the configuration from Consul, you'd probably have real agents
with unit tests. But now you know how to use Cloudless to deploy all that!

{% include post-footer.html %}
