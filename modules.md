---
layout: page
title: Module Directory
permalink: /modules/
---
Cloudless can pull blueprint files for service configuration from Github.  This
is the directory of the current list of known modules.  Submit a pull request to
[https://github.com/getcloudless/module_directory](https://github.com/getcloudless/module_directory)
if you would like to submit a new cluster and modules.

{% for cluster in site.data.modules.clusters %}

## `{{ cluster.name }}`

{{ cluster.description }}

{% for module in cluster.modules %}
  <hr>
### [`{{ module.name }}`]({{ module.url }})

{{ module.description }}

{% if module.image_build_configuration %}
This module has an image build configuration:

    cldls image-build {{ cluster.name }}/{{ module.name }}
{% endif %}
{% if module.service_test_configuration %}
This module has a service test configuration:

    cldls service-test {{ cluster.name }}/{{ module.name }}
{% endif %}

To deploy this service using its blueprint:

    cldls service deploy example-network example-service {{ cluster.name }}/{{ module.name }} vars.yml

{% endfor %}
{% endfor %}
