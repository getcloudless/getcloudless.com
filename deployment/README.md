# Cloudless on Cloudless

Example of how to deploy a static site on Cloudless, in particular
getcloudless.com.

You should install the python dependencies first.  This project uses
[pipenv](https://pipenv.readthedocs.io/en/latest/):

```shell
$ pipenv shell
$ pipenv install
```

First, deploy Consul.  This will store our secrets:

```shell
$ cldls network create cloudless network.yml
$ cldls service create --count 1 cloudless consul-1 example-consul/blueprint.yml
```

Then, upload the necessary secrets to Consul.  This assumes you have the
following environment variables set:

- `SSLMATE_API_ENDPOINT`: SSLMate endpoint to use.  Useful to test with the
  SSLMate sandbox.
- `SSLMATE_API_KEY`: Your secret SSLMate API key.  Get this from your [SSLMate
  account page](https://sslmate.com/account).
- `SSLMATE_PRIVATE_KEY_PATH`: Path to your private key.  This is generated
  automatically when you buy a certificate from SSLMate.
- `DATADOG_API_KEY`: API Key for Datadog.  You need both this and the APP key to
  connect to the Datadog API.
- `DATADOG_APP_KEY`: APP Key for Datadog.  You need both this and the API key to
  connect to the Datadog API.

Once you have these set, run:

```shell
$ cldls paths allow_network_block cloudless consul-1 $(curl --silent ipinfo.io/ip) 8500
$ CONSUL_IP=$(cldls service get cloudless consul-1 | grep public_ip | awk -F: '{print $2}')
$ python example-static-site/helpers/setup_consul.py $CONSUL_IP getcloudless.com both
$ cldls paths revoke_network_block cloudless consul-1 $(curl --silent ipinfo.io/ip) 8500
```

Now, run the deploy script to deploy the web service.  This has a lot hard coded
in it for now, and mostly just calls a helper in the module:

```shell
$ ./deploy.sh
```

This calls a python script that deploys the web service, sets up the proper
paths, and runs the health checks to make sure the service is logging and
responding.

Finally, update your DNS if you use NS1 by running
`example-static-site/helpers/update_dns.py`.
