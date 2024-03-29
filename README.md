# ATST

[![Build Status](https://circleci.com/gh/dod-ccpo/atst.svg?style=svg)](https://circleci.com/gh/dod-ccpo/atst)

## Description

This is the user-facing web application for ATAT.

## Installation

### System Requirements
ATST uses the [Scripts to Rule Them All](https://github.com/github/scripts-to-rule-them-all)
pattern for setting up and running the project. The scripts are located in the
`script` directory and use script fragments in the
[scriptz](https://github.com/dod-ccpo/scriptz) repository that are shared across
ATAT repositories.

Before running the setup scripts, a couple of dependencies need to be installed
locally:

* `python` == 3.7.3
  Python version 3.7.3 **must** be installed on your machine before installing `pipenv`.
  You can download Python 3.7.3 [from python.org](https://www.python.org/downloads/)
  or use your preferred system package manager. Multiple versions of Python can exist on one
  computer, but 3.7.3 is required for ATAT.

* `pipenv`
  ATST requires `pipenv` to be installed for python dependency management. `pipenv`
  will create the virtual environment that the app requires. [See
  `pipenv`'s documentation for instructions on installing `pipenv`](
  https://pipenv.readthedocs.io/en/latest/install/#installing-pipenv).

* `yarn`
  ATST requires `yarn` for installing and managing Javascript
  dependencies: https://yarnpkg.com/en/

* `postgres` >= 9.6
  ATST requires a PostgreSQL instance (>= 9.6) for persistence. Have PostgresSQL installed
  and running on the default port of 5432. (A good resource for installing and running
  PostgreSQL for Macs is [Postgres.app](https://postgresapp.com/). Follow the instructions,
  including the optional Step 3, and add `/Applications/Postgres.app/Contents/Versions/latest/bin`
  to your `PATH` environment variable.) You can verify that PostgresSQL is running
  by executing `psql` and ensuring that a connection is successfully made.

* `redis`
  ATST also requires a Redis instance for session management. Have Redis installed and
  running on the default port of 6379. You can ensure that Redis is running by
  executing `redis-cli` with no options and ensuring a connection is succesfully made.

* [`entr`](http://eradman.com/entrproject/)
  This dependency is optional. If present, the queue worker process will hot
  reload in development.

### Cloning
This project contains git submodules. Here is an example clone command that will
automatically initialize and update those modules:

    git clone --recurse-submodules git@github.com:dod-ccpo/atst.git

If you have an existing clone that does not yet contain the submodules, you can
set them up with the following command:

    git submodule update --init --recursive

### Setup
This application uses Pipenv to manage Python dependencies and a virtual
environment. Instead of the classic `requirements.txt` file, pipenv uses a
Pipfile and Pipfile.lock, making it more similar to other modern package managers
like yarn or mix.

To perform the installation, run the setup script:

    script/setup

The setup script creates the virtual environment, and then calls script/bootstrap
to install all of the Python and Node dependencies and run database migrations.

To enter the virtualenv manually (a la `source .venv/bin/activate`):

    pipenv shell

If you want to automatically load the virtual environment whenever you enter the
project directory, take a look at [direnv](https://direnv.net/).  An `.envrc`
file is included in this repository.  direnv will activate and deactivate
virtualenvs for you when you enter and leave the directory.

### Troubleshooting Setup

If you have a new postgres installation you might encounter
errors about the `postgres` role not existing. If so, run:

```
createuser -s postgres
```

If `script/setup` complains that the database does not exist,
run:

```
createdb atat
```

## Running (development)

To start the app locally in the foreground and watch for changes:

    script/server

After running `script/server`, the application is available at
[`http://localhost:8000`](http://localhost:8000).


### Users

There are currently six mock users for development:

- Sam (a CCPO)
- Amanda
- Brandon
- Christina
- Dominick
- Erica

To log in as one of them, navigate to `/login-dev?username=<lowercase name>`.
For example `/login-dev?username=amanda`.

In development mode, there is a `DEV Login` button available on the home page
that will automatically log you in as Amanda.

Additionally, this endpoint can be used to log into any real users in the dev environments by providing their DoD ID:
`/login-dev?dod_id=1234567890123`

When in development mode, you can create new users by passing first name, last name, and DoD ID query parameters to `/dev-new-user` like so:
```
/dev-new-user?first_name=Harrold&last_name=Henderson&dod_id=1234567890123
```
And it will create the new user, sign in as them, and load their profile page to fill out the rest of the details.

Once this user is created, you can log in as them again the future using the DoD ID dev login endpoint documented above.

### Seeding the database

We have a helper script that will seed the database with requests, portfolios and
applications for all of the test users:

`pipenv run python script/seed_sample.py`

### Email Notifications

To send email, the following configuration values must be set:

```
MAIL_SERVER = <SMTP server URL>
MAIL_PORT = <SMTP server port>
MAIL_SENDER = <Login name for the email account and sender address>
MAIL_PASSWORD = <login password for the email account>
MAIL_TLS = <Boolean, whether TLS should be enabled for outgoing email. Defaults to false.>
```

When the `DEBUG` environment variable is enabled and the app environment is not
set to production, sent email messages are available at the `/messages` endpoint.
Emails are not sent in development and test modes.

### File Uploads and Downloads

Testing file uploads and downloads locally requires a few configuration options.

In the flask config (`config/base.ini`, perhaps):

```
CSP=<aws | azure | mock>

AWS_REGION_NAME=""
AWS_ACCESS_KEY=""
AWS_SECRET_KEY=""
AWS_BUCKET_NAME=""

AZURE_STORAGE_KEY=""
AZURE_ACCOUNT_NAME=""
AZURE_TO_BUCKET_NAME=""
```

There are also some build-time configuration that are used by parcel. Add these to `.env.local`, and run `rm -r .cache/` before running `yarn build`:

```
CLOUD_PROVIDER=<aws | azure | mock>
AZURE_ACCOUNT_NAME=""
AZURE_CONTAINER_NAME=""
```

## Testing

Tests require a test database:

```
createdb atat_test
```

To run lint, static analysis, and Python unit tests:

    script/test

To run only the Python unit tests:

    pipenv run python -m pytest

To re-run Python tests each time a file is changed:

    pipenv run ptw

This project also runs Javascript tests using jest. To run the Javascript tests:

    yarn test

To re-run the Javascript tests each time a file is changed:

    yarn test:watch

To generate coverage reports for the Javascript tests:

    yarn test:coverage

### Ghost Inspector Tests

AT-AT uses [Ghost Inpsector](https://app.ghostinspector.com/) for
integration testing. These tests do not run locally as part of the
regular test suite but do run in CI. To run them locally, you will
need the following:

- [docker](https://docs.docker.com/v17.12/install/)
- [circleci CLI tool](https://circleci.com/docs/2.0/local-cli/#installation)
- the prerequisite variable information listed [here](https://ghostinspector.com/docs/integration/circle-ci/)

The version of our CircleCI config (2.1) is incompatible with the
`circleci` tool. First run:

```
circleci config process .circleci/config.yml > local-ci.yml
```

Then run the job:

```
circleci local execute -e GI_SUITE=<SUITE_ID> -e GI_API_KEY=<API KEY> -e NGROK_TOKEN=<NGROK TOKEN> --job integration-tests -c local-ci.yml
```

If the job fails and you want to re-run it, you may receive errors
about running docker containers or the network already existing.
Some version of the following should reset your local docker state:

```
docker container stop redis postgres test-atat; docker container rm redis postgres test-atat ; docker network rm atat
```

## Notes

Jinja templates are like mustache templates -- add the
following to `~/.vim/filetype.vim` for syntax highlighting:

    :au BufRead *.html.to set filetype=mustache


## Icons
To render an icon, use

```jinja
{% import "components/icon.html" %}
{{ Icon("icon-name", classes="css-classes") }}
```

where `icon-name` is the filename of an svg in `static/icons`.

All icons used should be from the Noun Project, specifically [this collection](https://thenounproject.com/monstercritic/collection/tinicons-a-set-of-tiny-icons-perfect-for-ui-elemen/) if possible.

SVG markup should be cleaned an minified, [Svgsus](http://www.svgs.us/) works well.

## Deployment

### Docker build

For testing the Docker build, the repo includes a `docker-compose.yml` that will run the app container with an NGINX server in front of it. To run it, you will need `docker` and `docker-compose` installed, then:

```
docker-compose up
```

The app will be available on http://localhost:8080.

The build assumes that you have redis and postgres running on their usual ports on your host machine; it does not pull images for those services. The docker-compose build is not suitable for development because it does not mount or reload working files.

### Dev login

The `/login-dev` endpoint is protected by HTTP basic auth when deployed. This can be configured for NGINX following the instructions [here](https://docs.nginx.com/nginx/admin-guide/security-controls/configuring-http-basic-authentication/). The following config should added within the main server block for the site:

```nginx
location /login-dev {
    auth_basic "Developer Access";
    auth_basic_user_file /etc/apache2/.htpasswd;
    [proxy information should follow this]
}
```

The location block will require the same proxy pass configuration as other location blocks for the app.

## Secrets Detection

This project uses [detect-secrets](https://github.com/Yelp/detect-secrets) to help prevent secrets from being checked into source control. Secret detection is run automatically as part of `script/test` and can be run separately with `script/detect_secrets`.

If you need to check in a file that raises false positives from `detect-secrets`, you can add it to the whitelist. Run:

```
pipenv run detect-secrets scan --no-aws-key-scan --no-stripe-scan --no-slack-scan --no-artifactory-scan --update .secrets.baseline
```

and then:

```
pipenv run detect-secrets audit .secrets.baseline
```

The audit will open an interactive prompt where you can whitelist the file. This is useful if you're checking in an entire file that looks like or is a secret (like a sample PKI file).

Alternatively, you can add a `# pragma: allowlist secret` comment to the line that raised the false positive. See the [detect-secret](https://github.com/Yelp/detect-secrets#inline-allowlisting) docs for more information.

It's recommended that you add a pre-commit hook to invoke `script/detect_secrets`. Add the example below or something equivalent to `.git/hooks/pre-commit`:

```
#!/usr/bin/env bash

if ./script/detect_secrets staged; then
  echo "secrets check passed"
else
  echo -e "**SECRETS DETECTED**"
  exit 1
fi
```

Also note that if the line number of a previously whitelisted secret changes, the whitelist file, `.secrets.baseline`, will be updated and needs to be committed.

## Local Kubernetes Setup

A modified version of the Kubernetes cluster can be deployed locally for
testing and development purposes.

It is strongly recommended that you backup your local K8s config (usually
`~/.kube/config`) before launching Minikube for the first time.

Before beginning:

- install the [Docker CLI](https://docs.docker.com/v17.12/install/)
- install [Minikube](https://kubernetes.io/docs/tasks/tools/install-minikube/)
  (this will also require installing a Hypervisor, such as VirtualBox)

### Setup

Run

```
script/minikube_setup
```

Once the script exits successfully, run

```
minikube service list
```

### Access the site

One of the two URLs given for the `atat-auth` service will load an HTTP version
of the application.

For HTTP basic auth, the username and password are both `minikube`.

### Differences from the main config

As of the time of writing, this setup does not include the following:

- SSL/TLS or the complete DoD PKI
- the cronjob for syncing CRLs and the peristent storage
- production configuration

In order for the application to run, the K8s config for Minikube includes an
additional deployment resource called `datastores`. This includes Postgres
and Redis containers. It also includes hard-coded versions of the K8s secrets
used in the regular clusters.
