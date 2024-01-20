---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: home
title: "Cloudless"
---

{% capture abandon_blurb %}
NOTE: This is a research project and should not be used in production, see <a href="{% post_url 2020-02-21-abandoning-cloudless-v1 %}">this post for the findings.</a>.
{% endcapture %}

{% include abandon.html
    pitch_subtitle=abandon_blurb %}
<hr>

{% capture dev_workflow_blurb %}
Cloudless has no opinions on what you install on your servers, so <a href="{%
post_url 2018-09-24-the-cloudless-development-workflow %}">you can use any
configuration management tool you choose</a>.
{% endcapture %}
{% include pitch.html
    pitch_title="Truly Portable Infrastructure"
    pitch_subtitle="Declarative infrastructure that's actually reusable"
    pitch_cta_url="https://docs.getcloudless.com/#quick-start"
    pitch_cta_message="Get Started"
    pitch_cta2_url="/cloudless/production/2018/12/07/cloudless-on-cloudless-3.html"
    pitch_cta2_message="See It In Action" %}

{% include intro-grid.html
    section_1_header="Testable"
    section_1_content="The only way to viably share infrastructure components is
    to have deterministic testing.  Cloudless makes this a first class citizen
    with a <a href=\"https://docs.getcloudless.com/#service-tester\">built in
    module test framework</a>."

    section_2_header="Lightweight"
    section_2_content="No framework or extra infrastructure necessary.  The
    library and command line interface <a
    href=\"https://docs.getcloudless.com/providers/\">interact directly with the
    cloud provider</a>."

    section_3_header="Flexible"
    section_3_content=dev_workflow_blurb

    section_4_header="Portable"
    section_4_content="Because instance types, feature names, and cloud-specific
    property names are all abstracted away, <a
    href=\"https://docs.getcloudless.com/#service\">any infrastructure built
    using Cloudless works across all supported providers</a>." %}

Check out the [Blog](/blog) to learn more about Cloudless and how to use it, or
just go straight to the [Docs]({{ site.docs_url }}) and [Github
Repo](https://github.com/{{ site.github_username }}) to get started!
