---
layout: page
title: Module Directory
permalink: /modules/
---
Cloudless can pull blueprint files for service configuration from Github.  This
is the directory of the current list of known modules.  Submit a pull request to
[https://github.com/getcloudless/module_directory](https://github.com/getcloudless/module_directory)
if you would like to submit a new module.

{% for namespace in site.data.modules.namespaces %}

## `{{ namespace.name }}`

{{ namespace.description }}

{% for module in namespace.modules %}
  <hr>
### [`{{ module.name }}`]({{ module.url }})

{{ module.description }}

{% if module.image_build_configuration %}
This module has an image build configuration:

    cldls image-build {{ namespace.name }}/{{ module.name }}
{% endif %}
{% if module.service_test_configuration %}
This module has a service test configuration:

    cldls service-test {{ namespace.name }}/{{ module.name }}
{% endif %}

To deploy this service using its blueprint:

    cldls service deploy example-network example-service {{ namespace.name }}/{{ module.name }} vars.yml

{% endfor %}
{% endfor %}
