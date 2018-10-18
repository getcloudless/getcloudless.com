---
layout: post
title:  "Deploying getcloudless.com on Cloudless (Part 1.5)"
date:   2018-10-14 20:30:00 -0400
categories: cloudless production
---
In the last post we set up a [Vault server]({% post_url
2018-10-03-cloudless-on-cloudless %}). I was planning on using this to store the
monitoring and HTTPS certificate provisioning API keys. However, since that
doesn't have proper authentication set up and has no TLS, I thought it would be
misleading to use that in this deployment since I'm really using it more as an
internal key value store than as a fully secured secret server.

So this post is about doing something similar to what we did in that post,
except instead we will deploy a simple single node deployment of
[Consul](https://www.consul.io/), a Cluster key value store.

## Consul Setup

As a first step, I'll copy the vault configuration that I set up in Part 1
[here](https://github.com/getcloudless/example-vault), because at least the
initial download will be similar. This initial import is
[here](https://github.com/getcloudless/example-consul/pull/1).

Just like before, we will create the service using the `service-test` command.
However, I'm going to start off by trying my best to do a search/replace and
configure consul according to the Hashicorp docs. You can follow that work in
[this pull request](https://github.com/getcloudless/example-consul/pull/2).

So now, I'll deploy the test service:

```shell
sverch@local:$ cldls service-test deploy service_test_configuration.yml
Service test group with provider: gce
...
Deploy complete!
To log in, run:
ssh -i /home/sverch/projects/example-consul/.cloudless/id_rsa_test cloudless_service_test@35.237.102.128
sverch@local:$ ssh -i /home/sverch/projects/example-consul/.cloudless/id_rsa_test cloudless_service_test@35.237.102.128
...
sverch@remote:$
```

Great, we have our service!  Let's check if the Consul set up actually worked:

```shell
sverch@remote:$ cat /var/log/consul.log
Usage: consul [--version] [--help] <command> [<args>]
```

Ok, not a big surprise, considering I was running this blindly.  I think I'm
missing the `agent` subcommand, so let's try that:

```shell
sverch@remote:$ sudo /opt/consul/consul agent -server -bootstrap-expect=1 -data-dir=/var/consul/data/
...
    2018/10/15 01:00:53 [INFO] raft: Election won. Tally: 1
    2018/10/15 01:00:53 [INFO] raft: Node at 10.0.0.2:8300 [Leader] entering Leader state
    2018/10/15 01:00:53 [INFO] consul: cluster leadership acquired
    2018/10/15 01:00:53 [INFO] consul: New leader elected: test-network-dtzwouskir-test-service-ouwovhutcy-0
    2018/10/15 01:00:53 [INFO] consul: member 'test-network-dtzwouskir-test-service-ouwovhutcy-0' joined, marking health alive
    2018/10/15 01:00:56 [INFO] agent: Synced node info
```

All right, this looks reasonable. We're explicitly starting with a single node
cluster, so it just elected itself as leader and considered the work done.

Now that we're here, let's add some regression tests. I'm going to use the
[python-consul](https://github.com/cablehead/python-consul) library for this.
First, I realized that I forgot to open up Consul port 8300 in the fixture, so
let's just do that manually for now:

```shell
sverch@local:$ cldls paths alow_network_block test-network-dtzwouskir test-service-ouwovhutcy 0.0.0.0/0 8500
Paths group with provider: gce
...
Added path from 0.0.0.0/0 to test-service-ouwovhutcy in network test-network-dtzwouskir for port 8500
```

So now let's open up ipython and try to connect:

```shell
sverch@local:$ ipython
In [1]: import consul
In [2]: c = consul.Consul("35.237.102.128")
In [3]: c.kv.put('foo', 'bar')
...
ConnectionError: HTTPConnectionPool(host='35.237.102.128', port=8500): Max retries exceeded with url: /v1/kv/foo (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f665484d7f0>: Failed to establish a new connection: [Errno 111] Connection refused',))
```

Well, that's unfortunate. Let's use the same `nc` trick we used in [part 1]({%
post_url 2018-10-03-cloudless-on-cloudless %}) to see if the server is even
getting the connection, and try to connect with the python library:

```shell
sverch@remote:$ nc -l 8500
PUT /v1/kv/foo HTTP/1.1
Host: 35.237.102.128:8500
User-Agent: python-requests/2.19.1
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
Content-Length: 3

bar
```

So the server is receiving the request, which means Consul isn't accepting the
connection. It's probably not binding to all addresses, just like we found in
the [Vault setup]({% post_url 2018-10-03-cloudless-on-cloudless %}). Sure
enough, [there's a `-client`
option](https://www.consul.io/docs/agent/options.html#_client) that controls
which addresses the server will bind to. So now let's rerun Consul with that
option, passing `0.0.0.0` to bind all addresses:

```shell
sverch@remote:$ sudo /opt/consul/consul agent -server -bootstrap-expect=1 -data-dir=/var/consul/data/ -client "0.0.0.0"
```

Now, trying to connect from ipython:

```python
In [8]: c.kv.put('foo', 'bar')
Out[8]: True
In [9]: c.kv.get('foo')
Out[9]:
('45',
 {'LockIndex': 0,
  'Key': 'foo',
  'Flags': 0,
  'Value': b'bar',
  'CreateIndex': 43,
  'ModifyIndex': 45})
```

Great!  Next let's add a regression test and do the full run!

## Regression Testing

We'll add a regression test to our python test fixture just like we did in the
Vault setup, except this time with the Consul client library:

```python
def verify(self, network, service, setup_info):
    """
    Given the network name and the service name of the service under test,
    verify that it's behaving as expected.
    """
    def check_consul_setup():
        public_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
        assert public_ips, "No services are running..."
        for public_ip in public_ips:
            consul_client = consul.Consul(public_ip)
            assert consul_client.kv.put('testkey', 'testvalue'), "Failed to put test key!"
            testvalue = consul_client.kv.get('testkey')
            assert testvalue[1]["Key"] == "testkey"
            consul_client.kv.delete('testkey')
    call_with_retries(check_consul_setup, RETRY_COUNT, RETRY_DELAY)
```

Now let's run it against the Consul service we just started:

```shell
sverch@local:$ cldls service-test check service_test_configuration.yml
Service test group with provider: gce
...
Check complete!
...
```

I'm very suspicious that it worked the first time. Let's try running it when
Consul is stopped:

```shell
sverch@local:$ cldls service-test check service_test_configuration.yml
Service test group with provider: gce
...
INFO:cloudless.util:Attempt number: 0
INFO:cloudless.util:Verify exception: HTTPConnectionPool(host='35.237.102.128', port=8500): Max retries exceeded with url: /v1/kv/testkey (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7fdb48e8e4a8>: Failed to establish a new connection: [Errno 111] Connection refused',))
```

Ok, so the test does actually fail if Consul isn't working properly, that's
good. So at this point we're basically done! Let's copy the consul command to
the startup script and run the full create/test/destroy cycle:

```
sverch@local:$ cldls service-test run service_test_configuration.yml
Service test group with provider: gce
...
INFO:cloudless.util:Attempt number: 0
INFO:cloudless.util:Verify exception: 500 No cluster leader
INFO:cloudless.util:Attempt number: 1
INFO:cloudless.util:Verify successful!
...
INFO:cloudless.util:All tests passed!
Full test run complete!
```

Excellent. So now we have a basic Consul setup. I put all this work in [the same
pull request](https://github.com/getcloudless/example-consul/pull/2) just to
make it easier.

Remember, this automatically works on both AWS and GCE because it's the same API
for both. I can test this with this command because my `aws` profile is set up
to run against my AWS account:

```
sverch@local:$ cldls --profile aws service-test run service_test_configuration.yml
```

Check back for part 2, where I'll use this to create the web servers and finish
deploying [getcloudless.com](https://getcloudless.com) on Cloudless!

{% include post-footer.html %}
