---
layout: post
title:  "Deploying getcloudless.com on Cloudless (Part 1)"
date:   2018-10-3 16:30:00 -0400
categories: cloudless production
---
It's hard to evaluate whether something is useful until there's an example of
how it works in a real production setting.  Cool ideas are free but actually
building something that works isn't.

Given that, this post is meant to document the process of deploying
[getcloudless.com](https://getcloudless.com) on Cloudless.  It's a small test
case because getcloudless.com is a simple static site, but everything has to
start somewhere and this will be a good way to show the "minimum viable"
deployment.

This post is Part One of a two part setup, since the architecture (described
below) has two separate components.

## Architecture

The simplest _possible_ deployment would be to spin up a server that clones the
[getcloudless.com git
repository](https://github.com/getcloudless/getcloudless.com/), builds it using
jekyll and serves it up over http.  This would require nothing secret and be
easy to set up in a simple startup script.

However, to make this more like a minimum production setup, the deployment of
getcloudless.com will use https and have a simple monitoring setup.  This means
that the web servers will need the API keys for the certificate renewal and
monitoring agent.  These are sensitive, so they shouldn't be hard coded in the
startup script or built into the image.  As a result, the deployment will
require two parts: a basic secrets server, and the web servers themselves.

### Secrets

If you are new to secrets management, see [this blog
post](https://medium.com/square-corner-blog/protecting-infrastructure-secrets-with-keywhiz-af674410832f)
by Square for a good overview of the alternatives.

Without a secrets server, your options are limited.  You can manually log into
the instances to add secrets, or have some other out of band automated process
log in to effectively do the same thing.  Besides the drawbacks they described
in that post, [the Cloudless model]({% post_url
2018-09-24-the-cloudless-development-workflow %}) explicitly doesn't encourage
logging in to set up machines, so the instances need some way to get their own
secrets.

For our secrets server, we will do a simple single node setup of [Hashicorp's
Vault](https://www.vaultproject.io/), which will store the API keys that the web
servers need on its local filesystem.  Note this is not HA, but in our setup
Vault going down will not take the site down (the webservers that are already
running will cache the secrets and be unaffected) so this is kept simple in the
spirit of keeping the setup as minimal as possible.  Future work would be needed
to deploy a [Consul](https://www.consul.io/) cluster to act as the Vault
backend, which would make this setup more resilient.

This is what we will cover in Part One (this post).

### Web Server

The web server will be running a basic [nginx](https://www.nginx.com/) server
that is configured with SSL certificates from [sslmate](https://sslmate.com/)
and monitored using [Datadog](https://www.datadoghq.com/).  It will periodically
pull the [getcloudless.com
repository](https://github.com/getcloudless/getcloudless.com/), build it using
[jekyll](https://jekyllrb.com/), and update the files being served by nginx.  It
will also use [uptime](https://uptime.com/) for external website monitoring.

This is what we will cover in Part Two.

## Development

This is a walkthrough of all the steps I went through to get this set up,
including any mistakes and messy debugging.  It's meant to show the real
workflow of developing a new module with Cloudless.

Note that this is also my first time using Vault, so I'm sure I'm making
mistakes.  Everything I'm doing will live in
[https://github.com/getcloudless/example-vault](https://github.com/getcloudless/example-vault)
so please submit an issue there if you have corrections!

### Initial Copy

First, let's copy the
[example-apache](https://github.com/getcloudless/example-apache.git) repository,
since that's the simplest starting point, and use it to create [example-vault](https://github.com/getcloudless/example-vault):

```shell
$ git clone https://github.com/getcloudless/example-apache.git
$ git clone https://github.com/getcloudless/example-vault.git
$ cp -r example-apache/* example-vault/
cp: overwrite 'example-vault/README.md'? y
$ cd example-vault/
$ git checkout -b initial-apache-copy
$ git add .
$ git commit
$ git push origin initial-apache-copy 
Counting objects: 8, done.
Delta compression using up to 8 threads.
Compressing objects: 100% (8/8), done.
Writing objects: 100% (8/8), 3.28 KiB | 1.09 MiB/s, done.
Total 8 (delta 0), reused 0 (delta 0)
remote: 
remote: Create a pull request for 'initial-apache-copy' on GitHub by visiting:
remote:      https://github.com/getcloudless/example-vault/pull/new/initial-apache-copy
remote: 
To github.com:getcloudless/example-vault.git
 * [new branch]      initial-apache-copy -> initial-apache-copy
```

You can find that pull request
[here](https://github.com/getcloudless/example-vault/pull/1).

### Development Server

These steps set up the server we're going to use to iterate on our Vault setup.

Before we deploy the server let's first change [this
line](https://github.com/getcloudless/example-vault/blob/13bc953d63939773d9baeaf2725a6e3bc8a0602e/blueprint_fixture.py#L32)
in the service test fixture to [allow the Vault ports (8200,
8201)](https://github.com/getcloudless/example-vault/pull/3).  This will ensure
these ports are open from our test machine to the server we are working on.

Now, we install cloudless using the [Pipfile](https://github.com/pypa/pipfile)
that comes with the repo:

```shell
$ pipenv install
Installing -e git+https://github.com/getcloudless/cloudless@master#egg=cloudless...
...
$ pipenv shell
$ which cldls
```

And finally, we can create and log in to the server we are going to use for
development:

```shell
$ cldls service-test deploy service_test_configuration.yml

...

Deploy complete!
To log in, run:
ssh -i /home/sverch/projects/example-vault/.cloudless/id_rsa_test cloudless_service_test@35.237.47.21
$ ssh -i /home/sverch/projects/example-vault/.cloudless/id_rsa_test cloudless_service_test@35.237.47.21

...

Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
applicable law.

cloudless_service_test@test-network-ahcwqxezbk-test-service-vhhjzhzyph-0:~$ 
```

### Vault Installation

Now that we're on the machine, we can try out the Vault installation.  I'm not
doing anything fancy here, just following the [Vault Installation
Documentation](https://www.vaultproject.io/intro/getting-started/install.html).

First, we need to download Vault.  These steps also include verifification of
the package signature.  See [here](https://www.hashicorp.com/security.html) for
documentation on how to do this and how to find Hashicorp's keys.

```shell
$ gpg --keyserver keys.gnupg.net --recv-key 0x51852D87348FFC4C
gpg: requesting key 348FFC4C from hkp server keys.gnupg.net
gpg: key 348FFC4C: public key "HashiCorp Security <security@hashicorp.com>" imported
gpg: no ultimately trusted keys found
gpg: Total number processed: 1
gpg:               imported: 1  (RSA: 1)
$ # Download the binary and signature files.
$ curl -Os https://releases.hashicorp.com/vault/0.11.2/vault_0.11.2_linux_amd64.zip
$ curl -Os https://releases.hashicorp.com/vault/0.11.2/vault_0.11.2_SHA256SUMS
$ curl -Os https://releases.hashicorp.com/vault/0.11.2/vault_0.11.2_SHA256SUMS.sig
$ # Verify the signature file is untampered.
$ gpg --verify vault_0.11.2_SHA256SUMS.sig vault_0.11.2_SHA256SUMS
gpg: Signature made Tue 02 Oct 2018 06:51:15 PM UTC using RSA key ID 348FFC4C
gpg: Good signature from "HashiCorp Security <security@hashicorp.com>"
gpg: WARNING: This key is not certified with a trusted signature!
gpg:          There is no indication that the signature belongs to the owner.
Primary key fingerprint: 91A6 E7F8 5D05 C656 30BE  F189 5185 2D87 348F FC4C
$ # Verify the SHASUM matches the binary.
$ shasum -a 256 -c vault_0.11.2_SHA256SUMS
...
vault_0.11.2_linux_amd64.zip: OK
...
$ gpg --fingerprint 0x51852D87348FFC4C | grep "91A6 E7F8 5D05 C656 30BE  F189 5185 2D87 348F FC4C"
      Key fingerprint = 91A6 E7F8 5D05 C656 30BE  F189 5185 2D87 348F FC4C
```

Now we can unzip the package and make sure it works!

```shell
$ sudo apt-get -y install unzip
$ unzip vault_0.11.2_linux_amd64.zip 
Archive:  vault_0.11.2_linux_amd64.zip
  inflating: vault                   
$ ./vault --help
Usage: vault <command> [args]

Common commands:
    read        Read data and retrieves secrets
    write       Write data, configuration, and secrets
    delete      Delete secrets and configuration
    list        List data or secrets
    login       Authenticate locally
    agent       Start a Vault agent
    server      Start a Vault server
    status      Print seal and HA status
    unwrap      Unwrap a wrapped secret

Other commands:
    audit          Interact with audit devices
    auth           Interact with auth methods
    kv             Interact with Vault's Key-Value storage
    lease          Interact with leases
    namespace      Interact with namespaces
    operator       Perform operator-specific tasks
    path-help      Retrieve API help for paths
    plugin         Interact with Vault plugins and catalog
    policy         Interact with policies
    secrets        Interact with secrets engines
    ssh            Initiate an SSH session
    token          Interact with tokens
```

### Vault First Run

To run Vault, we need to start vault with some initial configuration.  For this
example we are using the
[Filesystem](https://www.vaultproject.io/docs/configuration/storage/filesystem.html)
backend:

```shell
$ cat <<EOF >| vault.hcl
storage "file" {
  path = "/var/vault/data"
}

listener "tcp" {
 address     = "127.0.0.1:8200"
 tls_disable = 1
}
$ sudo mkdir -p /var/vault/data
$ sudo ./vault server -config=vault.hcl
...
==> Vault server started! Log data will stream in below:
```

### Verification and Debugging

Now that we have a basic Vault installation, we want to start adding tests to
verify the installation works.  These tests are sort of a halfway point between
integration tests and unit tests.  See [the Cloudless development workflow]({%
post_url 2018-09-24-the-cloudless-development-workflow %}) for more background
on this.

In our test fixture we will use the [Vault Python
Library](https://github.com/hvac/hvac).  To install and add this package to our
project's Pipfile, we run:

```shell
pipenv install hvac
```

Now we can change the verify function in the [test
fixture](https://github.com/getcloudless/example-vault/blob/master/blueprint_fixture.py)
to use this function to test whether vault is set up properly:

```python
import hvac

...
...

def verify(self, network, service, setup_info):
    """
    Given the network name and the service name of the service under test,
    verify that it's behaving as expected.
    """
    def check_vault_setup():
        public_ips = [i.public_ip for s in service.subnetworks for i in s.instances]
        assert public_ips, "No services are running..."
        for public_ip in public_ips:
            client = hvac.Client(url='http://%s:8200' % public_ip)
            client.write('secret/foo', baz='bar', lease='1h')
            my_secret = client.read('secret/foo')
            client.delete('secret/foo')
            assert "baz" in my_secret["data"], "Baz not in my_secret: %s" % my_secret
            assert my_secret["data"]["baz"] == "bar", "Baz not 'bar': %s" % my_secret
    call_with_retries(check_vault_setup, RETRY_COUNT, RETRY_DELAY)
```

Now, run the `check` step to run that verifier and see if everything is working:

```shell
$ cldls service-test check service_test_configuration.yml
...
INFO:cloudless.util:Verify exception: HTTPConnectionPool(host='35.237.47.21', port=8200): Max retries exceeded with url: /v1/secret/foo (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f36de803080>: Failed to establish a new connection: [Errno 111] Connection refused',))
```

Well, looks like we have a problem.  Maybe it's a firewall issue?  Let's check
our routes:

```shell
$ cldls paths list
...
external:0.0.0.0/0 -(22)-> test-network-ahcwqxezbk:test-service-vhhjzhzyph
external:33.33.33.33/32 -(8200)-> test-network-ahcwqxezbk:test-service-vhhjzhzyph
external:33.33.33.33/32 -(8201)-> test-network-ahcwqxezbk:test-service-vhhjzhzyph
$ curl ipinfo.io/ip
33.33.33.33
```

Those generally look ok.  In theory, my IP, `33.33.33.33` should have access on
port `8200`.  Let's try a sanity check and run the `nc` command to listen on
port `8200` on the server instead of Vault:

```shell
$ nc -l 8200
```

Now, from the local machine:

```shell
$ curl 35.237.47.21:8200
```

And on the server, we see:

```shell
GET / HTTP/1.1
Host: 35.237.47.21:8200
User-Agent: curl/7.59.0
Accept: */*
```

So the firewall is fine, which means the problem is that Vault is not listening
on port 8200.  This makes sense because we got "connection refused" instead of
"host unreachable", which tells us that we were able to reach the destination
server but it refused our connection request.

Looking at the [Vault listener
configuration](https://www.vaultproject.io/docs/configuration/listener/tcp.html)
and doing a little bit of searching, I found that the string `127.0.0.1:8200`
means to only bind localhost (which in
retrospect is obvious) and `0.0.0.0` means to bind all interfaces.  Changing
that in the configuration causes the check to yield this error:

```shell
$ cldls service-test check service_test_configuration.yml 
...
INFO:cloudless.util:Attempt number: 0
INFO:cloudless.util:Verify exception: Vault is sealed
INFO:cloudless.util:Attempt number: 1
INFO:cloudless.util:Verify exception: Vault is sealed
```

Great, we got a different error!  This is telling us that we have to actually
initialize and unseal the Vault by providing the Vault master keys.  Fortunately
our [python library has this
capability](https://hvac.readthedocs.io/en/latest/usage/system_backend.html?highlight=unseal).

Let's add a simplified version of those code examples to our verify step:

```
shares = 1
threshold = 1
result = client.initialize(shares, threshold)
root_token = result['root_token']
keys = result['keys']
client.unseal_multi(keys)
```

For simplicity we will just use the root token in the rest of the calls.  The
goal is to test that Vault is running, not to do a full secure setup for now.

Now when we run the `check` command, the verify succeeds!

```shell
$ cldls service-test check service_test_configuration.yml
...
INFO:cloudless.util:Verify successful!
...
```

This may not seem like much, but think about what just happened:  We just wrote
a very simple Vault integration test.  With some cleanup, we could factor this
out and run it against other Vault servers, possibly even as an ongoing health
check.

This shows one of the big goals of Cloudless, which is to make this kind of end
to end testing part of the normal development workflow.

### The Startup Script

Now that we've iterated on this and got our first Vault server running, let's
take a first pass at putting all this into a startup script.  I'm going to be
extremely lazy and run:

```shell
$ ssh -i /home/sverch/projects/example-vault/.cloudless/id_rsa_test cloudless_service_test@35.237.47.21 cat .bash_history > setup_vault.sh
```

To make the test framework ssh keys work, I have to add this to the beginning of
the startup script:

```shell
{% raw %}
{% if cloudless_test_framework_ssh_key %}
adduser "{{ cloudless_test_framework_ssh_username }}" --disabled-password --gecos "Cloudless Test User"
echo "{{ cloudless_test_framework_ssh_username }} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
mkdir /home/{{ cloudless_test_framework_ssh_username }}/.ssh/
echo "{{ cloudless_test_framework_ssh_key }}" >> /home/{{ cloudless_test_framework_ssh_username }}/.ssh/authorized_keys
{% endif %}
{% endraw %}
```

In a real deployment, you don't set these variables and this block gets
templated out.

Now, after a lot of editing/removing unnecessary lines where I made mistakes or
typos, I can run this to remove my crufty test service:

```shell
$ cldls service-test cleanup service_test_configuration.yml
```

And run this to see if it's working:

```shell
$ cldls service-test deploy service_test_configuration.yml
$ cldls service-test check service_test_configuration.yml
```

I had a small typo where I had a `$ cat` command instead of just `cat`, but I
was able to log in, find the problem, and fix it in the startup script.

Now that I'm more confident everything is working, do the full run for good
measure (just runs all the above commands in order):

```shell
$ cldls service-test run service_test_configuration.yml
...
Full test run complete!
```

And let's try it on AWS:

```shell
$ cldls --profile aws service-test run service_test_configuration.yml
...
Full test run complete!
```

Great!  Now we have a basic Vault setup that works on both Amazon Web Services
and Google Compute Engine.  You can find the results in [this pull
request](https://github.com/getcloudless/example-vault/pull/4).  It's also
merged into master, so you could run this all yourself!

## Coming Up Next

This is part one of a two part setup, and we still need to deploy the web
service itself, so check back for updates!

<hr>

Thanks for trying Cloudless!  Check out the
[Documentation](https://docs.getcloudless.com/) for more info, and star the
[Github Repo](https://github.com/getcloudless/cloudless) if you like this
project.  You can also [subscribe for updates](/#subscribe-for-updates) or email
[info@getcloudless.com](info@getcloudless.com).
