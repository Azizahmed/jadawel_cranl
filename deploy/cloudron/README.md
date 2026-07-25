# Jadawel's Cloudron image 

This is the Jadawel maintained [Cloudron Image](https://cloudron.io).

Please see the [Cloudron manifest](./CloudronManifest.json) and [Dockerfile](./Dockerfile)
guide for more details.

## About Jadawel

* A spreadsheet database hybrid combining ease of use and powerful data organization.
* Easily self-hosted with no storage restrictions.
* Alternative to Airtable.
* Open-core with all non-premium and non-enterprise features under
  the [MIT License](https://choosealicense.com/licenses/mit/) allowing commercial and
  private use.
* Headless and API first.
* Uses popular frameworks and tools like [Django](https://www.djangoproject.com/),
  [Vue.js](https://vuejs.org/) and [PostgreSQL](https://www.postgresql.org/).

## Quick Reference

* **Source Code Available At**: [github.com/Azizahmed/Jadawel](https://github.com/Azizahmed/Jadawel)
* **Docs At**: [`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md)
* **License**: Open-Core with all non-premium and non-enterprise code under the MIT 
  license.

## Supported tags and Dockerfile Links

* [`X.Y.Z`](./Dockerfile) Tagged by Jadawel version.
* [`latest`](./Dockerfile)

## Application builder domains

Jadawel has an application builder that allows to deploy an application to a specific
domain. Because Cloudron has a reverse proxy that routes a domain to the right Cloudron
app, the deployed application isn't automatically available on the chosen domain.

To make this work, you must add a domain alias in the Cloudron settings. This can be
done by going to the settings of your Jadawel app, then click on `Location`, click on
`Add an alias`, and then add the domain you've published the application to in Jadawel.
Make sure that the alias matches the full domain name in Jadawel. After that, Cloudron
will request the SSL certificate, and then you can visit your domain.

It's also possible to add a wildcard alias to Cloudron, but the SSL certificate then
doesn't work out of the box. Some additional settings on Cloudron might be required to
make it work.
