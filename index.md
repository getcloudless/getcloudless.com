---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults

layout: home
title: "Cloudless"
---
{% capture local_url %}{% post_url 2018-09-05-welcome-to-cloudless %}{% endcapture %}
{% include pitch.html
    pitch_title="Control Your Infrastructure"
    pitch_subtitle="The Open Source alternative to proprietary managed services"
    pitch_cta_url=local_url
    pitch_cta_message="Learn More" %}

{% include intro-grid.html
    section_1_header="Intuitive"
    section_1_content="Cloudless does the right thing and makes it obvious why.
    At its core, it creates and connects virtual machines in private networks.
    That's all there is to it."

    section_2_header="Lightweight"
    section_2_content="No framework or extra infrastructure necessary.  The
    library and command line interface interact directly with the cloud
    provider."

    section_3_header="Flexible"
    section_3_content="Cloudless has no opinions on what you install on your
    servers, so you can use any configuration management tool you choose, or
    just use Cloudless on its own."

    section_4_header="Portable"
    section_4_content="Because instance types, feature names, and cloud-specific
    property names are all abstracted away, any infrastructure built using
    Cloudless works across all supported providers." %}

Check out the [Blog](/blog) to learn more about Cloudless and how to use it, or
just go straight to the [Docs]({{ site.docs_url }}) and [Github
Repo](https://github.com/{{ site.github_username }}) to get started!

## Who Is Cloudless

{% include bio-picture.html file="/assets/images/sverch.jpg" alt="sverch in san francisco bio picture" %}

**Shaun Verch (Founder)**

Hi, I'm [@sverch](https://github.com/sverch)!  I'm a Site Reliability Engineer
who has built cloud infrastructure in a wide range of organizations: from a 15
person startup to the world's largest employer.  I started Cloudless in 2018 to
make it harder for humans to make harmful mistakes in software.  I'm passionate
about open source and about making it easier for people to develop robust, cloud
agnostic infrastructure solutions.

{% include bio-picture.html
   file="/assets/images/sswanke-cropped.jpg"
   alt="Sarah Swanke by the ocean bio picture" %}

**Sarah Swanke (Advisor)**

Hi, I'm [@jankyswanky](https://github.com/jankyswanky)!  I'm a Product Manager
and data nerd who's launched 3 successful products from the ground up, which are
used by ~6.75 million people. I'm good with data, teasing out user problems, and
asking lots of questions. I joined Cloudless because I have a passion for open
source and making it easier for people to build things that help other people.

{% include bio-picture.html
   file="/assets/images/jisaacso.jpg"
   alt="Joe Isaacson headshot picture" %}

**Joe Isaacson (Advisor)**

Hi, I'm [@jisaacso](https://github.com/jisaacso)!  I'm the VP of Engineering at
Asimov, a startup in Cambridge, MA that programs living cells to develop
previously impossible biotechnologies.  Prior to Asimov, I managed machine
learning teams at Quora and at URX (acquired by Pinterest).
