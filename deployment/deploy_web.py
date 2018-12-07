"""
Simple Python Deployment Script for Cloudless!
"""
import os
import sys
import click
import cloudless
import cloudless.profile
from cloudless.types.networking import CidrBlock
sys.path.append("example-static-site")
# pylint: disable=no-name-in-module,import-error,wrong-import-position
from helpers.health import check_health

@click.command()
@click.argument("consul-name")
@click.argument("service-name")
@click.option("--count", default=1, help="Number of web services.")
@click.option("--profile-name", default=None, help="Profile to use.")
def deploy(consul_name, service_name, profile_name, count):
    """Deploy the service in the cloudless environment in the given profile."""
    # Need to do this outside our client because of
    # https://github.com/getcloudless/cloudless/issues/56
    if profile_name:
        profile_name = profile_name
    elif "CLOUDLESS_PROFILE" in os.environ:
        profile_name = os.environ["CLOUDLESS_PROFILE"]
    else:
        profile_name = "default"
    profile = cloudless.profile.load_profile(profile_name)
    if not profile:
        click.echo("Profile: \"%s\" not found." % profile_name)
        click.echo("Try running \"cldls --profile %s init\"." % profile_name)
        sys.exit(1)
    client = cloudless.Client(provider=profile['provider'], credentials=profile['credentials'])
    service = client.service.get(client.network.get("cloudless"), service_name)
    network = client.network.get("cloudless")
    if service:
        print("Service: %s already exists!" % service_name)
    else:
        print("Service: %s not found!  Creating." % service_name)
        consul_service = client.service.get(network, consul_name)
        consul_instances = client.service.get_instances(consul_service)
        blueprint_vars = {
            "jekyll_site_domain": "getcloudless.com",
            "jekyll_site_github_url": "https://github.com/getcloudless/getcloudless.com/",
            "consul_ips": [instance.private_ip for instance in consul_instances],
            "use_sslmate": True,
            "use_datadog": True}
        internet = CidrBlock("0.0.0.0/0")
        service = client.service.create(network, service_name,
                                        blueprint="example-static-site/blueprint.yml", count=count,
                                        template_vars=blueprint_vars)
        client.paths.add(service, consul_service, 8500)
        client.paths.add(internet, service, 80)
        client.paths.add(internet, service, 443)
        print("Created service: %s!" % service_name)
        service_instances = client.service.get_instances(service)
        service_ips = [{"public_ip": instance.public_ip, "private_ip": instance.private_ip}
                       for instance in service_instances]
        check_health(service_ips, "Cloudless", use_datadog=True, use_sslmate=True)
        print("")
        print("Deploy Successful!")
        print("")
        print("Service IPs: %s" % service_ips)
    print("Use 'cldls service get cloudless %s' for more info." % service_name)

if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    deploy()
